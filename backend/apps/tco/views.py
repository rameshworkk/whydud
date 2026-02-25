"""TCO views — model lookup, calculate, compare, profile, cities."""
import ast
import logging
import operator
from decimal import Decimal, InvalidOperation
from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from apps.products.models import Category, Product
from .models import CityReferenceData, TCOModel, UserTCOProfile
from .serializers import (
    CitySerializer,
    TCOCalculateSerializer,
    TCOModelSerializer,
    UserTCOProfileSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe formula evaluator (ast-based — never uses eval())
# ---------------------------------------------------------------------------

_SAFE_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_SAFE_UNARY_OPS: dict[type, Any] = {
    ast.USub: operator.neg,
}

_SAFE_FUNCTIONS = frozenset({"min", "max"})


def _eval_node(node: ast.AST, variables: dict[str, float]) -> float:
    """Recursively evaluate an AST node with variable substitution."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.Name):
        return variables.get(node.id, 0.0)

    if isinstance(node, ast.BinOp):
        op_fn = _SAFE_BIN_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Div) and right == 0:
            return 0.0
        return op_fn(left, right)

    if isinstance(node, ast.UnaryOp):
        op_fn = _SAFE_UNARY_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op_fn(_eval_node(node.operand, variables))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn_name = node.func.id
        if fn_name in _SAFE_FUNCTIONS:
            args = [_eval_node(a, variables) for a in node.args]
            if not args:
                return 0.0
            return min(args) if fn_name == "min" else max(args)
        raise ValueError(f"Unsupported function: {fn_name}")

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def safe_eval_formula(formula: str, variables: dict[str, float]) -> float:
    """Safely evaluate an arithmetic formula with variable substitution.

    Supports: numbers, named variables, ``+  -  *  /``, unary ``-``,
    parentheses, ``min()`` and ``max()``.
    """
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula: {formula!r}") from exc
    return _eval_node(tree.body, variables)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_variables(
    tco_model: TCOModel,
    product: Product,
    user_inputs: dict[str, Any],
    city_id: int | None,
    electricity_tariff: Decimal | None,
    ownership_years: int,
) -> dict[str, float]:
    """Build the variable dict used by formula evaluation.

    Priority (lowest -> highest):
      1. input_schema defaults
      2. Product specs (product.specs JSONB)
      3. Product current_best_price -> ``purchase_price``
      4. City reference data
      5. Explicit overrides (electricity_tariff, ownership_years)
      6. User-provided inputs dict
    """
    variables: dict[str, float] = {}

    # 1. Defaults from input_schema
    input_schema = tco_model.input_schema or {}
    for field in input_schema.get("inputs", []):
        key = field.get("key")
        default = field.get("default_value")
        if key and default is not None:
            try:
                variables[key] = float(default)
            except (ValueError, TypeError):
                pass

    # 2. Auto-fill from product specs
    specs = product.specs or {}
    for k, v in specs.items():
        if isinstance(v, (int, float)):
            variables[k] = float(v)
        elif isinstance(v, str):
            try:
                variables[k] = float(v)
            except ValueError:
                pass

    # 3. Product price
    if product.current_best_price is not None:
        variables["purchase_price"] = float(product.current_best_price)

    # 4. City reference data
    if city_id is not None:
        try:
            city = CityReferenceData.objects.get(id=city_id)
            if city.electricity_tariff_residential is not None:
                variables["electricity_tariff"] = float(
                    city.electricity_tariff_residential
                )
            if city.cooling_days_per_year is not None:
                variables["cooling_days_per_year"] = float(
                    city.cooling_days_per_year
                )
            if city.water_tariff_per_kl is not None:
                variables["water_tariff_per_kl"] = float(city.water_tariff_per_kl)
        except CityReferenceData.DoesNotExist:
            pass

    # 5. Explicit overrides
    if electricity_tariff is not None:
        variables["electricity_tariff"] = float(electricity_tariff)
    variables["ownership_years"] = float(ownership_years)

    # 6. User-provided inputs (highest priority)
    for k, v in user_inputs.items():
        if v is not None:
            try:
                variables[k] = float(v)
            except (ValueError, TypeError):
                pass

    return variables


def _evaluate_tco(
    cost_components: dict, variables: dict[str, float]
) -> dict[str, Any]:
    """Evaluate all cost component formulas and return the TCO breakdown.

    ``cost_components`` is expected to have keys:
      purchase, ongoing_annual, one_time_risk, resale
    Each key maps to ``{"label": str, "components": [{"name", "label", "formula"}]}``.

    Returns::

        {
            "total": float,
            "per_year": float,
            "per_month": float,
            "ownership_years": int,
            "breakdown": {
                "purchase":        {"label", "total", "components": [...]},
                "ongoing_annual":  {"label", "total", "components": [...]},
                "one_time_risk":   {"label", "total", "components": [...]},
                "resale":          {"label", "total", "components": [...]},
            }
        }
    """
    ownership_years = variables.get("ownership_years", 5.0)

    breakdown: dict[str, Any] = {}
    for group_key in ("purchase", "ongoing_annual", "one_time_risk", "resale"):
        group = cost_components.get(group_key, {})
        components = group.get("components", [])
        group_total = 0.0
        component_details: list[dict] = []

        for comp in components:
            formula = comp.get("formula", "0")
            try:
                value = safe_eval_formula(formula, variables)
            except ValueError as exc:
                logger.warning(
                    "TCO formula error in %s.%s: %s",
                    group_key,
                    comp.get("name"),
                    exc,
                )
                value = 0.0

            value = round(value, 2)
            group_total += value
            component_details.append(
                {
                    "name": comp.get("name", ""),
                    "label": comp.get("label", ""),
                    "value": value,
                }
            )

        breakdown[group_key] = {
            "label": group.get("label", group_key),
            "total": round(group_total, 2),
            "components": component_details,
        }

    purchase = breakdown["purchase"]["total"]
    ongoing_annual = breakdown["ongoing_annual"]["total"]
    one_time_risk = breakdown["one_time_risk"]["total"]
    resale = breakdown["resale"]["total"]

    total = purchase + (ongoing_annual * ownership_years) + one_time_risk + resale
    per_year = total / ownership_years if ownership_years > 0 else 0.0
    per_month = per_year / 12.0

    return {
        "total": round(total, 2),
        "per_year": round(per_year, 2),
        "per_month": round(per_month, 2),
        "ownership_years": int(ownership_years),
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class CityListView(APIView):
    """GET /api/v1/tco/cities — list Indian cities with tariff data."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        state = request.query_params.get("state")
        qs = CityReferenceData.objects.order_by("state", "city_name")
        if state:
            qs = qs.filter(state__icontains=state)
        return success_response(CitySerializer(qs, many=True).data)


class TCOModelView(APIView):
    """GET /api/v1/tco/models/:category_slug — returns model + input_schema."""

    permission_classes = [AllowAny]

    def get(self, request: Request, category_slug: str) -> Response:
        category = get_object_or_404(
            Category, slug=category_slug, has_tco_model=True
        )
        tco_model = (
            TCOModel.objects.filter(category=category, is_active=True)
            .order_by("-version")
            .first()
        )
        if not tco_model:
            return error_response(
                "not_found",
                "No active TCO model for this category.",
                status=404,
            )
        return success_response(TCOModelSerializer(tco_model).data)


class TCOCalculateView(APIView):
    """POST /api/v1/tco/calculate — evaluate cost formula, return breakdown."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = TCOCalculateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        data = serializer.validated_data

        product = (
            Product.objects.filter(
                slug=data["product_slug"], status=Product.Status.ACTIVE
            )
            .select_related("category", "brand")
            .first()
        )
        if not product:
            return error_response("not_found", "Product not found.", status=404)

        if not product.category or not product.category.has_tco_model:
            return error_response(
                "not_available",
                "TCO calculation is not available for this product's category.",
                status=404,
            )

        tco_model = (
            TCOModel.objects.filter(category=product.category, is_active=True)
            .order_by("-version")
            .first()
        )
        if not tco_model:
            return error_response(
                "not_found",
                "No active TCO model for this category.",
                status=404,
            )

        # Merge convenience fields into inputs dict
        inputs = dict(data.get("inputs", {}))
        if data.get("ac_hours_per_day") is not None:
            inputs.setdefault("ac_hours_per_day", data["ac_hours_per_day"])

        variables = _build_variables(
            tco_model=tco_model,
            product=product,
            user_inputs=inputs,
            city_id=data.get("city_id"),
            electricity_tariff=data.get("electricity_tariff"),
            ownership_years=data.get("ownership_years", 5),
        )

        try:
            result = _evaluate_tco(tco_model.cost_components, variables)
        except ValueError as exc:
            return error_response("calculation_error", str(exc))

        result["product"] = {
            "slug": product.slug,
            "title": product.title,
            "brand": product.brand.name if product.brand else None,
        }
        result["tco_model"] = {
            "name": tco_model.name,
            "version": tco_model.version,
            "category_slug": product.category.slug,
        }

        return success_response(result)


class TCOCompareView(APIView):
    """GET /api/v1/tco/compare?products=slug1,slug2,slug3 — side-by-side TCO."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        products_param = request.query_params.get("products", "")
        slugs = [s.strip() for s in products_param.split(",") if s.strip()]

        if len(slugs) < 2:
            return error_response(
                "validation_error",
                "Provide at least 2 product slugs (comma-separated).",
            )
        if len(slugs) > 3:
            return error_response(
                "validation_error",
                "Maximum 3 products for TCO comparison.",
            )

        # Shared params
        try:
            ownership_years = int(
                request.query_params.get("ownership_years", 5)
            )
            ownership_years = max(1, min(ownership_years, 20))
        except (ValueError, TypeError):
            ownership_years = 5

        city_id = _parse_int(request.query_params.get("city_id"))
        electricity_tariff = _parse_decimal(
            request.query_params.get("electricity_tariff")
        )

        # Batch-fetch products
        products = Product.objects.filter(
            slug__in=slugs, status=Product.Status.ACTIVE
        ).select_related("category", "brand")
        product_map = {p.slug: p for p in products}

        comparisons: list[dict] = []
        for slug in slugs:
            product = product_map.get(slug)
            if not product:
                comparisons.append({"slug": slug, "error": "Product not found."})
                continue

            if not product.category or not product.category.has_tco_model:
                comparisons.append(
                    {
                        "slug": slug,
                        "error": "TCO not available for this category.",
                    }
                )
                continue

            tco_model = (
                TCOModel.objects.filter(
                    category=product.category, is_active=True
                )
                .order_by("-version")
                .first()
            )
            if not tco_model:
                comparisons.append(
                    {"slug": slug, "error": "No active TCO model."}
                )
                continue

            variables = _build_variables(
                tco_model=tco_model,
                product=product,
                user_inputs={},
                city_id=city_id,
                electricity_tariff=electricity_tariff,
                ownership_years=ownership_years,
            )

            try:
                tco_result = _evaluate_tco(tco_model.cost_components, variables)
            except ValueError as exc:
                comparisons.append({"slug": slug, "error": str(exc)})
                continue

            images = product.images or []
            comparisons.append(
                {
                    "product": {
                        "slug": product.slug,
                        "title": product.title,
                        "brand": product.brand.name if product.brand else None,
                        "current_best_price": (
                            str(product.current_best_price)
                            if product.current_best_price
                            else None
                        ),
                        "image": images[0] if images else None,
                    },
                    "tco": tco_result,
                }
            )

        return success_response({"comparisons": comparisons})


class TCOProfileView(APIView):
    """GET / PATCH /api/v1/tco/profile — user's saved TCO defaults."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile, _ = UserTCOProfile.objects.get_or_create(user=request.user)
        return success_response(UserTCOProfileSerializer(profile).data)

    def patch(self, request: Request) -> Response:
        profile, _ = UserTCOProfile.objects.get_or_create(user=request.user)
        serializer = UserTCOProfileSerializer(
            profile, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)


# ---------------------------------------------------------------------------
# Tiny parsing helpers
# ---------------------------------------------------------------------------

def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return None

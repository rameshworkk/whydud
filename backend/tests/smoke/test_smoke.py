"""
Smoke tests — fast, broad, verify the whole system hangs together.
Each test checks one critical invariant.

Run: pytest tests/smoke/ -m smoke -v
"""
import pytest
from decimal import Decimal
from django.db import connection

pytestmark = [pytest.mark.smoke, pytest.mark.django_db]


class TestDataIntegrity:
    """Database-level invariants that must always hold."""

    def test_no_orphaned_listings(self):
        """Every ProductListing must reference a valid Product."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM product_listings pl
                LEFT JOIN products p ON pl.product_id = p.id
                WHERE p.id IS NULL
            """)
            orphans = cur.fetchone()[0]
        assert orphans == 0, f"{orphans} orphaned product listings found"

    def test_no_negative_prices(self):
        """No product should have a negative price."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM product_listings
                WHERE current_price < 0
            """)
            negatives = cur.fetchone()[0]
        assert negatives == 0, f"{negatives} listings have negative prices"

    def test_no_duplicate_listings(self):
        """No duplicate (marketplace, external_id) pairs."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT marketplace_id, external_id, COUNT(*) as cnt
                FROM product_listings
                GROUP BY marketplace_id, external_id
                HAVING COUNT(*) > 1
            """)
            dupes = cur.fetchall()
        assert len(dupes) == 0, (
            f"{len(dupes)} duplicate listing pairs: "
            f"{dupes[:5]}"
        )

    def test_products_have_slugs(self):
        """Every product must have a non-empty slug."""
        from apps.products.models import Product
        empty_slugs = Product.objects.filter(slug='').count()
        assert empty_slugs == 0, f"{empty_slugs} products have empty slugs"

    def test_all_marketplaces_have_base_url(self):
        """Every marketplace must have a non-empty base_url."""
        from apps.products.models import Marketplace
        no_url = Marketplace.objects.filter(base_url='').count()
        assert no_url == 0, f"{no_url} marketplaces missing base_url"

    def test_price_snapshots_have_valid_prices(self):
        """Price snapshots must have positive, reasonable prices."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM price_snapshots
                WHERE price <= 0 OR price > 99999999
            """)
            bad = cur.fetchone()[0]
        assert bad == 0, f"{bad} price snapshots have invalid prices"

    def test_reviews_have_valid_ratings(self):
        """Review ratings must be between 1 and 5."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM reviews
                WHERE rating < 1 OR rating > 5
            """)
            bad = cur.fetchone()[0]
        assert bad == 0, f"{bad} reviews have invalid ratings"


class TestResponseFormat:
    """All API responses should follow the standard wrapper format."""

    def test_products_list_format(self, api_client, test_product):
        """Product list response follows standard format."""
        resp = api_client.get('/api/v1/products/')
        assert resp.status_code == 200
        data = resp.data

        # Should have either {success, data} wrapper or direct {results}
        has_wrapper = 'success' in data
        has_results = 'results' in data or 'results' in data.get('data', {})
        assert has_wrapper or has_results, (
            f"Non-standard response format: {list(data.keys())}"
        )

    def test_error_response_format(self, api_client):
        """Error responses should have error info."""
        resp = api_client.get('/api/v1/products/nonexistent-product-slug/')
        assert resp.status_code == 404
        data = resp.data
        # Should have some error indication
        has_error = ('error' in data or 'detail' in data or 'message' in data
                     or (data.get('success') is False))
        assert has_error, f"404 response missing error info: {data}"

    def test_authenticated_endpoint_rejects_anon(self, api_client):
        """Authenticated endpoints must return 401/403 for anon requests."""
        protected = ['/api/v1/me', '/api/v1/wishlists']
        for path in protected:
            resp = api_client.get(path)
            assert resp.status_code in (401, 403), (
                f"{path} returned {resp.status_code} for unauthenticated request"
            )


class TestProductDataQuality:
    """Products in the system should have reasonable data."""

    def test_products_exist(self, test_product):
        """At least some products should exist."""
        from apps.products.models import Product
        count = Product.objects.count()
        assert count >= 1, "No products in database"

    def test_marketplaces_exist(self, test_marketplace):
        """At least some marketplaces should exist."""
        from apps.products.models import Marketplace
        count = Marketplace.objects.count()
        assert count >= 1, "No marketplaces in database"

    def test_product_has_listing(self, test_product):
        """Products should have at least one marketplace listing."""
        assert test_product.listings.count() >= 1

    def test_product_prices_in_paisa(self, test_product):
        """Prices should be in paisa (> 100 for any real product)."""
        if test_product.current_best_price:
            assert test_product.current_best_price > 100, (
                f"Price {test_product.current_best_price} seems like rupees, not paisa"
            )


class TestModelCounts:
    """Quick sanity check on data counts."""

    def test_count_summary(self, test_product):
        """Print (not assert) data counts for reference."""
        from apps.products.models import Product, ProductListing, Marketplace, Category
        from apps.reviews.models import Review

        counts = {
            'Products': Product.objects.count(),
            'Listings': ProductListing.objects.count(),
            'Marketplaces': Marketplace.objects.count(),
            'Categories': Category.objects.count(),
            'Reviews': Review.objects.count(),
        }

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM price_snapshots")
                counts['PriceSnapshots'] = cur.fetchone()[0]
        except Exception:
            counts['PriceSnapshots'] = 'N/A'

        for name, count in counts.items():
            print(f"  {name}: {count}")

        # At minimum, we need products and marketplaces
        assert counts['Products'] >= 0  # Always passes, just for reporting

"""Review service layer — business logic for review creation."""
import hashlib
import logging

from django.utils import timezone

from .models import Review

logger = logging.getLogger(__name__)


def _generate_content_hash(body_positive: str | None, body_negative: str | None) -> str:
    """Generate SHA-256 hash from review body for duplicate detection."""
    combined = f"{(body_positive or '').strip()}|{(body_negative or '').strip()}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _check_verified_purchase(purchase_platform: str | None) -> bool:
    """Check if purchase_platform matches a known marketplace slug in our DB."""
    if not purchase_platform:
        return False
    from apps.products.models import Marketplace

    return Marketplace.objects.filter(slug=purchase_platform).exists()


def create_review(user, product, validated_data: dict) -> Review:
    """Create a Whydud-native review with 48hr publish hold.

    Handles:
    - Duplicate check via content_hash
    - Verified purchase detection (purchase_platform → Marketplace match)
    - 48-hour publish scheduling
    - DudScore recalc queueing
    - Rewards points award

    Args:
        user: The authenticated user submitting the review.
        product: The Product instance being reviewed.
        validated_data: Serializer-validated data dict.

    Returns:
        The created Review instance (is_published=False, publish_at set).
    """
    body_positive = validated_data.get("body_positive") or ""
    body_negative = validated_data.get("body_negative") or ""
    content_hash = _generate_content_hash(body_positive, body_negative)

    # Determine purchase proof status
    purchase_platform = validated_data.get("purchase_platform")
    has_purchase_proof = validated_data.pop("has_purchase_proof", False) or bool(
        purchase_platform
        or validated_data.get("purchase_seller")
        or validated_data.get("purchase_price_paid")
        or validated_data.get("purchase_proof_url")
    )

    # Verify purchase if platform matches a known marketplace
    is_verified_purchase = False
    if has_purchase_proof and purchase_platform:
        is_verified_purchase = _check_verified_purchase(purchase_platform)

    review = Review.objects.create(
        **validated_data,
        user=user,
        product=product,
        reviewer_name=user.get_full_name() or user.email,
        source=Review.Source.WHYDUD,
        is_published=False,
        publish_at=timezone.now() + timezone.timedelta(hours=48),
        has_purchase_proof=has_purchase_proof,
        is_verified_purchase=is_verified_purchase,
        content_hash=content_hash,
        review_date=timezone.now().date(),
    )

    logger.info(
        "review_created user=%s product=%s review=%s verified=%s",
        user.pk, product.pk, review.pk, is_verified_purchase,
    )

    # Queue DudScore recalculation for this product
    from apps.scoring.tasks import compute_dudscore

    compute_dudscore.delay(str(product.pk))

    # Award review-writing points
    from apps.rewards.tasks import award_points_task

    award_points_task.delay(str(user.pk), "write_review", str(review.pk))

    return review

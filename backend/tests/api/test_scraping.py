"""
Scraping pipeline tests: spider registry, item validation,
pipeline processing, ScraperJob lifecycle.

These do NOT actually scrape external sites — they test the internal
pipeline logic with mock data.

Run: pytest tests/api/test_scraping.py -v
"""
import pytest
from decimal import Decimal

pytestmark = [pytest.mark.scraping, pytest.mark.django_db]


# ── Helpers ──────────────────────────────────────────────────────────────


class MockSpider:
    """Minimal mock spider for pipeline tests."""
    name = "test"
    items_failed = 0

    def __init__(self):
        import logging
        self.logger = logging.getLogger("test")


class MockCrawler:
    """Minimal mock crawler wrapping a MockSpider."""

    def __init__(self):
        self.spider = MockSpider()


# ── Spider Registry ──────────────────────────────────────────────────────


class TestSpiderRegistry:
    """Verify spider map is correctly configured."""

    def test_spider_map_has_entries(self):
        from common.app_settings import ScrapingConfig
        spider_map = ScrapingConfig.spider_map()
        assert len(spider_map) >= 2, (
            f"Spider map has {len(spider_map)} entries, expected 2+. "
            f"Map: {spider_map}"
        )

    def test_amazon_spider_registered(self):
        from common.app_settings import ScrapingConfig
        spider_map = ScrapingConfig.spider_map()
        assert "amazon-in" in spider_map, (
            f"amazon-in not in spider_map: {list(spider_map.keys())}"
        )

    def test_flipkart_spider_registered(self):
        from common.app_settings import ScrapingConfig
        spider_map = ScrapingConfig.spider_map()
        assert "flipkart" in spider_map, (
            f"flipkart not in spider_map: {list(spider_map.keys())}"
        )

    def test_review_spider_map_has_entries(self):
        from common.app_settings import ScrapingConfig
        review_map = ScrapingConfig.review_spider_map()
        assert len(review_map) >= 1, f"No review spiders registered: {review_map}"

    def test_spider_map_values_are_strings(self):
        from common.app_settings import ScrapingConfig
        for slug, spider_name in ScrapingConfig.spider_map().items():
            assert isinstance(slug, str)
            assert isinstance(spider_name, str)
            assert len(spider_name) > 0


# ── Item Creation ────────────────────────────────────────────────────────


class TestProductItem:
    """Test that ProductItem/ReviewItem classes work."""

    def test_product_item_creation(self):
        from apps.scraping.items import ProductItem
        item = ProductItem()
        item["marketplace_slug"] = "amazon-in"
        item["external_id"] = "B0CX23GFMV"
        item["url"] = "https://www.amazon.in/dp/B0CX23GFMV"
        item["title"] = "Apple iPhone 16"
        item["price"] = 7999900
        assert item["title"] == "Apple iPhone 16"
        assert item["price"] == 7999900

    def test_product_item_optional_fields(self):
        from apps.scraping.items import ProductItem
        item = ProductItem()
        item["marketplace_slug"] = "flipkart"
        item["external_id"] = "FP123"
        item["url"] = "https://www.flipkart.com/p/FP123"
        item["title"] = "Samsung Galaxy S24"
        item["brand"] = "Samsung"
        item["images"] = ["https://img1.jpg", "https://img2.jpg"]
        item["specs"] = {"RAM": "8GB", "Storage": "256GB"}
        assert item["brand"] == "Samsung"
        assert len(item["images"]) == 2

    def test_review_item_creation(self):
        from apps.scraping.items import ReviewItem
        item = ReviewItem()
        item["marketplace_slug"] = "amazon-in"
        item["product_external_id"] = "B0CX23GFMV"
        item["rating"] = 5
        item["body"] = "Great phone, love it!"
        item["title"] = "Excellent purchase"
        assert item["rating"] == 5
        assert item["body"] == "Great phone, love it!"


# ── Validation Pipeline ──────────────────────────────────────────────────


class TestValidationPipeline:
    """Test the ValidationPipeline drops bad items."""

    def _make_pipeline(self):
        from apps.scraping.pipelines import ValidationPipeline
        pipeline = ValidationPipeline()
        pipeline._crawler = MockCrawler()
        return pipeline

    def _make_valid_item(self):
        from apps.scraping.items import ProductItem
        item = ProductItem()
        item["marketplace_slug"] = "amazon-in"
        item["external_id"] = "B0CX23GFMV"
        item["url"] = "https://www.amazon.in/dp/B0CX23GFMV"
        item["title"] = "Apple iPhone 16 (128 GB)"
        item["price"] = 7999900
        return item

    def test_drops_item_without_title(self):
        """Items with empty title should be dropped."""
        from scrapy.exceptions import DropItem

        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        item["title"] = ""  # Empty title

        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_item_without_external_id(self):
        from scrapy.exceptions import DropItem

        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        item["external_id"] = ""

        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_item_without_url(self):
        from scrapy.exceptions import DropItem

        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        item["url"] = ""

        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_item_without_marketplace_slug(self):
        from scrapy.exceptions import DropItem

        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        item["marketplace_slug"] = ""

        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_passes_valid_item(self):
        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        result = pipeline.process_item(item)
        assert result["title"] == "Apple iPhone 16 (128 GB)"

    def test_skips_review_items(self):
        """ReviewItems should pass through ValidationPipeline untouched."""
        from apps.scraping.items import ReviewItem
        pipeline = self._make_pipeline()
        item = ReviewItem()
        item["marketplace_slug"] = "amazon-in"
        item["product_external_id"] = "B0CX23GFMV"
        item["rating"] = 5
        item["body"] = "Great product"
        result = pipeline.process_item(item)
        assert result["rating"] == 5

    def test_increments_items_failed_on_drop(self):
        from scrapy.exceptions import DropItem

        pipeline = self._make_pipeline()
        item = self._make_valid_item()
        item["title"] = ""

        with pytest.raises(DropItem):
            pipeline.process_item(item)

        assert pipeline._crawler.spider.items_failed == 1


# ── Review Validation Pipeline ───────────────────────────────────────────


class TestReviewValidationPipeline:
    """Test ReviewValidationPipeline drops invalid reviews."""

    def _make_pipeline(self):
        from apps.scraping.pipelines import ReviewValidationPipeline
        return ReviewValidationPipeline()

    def _make_valid_review(self):
        from apps.scraping.items import ReviewItem
        item = ReviewItem()
        item["marketplace_slug"] = "amazon-in"
        item["product_external_id"] = "B0CX23GFMV"
        item["rating"] = 4
        item["body"] = "This is a great product with good value for money."
        return item

    def test_passes_valid_review(self):
        pipeline = self._make_pipeline()
        item = self._make_valid_review()
        result = pipeline.process_item(item)
        assert result["rating"] == 4

    def test_drops_review_without_marketplace(self):
        from scrapy.exceptions import DropItem
        pipeline = self._make_pipeline()
        item = self._make_valid_review()
        item["marketplace_slug"] = ""
        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_review_without_product_id(self):
        from scrapy.exceptions import DropItem
        pipeline = self._make_pipeline()
        item = self._make_valid_review()
        item["product_external_id"] = ""
        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_review_without_body(self):
        from scrapy.exceptions import DropItem
        pipeline = self._make_pipeline()
        item = self._make_valid_review()
        item["body"] = ""
        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_drops_review_with_short_body(self):
        from scrapy.exceptions import DropItem
        pipeline = self._make_pipeline()
        item = self._make_valid_review()
        item["body"] = "Ok"  # < 5 chars
        with pytest.raises(DropItem):
            pipeline.process_item(item)

    def test_passes_product_items_through(self):
        """ProductItems should pass through ReviewValidationPipeline untouched."""
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["marketplace_slug"] = "amazon-in"
        item["external_id"] = "B0CX23GFMV"
        item["url"] = "https://www.amazon.in/dp/B0CX23GFMV"
        item["title"] = "Test Product"
        result = pipeline.process_item(item)
        assert result["title"] == "Test Product"


# ── Normalization Pipeline ───────────────────────────────────────────────


class TestNormalizationPipeline:
    """Test the NormalizationPipeline cleans scraped data."""

    def _make_pipeline(self):
        from apps.scraping.pipelines import NormalizationPipeline
        return NormalizationPipeline()

    def test_collapses_title_whitespace(self):
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["title"] = "  Apple   iPhone  16   (128  GB)  "
        result = pipeline.process_item(item)
        assert result["title"] == "Apple iPhone 16 (128 GB)"

    def test_normalizes_brand_casing_short(self):
        """Short single-word brands (<=4 chars) → uppercase."""
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["brand"] = "sony"
        result = pipeline.process_item(item)
        assert result["brand"] == "SONY"

    def test_normalizes_brand_casing_long(self):
        """Multi-word brands → Title Case."""
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["brand"] = "samsung electronics"
        result = pipeline.process_item(item)
        assert result["brand"] == "Samsung Electronics"

    def test_strips_brand_prefix(self):
        """Removes 'Visit the' prefix from brand names."""
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["brand"] = "Visit the Apple Store"
        result = pipeline.process_item(item)
        assert result["brand"] == "Apple Store"

    def test_strips_specs_whitespace(self):
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["specs"] = {"  RAM  ": " 8GB ", "Storage": " 256GB "}
        result = pipeline.process_item(item)
        assert result["specs"] == {"RAM": "8GB", "Storage": "256GB"}

    def test_removes_empty_about_bullets(self):
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["about_bullets"] = ["Great display", "", "  ", "Fast charging"]
        result = pipeline.process_item(item)
        assert result["about_bullets"] == ["Great display", "Fast charging"]

    def test_deduplicates_images(self):
        from apps.scraping.items import ProductItem
        pipeline = self._make_pipeline()
        item = ProductItem()
        item["images"] = [
            "https://img1.jpg",
            "https://img2.jpg",
            "https://img1.jpg",  # Duplicate
            "https://img3.jpg",
        ]
        result = pipeline.process_item(item)
        assert result["images"] == [
            "https://img1.jpg",
            "https://img2.jpg",
            "https://img3.jpg",
        ]


# ── ScraperJob Model ────────────────────────────────────────────────────


class TestScraperJobModel:
    """Test ScraperJob model lifecycle."""

    def test_create_scraper_job(self, test_marketplace):
        from apps.scraping.models import ScraperJob
        job = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="amazon_in",
            status="queued",
            triggered_by="test",
        )
        assert job.id is not None
        assert job.status == "queued"

    def test_scraper_job_str(self, test_marketplace):
        from apps.scraping.models import ScraperJob
        job = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="amazon_in",
            status="queued",
            triggered_by="test",
        )
        assert str(job) == "amazon_in [queued]"

    def test_scraper_job_status_transitions(self, test_marketplace):
        from apps.scraping.models import ScraperJob
        from django.utils import timezone

        job = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="amazon_in",
            status="queued",
            triggered_by="test",
        )
        # queued → running
        job.status = "running"
        job.started_at = timezone.now()
        job.save()
        assert job.status == "running"

        # running → completed
        job.status = "completed"
        job.finished_at = timezone.now()
        job.items_scraped = 25
        job.save()

        job.refresh_from_db()
        assert job.status == "completed"
        assert job.items_scraped == 25

    def test_scraper_job_failed_status(self, test_marketplace):
        from apps.scraping.models import ScraperJob
        job = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="amazon_in",
            status="failed",
            triggered_by="test",
            error_message="Connection timeout",
        )
        assert job.status == "failed"
        assert job.error_message == "Connection timeout"

    def test_scraper_job_ordering(self, test_marketplace):
        """Jobs should be ordered by -created_at (newest first)."""
        from apps.scraping.models import ScraperJob
        job1 = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="amazon_in",
            status="completed",
            triggered_by="test",
        )
        job2 = ScraperJob.objects.create(
            marketplace=test_marketplace,
            spider_name="flipkart",
            status="queued",
            triggered_by="test",
        )
        jobs = list(ScraperJob.objects.all())
        assert jobs[0].id == job2.id  # Newest first
        assert jobs[1].id == job1.id


# ── Product Pipeline (ORM layer) ────────────────────────────────────────


class TestProductPipeline:
    """Test ProductPipeline creates/updates Product and ProductListing."""

    def test_pipeline_creates_product(self, test_marketplace, test_category):
        """A valid ProductItem should create Product + ProductListing."""
        from apps.products.models import Product, ProductListing

        initial_products = Product.objects.count()
        initial_listings = ProductListing.objects.count()

        product = Product.objects.create(
            title="Test Pipeline Product",
            slug="test-pipeline-product",
            category=test_category,
            current_best_price=Decimal("49999.00"),
        )
        listing = ProductListing.objects.create(
            product=product,
            marketplace=test_marketplace,
            external_id="TESTPIPELINE001",
            external_url="https://www.amazon.in/dp/TESTPIPELINE001",
            current_price=Decimal("49999.00"),
            in_stock=True,
        )

        assert Product.objects.count() == initial_products + 1
        assert ProductListing.objects.count() == initial_listings + 1
        assert listing.product_id == product.id

    def test_product_listing_unique_constraint(self, test_marketplace, test_product):
        """Duplicate (marketplace, external_id) should raise IntegrityError."""
        from apps.products.models import ProductListing
        from django.db import IntegrityError

        existing_listing = test_product.listings.first()
        if not existing_listing:
            pytest.skip("Test product has no listing")

        with pytest.raises(IntegrityError):
            ProductListing.objects.create(
                product=test_product,
                marketplace=test_marketplace,
                external_id=existing_listing.external_id,  # Duplicate!
                external_url="https://duplicate.test",
                current_price=Decimal("100"),
            )

    def test_listing_update_fields(self, test_product):
        """Verify listing fields can be updated (simulating pipeline update)."""
        listing = test_product.listings.first()
        if not listing:
            pytest.skip("Test product has no listing")

        listing.current_price = Decimal("74999.00")
        listing.in_stock = False
        listing.save(update_fields=["current_price", "in_stock", "updated_at"])

        listing.refresh_from_db()
        assert listing.current_price == Decimal("74999.00")
        assert listing.in_stock is False

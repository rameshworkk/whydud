"""
Product, search, compare, pricing, deals, reviews, and trending API tests.

Run: POSTGRES_PASSWORD=whydud_dev pytest tests/api/test_products.py -v
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.django_db]


# ---------------------------------------------------------------------------
# Product List
# ---------------------------------------------------------------------------


class TestProductList:
    """GET /api/v1/products/"""

    def test_list_returns_200(self, api_client):
        response = api_client.get('/api/v1/products/')
        assert response.status_code == 200

    def test_list_response_shape(self, api_client, test_product):
        """Response: {success, data: [...], pagination: {next, previous}}."""
        response = api_client.get('/api/v1/products/')
        assert response.data['success'] is True
        assert isinstance(response.data['data'], list)
        assert 'pagination' in response.data

    def test_list_contains_created_product(self, api_client, test_product):
        response = api_client.get('/api/v1/products/')
        results = response.data['data']
        slugs = [p.get('slug') for p in results]
        assert test_product.slug in slugs, (
            f"Product {test_product.slug} not in response. Got slugs: {slugs}"
        )

    def test_list_product_has_required_fields(self, api_client, test_product):
        """Each product in list must have key display fields."""
        response = api_client.get('/api/v1/products/')
        results = response.data['data']
        assert len(results) >= 1, "Expected at least 1 product"

        product = results[0]
        required_fields = [
            'id', 'slug', 'title', 'brand_name', 'category_name',
            'current_best_price', 'avg_rating', 'dud_score', 'images',
        ]
        for field in required_fields:
            assert field in product, f"Missing '{field}' in product list response"

    def test_list_filter_by_category(self, api_client, test_product):
        response = api_client.get('/api/v1/products/', {'category': 'smartphones'})
        assert response.status_code == 200
        results = response.data['data']
        assert len(results) >= 1

    def test_list_filter_by_brand(self, api_client, test_product):
        response = api_client.get('/api/v1/products/', {'brand': 'apple'})
        assert response.status_code == 200
        results = response.data['data']
        assert len(results) >= 1

    def test_list_filter_by_price_range(self, api_client, test_product):
        response = api_client.get('/api/v1/products/', {
            'min_price': '70000',
            'max_price': '90000',
        })
        assert response.status_code == 200

    def test_list_invalid_price_returns_error(self, api_client):
        response = api_client.get('/api/v1/products/', {'min_price': 'notanumber'})
        assert response.status_code == 400

    def test_list_sort_by_options(self, api_client, test_product):
        """Valid sort options should return 200."""
        for sort in ['newest', 'price_asc', 'price_desc', 'dud_score', 'top_rated']:
            response = api_client.get('/api/v1/products/', {'sort_by': sort})
            assert response.status_code == 200, f"sort_by={sort} failed"

    def test_list_invalid_sort_returns_error(self, api_client):
        response = api_client.get('/api/v1/products/', {'sort_by': 'invalid'})
        assert response.status_code == 400

    def test_list_keyword_filter(self, api_client, test_product):
        """?q= filters by title icontains."""
        response = api_client.get('/api/v1/products/', {'q': 'iPhone'})
        assert response.status_code == 200
        results = response.data['data']
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Product Detail
# ---------------------------------------------------------------------------


class TestProductDetail:
    """GET /api/v1/products/:slug/"""

    def test_detail_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/')
        assert response.status_code == 200

    def test_detail_has_full_data(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/')
        assert response.data['success'] is True
        data = response.data['data']
        required_fields = [
            'title', 'slug', 'brand', 'category', 'listings',
            'review_summary', 'dud_score', 'current_best_price',
        ]
        for field in required_fields:
            assert field in data, f"Missing '{field}' in product detail"

    def test_detail_includes_listings(self, api_client, test_product):
        """Product detail should include marketplace listings."""
        response = api_client.get(f'/api/v1/products/{test_product.slug}/')
        data = response.data['data']
        assert 'listings' in data
        assert len(data['listings']) >= 1, "Product should have at least 1 listing"

    def test_detail_listing_has_marketplace(self, api_client, test_product):
        """Each listing should include marketplace info."""
        response = api_client.get(f'/api/v1/products/{test_product.slug}/')
        listing = response.data['data']['listings'][0]
        assert 'marketplace' in listing
        assert listing['marketplace']['slug'] == 'amazon-in'

    def test_detail_includes_review_summary(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/')
        summary = response.data['data']['review_summary']
        assert 'total_reviews' in summary
        assert 'rating_distribution' in summary

    def test_detail_404_for_missing_slug(self, api_client):
        response = api_client.get('/api/v1/products/nonexistent-slug-xyz/')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Product Listings & Best Price
# ---------------------------------------------------------------------------


class TestProductListings:
    """GET /api/v1/products/:slug/listings/"""

    def test_listings_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/listings/')
        assert response.status_code == 200

    def test_listings_response_shape(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/listings/')
        data = response.data['data']
        assert 'listings' in data
        assert 'total_listings' in data
        assert isinstance(data['listings'], list)

    def test_listings_404_for_missing_product(self, api_client):
        response = api_client.get('/api/v1/products/nonexistent-slug/listings/')
        assert response.status_code == 404


class TestBestPrice:
    """GET /api/v1/products/:slug/best-price/"""

    def test_best_price_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/best-price/')
        assert response.status_code == 200

    def test_best_price_includes_product_info(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/best-price/')
        data = response.data['data']
        assert data['product_slug'] == test_product.slug
        assert 'current_price' in data


# ---------------------------------------------------------------------------
# Similar & Alternatives
# ---------------------------------------------------------------------------


class TestSimilarProducts:
    """GET /api/v1/products/:slug/similar/"""

    def test_similar_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/similar/')
        assert response.status_code == 200

    def test_similar_404_for_missing_product(self, api_client):
        response = api_client.get('/api/v1/products/nonexistent-slug/similar/')
        assert response.status_code == 404


class TestAlternativeProducts:
    """GET /api/v1/products/:slug/alternatives/"""

    def test_alternatives_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/alternatives/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Share
# ---------------------------------------------------------------------------


class TestShareProduct:
    """GET /api/v1/products/:slug/share/"""

    def test_share_returns_200(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/share/')
        assert response.status_code == 200

    def test_share_has_og_data(self, api_client, test_product):
        response = api_client.get(f'/api/v1/products/{test_product.slug}/share/')
        data = response.data['data']
        assert 'url' in data
        assert 'og' in data
        assert data['og']['og:type'] == 'product'


# ---------------------------------------------------------------------------
# Product Lookup
# ---------------------------------------------------------------------------


class TestProductLookup:
    """GET /api/v1/products/lookup/"""

    def test_lookup_returns_200(self, api_client, test_product):
        response = api_client.get('/api/v1/products/lookup/', {
            'marketplace': 'amazon-in',
            'external_id': 'B0CX23GFMV',
        })
        assert response.status_code == 200
        data = response.data['data']
        assert data['slug'] == test_product.slug

    def test_lookup_missing_params(self, api_client):
        response = api_client.get('/api/v1/products/lookup/')
        assert response.status_code == 400

    def test_lookup_not_found(self, api_client, test_marketplace):
        response = api_client.get('/api/v1/products/lookup/', {
            'marketplace': 'amazon-in',
            'external_id': 'NONEXISTENT',
        })
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    """GET /api/v1/search"""

    def test_search_returns_200(self, api_client, test_product):
        response = api_client.get('/api/v1/search', {'q': 'iPhone'})
        assert response.status_code == 200

    def test_search_finds_product(self, api_client, test_product):
        """Searching for 'iPhone' should find our test product via DB fallback."""
        response = api_client.get('/api/v1/search', {'q': 'iPhone'})
        assert response.status_code == 200
        data = response.data['data']
        assert 'results' in data
        slugs = [p.get('slug') for p in data['results']]
        assert test_product.slug in slugs, (
            f"Expected {test_product.slug} in results. Got: {slugs}"
        )

    def test_search_response_shape(self, api_client, test_product):
        response = api_client.get('/api/v1/search', {'q': 'iPhone'})
        data = response.data['data']
        assert 'results' in data
        assert 'total' in data
        assert 'offset' in data
        assert 'limit' in data
        assert 'query' in data

    def test_search_empty_query_returns_400(self, api_client):
        """Empty q= should return validation error."""
        response = api_client.get('/api/v1/search', {'q': ''})
        assert response.status_code == 400

    def test_search_missing_q_returns_400(self, api_client):
        response = api_client.get('/api/v1/search')
        assert response.status_code == 400

    def test_search_with_category_filter(self, api_client, test_product):
        response = api_client.get('/api/v1/search', {
            'q': 'iPhone',
            'category': 'smartphones',
        })
        assert response.status_code == 200

    def test_search_with_price_filter(self, api_client, test_product):
        response = api_client.get('/api/v1/search', {
            'q': 'iPhone',
            'min_price': '70000',
            'max_price': '90000',
        })
        assert response.status_code == 200

    def test_search_sort_options(self, api_client, test_product):
        for sort in ['relevance', 'price_asc', 'price_desc', 'dud_score', 'top_rated']:
            response = api_client.get('/api/v1/search', {
                'q': 'iPhone', 'sort_by': sort,
            })
            assert response.status_code == 200, f"sort_by={sort} failed"


class TestAutocomplete:
    """GET /api/v1/search/autocomplete"""

    def test_autocomplete_returns_200(self, api_client):
        response = api_client.get('/api/v1/search/autocomplete', {'q': 'iph'})
        assert response.status_code == 200

    def test_autocomplete_finds_product(self, api_client, test_product):
        response = api_client.get('/api/v1/search/autocomplete', {'q': 'Apple'})
        assert response.status_code == 200
        data = response.data['data']
        if isinstance(data, list) and len(data) > 0:
            assert 'slug' in data[0]

    def test_autocomplete_short_query_returns_empty(self, api_client):
        """Query shorter than min length returns empty results."""
        response = api_client.get('/api/v1/search/autocomplete', {'q': 'a'})
        assert response.status_code == 200
        assert response.data['data'] == []


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


class TestCompare:
    """GET /api/v1/compare/"""

    def test_compare_needs_2_slugs(self, api_client, test_product):
        """Compare with only 1 slug returns 400."""
        response = api_client.get('/api/v1/compare/', {
            'slugs': test_product.slug,
        })
        assert response.status_code == 400

    def test_compare_with_no_slugs(self, api_client):
        response = api_client.get('/api/v1/compare/')
        assert response.status_code == 400

    def test_compare_with_valid_slugs(self, api_client, test_product, test_category, test_brand, test_marketplace):
        """Compare with 2 valid product slugs returns 200."""
        from decimal import Decimal
        from apps.products.models import Product, ProductListing

        product2 = Product.objects.create(
            title='Samsung Galaxy S24 Ultra',
            slug='samsung-galaxy-s24-ultra',
            brand=test_brand,
            category=test_category,
            current_best_price=Decimal('134999.00'),
        )
        ProductListing.objects.create(
            product=product2,
            marketplace=test_marketplace,
            external_id='B0SAMTEST',
            external_url='https://www.amazon.in/dp/B0SAMTEST',
            title='Samsung Galaxy S24 Ultra',
            current_price=Decimal('134999.00'),
            mrp=Decimal('134999.00'),
            in_stock=True,
        )

        response = api_client.get('/api/v1/compare/', {
            'slugs': f'{test_product.slug},{product2.slug}',
        })
        assert response.status_code == 200
        data = response.data['data']
        assert 'products' in data
        assert 'price_matrix' in data
        assert 'spec_diff' in data
        assert len(data['products']) == 2

    def test_compare_with_nonexistent_slug(self, api_client, test_product):
        """Compare with one missing product returns 404."""
        response = api_client.get('/api/v1/compare/', {
            'slugs': f'{test_product.slug},nonexistent-slug',
        })
        assert response.status_code == 404


class TestShareCompare:
    """GET /api/v1/compare/share/"""

    def test_share_compare_needs_2_slugs(self, api_client):
        response = api_client.get('/api/v1/compare/share/', {'slugs': 'one'})
        assert response.status_code == 400

    def test_share_compare_returns_og_data(self, api_client, test_product, test_category, test_brand):
        from decimal import Decimal
        from apps.products.models import Product

        product2 = Product.objects.create(
            title='Samsung Galaxy S24',
            slug='samsung-galaxy-s24',
            brand=test_brand,
            category=test_category,
            current_best_price=Decimal('79999.00'),
        )
        response = api_client.get('/api/v1/compare/share/', {
            'slugs': f'{test_product.slug},{product2.slug}',
        })
        assert response.status_code == 200
        assert 'og' in response.data['data']


# ---------------------------------------------------------------------------
# Price History (currently 501)
# ---------------------------------------------------------------------------


class TestPriceHistory:
    """GET /api/v1/products/:slug/price-history/"""

    def test_price_history_returns_501(self, api_client, test_product):
        """Sprint 2 stub — should return 501 not_implemented."""
        response = api_client.get(
            f'/api/v1/products/{test_product.slug}/price-history/'
        )
        assert response.status_code == 501

    def test_price_history_stub_for_missing_product(self, api_client):
        """Stub returns 501 even for nonexistent slugs (no product check yet)."""
        response = api_client.get('/api/v1/products/nonexistent-slug/price-history/')
        assert response.status_code == 501


# ---------------------------------------------------------------------------
# Product Reviews
# ---------------------------------------------------------------------------


class TestProductReviews:
    """GET /api/v1/products/:slug/reviews"""

    def test_reviews_returns_200(self, api_client, test_product):
        response = api_client.get(
            f'/api/v1/products/{test_product.slug}/reviews'
        )
        assert response.status_code == 200

    def test_reviews_404_for_missing_product(self, api_client):
        response = api_client.get('/api/v1/products/nonexistent-slug/reviews')
        assert response.status_code == 404

    def test_reviews_sort_options(self, api_client, test_product):
        for sort in ['helpful', 'recent', 'rating_asc', 'rating_desc']:
            response = api_client.get(
                f'/api/v1/products/{test_product.slug}/reviews',
                {'sort': sort},
            )
            assert response.status_code == 200, f"sort={sort} failed"


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


class TestDeals:
    """GET /api/v1/deals"""

    def test_deals_returns_200(self, api_client):
        response = api_client.get('/api/v1/deals')
        assert response.status_code == 200

    def test_deals_with_type_filter(self, api_client):
        response = api_client.get('/api/v1/deals', {'type': 'price_drop'})
        assert response.status_code == 200

    def test_deals_with_category_filter(self, api_client, test_category):
        response = api_client.get('/api/v1/deals', {'category': 'smartphones'})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


class TestOffers:
    """GET /api/v1/offers/active"""

    def test_active_offers_returns_200(self, api_client):
        response = api_client.get('/api/v1/offers/active')
        assert response.status_code == 200

    def test_active_offers_with_marketplace_filter(self, api_client, test_marketplace):
        response = api_client.get('/api/v1/offers/active', {
            'marketplace': 'amazon-in',
        })
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Trending
# ---------------------------------------------------------------------------


class TestTrending:
    """GET /api/v1/trending/*"""

    def test_trending_products_returns_200(self, api_client):
        response = api_client.get('/api/v1/trending/products')
        assert response.status_code == 200

    def test_rising_returns_200(self, api_client):
        response = api_client.get('/api/v1/trending/rising')
        assert response.status_code == 200

    def test_price_dropping_returns_200(self, api_client):
        response = api_client.get('/api/v1/trending/price-dropping')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Category Leaderboard / Most-Loved / Most-Hated
# ---------------------------------------------------------------------------


class TestCategoryEndpoints:
    """GET /api/v1/categories/:slug/leaderboard, most-loved, most-hated"""

    def test_leaderboard_returns_200(self, api_client, test_category):
        response = api_client.get(f'/api/v1/categories/{test_category.slug}/leaderboard')
        assert response.status_code == 200

    def test_most_loved_returns_200(self, api_client, test_category):
        response = api_client.get(f'/api/v1/categories/{test_category.slug}/most-loved')
        assert response.status_code == 200

    def test_most_hated_returns_200(self, api_client, test_category):
        response = api_client.get(f'/api/v1/categories/{test_category.slug}/most-hated')
        assert response.status_code == 200

    def test_leaderboard_404_for_missing_category(self, api_client):
        response = api_client.get('/api/v1/categories/nonexistent-cat/leaderboard')
        assert response.status_code == 404

    def test_leaderboard_has_products(self, api_client, test_product):
        """Category with a product that has dud_score should return it."""
        response = api_client.get(
            f'/api/v1/categories/{test_product.category.slug}/leaderboard'
        )
        assert response.status_code == 200
        data = response.data['data']
        assert len(data) >= 1


# ---------------------------------------------------------------------------
# Bank Cards
# ---------------------------------------------------------------------------


class TestBankCards:
    """GET /api/v1/cards/banks/ and variants"""

    def test_banks_list_returns_200(self, api_client):
        response = api_client.get('/api/v1/cards/banks/')
        assert response.status_code == 200

    def test_bank_variants_404_for_missing(self, api_client):
        response = api_client.get('/api/v1/cards/banks/nonexistent-bank/variants/')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Price Alerts (authenticated)
# ---------------------------------------------------------------------------


class TestPriceAlerts:
    """Authenticated price alert endpoints."""

    def test_list_alerts_unauthenticated(self, api_client):
        response = api_client.get('/api/v1/alerts')
        assert response.status_code == 401

    def test_list_alerts_authenticated(self, authenticated_client):
        response = authenticated_client.get('/api/v1/alerts')
        assert response.status_code == 200

    def test_create_alert(self, authenticated_client, test_product):
        response = authenticated_client.post('/api/v1/alerts/price', {
            'product_slug': test_product.slug,
            'target_price': '69999.00',
        }, format='json')
        assert response.status_code == 201

    def test_create_alert_missing_product(self, authenticated_client):
        response = authenticated_client.post('/api/v1/alerts/price', {
            'target_price': '69999.00',
        }, format='json')
        assert response.status_code == 400

    def test_triggered_alerts(self, authenticated_client):
        response = authenticated_client.get('/api/v1/alerts/triggered')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Stock Alerts (authenticated)
# ---------------------------------------------------------------------------


class TestStockAlerts:
    """GET/POST /api/v1/alerts/stock"""

    def test_stock_alerts_unauthenticated(self, api_client):
        response = api_client.get('/api/v1/alerts/stock')
        assert response.status_code == 401

    def test_stock_alerts_list(self, authenticated_client):
        response = authenticated_client.get('/api/v1/alerts/stock')
        assert response.status_code == 200

    def test_create_stock_alert(self, authenticated_client, test_product):
        response = authenticated_client.post('/api/v1/alerts/stock', {
            'product_slug': test_product.slug,
        }, format='json')
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# Recently Viewed (authenticated)
# ---------------------------------------------------------------------------


class TestRecentlyViewed:
    """GET/POST /api/v1/me/recently-viewed"""

    def test_recently_viewed_unauthenticated(self, api_client):
        response = api_client.get('/api/v1/me/recently-viewed')
        assert response.status_code == 401

    def test_recently_viewed_list(self, authenticated_client):
        response = authenticated_client.get('/api/v1/me/recently-viewed')
        assert response.status_code == 200

    def test_log_product_view(self, authenticated_client, test_product):
        response = authenticated_client.post('/api/v1/me/recently-viewed', {
            'product_slug': test_product.slug,
        }, format='json')
        assert response.status_code == 201

    def test_log_view_missing_slug(self, authenticated_client):
        response = authenticated_client.post('/api/v1/me/recently-viewed', {},
                                             format='json')
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Click Tracking
# ---------------------------------------------------------------------------


class TestClickTracking:
    """POST /api/v1/clicks/track"""

    def test_track_click(self, api_client, test_product):
        listing = test_product.listings.first()
        response = api_client.post('/api/v1/clicks/track', {
            'listing_id': str(listing.id),
            'referrer_page': 'product_page',
        }, format='json')
        assert response.status_code == 201
        data = response.data['data']
        assert 'affiliate_url' in data
        assert 'click_id' in data

    def test_track_click_missing_listing(self, api_client):
        response = api_client.post('/api/v1/clicks/track', {
            'referrer_page': 'product_page',
        }, format='json')
        assert response.status_code == 400

    def test_click_history_unauthenticated(self, api_client):
        response = api_client.get('/api/v1/clicks/history')
        assert response.status_code == 401

    def test_click_history_authenticated(self, authenticated_client):
        response = authenticated_client.get('/api/v1/clicks/history')
        assert response.status_code == 200

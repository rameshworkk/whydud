"""
Shared fixtures for the entire test suite.

Usage in tests:
    def test_something(api_client, test_user, auth_headers, test_product):
        response = api_client.get('/api/v1/products/', headers=auth_headers)
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

# ── Session-scoped Setup ──


@pytest.fixture(autouse=True)
def _disable_throttling(settings):
    """Set very high throttle rates during tests to avoid rate-limit flakes."""
    settings.REST_FRAMEWORK = {
        **getattr(settings, 'REST_FRAMEWORK', {}),
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {
            'auth': '9999/minute',
            'search': '9999/minute',
            'review': '9999/minute',
            'email_send': '9999/minute',
            'anon_search': '9999/minute',
            'user_search': '9999/minute',
            'product_view': '9999/minute',
        },
    }


# ── Core Fixtures ──


@pytest.fixture
def api_client():
    """DRF test client for making API requests."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user with known credentials."""
    user = User.objects.create_user(
        email='testuser@example.com',
        password='TestPass123!',
        name='Test User',
        is_active=True,
    )
    return user


@pytest.fixture
def test_user_2(db):
    """Second test user for multi-user scenarios."""
    user = User.objects.create_user(
        email='testuser2@example.com',
        password='TestPass456!',
        name='Another User',
        is_active=True,
    )
    return user


@pytest.fixture
def auth_token(api_client, test_user):
    """Get auth token for the test user."""
    response = api_client.post('/api/v1/auth/login', {
        'email': 'testuser@example.com',
        'password': 'TestPass123!',
    }, format='json')
    assert response.status_code == 200, f"Login failed: {response.data}"
    token = response.data.get('data', {}).get('token') or response.data.get('token')
    assert token, f"No token in response: {response.data}"
    return token


@pytest.fixture
def auth_headers(auth_token):
    """HTTP headers with auth token (DRF TokenAuthentication)."""
    return {'HTTP_AUTHORIZATION': f'Token {auth_token}'}


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """API client with auth token pre-configured."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {auth_token}')
    return api_client


# ── Data Fixtures ──


@pytest.fixture
def test_marketplace(db):
    """Create Amazon India marketplace."""
    from apps.products.models import Marketplace
    marketplace, _ = Marketplace.objects.get_or_create(
        slug='amazon-in',
        defaults={
            'name': 'Amazon India',
            'base_url': 'https://www.amazon.in',
            'affiliate_tag': 'whydud-21',
        }
    )
    return marketplace


@pytest.fixture
def test_marketplace_flipkart(db):
    """Create Flipkart marketplace."""
    from apps.products.models import Marketplace
    marketplace, _ = Marketplace.objects.get_or_create(
        slug='flipkart',
        defaults={
            'name': 'Flipkart',
            'base_url': 'https://www.flipkart.com',
        }
    )
    return marketplace


@pytest.fixture
def test_category(db):
    """Create a test category."""
    from apps.products.models import Category
    category, _ = Category.objects.get_or_create(
        slug='smartphones',
        defaults={
            'name': 'Smartphones',
        }
    )
    return category


@pytest.fixture
def test_brand(db):
    """Create a test brand."""
    from apps.products.models import Brand
    brand, _ = Brand.objects.get_or_create(
        slug='apple',
        defaults={
            'name': 'Apple',
        }
    )
    return brand


@pytest.fixture
def test_product(db, test_category, test_brand, test_marketplace):
    """Create a full test product with listing."""
    from apps.products.models import Product, ProductListing

    product = Product.objects.create(
        title='Apple iPhone 16 (128 GB) - Black',
        slug='apple-iphone-16-128gb-black',
        brand=test_brand,
        category=test_category,
        current_best_price=Decimal('79999.00'),
        avg_rating=Decimal('4.50'),
        total_reviews=1250,
        dud_score=Decimal('82.50'),
        images=['https://example.com/iphone16.jpg'],
    )

    ProductListing.objects.create(
        product=product,
        marketplace=test_marketplace,
        external_id='B0CX23GFMV',
        external_url='https://www.amazon.in/dp/B0CX23GFMV',
        title='Apple iPhone 16 (128 GB) - Black',
        current_price=Decimal('79999.00'),
        mrp=Decimal('79999.00'),
        in_stock=True,
        rating=Decimal('4.50'),
        review_count=1250,
    )

    return product


@pytest.fixture
def test_product_with_history(test_product, test_marketplace):
    """Product with price snapshot history for chart tests."""
    from django.db import connection
    from django.utils import timezone
    from datetime import timedelta

    listing = test_product.listings.first()
    now = timezone.now()

    # Insert 30 days of price history
    with connection.cursor() as cur:
        values = []
        for i in range(30):
            time = now - timedelta(days=30 - i)
            # Price fluctuates between ₹74,999 and ₹82,999
            price = Decimal('74999.00') + Decimal(str((i % 5) * 2000))
            values.append(
                f"('{time.isoformat()}'::timestamptz, '{listing.id}', "
                f"'{test_product.id}', {test_marketplace.id}, "
                f"{price}, 79999.00, true, NULL, 'scraper')"
            )
        if values:
            cur.execute(f"""
                INSERT INTO price_snapshots
                    (time, listing_id, product_id, marketplace_id,
                     price, mrp, in_stock, seller_name, source)
                VALUES {', '.join(values)}
            """)
    return test_product

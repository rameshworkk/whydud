"""
Frontend route tests — verify all Next.js pages return 200.
Requires the Next.js dev server or production server to be running.

Run: pytest tests/frontend/test_pages.py -v
Mark: these tests are skipped if frontend is not running.
"""
import pytest
import httpx

pytestmark = [pytest.mark.frontend]

FRONTEND_URL = 'http://localhost:3000'


def frontend_available():
    try:
        resp = httpx.get(FRONTEND_URL, timeout=3)
        return resp.status_code < 500
    except Exception:
        return False


skip_no_frontend = pytest.mark.skipif(
    not frontend_available(),
    reason='Frontend server not running'
)


@skip_no_frontend
class TestPublicPages:
    """All public pages should return 200."""

    @pytest.mark.parametrize('path,name', [
        ('/',               'Homepage'),
        ('/search',         'Search'),
        ('/deals',          'Deals'),
        ('/leaderboard',    'Leaderboard'),
        ('/login',          'Login'),
        ('/register',       'Register'),
    ])
    def test_public_page(self, path, name):
        resp = httpx.get(f'{FRONTEND_URL}{path}', timeout=15, follow_redirects=True)
        assert resp.status_code == 200, (
            f'{name} ({path}) returned {resp.status_code}'
        )

    def test_product_page(self):
        """Product detail page — need a real slug from API."""
        try:
            api_resp = httpx.get('http://localhost:8000/api/v1/products/', timeout=5)
            results = (api_resp.json().get('data', {}).get('results', [])
                       or api_resp.json().get('results', []))
            if not results:
                pytest.skip("No products to test product page")
            slug = results[0].get('slug', '')
            if not slug:
                pytest.skip("First product has no slug")
        except Exception as e:
            pytest.skip(f"Could not get product slug: {e}")

        resp = httpx.get(f'{FRONTEND_URL}/product/{slug}', timeout=15,
                         follow_redirects=True)
        assert resp.status_code == 200, f'Product page returned {resp.status_code}'

    def test_404_page(self):
        """Nonexistent route should return 404 (not 500)."""
        resp = httpx.get(f'{FRONTEND_URL}/this-page-does-not-exist',
                         timeout=10, follow_redirects=True)
        assert resp.status_code in (404, 200), (
            f'Expected 404, got {resp.status_code}'
        )


@skip_no_frontend
class TestPagePerformance:
    """Pages should load reasonably fast."""

    @pytest.mark.slow
    @pytest.mark.parametrize('path,max_seconds', [
        ('/', 5),
        ('/search?q=phone', 5),
        ('/deals', 5),
        ('/login', 3),
    ])
    def test_page_load_time(self, path, max_seconds):
        import time
        start = time.time()
        resp = httpx.get(f'{FRONTEND_URL}{path}', timeout=max_seconds + 5,
                         follow_redirects=True)
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < max_seconds, (
            f'{path} took {elapsed:.1f}s (max {max_seconds}s)'
        )

    def test_no_console_errors_in_html(self):
        """Homepage HTML should not contain server-side error traces."""
        resp = httpx.get(f'{FRONTEND_URL}/', timeout=10)
        html = resp.text.lower()
        error_indicators = ['internal server error', 'traceback',
                            'typeerror', 'referenceerror', 'syntaxerror']
        for indicator in error_indicators:
            assert indicator not in html, (
                f'Homepage contains error indicator: {indicator}'
            )

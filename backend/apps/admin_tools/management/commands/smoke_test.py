"""
Ultra-fast smoke test — hits every API endpoint, checks for 2xx or expected 4xx.
Takes ~30 seconds. Run after every deploy.

Usage:
  python manage.py smoke_test
  python manage.py smoke_test --base-url https://whydud.com
  python manage.py smoke_test --include-auth     # also test authenticated endpoints
  python manage.py smoke_test --include-frontend  # also test frontend routes
  python manage.py smoke_test --verbose           # show response bodies on failure
"""
import time

import httpx
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Fast smoke test — hit every endpoint, verify status codes'

    def add_arguments(self, parser):
        parser.add_argument('--base-url', default='http://localhost:8000',
                            help='Base URL for API requests')
        parser.add_argument('--frontend-url', default='http://localhost:3000',
                            help='Base URL for frontend requests')
        parser.add_argument('--include-auth', action='store_true',
                            help='Test authenticated endpoints (creates temp user)')
        parser.add_argument('--include-frontend', action='store_true',
                            help='Check frontend routes return 200')
        parser.add_argument('--verbose', action='store_true',
                            help='Show response body on failure')
        parser.add_argument('--timeout', type=int, default=10,
                            help='Request timeout in seconds')

    def handle(self, *args, **options):
        base = options['base_url'].rstrip('/')
        frontend = options['frontend_url'].rstrip('/')
        timeout = options['timeout']
        verbose = options['verbose']

        self.passed = 0
        self.failed = 0
        self.warned = 0
        self.errors = []
        start_time = time.time()

        client = httpx.Client(timeout=timeout, follow_redirects=True)

        self.stdout.write(self.style.WARNING('\n══════ WHYDUD SMOKE TEST ══════\n'))

        # ── PUBLIC ENDPOINTS (no auth) ──
        self.stdout.write(self.style.MIGRATE_HEADING('Public API Endpoints'))

        public_endpoints = [
            # Products
            ('GET', '/api/v1/products/',                          200, 'Product list'),
            ('GET', '/api/v1/products/lookup/',                   200, 'Product lookup'),
            ('GET', '/api/v1/compare/',                           200, 'Compare'),
            ('GET', '/api/v1/cards/banks/',                       200, 'Bank list'),
            ('GET', '/api/v1/trending/products',                  200, 'Trending products'),
            ('GET', '/api/v1/trending/rising',                    200, 'Rising products'),
            ('GET', '/api/v1/trending/price-dropping',            200, 'Price dropping'),
            # Search
            ('GET', '/api/v1/search?q=phone',                    200, 'Search'),
            ('GET', '/api/v1/search/autocomplete?q=ip',          200, 'Autocomplete'),
            # Deals
            ('GET', '/api/v1/deals',                              200, 'Deals list'),
            # Reviews
            ('GET', '/api/v1/leaderboard/reviewers',              200, 'Reviewer leaderboard'),
            # Scoring
            ('GET', '/api/v1/scoring/config',                     200, 'DudScore config'),
            ('GET', '/api/v1/brands/leaderboard',                 200, 'Brand leaderboard'),
            # Pricing
            ('GET', '/api/v1/offers/active',                      200, 'Active offers'),
            # TCO
            ('GET', '/api/v1/tco/cities',                         200, 'TCO cities'),
            # Preferences (public schemas)
            ('GET', '/api/v1/preferences/schemas',                200, 'Preference schemas'),
            # Auth endpoints (should return 400/401 for GET, just check they're alive)
            ('POST', '/api/v1/auth/login',                        400, 'Login (no body → 400)'),
            ('POST', '/api/v1/auth/register',                     400, 'Register (no body → 400)'),
        ]

        for method, path, expected_status, label in public_endpoints:
            self._check(client, method, f"{base}{path}", expected_status, label, verbose)

        # Test product detail (get slug from product list)
        try:
            resp = client.get(f"{base}/api/v1/products/")
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('data', {}).get('results', []) or data.get('results', [])
                if results:
                    slug = results[0].get('slug', '')
                    if slug:
                        detail_endpoints = [
                            ('GET', f'/api/v1/products/{slug}/',               200, f'Product detail ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/price-history/',  200, f'Price history ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/reviews',         200, f'Product reviews ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/best-deals/',     200, f'Best deals ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/listings/',       200, f'Listings ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/similar/',        200, f'Similar products ({slug[:30]})'),
                            ('GET', f'/api/v1/products/{slug}/discussions/',    200, f'Discussions ({slug[:30]})'),
                        ]
                        for method, path, expected_status, label in detail_endpoints:
                            self._check(client, method, f"{base}{path}",
                                        expected_status, label, verbose)
                else:
                    self._warn('Product detail', 'No products in DB to test detail endpoint')
        except Exception as e:
            self._warn('Product detail', f'Could not get product list: {e}')

        # ── AUTH ENDPOINTS ──
        if options['include_auth']:
            self.stdout.write(self.style.MIGRATE_HEADING('\nAuthenticated Endpoints'))
            token = self._get_or_create_test_token(client, base, verbose)

            if token:
                auth_headers = {'Authorization': f'Token {token}'}

                auth_endpoints = [
                    # Account
                    ('GET',  '/api/v1/me/',                         200, 'Profile (me)'),
                    ('GET',  '/api/v1/me/marketplace-preferences',  200, 'Marketplace preferences'),
                    ('GET',  '/api/v1/me/recently-viewed',          200, 'Recently viewed'),
                    ('GET',  '/api/v1/me/reviews',                  200, 'My reviews'),
                    ('GET',  '/api/v1/me/reviewer-profile',         200, 'Reviewer profile'),
                    # Cards
                    ('GET',  '/api/v1/cards',                       200, 'Payment cards'),
                    # Wishlists
                    ('GET',  '/api/v1/wishlists',                   200, 'Wishlists'),
                    # Notifications
                    ('GET',  '/api/v1/notifications',               200, 'Notifications'),
                    ('GET',  '/api/v1/notifications/unread-count',  200, 'Unread count'),
                    ('GET',  '/api/v1/notifications/preferences',   200, 'Notification preferences'),
                    # Alerts
                    ('GET',  '/api/v1/alerts',                      200, 'Price alerts'),
                    ('GET',  '/api/v1/alerts/triggered',            200, 'Triggered alerts'),
                    ('GET',  '/api/v1/alerts/stock',                200, 'Stock alerts'),
                    # Email intel
                    ('GET',  '/api/v1/inbox',                       200, 'Inbox'),
                    ('GET',  '/api/v1/email/whydud/status',         200, 'Whydud email status'),
                    # Purchases
                    ('GET',  '/api/v1/purchases',                   200, 'Purchases'),
                    ('GET',  '/api/v1/purchases/dashboard',         200, 'Purchase dashboard'),
                    ('GET',  '/api/v1/purchases/refunds',           200, 'Refunds'),
                    ('GET',  '/api/v1/purchases/return-windows',    200, 'Return windows'),
                    ('GET',  '/api/v1/purchases/subscriptions',     200, 'Subscriptions'),
                    # Rewards
                    ('GET',  '/api/v1/rewards/balance',             200, 'Reward balance'),
                    ('GET',  '/api/v1/rewards/history',             200, 'Reward history'),
                    ('GET',  '/api/v1/rewards/gift-cards',          200, 'Gift card catalog'),
                    ('GET',  '/api/v1/rewards/redemptions',         200, 'Redemption history'),
                    # Click history
                    ('GET',  '/api/v1/clicks/history',              200, 'Click history'),
                    # Preferences
                    ('GET',  '/api/v1/preferences',                 200, 'User preferences'),
                    # Subscription
                    ('GET',  '/api/v1/subscription/status',         200, 'Subscription status'),
                    # TCO
                    ('GET',  '/api/v1/tco/profile',                 200, 'TCO profile'),
                ]

                for method, path, expected_status, label in auth_endpoints:
                    self._check(client, method, f"{base}{path}",
                                expected_status, label, verbose, headers=auth_headers)
            else:
                self._warn('Auth endpoints', 'Could not obtain auth token, skipping')

        # ── FRONTEND ROUTES ──
        if options['include_frontend']:
            self.stdout.write(self.style.MIGRATE_HEADING('\nFrontend Routes'))

            frontend_routes = [
                ('/',               200, 'Homepage'),
                ('/search',         200, 'Search page'),
                ('/deals',          200, 'Deals page'),
                ('/login',          200, 'Login page'),
                ('/register',       200, 'Register page'),
                ('/leaderboard',    200, 'Leaderboard page'),
            ]

            for path, expected, label in frontend_routes:
                self._check(client, 'GET', f"{frontend}{path}",
                            expected, f'[FE] {label}', verbose)

        # ── SUMMARY ──
        elapsed = time.time() - start_time
        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(self.style.SUCCESS(f'  Passed:  {self.passed}'))
        if self.warned:
            self.stdout.write(self.style.WARNING(f'  Warned:  {self.warned}'))
        if self.failed:
            self.stdout.write(self.style.ERROR(f'  Failed:  {self.failed}'))
        self.stdout.write(f'  Time:    {elapsed:.1f}s')
        self.stdout.write('─' * 50 + '\n')

        if self.errors:
            self.stdout.write(self.style.ERROR('\nFailed endpoints:'))
            for err in self.errors:
                self.stdout.write(f'  - {err}')

        if self.failed > 0:
            self.stdout.write(self.style.ERROR(
                '\nSmoke test FAILED. Fix the above before deploying.'
            ))
            raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS('\nSmoke test PASSED.'))

    def _check(self, client, method, url, expected_status, label, verbose, headers=None):
        try:
            start = time.time()
            resp = client.request(method, url, headers=headers or {})
            elapsed_ms = (time.time() - start) * 1000

            status_ok = resp.status_code == expected_status
            # Also accept 200-299 range if we expected 200
            if not status_ok and expected_status == 200:
                status_ok = 200 <= resp.status_code < 300

            # Format the path for display
            display_path = url.split('/api/')[-1] if '/api/' in url else url

            if status_ok:
                self.passed += 1
                self.stdout.write(
                    f'  OK  {method:4s} {display_path:55s} '
                    f'{resp.status_code} ({elapsed_ms:.0f}ms)'
                )
            else:
                self.failed += 1
                error_msg = f'{method} {label}: expected {expected_status}, got {resp.status_code}'
                self.errors.append(error_msg)
                self.stdout.write(self.style.ERROR(
                    f'  FAIL {method:4s} {display_path:55s} '
                    f'{resp.status_code} (expected {expected_status})'
                ))
                if verbose:
                    body = resp.text[:500]
                    self.stdout.write(f'     Response: {body}')

        except httpx.ConnectError:
            self.failed += 1
            self.errors.append(f'{method} {label}: Connection refused')
            self.stdout.write(self.style.ERROR(f'  FAIL {method:4s} {label:55s} CONNECTION REFUSED'))
        except httpx.TimeoutException:
            self.failed += 1
            self.errors.append(f'{method} {label}: Timeout')
            self.stdout.write(self.style.ERROR(f'  FAIL {method:4s} {label:55s} TIMEOUT'))
        except Exception as e:
            self.failed += 1
            self.errors.append(f'{method} {label}: {e}')
            self.stdout.write(self.style.ERROR(f'  FAIL {method:4s} {label:55s} ERROR: {e}'))

    def _warn(self, label, message):
        self.warned += 1
        self.stdout.write(self.style.WARNING(f'  WARN {label:55s} {message}'))

    def _get_or_create_test_token(self, client, base, verbose):
        """Get auth token, creating test user if needed."""
        test_email = '_smoketest@whydud.com'
        test_pass = 'SmokeTest123!!'

        # Try login first
        resp = client.post(f"{base}/api/v1/auth/login", json={
            'email': test_email, 'password': test_pass,
        })
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('token') or data.get('token')

        # Create user via Django ORM (not via API, to avoid email requirements)
        try:
            user, created = User.objects.get_or_create(
                email=test_email,
                defaults={'name': 'Smoke Test', 'is_active': True, 'email_verified': True}
            )
            if created:
                user.set_password(test_pass)
                user.save()

            # Try login again
            resp = client.post(f"{base}/api/v1/auth/login", json={
                'email': test_email, 'password': test_pass,
            })
            if resp.status_code == 200:
                data = resp.json()
                return data.get('data', {}).get('token') or data.get('token')

            if verbose:
                self.stdout.write(f'     Login response: {resp.text[:200]}')
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'     Could not create test user: {e}'))
            return None

"""
Auth endpoint tests: register, login, logout, profile, password change, whydud email.

Run: pytest tests/api/test_auth.py -v
"""
import pytest

pytestmark = [pytest.mark.api, pytest.mark.auth, pytest.mark.django_db]


class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_success(self, api_client):
        """Register with valid data returns 201 + user data + token."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'name': 'New User',
        }, format='json')
        assert response.status_code == 201, f"Register failed: {response.data}"
        assert response.data['success'] is True
        data = response.data['data']
        assert data['user']['email'] == 'newuser@example.com'
        assert 'token' in data

    def test_register_duplicate_email(self, api_client, test_user):
        """Register with existing email returns 400."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'testuser@example.com',  # Same as test_user fixture
            'password': 'StrongPass123!',
            'name': 'Dupe User',
        }, format='json')
        assert response.status_code == 400
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'email_taken'

    def test_register_weak_password(self, api_client):
        """Register with password shorter than 8 chars returns 400."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'weak@example.com',
            'password': 'short',
            'name': 'Weak User',
        }, format='json')
        assert response.status_code == 400

    def test_register_missing_email(self, api_client):
        """Register without email returns 400."""
        response = api_client.post('/api/v1/auth/register', {
            'password': 'StrongPass123!',
            'name': 'No Email',
        }, format='json')
        assert response.status_code == 400

    def test_register_missing_password(self, api_client):
        """Register without password returns 400."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'nopass@example.com',
            'name': 'No Password',
        }, format='json')
        assert response.status_code == 400

    def test_register_invalid_email_format(self, api_client):
        """Register with invalid email format returns 400."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'not-an-email',
            'password': 'StrongPass123!',
        }, format='json')
        assert response.status_code == 400

    def test_register_name_optional(self, api_client):
        """Register without name still succeeds (name is optional)."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'noname@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert response.status_code == 201

    def test_register_with_referral_code(self, api_client, test_user):
        """Register with referral code succeeds."""
        response = api_client.post('/api/v1/auth/register', {
            'email': 'referred@example.com',
            'password': 'StrongPass123!',
            'name': 'Referred User',
            'referral_code': test_user.referral_code,
        }, format='json')
        # Succeeds even if referral code is valid or invalid
        assert response.status_code == 201


class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_success(self, api_client, test_user):
        """Login with correct credentials returns 200 + token."""
        response = api_client.post('/api/v1/auth/login', {
            'email': 'testuser@example.com',
            'password': 'TestPass123!',
        }, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True
        data = response.data['data']
        assert 'token' in data
        assert data['user']['email'] == 'testuser@example.com'

    def test_login_wrong_password(self, api_client, test_user):
        """Login with wrong password returns 401."""
        response = api_client.post('/api/v1/auth/login', {
            'email': 'testuser@example.com',
            'password': 'WrongPassword!',
        }, format='json')
        assert response.status_code == 401
        assert response.data['error']['code'] == 'invalid_credentials'

    def test_login_nonexistent_user(self, api_client):
        """Login with nonexistent email returns 401."""
        response = api_client.post('/api/v1/auth/login', {
            'email': 'nobody@example.com',
            'password': 'Whatever123!',
        }, format='json')
        assert response.status_code == 401

    def test_login_missing_fields(self, api_client):
        """Login without email or password returns 400."""
        response = api_client.post('/api/v1/auth/login', {}, format='json')
        assert response.status_code == 400

    def test_login_returns_valid_token(self, api_client, test_user):
        """Token from login should work for /me endpoint."""
        login_resp = api_client.post('/api/v1/auth/login', {
            'email': 'testuser@example.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_resp.data['data']['token']

        me_resp = api_client.get('/api/v1/me',
                                 HTTP_AUTHORIZATION=f'Token {token}')
        assert me_resp.status_code == 200
        assert me_resp.data['data']['email'] == 'testuser@example.com'


class TestProfile:
    """GET /api/v1/me"""

    def test_me_authenticated(self, authenticated_client, test_user):
        """Authenticated user can fetch their profile."""
        response = authenticated_client.get('/api/v1/me')
        assert response.status_code == 200
        assert response.data['success'] is True
        data = response.data['data']
        assert data['email'] == test_user.email
        assert 'id' in data
        assert 'name' in data

    def test_me_unauthenticated(self, api_client):
        """Unauthenticated request to /me returns 401."""
        response = api_client.get('/api/v1/me')
        assert response.status_code == 401

    def test_me_response_fields(self, authenticated_client):
        """Profile response contains expected fields."""
        response = authenticated_client.get('/api/v1/me')
        data = response.data['data']
        expected_fields = {
            'id', 'email', 'email_verified', 'name', 'avatar_url',
            'role', 'subscription_tier', 'has_whydud_email',
            'deletion_requested_at', 'created_at',
        }
        assert expected_fields.issubset(set(data.keys()))


class TestLogout:
    """POST /api/v1/auth/logout"""

    def test_logout_success(self, authenticated_client):
        """Authenticated user can logout."""
        response = authenticated_client.post('/api/v1/auth/logout')
        assert response.status_code == 200
        assert response.data['success'] is True

    def test_logout_unauthenticated(self, api_client):
        """Unauthenticated logout returns 401."""
        response = api_client.post('/api/v1/auth/logout')
        assert response.status_code == 401

    def test_logout_invalidates_token(self, api_client, test_user):
        """After logout, the same token should no longer work."""
        # Login
        login_resp = api_client.post('/api/v1/auth/login', {
            'email': 'testuser@example.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_resp.data['data']['token']

        # Logout
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        api_client.post('/api/v1/auth/logout')

        # Token should be invalid now
        me_resp = api_client.get('/api/v1/me',
                                 HTTP_AUTHORIZATION=f'Token {token}')
        assert me_resp.status_code == 401


class TestPasswordChange:
    """POST /api/v1/auth/change-password"""

    def test_change_password_success(self, authenticated_client):
        """Change password with correct current password succeeds."""
        response = authenticated_client.post('/api/v1/auth/change-password', {
            'current_password': 'TestPass123!',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True
        # Should return a new token
        assert 'token' in response.data['data']

    def test_change_password_wrong_current(self, authenticated_client):
        """Change password with wrong current password returns 400."""
        response = authenticated_client.post('/api/v1/auth/change-password', {
            'current_password': 'WrongOldPass!',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        assert response.status_code == 400
        assert response.data['error']['code'] == 'wrong_password'

    def test_change_password_weak_new(self, authenticated_client):
        """Change password with weak new password returns 400."""
        response = authenticated_client.post('/api/v1/auth/change-password', {
            'current_password': 'TestPass123!',
            'new_password': 'short',
        }, format='json')
        assert response.status_code == 400

    def test_change_password_unauthenticated(self, api_client):
        """Unauthenticated password change returns 401."""
        response = api_client.post('/api/v1/auth/change-password', {
            'current_password': 'TestPass123!',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        assert response.status_code == 401

    def test_change_password_new_token_works(self, api_client, test_user):
        """After password change, the new token should work."""
        # Login
        login_resp = api_client.post('/api/v1/auth/login', {
            'email': 'testuser@example.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_resp.data['data']['token']

        # Change password
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        change_resp = api_client.post('/api/v1/auth/change-password', {
            'current_password': 'TestPass123!',
            'new_password': 'NewStrongPass456!',
        }, format='json')
        new_token = change_resp.data['data']['token']

        # New token should work
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {new_token}')
        me_resp = api_client.get('/api/v1/me')
        assert me_resp.status_code == 200


class TestWhydudEmail:
    """Whydud email creation and availability check."""

    def test_check_username_available(self, api_client):
        """Check availability for an unused username returns available=True."""
        response = api_client.get(
            '/api/v1/email/whydud/check-availability',
            {'username': 'testusername123'}
        )
        assert response.status_code == 200
        assert response.data['data']['available'] is True

    def test_check_username_missing(self, api_client):
        """Check availability without username param returns 400."""
        response = api_client.get('/api/v1/email/whydud/check-availability')
        assert response.status_code == 400

    def test_check_username_with_domain(self, api_client):
        """Check availability with specific domain."""
        response = api_client.get(
            '/api/v1/email/whydud/check-availability',
            {'username': 'testuser99', 'domain': 'whyd.in'}
        )
        assert response.status_code == 200

    def test_check_username_invalid_domain(self, api_client):
        """Check availability with invalid domain returns 400."""
        response = api_client.get(
            '/api/v1/email/whydud/check-availability',
            {'username': 'testuser99', 'domain': 'invalid.com'}
        )
        assert response.status_code == 400

    def test_create_whydud_email(self, authenticated_client):
        """Create a whydud email for authenticated user."""
        response = authenticated_client.post('/api/v1/email/whydud/create', {
            'username': 'smoketestuser',
        }, format='json')
        assert response.status_code == 201
        assert response.data['success'] is True
        assert response.data['data']['username'] == 'smoketestuser'

    def test_create_whydud_email_duplicate(self, authenticated_client):
        """Creating a second whydud email returns 400 (already_exists)."""
        # Create first
        authenticated_client.post('/api/v1/email/whydud/create', {
            'username': 'firstuser',
        }, format='json')
        # Try second
        response = authenticated_client.post('/api/v1/email/whydud/create', {
            'username': 'seconduser',
        }, format='json')
        assert response.status_code == 400

    def test_create_whydud_email_unauthenticated(self, api_client):
        """Creating whydud email without auth returns 401."""
        response = api_client.post('/api/v1/email/whydud/create', {
            'username': 'nope',
        }, format='json')
        assert response.status_code == 401

    def test_get_whydud_email_status(self, authenticated_client):
        """Get whydud email status after creating one."""
        # Create first
        authenticated_client.post('/api/v1/email/whydud/create', {
            'username': 'statususer',
        }, format='json')
        # Check status
        response = authenticated_client.get('/api/v1/email/whydud/status')
        assert response.status_code == 200
        assert response.data['data']['username'] == 'statususer'

    def test_get_whydud_email_status_none(self, authenticated_client):
        """Get whydud email status when none exists returns 404."""
        response = authenticated_client.get('/api/v1/email/whydud/status')
        assert response.status_code == 404


class TestVerifyEmail:
    """POST /api/v1/auth/verify-email"""

    def test_verify_email_missing_fields(self, api_client):
        """Verify email without required fields returns 400."""
        response = api_client.post('/api/v1/auth/verify-email', {}, format='json')
        assert response.status_code == 400

    def test_verify_email_invalid_otp(self, api_client, test_user):
        """Verify email with wrong OTP returns 400."""
        response = api_client.post('/api/v1/auth/verify-email', {
            'email': 'testuser@example.com',
            'otp': '000000',
        }, format='json')
        assert response.status_code == 400


class TestForgotPassword:
    """POST /api/v1/auth/forgot-password"""

    def test_forgot_password_existing_email(self, api_client, test_user):
        """Forgot password for existing email returns 200 (no leaking)."""
        response = api_client.post('/api/v1/auth/forgot-password', {
            'email': 'testuser@example.com',
        }, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True

    def test_forgot_password_nonexistent_email(self, api_client):
        """Forgot password for nonexistent email still returns 200 (prevent enumeration)."""
        response = api_client.post('/api/v1/auth/forgot-password', {
            'email': 'nobody@example.com',
        }, format='json')
        assert response.status_code == 200
        assert response.data['success'] is True

    def test_forgot_password_missing_email(self, api_client):
        """Forgot password without email returns 400."""
        response = api_client.post('/api/v1/auth/forgot-password', {}, format='json')
        assert response.status_code == 400

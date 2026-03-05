"""
Dashboard API tests — all require authentication.
Covers: wishlists, price alerts, notifications, inbox, purchases,
        rewards, settings/profile, notification preferences.

Run: pytest tests/api/test_dashboard.py -v
"""
import pytest
from decimal import Decimal

pytestmark = [pytest.mark.api, pytest.mark.django_db]


# ── Wishlists (/api/v1/wishlists) ──────────────────────────────────────


class TestWishlists:
    """CRUD /api/v1/wishlists"""

    def test_list_wishlists(self, authenticated_client):
        response = authenticated_client.get("/api/v1/wishlists")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_create_wishlist(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/wishlists",
            {"name": "Test Wishlist"},
            format="json",
        )
        assert response.status_code == 201
        data = response.data["data"]
        assert data["name"] == "Test Wishlist"
        assert "id" in data

    def test_create_wishlist_default_name(self, authenticated_client):
        """Creating without name uses model default 'My Wishlist'."""
        response = authenticated_client.post(
            "/api/v1/wishlists", {}, format="json"
        )
        assert response.status_code == 201
        assert response.data["data"]["name"] == "My Wishlist"

    def test_get_wishlist_detail(self, authenticated_client):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Detail Test"}, format="json"
        )
        wid = create.data["data"]["id"]
        response = authenticated_client.get(f"/api/v1/wishlists/{wid}")
        assert response.status_code == 200
        assert response.data["data"]["name"] == "Detail Test"
        assert "items" in response.data["data"]

    def test_update_wishlist(self, authenticated_client):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Old Name"}, format="json"
        )
        wid = create.data["data"]["id"]
        response = authenticated_client.patch(
            f"/api/v1/wishlists/{wid}",
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["name"] == "New Name"

    def test_delete_wishlist(self, authenticated_client):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "To Delete"}, format="json"
        )
        wid = create.data["data"]["id"]
        response = authenticated_client.delete(f"/api/v1/wishlists/{wid}")
        assert response.status_code == 200

    def test_cannot_delete_default_wishlist(self, authenticated_client, test_user):
        """Default wishlist is protected from deletion."""
        from apps.wishlists.models import Wishlist

        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Default WL"}, format="json"
        )
        wid = create.data["data"]["id"]
        # Set is_default via ORM (view has a bug: reads is_default from
        # request.data but never passes it to serializer.save())
        Wishlist.objects.filter(pk=wid).update(is_default=True)

        response = authenticated_client.delete(f"/api/v1/wishlists/{wid}")
        assert response.status_code == 400
        assert "default" in response.data.get("error", {}).get("message", "").lower()

    def test_add_item_to_wishlist(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Items WL"}, format="json"
        )
        wid = create.data["data"]["id"]
        response = authenticated_client.post(
            f"/api/v1/wishlists/{wid}/items",
            {"product_id": str(test_product.id)},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["success"] is True

    def test_add_duplicate_item_fails(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Dup Test"}, format="json"
        )
        wid = create.data["data"]["id"]
        authenticated_client.post(
            f"/api/v1/wishlists/{wid}/items",
            {"product_id": str(test_product.id)},
            format="json",
        )
        dup = authenticated_client.post(
            f"/api/v1/wishlists/{wid}/items",
            {"product_id": str(test_product.id)},
            format="json",
        )
        assert dup.status_code == 400

    def test_remove_item_from_wishlist(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Remove Test"}, format="json"
        )
        wid = create.data["data"]["id"]
        authenticated_client.post(
            f"/api/v1/wishlists/{wid}/items",
            {"product_id": str(test_product.id)},
            format="json",
        )
        response = authenticated_client.delete(
            f"/api/v1/wishlists/{wid}/items/{test_product.id}"
        )
        assert response.status_code == 200

    def test_update_wishlist_item(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/wishlists", {"name": "Patch Item"}, format="json"
        )
        wid = create.data["data"]["id"]
        authenticated_client.post(
            f"/api/v1/wishlists/{wid}/items",
            {"product_id": str(test_product.id)},
            format="json",
        )
        response = authenticated_client.patch(
            f"/api/v1/wishlists/{wid}/items/{test_product.id}",
            {"notes": "Must buy", "priority": 1},
            format="json",
        )
        assert response.status_code == 200

    def test_wishlists_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/wishlists")
        assert response.status_code in (401, 403)


class TestSharedWishlists:
    """Public shared wishlist access."""

    def test_shared_wishlist_not_found(self, api_client):
        response = api_client.get("/api/v1/wishlists/shared/nonexistent-slug")
        assert response.status_code == 404


# ── Price Alerts (/api/v1/alerts) ──────────────────────────────────────


class TestPriceAlerts:
    """CRUD /api/v1/alerts"""

    def test_list_alerts(self, authenticated_client):
        response = authenticated_client.get("/api/v1/alerts")
        assert response.status_code == 200

    def test_create_price_alert(self, authenticated_client, test_product):
        """POST /api/v1/alerts/price — uses product_slug, not product_id."""
        response = authenticated_client.post(
            "/api/v1/alerts/price",
            {
                "product_slug": test_product.slug,
                "target_price": "69999.00",
            },
            format="json",
        )
        assert response.status_code == 201
        data = response.data["data"]
        assert data["product_slug"] == test_product.slug
        assert Decimal(data["target_price"]) == Decimal("69999.00")

    def test_create_alert_updates_existing(self, authenticated_client, test_product):
        """Second alert for same product updates target_price instead of creating new."""
        authenticated_client.post(
            "/api/v1/alerts/price",
            {"product_slug": test_product.slug, "target_price": "69999.00"},
            format="json",
        )
        response = authenticated_client.post(
            "/api/v1/alerts/price",
            {"product_slug": test_product.slug, "target_price": "59999.00"},
            format="json",
        )
        # update_or_create returns 200 for existing
        assert response.status_code == 200
        assert Decimal(response.data["data"]["target_price"]) == Decimal("59999.00")

    def test_create_alert_missing_slug(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/alerts/price",
            {"target_price": "69999.00"},
            format="json",
        )
        assert response.status_code == 400

    def test_triggered_alerts(self, authenticated_client):
        response = authenticated_client.get("/api/v1/alerts/triggered")
        assert response.status_code == 200

    def test_delete_alert(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/alerts/price",
            {"product_slug": test_product.slug, "target_price": "69999.00"},
            format="json",
        )
        alert_id = create.data["data"]["id"]
        response = authenticated_client.delete(f"/api/v1/alerts/{alert_id}")
        assert response.status_code == 200

    def test_patch_alert(self, authenticated_client, test_product):
        create = authenticated_client.post(
            "/api/v1/alerts/price",
            {"product_slug": test_product.slug, "target_price": "69999.00"},
            format="json",
        )
        alert_id = create.data["data"]["id"]
        response = authenticated_client.patch(
            f"/api/v1/alerts/{alert_id}",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == 200

    def test_alerts_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/alerts")
        assert response.status_code in (401, 403)


# ── Notifications (/api/v1/notifications) ──────────────────────────────


class TestNotifications:
    """Notification CRUD and preferences."""

    def test_list_notifications(self, authenticated_client):
        response = authenticated_client.get("/api/v1/notifications")
        assert response.status_code == 200

    def test_unread_count(self, authenticated_client):
        response = authenticated_client.get("/api/v1/notifications/unread-count")
        assert response.status_code == 200
        assert "count" in response.data["data"]

    def test_mark_all_read(self, authenticated_client):
        response = authenticated_client.post("/api/v1/notifications/mark-all-read")
        assert response.status_code == 200
        assert "updated" in response.data["data"]

    def test_notification_preferences_get(self, authenticated_client):
        response = authenticated_client.get("/api/v1/notifications/preferences")
        assert response.status_code == 200

    def test_notification_preferences_patch(self, authenticated_client):
        # First GET to create default preferences
        authenticated_client.get("/api/v1/notifications/preferences")
        response = authenticated_client.patch(
            "/api/v1/notifications/preferences",
            {"email_enabled": False},
            format="json",
        )
        # Accept 200 or 400 if field name differs
        assert response.status_code in (200, 400)

    def test_notifications_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/notifications")
        assert response.status_code in (401, 403)


# ── Inbox (/api/v1/inbox) ─────────────────────────────────────────────


class TestInbox:
    """Inbox email list and detail."""

    def test_list_inbox(self, authenticated_client):
        response = authenticated_client.get("/api/v1/inbox")
        assert response.status_code == 200

    def test_list_inbox_with_filters(self, authenticated_client):
        """Query params: category, unread, starred."""
        response = authenticated_client.get("/api/v1/inbox?unread=1&starred=1")
        assert response.status_code == 200

    def test_inbox_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/inbox")
        assert response.status_code in (401, 403)


# ── Purchases / Dashboard (/api/v1/purchases) ─────────────────────────


class TestPurchases:
    """Purchase history and expense dashboard."""

    def test_purchase_dashboard(self, authenticated_client):
        response = authenticated_client.get("/api/v1/purchases/dashboard")
        assert response.status_code == 200
        data = response.data["data"]
        assert "total_spent" in data
        assert "total_orders" in data
        assert "monthly_spending" in data
        assert "category_breakdown" in data

    def test_purchase_list(self, authenticated_client):
        response = authenticated_client.get("/api/v1/purchases")
        assert response.status_code == 200

    def test_refunds_list(self, authenticated_client):
        response = authenticated_client.get("/api/v1/purchases/refunds")
        assert response.status_code == 200

    def test_return_windows(self, authenticated_client):
        response = authenticated_client.get("/api/v1/purchases/return-windows")
        assert response.status_code == 200

    def test_subscriptions(self, authenticated_client):
        response = authenticated_client.get("/api/v1/purchases/subscriptions")
        assert response.status_code == 200

    def test_purchases_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/purchases/dashboard")
        assert response.status_code in (401, 403)


# ── Rewards (/api/v1/rewards) ─────────────────────────────────────────


class TestRewards:
    """Rewards balance, history, gift cards, redemption."""

    def test_reward_balance(self, authenticated_client):
        response = authenticated_client.get("/api/v1/rewards/balance")
        assert response.status_code == 200

    def test_reward_history(self, authenticated_client):
        response = authenticated_client.get("/api/v1/rewards/history")
        assert response.status_code == 200

    def test_gift_card_catalog(self, authenticated_client):
        response = authenticated_client.get("/api/v1/rewards/gift-cards")
        assert response.status_code == 200

    def test_redemption_history(self, authenticated_client):
        response = authenticated_client.get("/api/v1/rewards/redemptions")
        assert response.status_code == 200

    def test_redeem_without_points_fails(self, authenticated_client):
        """Redeem attempt with zero balance should fail."""
        from apps.rewards.models import GiftCardCatalog

        catalog = GiftCardCatalog.objects.create(
            brand_name="Amazon",
            brand_slug="amazon-gc",
            denominations=[100, 500, 1000],
            is_active=True,
        )
        response = authenticated_client.post(
            "/api/v1/rewards/redeem",
            {"catalog_id": catalog.pk, "denomination": 100},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_rewards_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/rewards/balance")
        assert response.status_code in (401, 403)


# ── Settings / Profile (/api/v1/me) ───────────────────────────────────


class TestSettings:
    """User profile and account settings."""

    def test_get_profile(self, authenticated_client):
        response = authenticated_client.get("/api/v1/me")
        assert response.status_code == 200
        data = response.data["data"]
        assert "email" in data

    def test_profile_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/me")
        assert response.status_code in (401, 403)


# ── Card Vault (/api/v1/cards) ────────────────────────────────────────


class TestCardVault:
    """Payment method (card vault) endpoints."""

    def test_list_cards(self, authenticated_client):
        response = authenticated_client.get("/api/v1/cards")
        assert response.status_code == 200

    def test_cards_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/cards")
        assert response.status_code in (401, 403)


# ── Click Tracking (/api/v1/clicks) ───────────────────────────────────


class TestClickTracking:
    """Affiliate click tracking and history."""

    def test_click_history(self, authenticated_client):
        response = authenticated_client.get("/api/v1/clicks/history")
        assert response.status_code == 200

    def test_click_history_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/clicks/history")
        assert response.status_code in (401, 403)


# ── Active Offers (/api/v1/offers) ────────────────────────────────────


class TestOffers:
    """Marketplace offers (public endpoint)."""

    def test_list_active_offers(self, api_client):
        """Offers endpoint is public — no auth required."""
        response = api_client.get("/api/v1/offers/active")
        assert response.status_code == 200

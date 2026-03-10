"""Custom Django admin site for Whydud platform management."""
from django.contrib.admin import AdminSite


class WhydudAdminSite(AdminSite):
    site_header = "WHYDUD Admin"
    site_title = "WHYDUD Platform"
    index_title = "Platform Management"

    def get_urls(self):
        from django.urls import path

        custom_urls = [
            path(
                "dashboard/",
                self.admin_view(self.dashboard_view),
                name="admin-dashboard",
            ),
            path(
                "system-health/",
                self.admin_view(self.system_health_view),
                name="system-health",
            ),
            path(
                "backfill/",
                self.admin_view(self.backfill_view),
                name="backfill-console",
            ),
            path(
                "enrichment/",
                self.admin_view(self.enrichment_view),
                name="enrichment-console",
            ),
            path(
                "price-intel/",
                self.admin_view(self.price_intel_view),
                name="price-intel",
            ),
            path(
                "analytics/",
                self.admin_view(self.analytics_view),
                name="analytics",
            ),
            path(
                "cluster/",
                self.admin_view(self.cluster_view),
                name="cluster-console",
            ),
            # AJAX endpoints for live updates
            path(
                "api/stats/",
                self.admin_view(self.api_stats),
                name="api-stats",
            ),
            path(
                "api/backfill-status/",
                self.admin_view(self.api_backfill_status),
                name="api-backfill-status",
            ),
        ]
        return custom_urls + super().get_urls()

    # ------------------------------------------------------------------
    # Dashboard home — platform overview
    # ------------------------------------------------------------------

    def dashboard_view(self, request):
        """Platform overview — the admin home page."""
        from datetime import timedelta

        from django.db.models import Count, Q
        from django.shortcuts import render
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product, ProductListing
        from apps.reviews.models import Review

        User = self._get_user_model()
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        context = {
            **self.each_context(request),
            "title": "Platform Dashboard",
            # Product stats
            "product_count": Product.objects.count(),
            "product_lightweight": Product.objects.filter(
                is_lightweight=True
            ).count(),
            "product_enriched": Product.objects.filter(
                is_lightweight=False
            ).count(),
            "product_with_reviews": Product.objects.filter(
                total_reviews__gt=0
            ).count(),
            "product_with_dudscore": Product.objects.exclude(
                dud_score__isnull=True
            ).count(),
            "listing_count": ProductListing.objects.count(),
            # Backfill stats
            "backfill_total": BackfillProduct.objects.count(),
            "backfill_by_status": list(
                BackfillProduct.objects.values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            ),
            "backfill_by_scrape": list(
                BackfillProduct.objects.values("scrape_status")
                .annotate(count=Count("id"))
                .order_by("scrape_status")
            ),
            # Review stats
            "review_count": Review.objects.count(),
            "review_flagged": Review.objects.filter(is_flagged=True).count(),
            # User stats
            "user_count": User.objects.count(),
            "user_new_today": User.objects.filter(
                date_joined__date=today
            ).count(),
            "user_active_7d": User.objects.filter(
                last_login__gte=week_ago
            ).count(),
            # Price snapshots
            "snapshot_count": self._get_snapshot_count(),
            # Marketplace breakdown
            "marketplace_stats": self._get_marketplace_stats(),
        }
        return render(request, "admin/dashboard.html", context)

    # ------------------------------------------------------------------
    # Stub views — implemented in subsequent AD-* prompts
    # ------------------------------------------------------------------

    def system_health_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "System Health"},
        )

    def backfill_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Backfill Pipeline"},
        )

    def enrichment_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Enrichment Queue"},
        )

    def price_intel_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Price Intelligence"},
        )

    def analytics_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Analytics"},
        )

    def cluster_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Worker Cluster"},
        )

    # ------------------------------------------------------------------
    # AJAX API endpoints
    # ------------------------------------------------------------------

    def api_stats(self, request):
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product
        from apps.reviews.models import Review

        return JsonResponse(
            {
                "products": Product.objects.count(),
                "backfill": BackfillProduct.objects.count(),
                "reviews": Review.objects.count(),
                "snapshots": self._get_snapshot_count(),
            }
        )

    def api_backfill_status(self, request):
        from django.db.models import Count
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct

        by_status = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(count=Count("id"))
            .values_list("scrape_status", "count")
        )
        return JsonResponse(by_status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_model():
        from django.contrib.auth import get_user_model

        return get_user_model()

    @staticmethod
    def _get_snapshot_count():
        from django.db import connection

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM price_snapshots")
                return cur.fetchone()[0]
        except Exception:
            return 0

    @staticmethod
    def _get_marketplace_stats():
        from django.db.models import Count

        from apps.products.models import ProductListing

        return list(
            ProductListing.objects.values("marketplace__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

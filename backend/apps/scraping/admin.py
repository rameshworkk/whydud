"""Enhanced scraping console — Apex-style ScraperJob admin with status badges, run buttons, stats header."""
from datetime import timedelta

from django.contrib import admin
from django.db.models import Avg, Count, Q
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import ScraperJob


@admin.register(ScraperJob)
class ScraperJobAdmin(admin.ModelAdmin):
    list_display = [
        "spider_display",
        "marketplace_badge",
        "status_badge",
        "items_display",
        "failed_display",
        "duration_display",
        "triggered_badge",
        "started_ago",
    ]
    list_filter = ["status", "marketplace__slug", "triggered_by", "started_at"]
    search_fields = ["marketplace__slug", "spider_name"]
    readonly_fields = [
        "id",
        "marketplace",
        "spider_name",
        "status",
        "started_at",
        "finished_at",
        "items_scraped",
        "items_failed",
        "error_message",
        "triggered_by",
        "created_at",
    ]
    ordering = ["-started_at"]
    list_per_page = 30
    list_select_related = ["marketplace"]
    actions = [
        "run_amazon_spider",
        "run_flipkart_spider",
        "run_amazon_reviews",
        "run_flipkart_reviews",
    ]

    # ------------------------------------------------------------------
    # Custom display columns — Apex-style
    # ------------------------------------------------------------------

    @admin.display(description="Spider", ordering="spider_name")
    def spider_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.spider_name or "\u2014",
        )

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        name = obj.marketplace.name if obj.marketplace else "\u2014"
        colors = {
            "Amazon.in": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "Flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = colors.get(name, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, name,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status_colors = {
            "completed": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "running": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "queued": "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
            "partial": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
        }
        classes = status_colors.get(obj.status, status_colors["queued"])
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-semibold {}">{}</span>',
            classes, obj.get_status_display(),
        )

    @admin.display(description="Items", ordering="items_scraped")
    def items_display(self, obj):
        count = obj.items_scraped or 0
        if count > 0:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-700 dark:text-slate-300">{}</span>',
                f"{count:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Failed", ordering="items_failed")
    def failed_display(self, obj):
        count = obj.items_failed or 0
        if count > 0:
            return format_html(
                '<span class="text-[13px] font-medium text-red-600 dark:text-red-400">{}</span>',
                f"{count:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Duration", ordering="finished_at")
    def duration_display(self, obj):
        if not obj.started_at:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        end = obj.finished_at or timezone.now()
        delta = end - obj.started_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        if total_seconds < 60:
            dur = f"{total_seconds}s"
        else:
            minutes, seconds = divmod(total_seconds, 60)
            if minutes < 60:
                dur = f"{minutes}m {seconds}s"
            else:
                hours, minutes = divmod(minutes, 60)
                dur = f"{hours}h {minutes}m"
        return format_html(
            '<span class="text-[12px] font-mono text-slate-600 dark:text-slate-400">{}</span>',
            dur,
        )

    @admin.display(description="Trigger")
    def triggered_badge(self, obj):
        trigger = obj.triggered_by or "\u2014"
        trigger_colors = {
            "celery": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "admin": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "manual": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "schedule": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = trigger_colors.get(
            trigger.lower() if trigger != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, trigger,
        )

    @admin.display(description="Started", ordering="started_at")
    def started_ago(self, obj):
        if obj.started_at:
            delta = timezone.now() - obj.started_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.started_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.started_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    # ------------------------------------------------------------------
    # Admin actions — trigger spiders
    # ------------------------------------------------------------------

    @admin.action(description="Run Amazon.in product spider now")
    def run_amazon_spider(self, request, queryset):
        self._trigger_spider(request, "amazon-in", "marketplace")

    @admin.action(description="Run Flipkart product spider now")
    def run_flipkart_spider(self, request, queryset):
        self._trigger_spider(request, "flipkart", "marketplace")

    @admin.action(description="Run Amazon.in review spider now")
    def run_amazon_reviews(self, request, queryset):
        self._trigger_spider(request, "amazon-in", "review")

    @admin.action(description="Run Flipkart review spider now")
    def run_flipkart_reviews(self, request, queryset):
        self._trigger_spider(request, "flipkart", "review")

    def _trigger_spider(self, request, marketplace_slug, spider_type):
        from django.contrib import messages

        try:
            if spider_type == "review":
                from apps.scraping.tasks import run_review_spider

                result = run_review_spider.delay(marketplace_slug)
            else:
                from apps.scraping.tasks import run_marketplace_spider

                result = run_marketplace_spider.delay(marketplace_slug)
            messages.success(
                request,
                f"{spider_type.title()} spider for {marketplace_slug} queued. "
                f"Task: {result.id}",
            )
        except Exception as e:
            messages.error(request, f"Failed to queue spider: {e}")

    # ------------------------------------------------------------------
    # Custom URLs — scrape single URL form
    # ------------------------------------------------------------------

    def get_urls(self):
        custom_urls = [
            path(
                "scrape-single/",
                self.admin_site.admin_view(self.scrape_single_view),
                name="scraping_scraperjob_scrape_single",
            ),
        ]
        return custom_urls + super().get_urls()

    def scrape_single_view(self, request):
        from django.contrib import messages
        from django.shortcuts import redirect

        if request.method == "POST":
            url = request.POST.get("url", "").strip()
            marketplace_slug = request.POST.get("marketplace", "").strip()
            if url and marketplace_slug:
                try:
                    from apps.scraping.tasks import scrape_product_adhoc

                    result = scrape_product_adhoc.delay(url, marketplace_slug)
                    messages.success(
                        request,
                        f"Ad-hoc scrape queued for {marketplace_slug}: {url[:80]}... "
                        f"Task: {result.id}",
                    )
                except Exception as e:
                    messages.error(request, f"Failed to queue scrape: {e}")
            else:
                messages.error(request, "URL and marketplace are required.")
            return redirect("admin:scraping_scraperjob_changelist")

        # GET — shouldn't normally happen, redirect to changelist
        return redirect("admin:scraping_scraperjob_changelist")

    # ------------------------------------------------------------------
    # Stats header via changelist_view override
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # Jobs today
        jobs_today = ScraperJob.objects.filter(started_at__gte=today)
        jobs_today_success = jobs_today.filter(status="completed").count()
        jobs_today_failed = jobs_today.filter(status="failed").count()
        jobs_today_total = jobs_today.count()

        # Items scraped today
        items_today = (
            jobs_today.filter(status__in=["completed", "partial"]).aggregate(
                total=Count("id"),
                items=Avg("items_scraped"),  # we actually want Sum
            )
        )
        # Use raw aggregation for sum
        from django.db.models import Sum

        items_scraped_today = (
            jobs_today.filter(status__in=["completed", "partial"]).aggregate(
                total=Sum("items_scraped")
            )["total"]
            or 0
        )

        # Success rate 7d
        jobs_7d = ScraperJob.objects.filter(started_at__gte=week_ago)
        jobs_7d_total = jobs_7d.exclude(status="queued").count()
        jobs_7d_success = jobs_7d.filter(
            status__in=["completed", "partial"]
        ).count()
        success_rate_7d = (
            round(jobs_7d_success / jobs_7d_total * 100, 1) if jobs_7d_total else 0
        )

        # Last successful scrape per marketplace
        last_scrapes = []
        marketplace_slugs = (
            ScraperJob.objects.filter(status="completed")
            .values_list("marketplace__slug", flat=True)
            .distinct()
        )
        for slug in marketplace_slugs:
            last_job = (
                ScraperJob.objects.filter(
                    marketplace__slug=slug, status="completed"
                )
                .order_by("-finished_at")
                .first()
            )
            if last_job and last_job.finished_at:
                ago = now - last_job.finished_at
                if ago.days > 0:
                    ago_str = f"{ago.days}d ago"
                elif ago.seconds >= 3600:
                    ago_str = f"{ago.seconds // 3600}h ago"
                else:
                    ago_str = f"{ago.seconds // 60}m ago"
                last_scrapes.append(
                    {
                        "marketplace": slug,
                        "spider": last_job.spider_name,
                        "finished": timezone.localtime(last_job.finished_at).strftime("%Y-%m-%d %H:%M"),
                        "ago": ago_str,
                        "items": last_job.items_scraped,
                    }
                )

        # Currently running
        running_count = ScraperJob.objects.filter(status="running").count()

        # Scrape single URL form — marketplace choices
        from apps.products.models import Marketplace

        marketplaces = list(
            Marketplace.objects.values_list("slug", flat=True).order_by("slug")
        )

        extra_context.update(
            {
                "stats_header": True,
                "jobs_today_success": jobs_today_success,
                "jobs_today_failed": jobs_today_failed,
                "jobs_today_total": jobs_today_total,
                "items_scraped_today": items_scraped_today,
                "success_rate_7d": success_rate_7d,
                "jobs_7d_total": jobs_7d_total,
                "last_scrapes": last_scrapes,
                "running_count": running_count,
                "marketplace_choices": marketplaces,
                "scrape_single_url": reverse(
                    "admin:scraping_scraperjob_scrape_single"
                ),
            }
        )

        return super().changelist_view(request, extra_context=extra_context)

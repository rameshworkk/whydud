from django.contrib import admin
from .models import DetectedSubscription, InboxEmail, ParsedOrder, RefundTracking, ReturnWindow

@admin.register(InboxEmail)
class InboxEmailAdmin(admin.ModelAdmin):
    list_display = ["user", "sender_address", "subject", "category", "parse_status", "received_at"]
    list_filter = ["category", "parse_status"]
    search_fields = ["sender_address", "subject"]
    # NOTE: body fields contain encrypted data — never display in admin

@admin.register(ParsedOrder)
class ParsedOrderAdmin(admin.ModelAdmin):
    list_display = ["user", "marketplace", "product_name", "total_amount", "order_date"]
    list_filter = ["marketplace", "source"]
    search_fields = ["product_name", "order_id"]

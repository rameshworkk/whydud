"""Django admin registration for accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OAuthConnection, PaymentMethod, TCOProfile, User, WhydudEmail


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "name", "role", "subscription_tier", "has_whydud_email", "is_suspended", "created_at"]
    list_filter = ["role", "subscription_tier", "has_whydud_email", "is_suspended"]
    search_fields = ["email", "name"]
    ordering = ["-created_at"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("name", "avatar_url")}),
        ("Status", {"fields": ("role", "subscription_tier", "subscription_expires_at",
                               "has_whydud_email", "trust_score", "is_suspended")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("last_login_at", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at", "last_login_at"]
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(WhydudEmail)
class WhydudEmailAdmin(admin.ModelAdmin):
    list_display = ["username", "user", "is_active", "total_emails_received", "created_at"]
    search_fields = ["username", "user__email"]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["user", "method_type", "bank_name", "card_variant", "is_preferred"]
    list_filter = ["method_type"]
    search_fields = ["user__email", "bank_name"]

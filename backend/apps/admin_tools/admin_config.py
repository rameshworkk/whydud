"""Custom AdminConfig that replaces django.contrib.admin.

Put 'apps.admin_tools.admin_config.WhydudAdminConfig' in INSTALLED_APPS
instead of 'django.contrib.admin'.  All @admin.register() calls
and admin.site references then use WhydudAdminSite automatically.
"""
from django.contrib.admin.apps import AdminConfig


class WhydudAdminConfig(AdminConfig):
    default_site = "apps.admin_tools.admin_site.WhydudAdminSite"

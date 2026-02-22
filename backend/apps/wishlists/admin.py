from django.contrib import admin
from .models import Wishlist, WishlistItem

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "is_default", "is_public"]
    search_fields = ["user__email", "name"]

admin.site.register(WishlistItem)

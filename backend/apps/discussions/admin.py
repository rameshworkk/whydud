from django.contrib import admin
from .models import DiscussionThread, DiscussionReply

@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "thread_type", "reply_count", "is_removed", "created_at"]
    list_filter = ["thread_type", "is_removed", "is_pinned"]
    search_fields = ["title", "body"]

@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ["thread", "user", "is_accepted", "is_removed", "created_at"]

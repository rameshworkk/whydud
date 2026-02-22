from django.contrib import admin
from .models import Review, ReviewVote

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "rating", "reviewer_name", "is_verified_purchase", "is_flagged", "credibility_score"]
    list_filter = ["rating", "is_verified_purchase", "is_flagged"]
    search_fields = ["reviewer_name", "title", "body"]
    readonly_fields = ["id", "content_hash", "created_at"]

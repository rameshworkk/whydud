import uuid
from django.db import models

class DiscussionThread(models.Model):
    class ThreadType(models.TextChoices):
        QUESTION = "question", "Question"
        EXPERIENCE = "experience", "Experience"
        COMPARISON = "comparison", "Comparison"
        TIP = "tip", "Tip"
        ALERT = "alert", "Alert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="discussion_threads")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    thread_type = models.CharField(max_length=20, choices=ThreadType.choices)
    title = models.CharField(max_length=300)
    body = models.TextField()
    reply_count = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    last_reply_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'community"."discussion_threads'
        indexes = [models.Index(fields=["product", "-created_at"])]

    def __str__(self) -> str:
        return self.title


class DiscussionReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(DiscussionThread, on_delete=models.CASCADE, related_name="replies")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    parent_reply = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    body = models.TextField()
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    is_accepted = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'community"."discussion_replies'

    def __str__(self) -> str:
        return f"Reply by {self.user.email} on thread {self.thread_id}"


class DiscussionVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    target_type = models.CharField(max_length=10)  # thread | reply
    target_id = models.UUIDField()
    vote = models.SmallIntegerField()  # 1 or -1
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community"."discussion_votes'
        unique_together = [("user", "target_type", "target_id")]
        constraints = [models.CheckConstraint(check=models.Q(vote__in=[1, -1]), name="disc_vote_value")]

    def __str__(self) -> str:
        return f"{self.user.email} {'▲' if self.vote == 1 else '▼'} {self.target_type} {self.target_id}"

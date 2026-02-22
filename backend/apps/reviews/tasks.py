from celery import shared_task

@shared_task(queue="scoring")
def run_sentiment_analysis(review_id: str) -> None:
    """Run spaCy + TextBlob sentiment analysis on a review."""
    # TODO Sprint 3 Week 7
    pass

@shared_task(queue="scoring")
def detect_fake_reviews(product_id: str) -> None:
    """Rule-based fake review detection (copy-paste, burst, distribution)."""
    # TODO Sprint 3 Week 7
    pass

@shared_task(queue="scoring")
def aggregate_review_sentiment(product_id: str) -> None:
    """Generate AI summary: top 3 pros, top 3 cons for a product."""
    # TODO Sprint 3 Week 7
    pass

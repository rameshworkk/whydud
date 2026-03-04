"""Account services — notification creation and helpers."""
from __future__ import annotations

import logging
from typing import Any

from .models import Notification, User

logger = logging.getLogger(__name__)


def create_notification(
    user_id: str,
    type: str,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
    action_label: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Notification | None:
    """Create an in-app notification for a user.

    Args:
        user_id: UUID of the target user.
        type: One of Notification.Type values (e.g. 'price_drop', 'order_detected').
        title: Short notification headline.
        body: Optional longer description.
        action_url: Deep link (e.g. '/product/slug' or '/inbox/123').
        action_label: CTA text (e.g. 'Buy Now', 'View', 'Return').
        entity_type: Related entity kind ('product', 'review', 'order', 'alert').
        entity_id: Related entity identifier.
        metadata: Extra data (e.g. {price, marketplace, product_name}).

    Returns:
        The created Notification, or None if the user doesn't exist or type is invalid.
    """
    valid_types = {choice[0] for choice in Notification.Type.choices}
    if type not in valid_types:
        logger.warning("Invalid notification type: %s", type)
        return None

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Cannot create notification — user %s not found", user_id)
        return None

    return Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body or "",
        action_url=action_url or "",
        action_label=action_label or "",
        entity_type=entity_type or "",
        entity_id=entity_id or "",
        metadata=metadata or {},
    )

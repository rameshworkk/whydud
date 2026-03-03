"""Discord webhook notifications for Celery task monitoring."""

import json
import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Colors for Discord embeds
COLOR_SUCCESS = 0x16A34A  # green
COLOR_FAILURE = 0xDC2626  # red
COLOR_RETRY = 0xFBBF24  # yellow


def _get_webhook_url() -> str:
    """Return the Discord webhook URL from Django settings or env."""
    try:
        from django.conf import settings

        return getattr(settings, "DISCORD_WEBHOOK_URL", "") or ""
    except Exception:
        return os.environ.get("DISCORD_WEBHOOK_URL", "")


def _truncate(text: str, max_len: int = 1000) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_result(result) -> str:
    """Format a task result for display in Discord."""
    if result is None:
        return "None"
    if isinstance(result, dict):
        return json.dumps(result, indent=2, default=str)
    return str(result)


def _node_role() -> str:
    return os.environ.get("NODE_ROLE", "unknown")


def send_discord_embed(embed: dict) -> None:
    """POST a Discord embed to the configured webhook URL.

    Silent-fails: logs a warning on error, never raises.
    """
    url = _get_webhook_url()
    if not url:
        return

    payload = {"embeds": [embed]}
    try:
        resp = httpx.post(url, json=payload, timeout=5.0)
        if resp.status_code == 429:
            logger.warning("Discord rate limited, notification dropped")
        elif resp.status_code >= 400:
            logger.warning(
                "Discord webhook returned %s: %s", resp.status_code, resp.text[:200]
            )
    except Exception:
        logger.warning("Failed to send Discord notification", exc_info=True)


def notify_task_success(
    task_name: str,
    result,
    runtime: float | None = None,
    worker: str = "",
    queue: str = "",
) -> None:
    """Send a green success embed to Discord."""
    fields = [
        {"name": "Task", "value": f"`{task_name}`", "inline": False},
    ]
    if queue:
        fields.append({"name": "Queue", "value": f"`{queue}`", "inline": True})
    if worker:
        fields.append({"name": "Worker", "value": f"`{worker}`", "inline": True})
    if runtime is not None:
        fields.append(
            {"name": "Runtime", "value": f"`{runtime:.2f}s`", "inline": True}
        )

    result_str = _truncate(_format_result(result))
    fields.append({"name": "Result", "value": f"```json\n{result_str}\n```", "inline": False})

    send_discord_embed(
        {
            "title": "Task Succeeded",
            "color": COLOR_SUCCESS,
            "fields": fields,
            "footer": {"text": f"whydud \u00b7 {_node_role()}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def notify_task_failure(
    task_name: str,
    exception: str,
    traceback_str: str = "",
    worker: str = "",
    queue: str = "",
) -> None:
    """Send a red failure embed to Discord."""
    fields = [
        {"name": "Task", "value": f"`{task_name}`", "inline": False},
    ]
    if queue:
        fields.append({"name": "Queue", "value": f"`{queue}`", "inline": True})
    if worker:
        fields.append({"name": "Worker", "value": f"`{worker}`", "inline": True})

    fields.append({"name": "Error", "value": f"```\n{_truncate(exception, 500)}\n```", "inline": False})

    if traceback_str:
        fields.append(
            {
                "name": "Traceback",
                "value": f"```\n{_truncate(traceback_str, 800)}\n```",
                "inline": False,
            }
        )

    send_discord_embed(
        {
            "title": "Task Failed",
            "color": COLOR_FAILURE,
            "fields": fields,
            "footer": {"text": f"whydud \u00b7 {_node_role()}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def notify_task_retry(
    task_name: str,
    reason: str,
    retries: int = 0,
    worker: str = "",
    queue: str = "",
) -> None:
    """Send a yellow retry embed to Discord."""
    fields = [
        {"name": "Task", "value": f"`{task_name}`", "inline": False},
    ]
    if queue:
        fields.append({"name": "Queue", "value": f"`{queue}`", "inline": True})
    if worker:
        fields.append({"name": "Worker", "value": f"`{worker}`", "inline": True})
    if retries:
        fields.append({"name": "Retry #", "value": f"`{retries}`", "inline": True})

    fields.append({"name": "Reason", "value": f"```\n{_truncate(reason, 500)}\n```", "inline": False})

    send_discord_embed(
        {
            "title": "Task Retrying",
            "color": COLOR_RETRY,
            "fields": fields,
            "footer": {"text": f"whydud \u00b7 {_node_role()}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

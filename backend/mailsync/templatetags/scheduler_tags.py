import os
from datetime import datetime, timezone
from pathlib import Path

from django import template

register = template.Library()

HEARTBEAT_FILE = Path(
    os.environ.get("SCHEDULER_HEARTBEAT_FILE", "/tmp/scheduler_heartbeat")
)
STALE_MINUTES = 20


def _format_age(total_seconds: int) -> str:
    """Compact human age, e.g. '45s', '2m 45s', '1h 5m'."""
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds < 3600:
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}m {seconds}s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"


@register.inclusion_tag("admin/mailsync/scheduler_status.html")
def scheduler_status():
    if not HEARTBEAT_FILE.exists():
        return {"status": "unknown", "last_run": None, "age_label": None}

    mtime = datetime.fromtimestamp(HEARTBEAT_FILE.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    total_seconds = max(0, int((now - mtime).total_seconds()))

    status = "ok" if total_seconds < STALE_MINUTES * 60 else "stale"
    return {
        "status": status,
        "last_run": mtime,
        "age_label": _format_age(total_seconds),
        "last_run_epoch": int(mtime.timestamp()),
        "stale_seconds": STALE_MINUTES * 60,
    }

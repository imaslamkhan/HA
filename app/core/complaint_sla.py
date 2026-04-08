"""SLA deadlines derived from complaint priority (master spec J3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

RESOLVED_STATUSES = frozenset({"resolved", "closed", "rejected"})


def sla_hours_for_priority(priority: str) -> int:
    p = (priority or "medium").strip().lower()
    return {
        "low": 72,
        "medium": 48,
        "high": 24,
        "urgent": 4,
    }.get(p, 48)


def compute_sla_deadline(created_at: datetime, priority: str) -> datetime:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(hours=sla_hours_for_priority(priority))


def is_sla_breached(
    *,
    status: str,
    created_at: datetime,
    priority: str,
    resolved_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    st = (status or "").strip().lower()
    if st in RESOLVED_STATUSES or resolved_at is not None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now > compute_sla_deadline(created_at, priority)

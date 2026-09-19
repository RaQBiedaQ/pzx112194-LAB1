# ai-generated: 90% - Claude (AI assistant) generated this module under the student's direction (decisions, review, testing)
"""Priority computation and SLA due-instant math (REQUIREMENTS.md R-04..R-16, API.md sections 3-5)."""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

from . import config

WARSAW = ZoneInfo("Europe/Warsaw")

BUSINESS_OPEN = time(8, 0, 0)
BUSINESS_CLOSE = time(16, 0, 0)

# impact (1..3) x urgency (1..3) -> priority, API.md section 3 / REQUIREMENTS.md R-04.
_MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}

# priority -> (acknowledge target, resolve target), REQUIREMENTS.md R-12 / API.md section 4.
_TARGETS = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    """API.md section 3. Decision C3 governs the VIP floor."""
    base = _MATRIX[(impact, urgency)]
    if config.DECISION_C3 == "vip" and vip and base in ("P3", "P4"):
        return "P2"
    return base


def targets_for(priority: str) -> tuple[timedelta, timedelta]:
    return _TARGETS[priority]


def uses_business_clock(priority: str) -> bool:
    """Decision C1: does this priority's SLA clock pause outside business hours?"""
    if priority == "P1":
        return config.DECISION_C1 == "business"
    return True


def _is_business_day(local_dt: datetime) -> bool:
    return local_dt.weekday() < 5  # Monday=0 .. Friday=4


def _next_business_open(local_dt: datetime) -> datetime:
    """The next instant (possibly local_dt itself) that is inside or at the start of a business
    window, given local_dt is already >= a business open or needs to roll forward to one."""
    d = local_dt
    while True:
        if _is_business_day(d):
            open_dt = d.replace(hour=BUSINESS_OPEN.hour, minute=0, second=0, microsecond=0)
            close_dt = d.replace(hour=BUSINESS_CLOSE.hour, minute=0, second=0, microsecond=0)
            if d < open_dt:
                return open_dt
            if d < close_dt:
                return d
            # at or after closing: roll to next day's opening
            d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            continue
        # weekend: roll to next day's midnight and check again
        d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def business_due_instant(start_utc: datetime, target: timedelta) -> datetime:
    """API.md section 4: consume `target` from consecutive business windows starting at
    start_utc, with the tie rule that a target landing exactly at closing is due at that
    closing time, not the next day's opening."""
    local = start_utc.astimezone(WARSAW)
    current = _next_business_open(local)
    remaining = target
    while True:
        close_dt = current.replace(hour=BUSINESS_CLOSE.hour, minute=0, second=0, microsecond=0)
        available = close_dt - current
        if remaining <= available:
            due_local = current + remaining
            return due_local.astimezone(ZoneInfo("UTC"))
        remaining -= available
        next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        current = _next_business_open(next_day)


def wallclock_due_instant(start_utc: datetime, target: timedelta) -> datetime:
    return start_utc + target


def due_instants(priority: str, created_at: datetime) -> tuple[datetime, datetime]:
    """Returns (ack_due_at, resolve_due_at) in UTC, per the decision C1 for this priority."""
    ack_target, resolve_target = targets_for(priority)
    if uses_business_clock(priority):
        return business_due_instant(created_at, ack_target), business_due_instant(created_at, resolve_target)
    return wallclock_due_instant(created_at, ack_target), wallclock_due_instant(created_at, resolve_target)


def is_paused(priority: str, state: str, now: datetime) -> bool:
    """API.md section 5: paused only while open, only on the business-hours clock, only
    outside a business window."""
    if state in ("resolved", "closed"):
        return False
    if not uses_business_clock(priority):
        return False
    local = now.astimezone(WARSAW)
    if not _is_business_day(local):
        return True
    open_dt = local.replace(hour=BUSINESS_OPEN.hour, minute=0, second=0, microsecond=0)
    close_dt = local.replace(hour=BUSINESS_CLOSE.hour, minute=0, second=0, microsecond=0)
    return not (open_dt <= local < close_dt)

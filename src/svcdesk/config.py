# ai-generated: 90% - Claude (AI assistant) generated this module under the student's direction (decisions, review, testing)
"""Fixed configuration and the three contradiction-resolution decisions.

These three values are the ones declared and defended in DECISIONS.md (front matter
svcdesk_decisions). They are compiled into the service, not runtime-configurable, because they
are product decisions about which requirement each contradiction favours, not deployment knobs.
"""
import os

# C1 - SLA clock for P1: "wallclock" (P1 ignores business hours) or "business" (P1 also pauses).
DECISION_C1 = "wallclock"

# C2 - closed tickets and reopening: "immutable" (closed never reopens) or "reopen" (closed
# reopens within 7 days, like resolved).
DECISION_C2 = "immutable"

# C3 - VIP reporters and the priority matrix: "vip" (VIP floors at P2) or "matrix" (VIP ignored).
DECISION_C3 = "vip"


def test_clock_enabled() -> bool:
    return os.environ.get("SVCDESK_TEST_CLOCK", "0").strip().lower() in ("1", "true")


def db_path() -> str:
    return os.environ.get("SVCDESK_DB", "/data/svcdesk.db")

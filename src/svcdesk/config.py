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


# -------------------------- Lab 3: kb-index and the request histogram --------------------------


def kb_index_url() -> str:
    return os.environ.get("KB_INDEX_URL", "http://kb-index:8080")


def kb_index_timeout_seconds() -> float:
    # MONITORING-SPEC.md M-02: at least 2 s.
    return float(os.environ.get("KB_INDEX_TIMEOUT_SECONDS", "5"))


# M-06: at most 30 finite boundaries, in seconds, the same ladder for every label set.
# Placeholder (close to the client libraries' own defaults) until HANDOUT.md item 4: replaced once the
# ladder is designed from our own measured p99 (MONITORING-SPEC.md M-11 to M-13).
REQUEST_DURATION_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3,
    0.4, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0,
)

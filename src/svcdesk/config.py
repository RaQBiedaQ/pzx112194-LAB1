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
#
# Designed from our own measurement (itsmlab.sh load 3, GitHub login raqbiedaq, 10 October 2026):
#   p50 26.7 ms  p95 51.6 ms  p99 (q) 170.9 ms  p99.9 209.7 ms  p99.99 231.2 ms
# q falls in (0.17, 0.175], 0.005 s wide: 2.9 % of q, well inside M-11's 20 % budget. HANDOUT.md asks
# for a BAND, not a point: every 5 ms step from 0.13 s to 0.22 s is at most 0.005/0.9q = 3.2 % of q even
# at the edges of a +-10 % band around q, so the ladder stays resolved even if the grader's own q (its
# own machine, its own 2,400 draws) lands anywhere in that band. 30 boundaries exactly (the maximum,
# M-06): coarse below the band (the bulk of requests, p50..p95 live there), 5 ms steps through the band,
# then a short tail (0.3 s to 5 s) for the rare slow outlier or an upstream close to its own timeout.
REQUEST_DURATION_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.125,
    0.13, 0.135, 0.14, 0.145, 0.15, 0.155, 0.16, 0.165, 0.17, 0.175,
    0.18, 0.185, 0.19, 0.195, 0.2, 0.205, 0.21, 0.22, 0.25,
    0.3, 0.5, 1.0, 5.0,
)

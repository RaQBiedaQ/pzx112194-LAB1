# ai-generated: 85% - Claude (AI assistant) generated this module from METRIC-SPEC.md under the student's direction; the student reviewed the six edge-case rules and verified the output against fixtures/metrics-practice.json.
"""DORA delivery metrics (Lab 2). Pure function of (window, events); see ../../METRIC-SPEC.md.

Rule ids (R-01..R-21) refer to that document; this module is organised in the same order.
"""
import decimal
from datetime import datetime, timezone
from typing import Optional

from .errors import ApiError

_DEC = decimal.Decimal


def _round_seconds(x: float) -> int:
    return int(_DEC(repr(x)).quantize(_DEC("1"), rounding=decimal.ROUND_HALF_UP))


def _round6(x: float) -> float:
    return float(_DEC(repr(x)).quantize(_DEC("0.000001"), rounding=decimal.ROUND_HALF_UP))


def _median(values: list[float]) -> Optional[float]:
    """R-04: median of an odd count is the middle value; of an even count, the mean of the two
    middle values; median of no values is null."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def parse_instant(text: str) -> datetime:
    value = text.strip()
    if value.endswith("Z") or value.endswith("z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp has no offset")
    return dt.astimezone(timezone.utc)


def format_instant(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# -------------------------- request validation (section 6 errors) --------------------------


def _err(msg: str):
    raise ApiError(422, "validation", msg)


def parse_window(payload: dict) -> tuple[datetime, datetime]:
    if not isinstance(payload, dict):
        _err("request body must be a JSON object")
    window = payload.get("window")
    if not isinstance(window, dict):
        _err("window is required")
    try:
        w_from = parse_instant(window.get("from", ""))
        w_to = parse_instant(window.get("to", ""))
    except (ValueError, TypeError, AttributeError):
        _err("window.from and window.to must be RFC 3339 instants")
    if not (w_to > w_from):
        _err("window.to must be after window.from")
    return w_from, w_to


def parse_events(payload: dict) -> list:
    events = payload.get("events")
    if not isinstance(events, list):
        _err("events is required and must be an array")
    return events


# -------------------------- event parsing (section 1) --------------------------


def _validate_common(e: dict) -> None:
    if not isinstance(e, dict):
        _err("each event must be a JSON object")
    eid = e.get("event_id")
    if not isinstance(eid, str) or not (1 <= len(eid) <= 64):
        _err("event_id must be a string of 1..64 characters")
    if e.get("type") not in ("commit", "deployment", "incident"):
        _err("type must be commit, deployment or incident")
    try:
        parse_instant(e.get("at", ""))
    except (ValueError, TypeError, AttributeError):
        _err(f"event {eid!r}: at must be an RFC 3339 instant")


def _dedup_by_event_id(raw_events: list) -> list:
    """R-05: an event_id that appears more than once is counted once (first occurrence wins)."""
    seen = set()
    out = []
    for e in raw_events:
        _validate_common(e)
        eid = e["event_id"]
        if eid in seen:
            continue
        seen.add(eid)
        out.append(e)
    return out


class _Log:
    """The parsed, deduplicated, well-formed event log and its indices."""

    def __init__(self):
        self.commits: dict[str, dict] = {}          # sha -> event
        self.deployments: dict[str, dict] = {}       # deployment_id -> event
        self.incidents: dict[str, dict] = {}         # incident_id -> {"opened":dt|None,"resolved":dt|None,"deployments":set}


def build_log(raw_events: list) -> _Log:
    events = _dedup_by_event_id(raw_events)
    log = _Log()

    for e in events:
        if e["type"] == "commit":
            sha = e.get("sha")
            if not isinstance(sha, str) or not sha:
                _err(f"event {e['event_id']!r}: commit needs a non-empty sha")
            if sha in log.commits:
                _err(f"duplicate sha {sha!r} (not the same event_id)")
            branch = e.get("branch")
            if not isinstance(branch, str):
                _err(f"event {e['event_id']!r}: branch must be a string")
            change_id = e.get("change_id")
            reverts = e.get("reverts")
            if reverts is not None and not isinstance(reverts, str):
                _err(f"event {e['event_id']!r}: reverts must be a string or null")
            if (reverts is None) == (change_id is None):
                _err(f"event {e['event_id']!r}: exactly one of change_id/reverts must be null")
            log.commits[sha] = e

        elif e["type"] == "deployment":
            did = e.get("deployment_id")
            if not isinstance(did, str) or not did:
                _err(f"event {e['event_id']!r}: deployment needs a non-empty deployment_id")
            if e.get("environment") not in ("production", None) and not isinstance(e.get("environment"), str):
                _err(f"event {e['event_id']!r}: environment must be a string")
            if e.get("outcome") not in ("success", "failure"):
                _err(f"event {e['event_id']!r}: outcome must be success or failure")
            commits = e.get("commits")
            if not isinstance(commits, list) or not all(isinstance(c, str) for c in commits):
                _err(f"event {e['event_id']!r}: commits must be an array of strings")
            if not isinstance(e.get("unplanned"), bool):
                _err(f"event {e['event_id']!r}: unplanned must be a boolean")
            caused_by = e.get("caused_by")
            if caused_by is not None and not isinstance(caused_by, str):
                _err(f"event {e['event_id']!r}: caused_by must be a string or null")
            log.deployments[did] = e

        else:  # incident
            iid = e.get("incident_id")
            if not isinstance(iid, str) or not iid:
                _err(f"event {e['event_id']!r}: incident needs a non-empty incident_id")
            phase = e.get("phase")
            if phase not in ("opened", "resolved"):
                _err(f"event {e['event_id']!r}: phase must be opened or resolved")
            deps = e.get("deployments")
            if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
                _err(f"event {e['event_id']!r}: deployments must be an array of strings")
            rec = log.incidents.setdefault(iid, {"opened": None, "resolved": None, "deployments": set()})
            at = parse_instant(e["at"])
            if phase == "opened":
                if rec["opened"] is not None:
                    _err(f"incident {iid!r}: more than one opened event")
                rec["opened"] = at
            else:
                if rec["resolved"] is not None:
                    _err(f"incident {iid!r}: more than one resolved event")
                rec["resolved"] = at
            rec["deployments"].update(deps)

    # cross-reference well-formedness (section 1)
    for sha, c in log.commits.items():
        reverts = c.get("reverts")
        if reverts is not None and reverts not in log.commits:
            _err(f"commit {sha!r}: reverts names unknown sha {reverts!r}")
    for did, d in log.deployments.items():
        for sha in d["commits"]:
            if sha not in log.commits:
                _err(f"deployment {did!r}: commits names unknown sha {sha!r}")
        caused_by = d.get("caused_by")
        if caused_by is not None and caused_by not in log.incidents:
            _err(f"deployment {did!r}: caused_by names unknown incident {caused_by!r}")
    for iid, rec in log.incidents.items():
        if rec["resolved"] is not None and rec["opened"] is None:
            _err(f"incident {iid!r}: resolved without opened")
        for did in rec["deployments"]:
            if did not in log.deployments:
                _err(f"incident {iid!r}: deployments names unknown deployment {did!r}")

    return log


# -------------------------- change identity (section 3) --------------------------


def _resolve_change_ids(log: _Log) -> dict[str, str]:
    """sha -> change_id, following R-06 (transitive revert resolution)."""
    resolved: dict[str, str] = {}

    def resolve(sha: str, _stack: set) -> str:
        if sha in resolved:
            return resolved[sha]
        if sha in _stack:
            raise ApiError(422, "validation", f"cycle in reverts chain at {sha!r}")
        commit = log.commits[sha]
        reverts = commit.get("reverts")
        if reverts is None:
            change_id = commit["change_id"]
        else:
            change_id = resolve(reverts, _stack | {sha})
        resolved[sha] = change_id
        return change_id

    for sha in log.commits:
        resolve(sha, set())
    return resolved


# -------------------------- the metric computation (section 4-5) --------------------------


def compute(window_from: datetime, window_to: datetime, raw_events: list) -> dict:
    log = build_log(raw_events)
    change_of = _resolve_change_ids(log)

    # R-07: each change's first commit instant, anywhere in the log.
    first_commit_instant: dict[str, datetime] = {}
    for sha, commit in log.commits.items():
        cid = change_of[sha]
        at = parse_instant(commit["at"])
        if cid not in first_commit_instant or at < first_commit_instant[cid]:
            first_commit_instant[cid] = at

    counts_changes = len(set(change_of.values()))
    revert_chains_collapsed = sum(1 for c in log.commits.values() if c.get("reverts") is not None)

    # R-01/R-02: production deployments in the window.
    prod_in_window = []
    for d in log.deployments.values():
        if d.get("environment") != "production":
            continue
        at = parse_instant(d["at"])
        if window_from <= at < window_to:
            prod_in_window.append((at, d))
    prod_in_window.sort(key=lambda pair: (pair[0], pair[1]["deployment_id"]))

    n_deployments = len(prod_in_window)
    successful = [(at, d) for at, d in prod_in_window if d["outcome"] == "success"]
    failed = [(at, d) for at, d in prod_in_window if d["outcome"] == "failure"]

    # R-08/E1, R-09/E3, R-10/E4: lead-time pairs, one per sha, at its first qualifying deployment.
    assigned_sha_at: dict[str, datetime] = {}
    lead_time_durations = []
    negative_lead_time_pairs = 0
    for at, d in successful:  # already sorted ascending, so "first" = first seen here
        for sha in d["commits"]:
            if sha in assigned_sha_at:
                continue
            assigned_sha_at[sha] = at
            commit_at = parse_instant(log.commits[sha]["at"])
            raw = (at - commit_at).total_seconds()
            if raw < 0:
                negative_lead_time_pairs += 1
                raw = 0.0
            lead_time_durations.append(raw)
    lead_time_pairs = len(lead_time_durations)
    change_lead_time_seconds_p50 = _median(lead_time_durations)

    commits_never_on_main = set()
    deployments_without_commits = 0
    for at, d in prod_in_window:
        if not d["commits"]:
            deployments_without_commits += 1
        for sha in d["commits"]:
            commit = log.commits[sha]
            if commit.get("branch") != "main":
                commits_never_on_main.add(sha)

    window_days = (window_to - window_from).total_seconds() / 86400.0
    deployment_frequency_per_day = n_deployments / window_days if window_days > 0 else 0.0

    # R-12/E5, R-13/E6: recovery, per failed deployment.
    recovered_durations = []
    open_failures = 0
    for at, d in failed:
        did = d["deployment_id"]
        candidates = [
            (iid, rec) for iid, rec in log.incidents.items()
            if did in rec["deployments"] and rec["opened"] is not None
        ]
        if not candidates:
            open_failures += 1
            continue
        candidates.sort(key=lambda pair: (pair[1]["opened"], pair[0]))
        _, covering = candidates[0]
        if covering["resolved"] is None:
            open_failures += 1
            continue
        raw = (covering["resolved"] - at).total_seconds()
        recovered_durations.append(max(raw, 0.0))
    recovered_failures = len(recovered_durations)
    failed_deployment_recovery_time_seconds_p50 = _median(recovered_durations)

    overlapping_incident_pairs = 0
    incident_items = list(log.incidents.items())
    for i in range(len(incident_items)):
        _, a = incident_items[i]
        a_end = a["resolved"] if a["resolved"] is not None else window_to
        for j in range(i + 1, len(incident_items)):
            _, b = incident_items[j]
            b_end = b["resolved"] if b["resolved"] is not None else window_to
            if a["opened"] < b_end and b["opened"] < a_end:
                overlapping_incident_pairs += 1

    change_fail_rate = (len(failed) / n_deployments) if n_deployments > 0 else None
    rework_deployments = sum(1 for _, d in prod_in_window if d["unplanned"] is True and d.get("caused_by") is not None)
    deployment_rework_rate = (rework_deployments / n_deployments) if n_deployments > 0 else None

    # ground truth (section 5): over the whole run, not the practice/graded distinction.
    delivered_changes: dict[str, datetime] = {}
    for at, d in successful:
        for sha in d["commits"]:
            cid = change_of[sha]
            if cid not in delivered_changes or at < delivered_changes[cid]:
                delivered_changes[cid] = at
    changes_delivered = len(delivered_changes)
    true_lead_durations = []
    for cid, deploy_at in delivered_changes.items():
        raw = (deploy_at - first_commit_instant[cid]).total_seconds()
        true_lead_durations.append(max(raw, 0.0))
    true_change_lead_time_seconds_p50 = _median(true_lead_durations)

    def secs_or_null(x):
        return _round_seconds(x) if x is not None else None

    def rate_or_null(x):
        return _round6(x) if x is not None else None

    return {
        "spec_version": "1.0.0",
        "window": {"from": format_instant(window_from), "to": format_instant(window_to)},
        "deployment_frequency_per_day": _round6(deployment_frequency_per_day),
        "change_lead_time_seconds_p50": secs_or_null(change_lead_time_seconds_p50),
        "failed_deployment_recovery_time_seconds_p50": secs_or_null(failed_deployment_recovery_time_seconds_p50),
        "change_fail_rate": rate_or_null(change_fail_rate),
        "deployment_rework_rate": rate_or_null(deployment_rework_rate),
        "counts": {
            "deployments": n_deployments,
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": recovered_failures,
            "open_failures": open_failures,
            "rework_deployments": rework_deployments,
            "lead_time_pairs": lead_time_pairs,
            "changes": counts_changes,
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_time_pairs,
            "deployments_without_commits": deployments_without_commits,
            "commits_never_on_main": len(commits_never_on_main),
            "revert_chains_collapsed": revert_chains_collapsed,
            "overlapping_incident_pairs": overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered": changes_delivered,
            "true_change_lead_time_seconds_p50": secs_or_null(true_change_lead_time_seconds_p50),
        },
    }

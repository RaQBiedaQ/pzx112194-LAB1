# ai-generated: 80% - Claude (AI assistant) generated this test suite under the student's direction (design, review, and verification against the running service).
"""Own-tests suite (L2-STRETCH-3): integration tests over HTTP against the running svcdesk
service, covering the Lab 1 ticket lifecycle (API.md) and the Lab 2 DORA endpoint contract
(METRIC-SPEC.md sections 6-7)."""
from datetime import datetime, timedelta, timezone


def _new_ticket_payload(title="Printer on fire"):
    return {
        "title": title,
        "description": "Smoke coming out of the tray unit.",
        "reporter": {"name": "Ada Lovelace", "email": "ada@example.com", "vip": False},
        "impact": 2,
        "urgency": 2,
        "related_to": None,
    }


def _window():
    return {"from": "2026-01-01T00:00:00Z", "to": "2026-01-08T00:00:00Z"}


def _commit(event_id, sha, at, change_id="CHG-1", branch="main", reverts=None):
    return {
        "event_id": event_id, "type": "commit", "at": at,
        "sha": sha, "branch": branch,
        "change_id": None if reverts else change_id,
        "reverts": reverts,
    }


def _deployment(event_id, deployment_id, at, commits=None, outcome="success", unplanned=False, caused_by=None):
    return {
        "event_id": event_id, "type": "deployment", "at": at,
        "deployment_id": deployment_id, "environment": "production",
        "outcome": outcome, "commits": commits or [], "unplanned": unplanned, "caused_by": caused_by,
    }


def _simple_log():
    return [
        _commit("c-1", "sha-1", "2026-01-02T08:00:00Z", change_id="CHG-1"),
        _deployment("d-1", "DEP-1", "2026-01-02T09:00:00Z", commits=["sha-1"]),
        _commit("c-2", "sha-2", "2026-01-03T08:00:00Z", change_id="CHG-2"),
        _deployment("d-2", "DEP-2", "2026-01-03T09:00:00Z", commits=["sha-2"]),
    ]


# -------------------------- Lab 1: ticket lifecycle --------------------------


def test_health_ok(http, base_url):
    response = http.get(f"{base_url}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_ticket_returns_201_with_expected_fields(http, base_url):
    response = http.post(f"{base_url}/tickets", json=_new_ticket_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "new"
    assert body["priority"] in ("P1", "P2", "P3", "P4")
    assert "id" in body and body["id"]


def test_get_ticket_by_id_matches_created(http, base_url):
    created = http.post(f"{base_url}/tickets", json=_new_ticket_payload("Wifi down")).json()
    fetched = http.get(f"{base_url}/tickets/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_list_tickets_contains_created(http, base_url):
    created = http.post(f"{base_url}/tickets", json=_new_ticket_payload("Disk full")).json()
    listed = http.get(f"{base_url}/tickets")
    assert listed.status_code == 200
    ids = [t["id"] for t in listed.json()]
    assert created["id"] in ids


def test_ticket_lifecycle_ack_start_resolve_close(http, base_url):
    ticket = http.post(f"{base_url}/tickets", json=_new_ticket_payload("Lifecycle test")).json()
    tid = ticket["id"]
    ack = http.post(f"{base_url}/tickets/{tid}/ack")
    assert ack.status_code == 200 and ack.json()["state"] == "acknowledged"
    start = http.post(f"{base_url}/tickets/{tid}/start")
    assert start.status_code == 200 and start.json()["state"] == "in_progress"
    resolve = http.post(f"{base_url}/tickets/{tid}/resolve")
    assert resolve.status_code == 200 and resolve.json()["state"] == "resolved"
    close = http.post(f"{base_url}/tickets/{tid}/close")
    assert close.status_code == 200 and close.json()["state"] == "closed"


def test_reopen_after_resolve_returns_in_progress(http, base_url):
    ticket = http.post(f"{base_url}/tickets", json=_new_ticket_payload("Reopen test")).json()
    tid = ticket["id"]
    http.post(f"{base_url}/tickets/{tid}/ack")
    http.post(f"{base_url}/tickets/{tid}/start")
    http.post(f"{base_url}/tickets/{tid}/resolve")
    reopened = http.post(f"{base_url}/tickets/{tid}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["state"] == "in_progress"


def test_sla_endpoint_shape(http, base_url):
    ticket = http.post(f"{base_url}/tickets", json=_new_ticket_payload("SLA test")).json()
    sla = http.get(f"{base_url}/tickets/{ticket['id']}/sla")
    assert sla.status_code == 200
    for key in ("priority", "ack_due_at", "resolve_due_at", "ack_breached", "resolve_breached", "paused"):
        assert key in sla.json()


# -------------------------- Lab 2: /dora/metrics contract --------------------------


def test_dora_metrics_empty_log(http, base_url):
    response = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": []})
    assert response.status_code == 200
    body = response.json()
    assert body["deployment_frequency_per_day"] == 0.0
    assert body["change_lead_time_seconds_p50"] is None
    assert body["change_fail_rate"] is None
    assert body["deployment_rework_rate"] is None
    assert all(v == 0 for v in body["counts"].values())
    assert all(v == 0 for v in body["anomalies"].values())


def test_dora_metrics_is_a_pure_function(http, base_url):
    request = {"window": _window(), "events": _simple_log()}
    first = http.post(f"{base_url}/dora/metrics", json=request).json()
    second = http.post(f"{base_url}/dora/metrics", json=request).json()
    assert first == second


def test_dora_metrics_is_order_independent(http, base_url):
    events = _simple_log()
    forward = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": events}).json()
    reversed_events = list(reversed(events))
    backward = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": reversed_events}).json()
    assert forward == backward


def test_dora_metrics_duplicate_events_ingested_once(http, base_url):
    events = _simple_log()
    once = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": events}).json()
    doubled = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": events + events}).json()
    assert once == doubled


def test_dora_metrics_rejects_missing_window(http, base_url):
    response = http.post(f"{base_url}/dora/metrics", json={"events": []})
    assert response.status_code in (400, 422)
    assert "error" in response.json()


def test_dora_metrics_rejects_malformed_log(http, base_url):
    bad_events = [_commit("c-1", "sha-1", "2026-01-02T08:00:00Z", reverts="sha-does-not-exist")]
    response = http.post(f"{base_url}/dora/metrics", json={"window": _window(), "events": bad_events})
    assert response.status_code in (400, 422)
    assert "error" in response.json()


# -------------------------- Lab 2: /dora/ticket-events contract --------------------------


def test_dora_ticket_events_ordered_and_created_present(http, base_url):
    created = http.post(f"{base_url}/tickets", json=_new_ticket_payload("Events stream test")).json()
    events = http.get(f"{base_url}/dora/ticket-events")
    assert events.status_code == 200
    body = events.json()
    matching = [e for e in body if e["ticket_id"] == created["id"]]
    assert any(e["phase"] == "created" and e["state"] == "new" for e in matching)
    ordering_keys = [(e["at"], e["ticket_id"]) for e in body]
    assert ordering_keys == sorted(ordering_keys)

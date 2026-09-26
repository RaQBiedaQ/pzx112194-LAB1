# ai-generated: 85% - Claude (AI assistant) generated this module from API.md under the student's direction; the student chose the three decisions (config.py) and reviewed and tested the behaviour.
"""svcdesk - the service-desk API (Lab 1). See ../../REQUIREMENTS.md and ../../API.md."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Body, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, sla, storage
from . import metrics as dora_metrics
from .errors import ApiError, api_error_handler, validation_error_handler, http_exception_handler

app = FastAPI(title="svcdesk")

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

VALID_STATES = ("new", "acknowledged", "in_progress", "resolved", "closed")

# -------------------------- time helpers --------------------------


def parse_instant(text: str) -> datetime:
    """Parses an RFC 3339 instant. Raises ValueError if malformed or lacking an offset (a naive
    timestamp is malformed per API.md section 8)."""
    value = text.strip()
    if value.endswith("Z") or value.endswith("z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp has no offset")
    return dt.astimezone(timezone.utc)


def format_instant(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_now(request: Request) -> datetime:
    if config.test_clock_enabled():
        header = request.headers.get("X-Test-Clock")
        if header is not None:
            try:
                return parse_instant(header)
            except (ValueError, TypeError):
                raise ApiError(422, "validation", "X-Test-Clock header is not a valid RFC 3339 instant")
    return datetime.now(timezone.utc)


# -------------------------- validation --------------------------


def _require_str(value, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise ApiError(422, "validation", f"{field} must be a string")
    if not (min_len <= len(value) <= max_len):
        raise ApiError(422, "validation", f"{field} must be between {min_len} and {max_len} characters")
    return value


def _require_level(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(422, "validation", f"{field} must be an integer")
    if value not in (1, 2, 3):
        raise ApiError(422, "validation", f"{field} must be 1, 2 or 3")
    return value


def validate_create_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ApiError(422, "validation", "request body must be a JSON object")

    title = _require_str(payload.get("title"), "title", 1, 200)

    description = payload.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str) or len(description) > 4000:
        raise ApiError(422, "validation", "description must be a string of at most 4000 characters")

    reporter_in = payload.get("reporter")
    if not isinstance(reporter_in, dict):
        raise ApiError(422, "validation", "reporter is required")
    name = _require_str(reporter_in.get("name"), "reporter.name", 1, 100)
    email = reporter_in.get("email")
    if email is not None and not isinstance(email, str):
        raise ApiError(422, "validation", "reporter.email must be a string or null")
    vip = reporter_in.get("vip", False)
    if not isinstance(vip, bool):
        raise ApiError(422, "validation", "reporter.vip must be a boolean")

    impact = _require_level(payload.get("impact"), "impact")
    urgency = _require_level(payload.get("urgency"), "urgency")

    related_to = payload.get("related_to")
    if related_to is not None and not isinstance(related_to, str):
        raise ApiError(422, "validation", "related_to must be a string or null")

    return {
        "title": title,
        "description": description,
        "reporter": {"name": name, "email": email, "vip": vip},
        "impact": impact,
        "urgency": urgency,
        "related_to": related_to,
    }


# -------------------------- ticket helpers --------------------------


def _load_or_404(ticket_id: str) -> dict:
    ticket = storage.get(ticket_id)
    if ticket is None:
        raise ApiError(404, "not_found", f"no ticket with id {ticket_id}")
    return ticket


def _to_response(ticket: dict) -> dict:
    return ticket


# -------------------------- endpoints --------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
async def create_ticket(request: Request, payload: dict = Body(default={})):
    now = resolve_now(request)
    data = validate_create_payload(payload)

    priority = sla.compute_priority(data["impact"], data["urgency"], data["reporter"]["vip"])
    ack_due_at, resolve_due_at = sla.due_instants(priority, now)

    ticket = {
        "id": str(uuid.uuid4()),
        "title": data["title"],
        "description": data["description"],
        "reporter": data["reporter"],
        "impact": data["impact"],
        "urgency": data["urgency"],
        "priority": priority,
        "state": "new",
        "created_at": format_instant(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": data["related_to"],
        "sla": {
            "ack_due_at": format_instant(ack_due_at),
            "resolve_due_at": format_instant(resolve_due_at),
        },
    }
    storage.insert(ticket)
    return JSONResponse(status_code=201, content=_to_response(ticket))


@app.get("/tickets")
async def list_tickets(state: Optional[str] = None, priority: Optional[str] = None):
    return storage.list_all(state=state, priority=priority)


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    return _to_response(_load_or_404(ticket_id))


def _apply_transition(ticket: dict, now: datetime, action: str) -> dict:
    state = ticket["state"]

    if action == "ack":
        if state != "new":
            raise ApiError(409, "invalid_transition", f"cannot acknowledge a ticket in state {state}")
        ticket["state"] = "acknowledged"
        ticket["acknowledged_at"] = format_instant(now)

    elif action == "start":
        if state != "acknowledged":
            raise ApiError(409, "invalid_transition", f"cannot start a ticket in state {state}")
        ticket["state"] = "in_progress"

    elif action == "resolve":
        if state != "in_progress":
            raise ApiError(409, "invalid_transition", f"cannot resolve a ticket in state {state}")
        ticket["state"] = "resolved"
        ticket["resolved_at"] = format_instant(now)

    elif action == "close":
        if state != "resolved":
            raise ApiError(409, "invalid_transition", f"cannot close a ticket in state {state}")
        ticket["state"] = "closed"
        ticket["closed_at"] = format_instant(now)

    elif action == "reopen":
        if state == "resolved":
            resolved_at = parse_instant(ticket["resolved_at"])
            if now > resolved_at + timedelta(days=7):
                raise ApiError(409, "reopen_window_expired", "reopen window (7 days) has expired")
            ticket["state"] = "in_progress"
            ticket["resolved_at"] = None
            ticket["closed_at"] = None
        elif state == "closed":
            if config.DECISION_C2 != "reopen":
                raise ApiError(409, "ticket_closed", "closed tickets cannot be reopened")
            closed_at = parse_instant(ticket["closed_at"])
            if now > closed_at + timedelta(days=7):
                raise ApiError(409, "reopen_window_expired", "reopen window (7 days) has expired")
            ticket["state"] = "in_progress"
            ticket["resolved_at"] = None
            ticket["closed_at"] = None
        else:
            raise ApiError(409, "invalid_transition", f"cannot reopen a ticket in state {state}")

    else:  # pragma: no cover - guarded by the route definitions below
        raise ApiError(404, "not_found", "unknown action")

    return ticket


def _make_action_handler(action: str):
    async def handler(ticket_id: str, request: Request):
        now = resolve_now(request)
        ticket = _load_or_404(ticket_id)
        ticket = _apply_transition(ticket, now, action)
        storage.update(ticket)
        return _to_response(ticket)

    return handler


for _action in ("ack", "start", "resolve", "close", "reopen"):
    app.add_api_route(f"/tickets/{{ticket_id}}/{_action}", _make_action_handler(_action), methods=["POST"])


@app.get("/tickets/{ticket_id}/sla")
async def get_sla(ticket_id: str, request: Request):
    now = resolve_now(request)
    ticket = _load_or_404(ticket_id)
    priority = ticket["priority"]
    state = ticket["state"]
    ack_due_at = parse_instant(ticket["sla"]["ack_due_at"])
    resolve_due_at = parse_instant(ticket["sla"]["resolve_due_at"])

    acknowledged_at = parse_instant(ticket["acknowledged_at"]) if ticket["acknowledged_at"] else None
    resolved_at = parse_instant(ticket["resolved_at"]) if ticket["resolved_at"] else None

    if acknowledged_at is not None:
        ack_breached = acknowledged_at > ack_due_at
    else:
        ack_breached = now > ack_due_at

    if resolved_at is not None:
        resolve_breached = resolved_at > resolve_due_at
    else:
        resolve_breached = now > resolve_due_at

    paused = sla.is_paused(priority, state, now)

    return {
        "priority": priority,
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }


# -------------------------- Lab 2: DORA metrics endpoints --------------------------

# ai-generated: 85% - Claude (AI assistant) generated this section from METRIC-SPEC.md sections 6-7 under the student's direction.


@app.post("/dora/metrics")
async def dora_metrics_endpoint(payload: dict = Body(default={})):
    """METRIC-SPEC.md section 6: a pure function of (window, events)."""
    window_from, window_to = dora_metrics.parse_window(payload)
    events = dora_metrics.parse_events(payload)
    result = dora_metrics.compute(window_from, window_to, events)
    return JSONResponse(status_code=200, content=result)


_PHASE_STATE = {
    "created": "new",
    "acknowledged": "acknowledged",
    "resolved": "resolved",
    "closed": "closed",
}


@app.get("/dora/ticket-events")
async def dora_ticket_events():
    """METRIC-SPEC.md section 7: the ticket lifecycle stream, ordered by (at, ticket_id)."""
    events = []
    for ticket in storage.list_all():
        for phase, field in (
            ("created", "created_at"),
            ("acknowledged", "acknowledged_at"),
            ("resolved", "resolved_at"),
            ("closed", "closed_at"),
        ):
            at = ticket.get(field)
            if at:
                events.append(
                    {
                        "ticket_id": ticket["id"],
                        "at": at,
                        "phase": phase,
                        "priority": ticket["priority"],
                        "state": _PHASE_STATE[phase],
                    }
                )
    events.sort(key=lambda e: (e["at"], e["ticket_id"]))
    return events

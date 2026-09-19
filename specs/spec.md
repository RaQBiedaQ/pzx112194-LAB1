<!-- ai-generated: 85% - Claude (AI assistant) drafted this specification from REQUIREMENTS.md and API.md under the student's direction; the student chose the three conflict resolutions (C1/C2/C3) and reviewed the content. -->

# svcdesk - specification (Lab 1)

## 1. Purpose

A service-desk ticketing API for about 400 people across three offices, replacing a spreadsheet-and-inbox
workflow. The service must accept tickets over HTTP, compute their priority deterministically, track their
lifecycle, and expose SLA due instants and breach/pause status so that a Monday report can be produced from
one call per ticket. Full behavioural contract: [API.md](../API.md). Full requirements list:
[REQUIREMENTS.md](../REQUIREMENTS.md).

## 2. User scenarios

- **US-1 (desk agent, create).** An agent (or an integration) submits a new ticket with a title, an optional
  description, a reporter (name, optional email, optional VIP flag) and an impact/urgency pair. The service
  assigns an id, computes the priority, and returns the full ticket, including the SLA due instants, so the
  agent immediately knows the clock they are working against. (R-01, R-02, R-03, R-04, R-18)
- **US-2 (desk agent, work a ticket).** An agent acknowledges a new ticket, starts work on it, and resolves it,
  each as a separate, auditable action; the service refuses any transition that skips a step or targets a
  ticket that is not in the right state. (R-07, R-08)
- **US-3 (reporter, confirm or reopen).** After a fix, the reporter can accept the resolution (the ticket is
  closed) or, if the fix did not hold, reopen the ticket within a bounded window so that the same issue is not
  lost, without letting reopens run forever or without extending the original resolution target. (R-09, R-10,
  R-11)
- **US-4 (monitoring, SLA report).** Monitoring calls `GET /tickets/{id}/sla` for every open ticket to build a
  Monday report of what is late, what is on track, and what is currently paused because it is outside business
  hours. (R-12, R-13, R-15, R-16)
- **US-5 (VIP escalation).** A VIP reporter's ticket must never sit unnoticed at the bottom of the queue, even
  when the raw impact/urgency matrix would rank it low. (R-06)

## 3. Functional requirements

- **FR-01 (transport):** JSON-only HTTP API on port 8080; no other interface. (R-01, R-22)
- **FR-02 (health):** `GET /health` returns 200 with `{"status": "ok", "service": "svcdesk"}`. (R-02)
- **FR-03 (ticket shape):** a ticket carries title (1..200 chars, required), description (0..4000 chars,
  optional, default ""), reporter (name 1..100 required, email optional, vip optional default false), impact
  and urgency (each 1..3, required integers), an opaque server-assigned id, a computed priority, a state, four
  event timestamps (created/acknowledged/resolved/closed, null until they happen), an optional `related_to`,
  and an `sla` block. Server-owned fields and unknown fields sent by a client are ignored, never rejected.
  (R-03, R-18, R-20; API.md §2)
- **FR-04 (priority):** priority is P1..P4 from the impact x urgency matrix and nothing else, except the VIP
  floor of FR-05; a client-supplied `priority` field is always ignored. (R-04, R-05; API.md §3)
- **FR-05 (VIP floor - resolves conflict C3):** a VIP reporter's ticket is never lower than P2. The matrix
  value is computed first; if it is P3 or P4 and the reporter is VIP, the ticket is raised to P2. P1 and P2
  tickets are unaffected. **Decision C3 = `vip`** (see DECISIONS.md): this deliberately overrides the
  "matrix and nothing else" wording of R-04/R-05 for VIP reporters, because a VIP-visibility rule that never
  fires would defeat its own purpose. (R-06)
- **FR-06 (state machine):** `new -> acknowledged -> in_progress -> resolved -> closed`, each transition its
  own endpoint (`ack`, `start`, `resolve`, `close`), each recording its own timestamp. Any other transition is
  409; an action on an unknown id is 404. (R-07, R-08; API.md §6)
- **FR-07 (closed is terminal - resolves conflict C2):** a closed ticket cannot be reopened, at any age; new
  work on the same issue is a new ticket with `related_to` pointing at the closed one. **Decision C2 =
  `immutable`** (see DECISIONS.md): this rejects R-10's extension of the reopen window to closed tickets, to
  keep "closed this week" numbers stable once written. Reopen from `resolved` is still allowed within the
  7-day window described in FR-08. (R-09)
- **FR-08 (reopen window):** a resolved ticket can be reopened (back to `in_progress`, clearing
  `resolved_at`) while `now <= resolved_at + 7 days`; outside that window, or from any other state, reopen is
  409. Reopening never changes the original resolution due instant. (R-10, R-11; API.md §6)
- **FR-09 (SLA targets):** acknowledge and resolve targets by priority: P1 15min/4h, P2 1h/8h, P3 4h/24h,
  P4 8h/72h, both measured from `created_at`. (R-12; API.md §4)
- **FR-10 (business-hours clock):** a business-hours target only counts Monday-Friday 08:00-16:00
  Europe/Warsaw (DST-aware); a due instant that lands exactly at closing time is due at that closing time, not
  08:00 of the next business day. P2, P3 and P4 always use this clock. (R-13; API.md §4)
- **FR-11 (P1 clock - resolves conflict C1):** P1 targets are computed on the **wall-clock**, ignoring business
  hours, so a P1 raised Friday evening is late at 15 minutes past, not Monday morning. **Decision C1 =
  `wallclock`** (see DECISIONS.md): this honours R-14 literally for P1 and rejects extending R-13's pause to
  P1; P2-P4 keep the business-hours pause of FR-10. (R-14; API.md §4)
- **FR-12 (SLA reporting):** `GET /tickets/{id}/sla` returns priority, both due instants, `ack_breached`,
  `resolve_breached` and `paused`, evaluated at the request's clock. Breach is strict ("due exactly now" is not
  a breach); a ticket is paused only while open, only when its resolution clock is business-hours, and only
  outside a business window (so a wall-clock P1 is never reported paused). A reopened ticket counts as
  "not resolved" again, against its original resolve due instant. (R-15, R-16; API.md §5)
- **FR-13 (test clock):** when `SVCDESK_TEST_CLOCK` is `1`/`true`, a request may carry `X-Test-Clock` (an RFC
  3339 instant with an offset) that becomes "now" for that request alone; a header that fails to parse, or
  carries no offset, is 400/422. Without the header, or when the flag is unset, real UTC time is used.
  (R-21; API.md §8)
- **FR-14 (validation):** missing/oversized title, missing reporter name, and non-integer or out-of-range
  impact/urgency are all 400 or 422 with a JSON body `{"error": {"code", "message"}}`. (R-20; API.md §7)
- **FR-15 (listing):** `GET /tickets` supports exact-match `state` and `priority` filters and returns every
  match in one unpaginated array (the desk is small; at most ~100 tickets per run). (R-19)
- **FR-16 (not found):** an unknown route, or an action/GET against an unknown ticket id, is 404 with a JSON
  body carrying an `error` object. (R-25)
- **FR-17 (persistence):** tickets survive a container restart (a SQLite file in a named Docker volume is
  sufficient; not checked by the Lab 1 Tier A checker, but required by R-23 and needed from Lab 2 on).
- **FR-18 (deployment contract):** a Compose service named `svcdesk`, built from this repository (`build:`,
  never a bare `image:`), listening on 8080 inside the container, `SVCDESK_TEST_CLOCK` set, no host-path bind
  mounts anywhere in the resolved configuration, and no network access required once the image is built (all
  dependencies installed at build time). `docker compose up --wait` must bring the service up and `/health`
  must answer within 120 seconds. (R-22, R-24; API.md §9)

## 4. The three conflicts, and how this specification resolves them

The requirements document contains three pairs of requirements that cannot both hold in full. This
specification keeps the general rule in each pair and narrows the specific one, as follows (defended at
length, with the service-owner and customer-outcome framing, in `DECISIONS.md`):

- **C1 - SLA clock for P1.** R-13 ("SLA clocks pause outside business hours") versus R-14 ("P1 ... around the
  clock"). **Resolved as `wallclock`**: R-14 wins for P1 specifically; R-13 still governs P2-P4 (FR-11).
- **C2 - closed tickets and reopening.** R-09 ("a closed ticket is immutable") versus R-10 ("a reporter may
  reopen a resolved **or closed** ticket within 7 days"). **Resolved as `immutable`**: R-09 wins for closed
  tickets; R-10's window still applies to resolved tickets (FR-07, FR-08).
- **C3 - VIP reporters and the priority matrix.** R-05 ("priority ... from the matrix and nothing else")
  versus R-06 ("a VIP ticket is never lower than P2"). **Resolved as `vip`**: R-06 wins as a floor applied
  after the matrix; R-05 still governs every non-VIP ticket, and every VIP ticket at P1/P2 (FR-05).

## 5. Key entities

- **Ticket** - see FR-03 for the full shape; identity is the server-assigned `id`.
- **Reporter** - `name`, optional `email`, optional `vip` (embedded in Ticket, not a separate resource in
  Lab 1).
- **SLA block** - `ack_due_at`, `resolve_due_at` (embedded on create) and, via `GET /tickets/{id}/sla`, the
  derived `ack_breached`, `resolve_breached`, `paused`.

## 6. Out of scope for Lab 1

Authentication and authorisation, ticket editing (title/description/impact/urgency) after creation, deleting
tickets, pagination, and validating that a `related_to` id actually exists (R-03 explicitly leaves it
unvalidated in Lab 1). Persistence is implemented (FR-17) but not exercised by the Lab 1 Tier A checker.

## 7. Acceptance

This specification is satisfied when every check in [CHECKS.md](../CHECKS.md) under L1-CORE-1 through
L1-CORE-4 passes against the running service, and the values recorded in `DECISIONS.md` match what the
service actually exhibits (L1-CORE-4).

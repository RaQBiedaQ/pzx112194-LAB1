<!-- ai-generated: 85% - Claude (AI assistant) drafted this comparison between specs/spec.md and the src/ implementation, under the student's review. -->

# Convergence report - specification vs implementation

This is a written comparison of `specs/spec.md` against what `src/svcdesk` actually implements, in place of
spec-kit's `/speckit-converge` step (run without spec-kit in this attempt; see HANDOUT.md "AI usage").

## Requirements traced end to end

- **R-04/R-05 (priority matrix)** - `sla.compute_priority` implements the 3x3 matrix exactly as specified in
  FR-04, verified against all nine (impact, urgency) combinations plus the two VIP vectors (2.46-2.48) before
  the checker ran; the checker's own conformance run then confirmed all nine matrix checks (2.07-2.15) pass.
- **R-06 (VIP floor, decision C3)** - FR-05 of the spec says the floor applies only when the matrix result is
  P3 or P4; `compute_priority` implements precisely that condition (`base in ("P3", "P4")`), never touching
  P1/P2 VIP tickets, matching L1-CORE-2.47's "VIP P1 stays P1" and the checker's recorded `C3=vip`.
- **R-13/R-14 (SLA clocks, decision C1)** - FR-10/FR-11 resolve the conflict as `wallclock` for P1 and
  business-hours for P2-P4; `sla.uses_business_clock` and `sla.business_due_instant` implement this, and all
  eight test vectors in API.md section 4 (T1-T8) were reproduced exactly by a standalone script before the
  Docker-based checker ran them as L1-CORE-2.36-2.41, including the Friday-evening wall-clock case (T3) and
  the DST-crossing business-hours case (T8).
- **R-09/R-10 (decision C2)** - FR-07/FR-08 make `closed` terminal and keep the 7-day reopen window only for
  `resolved`; `main._apply_transition` enforces exactly this, matching L1-CORE-2.32 (reopen resolved after 6
  days succeeds), L1-CORE-2.33 (7 days + 1s fails) and L1-CORE-2.35 (reopen closed always 409, recording
  `C2=immutable`).
- **R-19 (listing)** - FR-15 asks for unpaginated exact-match filters on `state` and `priority`;
  `storage.list_all` implements both as an in-Python filter over every stored ticket, matching the "desk is
  small, no pagination" framing.
- **R-21 (test clock)** - FR-13 requires per-request `X-Test-Clock` with a parseable offset;
  `main.resolve_now`/`parse_instant` implement this and reject a naive or malformed header with 422, matching
  L1-CORE-2.04.
- **R-24 (compose contract)** - FR-18 requires `docker compose up --wait` plus `/health` within 120 s;
  observed at 1.0 s in the local `verify 1` run, well inside budget.

## Gaps and deliberate simplifications

- `related_to` (R-03) is stored but not validated against existing ticket ids, exactly as REQUIREMENTS.md
  says is out of scope for Lab 1.
- Error `code` strings (`invalid_transition`, `reopen_window_expired`, `ticket_closed`, `not_found`) are
  implemented for operator readability but are explicitly not graded in Lab 1 (API.md section 6); only the
  status code and the presence of a top-level `error` object are checked, and both are always present.
- Persistence (R-23, FR-17) uses a single SQLite connection guarded by a Python-level lock rather than a
  connection pool; correct for the traffic this lab exercises, and flagged here as a candidate to revisit in
  Lab 2, where persistence is actually part of the graded surface.

## Result

Every Core specification (L1-CORE-1 through L1-CORE-4) passed on the first `./itsmlab.ps1 verify 1` run
against this implementation, with zero divergence between the intended behaviour in `specs/spec.md` and the
service's observed behaviour; the checker's own `observations` line (`C1=wallclock C2=immutable C3=vip`)
matches `DECISIONS.md` exactly, which is what L1-CORE-4 checks.

---
feature: "own-tests: pytest suite for svcdesk running under the docker compose tests profile (L2-STRETCH-3)"
actual_minutes: 4.67
ratio_actual_over_predicted: 0.23
PREDICTION_receipt_issue: 107
PREDICTION_commit: 390f04e1280065e2d7428373ad66f8b6821b609b
---

<!-- ai-generated: 20% - Claude (AI assistant) wrote the tests and this reflection under the student's direction and review; the student verified the result against the actual running service. -->

## Outcome

Predicted: 20 minutes, from the prediction receipt (issue #107, received 2026-09-26T11:52:18Z) to a
passing `docker compose --profile tests run --rm --build tests`. Actual: about 4.67 minutes, ending
when `.\itsmlab.ps1 verify 2` reported `L2-STRETCH-3 own-tests: pass`. Ratio actual/predicted: **0.23**
— a large speedup against the prediction, not a slowdown, and scored the same either way per the
direction-neutral rule.

## Why the estimate missed high

The prediction assumed the compose plumbing (the healthcheck, `depends_on: condition: service_healthy`,
the `working_dir`/module-path wiring for `python -m tests.run`) would be the main source of friction,
because that is the part with no unit-testable feedback loop short of an actual container run. In
practice the course scaffold's commented-out template in `docker-compose.yml` already specified the
exact shape needed (healthcheck command, profile, environment variable, command), so uncommenting and
adapting it took a single edit with no iteration: no wrong working directory, no healthcheck timing
races, no port mismatch. The test logic itself was the part the prediction called "mechanical," and
that held: all 14 tests (ticket lifecycle plus the `/dora/metrics` and `/dora/ticket-events` contract
checks already exercised manually while building Lab 2 Core) were written directly from the endpoint
code and `METRIC-SPEC.md`/`API.md`, and passed against the running service on the first
`docker compose --profile tests run` with no debugging round-trip. The honest lesson is not "AI is
always this fast" but that this specific estimate priced in integration risk (compose wiring) that the
scaffold had already resolved, and underpriced how directly the already-implemented, already-manually-
tested endpoint contracts translate into passing automated assertions once the harness exists.

## What would have made the prediction closer

Reading `docker-compose.yml`'s commented `tests:` block *before* writing the prediction, rather than
after, would have removed most of the uncertainty the 20-minute estimate was pricing in, and the
estimate would likely have landed closer to 8-10 minutes instead of 20.

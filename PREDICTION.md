---
feature: "own-tests: pytest suite for svcdesk running under the docker compose tests profile (L2-STRETCH-3)"
predicted_minutes: 20
predicted_at: 2026-09-26T11:47:58Z
feature_path: "src/tests/"
---

<!-- ai-generated: 15% - Claude proposed the estimate and prose; the student reviewed and approved both before the receipt was filed -->

## Prediction

I predict that writing the `own-tests` suite for Lab 2 (L2-STRETCH-3) will take **20 minutes**
from this receipt to a passing `docker compose --profile tests run --rm --build tests`.

The suite needs at least 10 integration tests exercising the running `svcdesk` service over HTTP:
the ticket lifecycle endpoints already covered by Lab 1 (health, create, list, get, ack/start/resolve/close,
reopen, sla), and the new Lab 2 DORA endpoints' contract behaviour (empty log, purity, order independence,
duplicate-event idempotence, a couple of the required-rejection cases, and the ticket-events ordering).
A small runner (`src/tests/run.py`) collects pass/fail counts with a pytest plugin and prints the required
`ITSMLAB-TESTS: passed=<n> failed=0` line as the last line of stdout, and the `docker-compose.yml` `tests`
service (templated but commented out in the course scaffold) needs uncommenting, a healthcheck on `svcdesk`,
and a short retry loop before the suite runs so a cold container start does not race the first request.

Most of this is mechanical given the endpoint contracts already implemented and tested manually against
`METRIC-SPEC.md` and `API.md`, which is why the estimate is short; the main uncertainty is compose
plumbing (healthcheck timing, `depends_on: condition: service_healthy`, working directory / module path)
rather than the test logic itself.

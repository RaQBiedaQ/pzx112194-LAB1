---
lab3_first_draft:
  source: ai
  tool: "Claude (Claude Sonnet 5, Anthropic), 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
  verdict: refuted
  evidence: {p99_seconds: 0.1709, bucket: [0.1, 0.25], relative_width: 0.878}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1709, bucket: [0.04, 0.5], relative_width: 2.691}
---
<!-- ai-generated: 70% - the assistant wrote the Prompt/Answer exchange (asked and answered as instructed by HANDOUT.md before any design or measurement) and drafted the verdict arithmetic; the student reviewed it and supplied the real measurement. -->

# The assistant's first draft, and two verdicts

## Prompt

I'm building a FastAPI service with an endpoint, `GET /kb/search`, that calls an external HTTP
dependency on every request and returns its result. I want to instrument the endpoint with a
Prometheus histogram of request duration in seconds, using the `prometheus_client` Python library.
What bucket boundaries should I use for the histogram, and what would a reasonable Prometheus
alerting rule look like for monitoring errors and latency on this endpoint?

## Answer

A solid general-purpose starting point is a log-ish ladder that covers typical web request
latencies from a few milliseconds up to several seconds, for example, in seconds:

    [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]

This is close to what several Prometheus client libraries ship as their own default buckets, and
it spreads boundaries roughly evenly on a log scale, which works reasonably well when you don't
know your latency distribution yet.

For alerting, a simple approach is to watch the error rate and the latency over a trailing window
and fire when either crosses a threshold. For example:

    groups:
      - name: kb-search-alerts
        rules:
          - alert: KbSearchHighErrorRate
            expr: |
              sum(rate(http_server_request_duration_seconds_count{route="/kb/search", status=~"5.."}[5m]))
                /
              sum(rate(http_server_request_duration_seconds_count{route="/kb/search"}[5m]))
                > 0.05
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High error rate on /kb/search"

          - alert: KbSearchHighLatency
            expr: |
              histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{route="/kb/search"}[5m])) by (le))
                > 0.5
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "p99 latency on /kb/search above 500ms"

Adjust the 5% error-rate threshold and the 500ms latency threshold to whatever your service's
actual SLOs call for, and the 5-minute window to balance responsiveness against noise.

## Verdict on the draft ladder

Measured with `itsmlab.sh load 3` (GitHub login raqbiedaq, 10 October 2026, open-loop 40 req/s for
60 s): p99 (q) = 0.1709 s. In the draft's ladder `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5,
10]`, the largest boundary below q is 0.1 and the smallest at or above it is 0.25, so q falls in the
bucket (0.1, 0.25]: 0.15 s wide, (0.25 - 0.1) / 0.1709 = 0.878, or 87.8 % of q - more than four times
M-11's 20 % budget. `histogram_quantile` over that bucket could report anything from 0.1 s to 0.25 s
for this p99; the dashboard would show a number that is really a guess about where inside a 150 ms-wide
bucket the true value sits. **Verdict: refuted.** Between 100 ms and 500 ms this ladder has exactly the
two buckets MONITORING-SPEC.md warns about, (0.1, 0.25] and (0.25, 0.5] - our own slow mode sits
squarely inside the first, wide one.

## The draft alert rule

The assistant's alert rules use label names (`route`, `status`) that do not exist on our histogram at
all (ours are `http_route` and `http_response_status_code`, MONITORING-SPEC.md M-04) - as written,
both rules would simply never match any series and would silently never fire, which is a more basic
problem than their thresholds. They are also single-window (no short window alongside the long one),
so even with corrected label names they would fail the multiwindow reset probe (M-19) the same way the
shipped example `ExampleKbSearchErrorsSingleWindow` in `prometheus/alerts.yml` is documented to fail
(HANDOUT.md: it keeps firing for about half its long window after a burn stops). What we kept
conceptually: separating an availability (error-rate) alert from a latency alert, and the idea of
comparing a rate over a trailing window against a constant threshold - both correct shapes once
fixed with real label names, a multiwindow/multi-burn-rate structure (SRE Workbook), and thresholds
derived from `slo.md`'s declared objectives rather than picked by feel.

## Verdict on the instructor's flawed ladder

Same measured p99, 0.1709 s. `buckets-flawed.example.yml` is
`[0.001, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025, 0.03, 0.04, 0.5, 2.5]`: twelve
boundaries bunched below 40 ms - fine resolution exactly where our median (26.7 ms) lives - then one
enormous jump straight to 0.5 s. q = 0.1709 s falls in (0.04, 0.5]: 0.46 s wide, (0.5 - 0.04) / 0.1709 =
2.691, or 269 % of q - more than thirteen times the 20 % budget, and worse than the AI draft's own
failure. **Verdict: refuted.** This is the ladder's whole design flaw in one number: twelve of its fourteen
boundaries are spent below 40 ms, resolving a part of the distribution (the median) that was never the
SLO's concern, and the one bucket that actually holds the p99 is also the widest bucket in the entire
ladder.

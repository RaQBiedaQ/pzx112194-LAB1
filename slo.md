---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.95
      threshold_seconds: 0.2
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.2"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.05, minutes: 2016.0}
  alerts:
    - {alert: KbSearchAvailabilityFastBurn, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchAvailabilitySlowBurn, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 40% - Claude (AI assistant) proposed the objectives, thresholds and alert structure from the student's own measured profile (ai-first-draft.md), using the standard SRE Workbook multiwindow multi-burn-rate shape; the student reviewed and chose to keep the numbers as the right fit for this dependency. -->

# SLO for `GET /kb/search`

## Availability

The SLI is the share of `/kb/search` responses that are not a server error (5xx) over a trailing 5-minute
window. Objective: **99 %**, a 1 % error budget (403.2 minutes over the 28-day window).

`kb-index` fails a small, structural share of requests on its own - our own `load 3` runs measured 5 and
6 failures out of 2,400 requests, 0.21 % and 0.25 %. We cannot fix those: `svcdesk` has no retry (M-02
forbids it, and a retry would double the load on an already-degraded dependency) and no cache to paper
over them. A 99 % objective leaves roughly 4-5x headroom over what we have actually measured, which
matters because `kb-index`'s failure rate is a profile we did not choose and have seen vary run to run;
a tighter objective (99.9 %) would leave almost no room for that natural variance before the error
budget alerts start firing on noise rather than on a real incident.

## Latency

The SLI is the share of `/kb/search` responses observed at or below **200 ms** over a trailing 5-minute
window, since 0.2 is one of our ladder's finite boundaries (M-13) and counts requests directly from a
bucket instead of asking `histogram_quantile` to interpolate across one. Objective: **95 %**, a 5 %
error budget (2016 minutes over the window).

Our own measured p99 across two `load 3` runs was 170.9 ms and 177.8 ms: by definition at most 1 % of
requests were slower than that, so declaring the threshold at 200 ms with a 95 % objective leaves
deliberate room below the objective's own tight end - a few extra percentage points of slow requests
beyond our p99 before the budget starts burning, which is exactly the margin a profile we do not fully
control (and that moved by ~7 ms between two runs taken minutes apart) needs. 200 ms also sits just
above the point where the distribution's "fast mode" (p50 26.9 ms, p95 52.6 ms) ends and the slow mode
begins (the gap in oha's own histogram between roughly 90 ms and 110 ms, where almost nothing lands):
a request past 200 ms is, with high confidence, one that hit the slow mode, not an ordinary fast one
that happened to be a little slower.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---|---|---|---|
| KbSearchAvailabilityFastBurn | availability | 14.4 | 1h / 5m | 2 % of the 28-day budget per hour it stays above threshold | P1: pages |
| KbSearchAvailabilitySlowBurn | availability | 6 | 6h / 30m | 2.5 % of the 28-day budget per 6 hours | P2: chat |

`KbSearchAvailabilityFastBurn` is the one that pages a person (P1): a burn rate of 14.4 on a 1 % budget
means more than 14.4 % of `/kb/search` requests are failing, sustained for an hour - at that rate the
whole month's error budget is gone in under two days, which is squarely "this is an incident now, not a
trend to watch at standup." Waking someone for it costs one interrupted night occasionally; not waking
anyone for it costs the on-call team discovering, days later, that `kb-index` has been substantially
broken the entire time and the 28-day objective is already unrecoverable.

`KbSearchAvailabilitySlowBurn` goes to chat (P2): a sustained 6x burn rate exhausts the budget in about
5 days rather than two, which is a real problem worth someone looking at within the working day, but not
one where three minutes of extra delay before a human notices changes the outcome - `kb-index`'s known
error floor already eats a visible share of the budget on an ordinary day, and a P1 page for every
moderate wobble above that floor would train whoever is on call to stop trusting the pager.

## Buckets

Our ladder (`src/svcdesk/config.py`, `REQUEST_DURATION_BUCKETS`) has 30 boundaries, M-06's maximum.
Across two measurements q landed at 0.1709 s and 0.1778 s; both fall inside the 5 ms-stepped band from
0.13 s to 0.22 s, so the bucket holding q has stayed 0.005 s wide, 2.8-2.9 % of q - far inside the 20 %
budget, and HANDOUT.md's recommended band (at least +-10 % around q, every bucket at most 20 % as wide
as the band's lower end) is comfortably resolved across that whole range, not just at one point. We
spent the rest of the budget on two other things that matter: seven coarse boundaries from 5 ms to
125 ms that still separate the fast mode's own quartiles (p50 26.9 ms sits in its own bucket, distinct
from p95 52.6 ms), because a dashboard that can only say "fast" with no shape is not very useful either;
and a short tail (0.3 s, 0.5 s, 1 s, 5 s) wide enough to classify a genuinely pathological outlier - one
near `kb-index`'s own timeout - without spending fine resolution on a region that, on this profile, is
visited by a vanishingly small share of requests.

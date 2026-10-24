---
lab4_postmortem:
  ticket: "50ceffde-fa49-40b3-b4ca-957734d74bf7"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T06:36:23Z
  detection: 2026-10-12T06:39:19Z
  acknowledgement: 2026-10-12T06:40:09Z
  recovery: 2026-10-12T06:44:19Z
  mttd_seconds: 176
  mtta_seconds: 50
  mttr_seconds: 476
  identified_flags: [paymentFailure, loadGeneratorFloodHomepage]
---
<!-- ai-generated: 65% - Claude queried the recorded snapshot and drafted the structure and prose; the student reviewed every number and claim against the snapshot and the ledger. -->

# Postmortem: one in four shop orders failed at payment while the front page was flooded with traffic

This postmortem is written from the recorded incident `lab4-rec-4` (the recorded path of Lab 4): the instants, the ticket and the metrics are those of the lecturer's recorded run, which I reviewed through its Prometheus snapshot, not a run I operated. Where it says what the on-call did, it means what the recording shows.

## Date

The incident happened on 2026-10-12 between 06:36 and 06:51 UTC; this postmortem was written on 2026-10-24.

## Authors

Piotr Raczkowiak, as the reviewing on-call of the recorded incident; the AI investigator's hypotheses are quoted in the ledger `ai-rca-eval.json`.

## Status

Complete for the incident record: service was restored. Action items are proposed and not yet scheduled; the problem record below stays open until its action items are done.

## Summary

For about seven minutes (06:36:23Z to 06:43:20Z, when both faults were switched off) one in four attempts to pay in the shop failed at the payment service, so checkout orders failed, while the load generator flooded the front page with about fifteen times the usual traffic. The P1 alert `ShopCheckoutErrors` fired 176 seconds after the onset and resolved at 06:44:19Z.

## Impact

Users of the shop saw failed orders and a slow, overloaded front page. Failed orders: about 8 of about 54 `PlaceOrder` calls (roughly 15 %) between 06:36:23Z and 06:44:19Z, measured with `sum(increase(traces_span_metrics_calls_total{service_name="checkout",span_name="oteldemo.CheckoutService/PlaceOrder",status_code="STATUS_CODE_ERROR"}[8m]))` against the same query without the status filter, both at 06:44:19Z. The payment service failed 25 % of its charges: `sum(rate(traces_span_metrics_calls_total{service_name="payment",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) / sum(rate(traces_span_metrics_calls_total{service_name="payment",span_kind="SPAN_KIND_SERVER"}[5m]))` is 0.25 at 06:43:00Z and no payment span had failed before the onset. The front page took about 63 requests a second at the peak (06:42:00Z) against about 3.7 a second before the onset: `sum(rate(traces_span_metrics_calls_total{service_name="frontend",span_kind="SPAN_KIND_SERVER"}[5m]))`. The slowest span in the shop, `user_flood_home` of the load generator, had a p99 of 782 ms at 06:43:00Z. No data was lost: failed orders were failed requests that customers could retry.

## Root Causes

Two faults were active together. The payment service was configured to fail a quarter of its charge calls (the feature flag `paymentFailure`, variant 25 %), and `checkout` returned those failures to its callers; this is what made orders fail. The load generator was configured to flood the home page (the flag `loadGeneratorFloodHomepage`), which multiplied frontend traffic by about fifteen and made `frontend` and `frontend-proxy` the busiest services. A third class of fault (resources: email memory leak or recommendation cache failure) was possible by the design of the injector, but I could not see any sign of it in the metrics: the email service's memory stayed flat (`container_memory_percent_ratio{container_name="email"}` about 58 % throughout) and its call rate fell only in proportion to the failed payments, so I did not name a third flag.

## Trigger

Both faults switched on together at the onset, 06:36:23Z, the first sample of `seeded_fault_active`. Nothing in the shop's own telemetry changed before then: the baseline error rate of every shop service was zero except the load generator's own client calls, which fail on the healthy shop as well.

## Resolution

Both faults were switched off by 06:43:20Z (`seeded_fault_active` fell to 0 at that sample). `ShopCheckoutErrors` resolved at 06:44:19Z, when the 5-minute window of its rule had moved past the failing payments, so the recovery the alert reports is about one minute after the fault actually ended. The order of the two switches is not visible in the snapshot; the payment flag was the one that mattered for users, since it is the only one that made orders fail.

## Detection

The alert `ShopCheckoutErrors` (P1, `service=checkout`) detected the incident at 06:39:19Z, 176 seconds (MTTD) after the onset, and paged the on-call. The companion P2 `ShopServiceErrors` for `checkout` and `payment` was pending at the same time. Without the alert, the first people to notice would have been customers who could not pay: the flood made the front page slower but not unavailable, and orders are about 0.1 a second in this shop, so a failing minute is a handful of orders, easy to miss on a dashboard that no one is watching.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a P1 alert on the payment service's own error ratio (more than 15 % over 5 minutes) so the cause is paged, not only the symptom | mitigate | on-call team | ITSM-101 |
| Alert on frontend request rate more than five times its one-hour average, to name the flood fault early | prevent | on-call team | ITSM-102 |
| Add `keep_firing_for` and a shorter window to the checkout alert so that its recovery time is closer to the end of the fault | process | service owner | ITSM-103 |
| Put the feature flags' change history on the on-call dashboard so that "what changed recently" is answered in the first minute | prevent | platform team | ITSM-104 |

## Lessons Learned

### What went well

The symptom alert on checkout fired within three minutes of the onset, the ticket was acknowledged 50 seconds after the page, and the failure was fully visible in the shop's span metrics: a single query of failed payment spans showed the cause.

### What went wrong

The AI investigator's first runs asked for a `[1m]` rate on a metric that arrives once a minute and concluded that nothing was failing; the metric's sampling interval was not part of its question. The recovery time the alert reports is about a minute later than the end of the fault, because of its 5-minute window.

### Where we got lucky

Only a quarter of the charges failed and the shop's order rate is low; at 50 % or with real traffic the same fault would have cost many more orders in the three minutes before the page.

## Timeline

All times are UTC on 2026-10-12.

- 06:31:23 - the last quiet moment (five minutes before the onset): no failed spans on payment or checkout; `sum(rate(...status_code="STATUS_CODE_ERROR"...[5m]))` returns nothing.
- 06:36:23 - onset (2026-10-12T06:36:23Z): `seeded_fault_active` starts; payment begins failing a quarter of its charges and the front-page flood begins.
- 06:39:19 - detection (2026-10-12T06:39:19Z): `ShopCheckoutErrors` starts firing; the pager is notified.
- 06:40:09 - acknowledgement (2026-10-12T06:40:09Z): the P1 ticket `50ceffde-fa49-40b3-b4ca-957734d74bf7` is acknowledged (MTTA 50 seconds).
- 06:43:20 - both faults are switched off (`seeded_fault_active` becomes 0).
- 06:44:19 - recovery (2026-10-12T06:44:19Z): `ShopCheckoutErrors` resolves (MTTR 476 seconds).
- AI hypotheses I acted on: H1 and H4 (the payment service's charge span returns errors) and H2 (checkout, frontend and frontend-proxy errors follow from it) all held at 06:43:00Z, each with its own query in `ai-rca-eval.json`; H3 ("no span above 100 ms") did not: the load generator's flood span had a p99 of 782 ms.

## Supporting information

The four instants and three durations are the output of `itsmlab incident 4` on `incident/tsdb-snapshot.tar.gz`. The queries above ran on that snapshot, served on a local Prometheus. The ledger `ai-rca-eval.json` holds four hypotheses of the agent loop with `gemini-flash-lite-latest`, each with its prediction, instant and verdict, and `ai-rca/transcript.md` holds the conversation they quote.

## Problem record

- Incident record: the P1 ticket 50ceffde-fa49-40b3-b4ca-957734d74bf7, acknowledged 06:40:09Z and closed when service was restored at 06:44:19Z.
- Root cause: the payment service failed 25 % of charge calls through a feature flag (`paymentFailure`), alongside a front-page traffic flood (`loadGeneratorFloodHomepage`); the cause stays open until the flags' change control and a cause-level payment alert exist.
- Known error: the shop has no alert on the payment service itself, so a payment fault is seen only as a checkout symptom, and `ShopCheckoutErrors` resolves about a minute after the fault ends.
- Workaround: switch the failing flag off through the injector (`POST /flags/<flag>/off`) and watch the checkout error ratio fall below its threshold.

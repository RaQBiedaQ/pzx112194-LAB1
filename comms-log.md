---
lab4_comms:
  awareness: 2026-10-12T06:40:09Z
  detection: 2026-10-12T06:39:19Z
  classification: 2026-10-12T06:47:00Z
  nis2:
    early_warning_due: 2026-10-13T06:40:09Z
    notification_due: 2026-10-15T06:40:09Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  ksc:
    early_warning_due: 2026-10-13T06:39:19Z
    notification_due: 2026-10-15T06:39:19Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  dora:
    initial_due: 2026-10-12T10:47:00Z
    initial_sent: 2026-10-12T09:30:00Z
    intermediate_due: 2026-10-15T09:30:00Z
    intermediate_sent: 2026-10-14T10:00:00Z
    final_due: 2026-11-14T10:00:00Z
  log:
    - {at: 2026-10-12T09:30:00Z, to: the financial supervisor, what: DORA initial notification of a major ICT-related incident}
    - {at: 2026-10-13T09:00:00Z, to: the CSIRT, what: NIS2 and KSC incident notification}
    - {at: 2026-10-14T10:00:00Z, to: the financial supervisor, what: DORA intermediate report}
---
<!-- ai-generated: 60% - Claude drafted the instants, the deadline arithmetic and the prose from the postmortem's timestamps; the student reviewed each instant and each deadline. -->

# Communications log: the regulators' clocks

This is a thought exercise on the recorded incident `lab4-rec-4` (ticket 50ceffde-fa49-40b3-b4ca-957734d74bf7): suppose the shop is an entity that NIS2, the Polish KSC act and DORA all apply to, and that the incident was significant under the first two and major under the third. Every instant is UTC.

## The three instants you defend

**Awareness (NIS2), 2026-10-12T06:40:09Z.** This is the acknowledgement of the P1 ticket. The alert fired at 06:39:19Z, but an alert alone is a machine's signal; at 06:40:09Z a person took the page, looked at the failing checkout and became aware that orders were failing, which is when the entity "becomes aware" of a significant incident. At that moment I knew that checkout was failing and not why.

**Detection (KSC), 2026-10-12T06:39:19Z.** The Polish act counts from the moment of detection, which is the moment the detecting alert `ShopCheckoutErrors` started firing, as in the postmortem. The detection is 50 seconds before the awareness, so the KSC clock starts first.

**Classification as major (DORA), 2026-10-12T06:47:00Z.** The faults ended at 06:43:20Z and the alert resolved at 06:44:19Z. By 06:47:00Z the extent was known: about 15 % of the orders in the window failed and the shop was degraded for about seven minutes, which is when the entity could classify the incident as major. This is within 24 hours of the awareness, so the initial notification is due 4 hours after the classification (10:47:00Z), earlier than the 24-hour cap of 06:40:09Z on the next day.

## The log

| when (UTC) | to | what | which clock it answers |
|---|---|---|---|
| 2026-10-12T09:30:00Z | the financial supervisor | DORA initial notification | initial report, due 10:47:00Z the same day |
| 2026-10-13T09:00:00Z | the CSIRT | NIS2 and KSC incident notification | NIS2 early warning (due 2026-10-13T06:40:09Z) and KSC early warning (due 2026-10-13T06:39:19Z) are already past at this time; the notifications are due on 2026-10-15 at 06:40:09Z and 06:39:19Z |
| 2026-10-14T10:00:00Z | the financial supervisor | DORA intermediate report | due 72 hours after the initial notification, 2026-10-15T09:30:00Z |

The early warnings of NIS2 and KSC are due 24 hours after awareness and detection, which in this scenario means before the planned notification at 09:00 on the next day; a real entity would send a short early warning on the morning of 2026-10-13 before 06:39 UTC, and this log would then carry a fourth entry. The final reports follow one calendar month after the notifications sent: 2026-11-13T09:00:00Z for NIS2 and KSC, and 2026-11-14T10:00:00Z for DORA, counted from the intermediate report.

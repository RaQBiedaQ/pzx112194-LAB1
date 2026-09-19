---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 70% - Claude (AI assistant) drafted this reasoning from the student's chosen resolutions and REQUIREMENTS.md; the student picked each of the three values and reviewed the wording before submission. -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 acknowledge and resolve targets run on the wall-clock, around the clock, exactly as R-14
states. Business hours (Monday-Friday, 08:00-16:00 Europe/Warsaw) never pause a P1 clock. Every other
priority (P2, P3, P4) keeps the business-hours clock of R-13 unchanged.

**Rejected alternative:** Extending R-13's business-hours pause to P1 as well, so that a P1 raised at 17:00 on
a Friday would only start its 15-minute acknowledge clock at 08:00 the following Monday.

**Reason:** P1 means the whole organisation has stopped working. A rule that lets a P1 clock sleep all
weekend contradicts what P1 is for: it would let the desk report "on time" for an outage that sat unattended
for 63 hours. We accept the operational cost of an on-call rotation for this one priority level, and we do
not extend that cost to P2-P4, where the underlying impact is smaller and business-hours coverage is
proportionate.

**Service owner:** the IT Operations Manager, because they own the on-call rotation and its budget, and
because they are the one accountable when a Monday report shows a P1 that sat unacknowledged over the
weekend.

**Customer outcome:** a reporter whose entire office is down gets a real 15-minute acknowledgement promise,
seven days a week, instead of a promise that quietly stops applying outside office hours.

## C2 - Closed tickets and reopening

**Decision:** A closed ticket cannot be reopened, regardless of how recently it was closed. Reopening is only
possible from the `resolved` state, within the 7-day window of R-10. Once a ticket reaches `closed`, any
further work on the same underlying issue is a new ticket that references the old one through `related_to`.

**Rejected alternative:** Allowing reopen from `closed` within 7 days, as the literal wording of R-10 ("a
resolved or closed ticket") permits.

**Reason:** `closed` is meant to be the terminal, audit-safe state (R-09 says so directly): once closed, a
ticket's numbers ("resolved in 3.2 hours", "closed this week") are used in reports and should not be revised
retroactively by an unrelated later action. Letting a closed ticket silently reopen would mean last Monday's
report of "12 tickets closed" could change by Friday. Reopening from `resolved` already gives a reporter a
real 7-day safety net before the ticket becomes historical; we do not extend that safety net past the point
where the record is meant to be final.

**Service owner:** the Service Desk Manager, because they are accountable for the accuracy of the weekly and
monthly closure reports that this decision protects.

**Customer outcome:** a reporter whose fix did not hold, and who confirms this before closing the ticket, can
still reopen it within a week at no cost. A reporter who has already confirmed closure and later has a new
problem opens a fresh ticket, linked to the old one, which also gives the desk a clean history of two
distinct problems instead of one ticket's timeline getting reused for an unrelated regression.

## C3 - VIP reporters and the priority matrix

**Decision:** Priority is computed from the impact/urgency matrix first, exactly as R-04/R-05 describe. If the
matrix result for a VIP reporter's ticket is P3 or P4, the ticket is then raised to P2. VIP tickets that the
matrix already places at P1 or P2 are unaffected; the VIP flag never affects a non-VIP ticket at all.

**Rejected alternative:** Treating R-05 ("priority is derived from the matrix and from nothing else") as
absolute, so that `reporter.vip` is stored but never changes the computed priority, and a VIP reporter's
cosmetic, single-person issue would sit at P4 like anyone else's.

**Reason:** R-06 exists for a specific operational purpose: guaranteeing that executive-reported issues do not
sit unseen in a low-priority queue. A VIP rule that the matrix can always override would never actually fire
for the low-impact/low-urgency tickets it was written to catch, which defeats its own purpose. We therefore
treat R-04/R-05 as the general rule and R-06 as its one documented, narrow exception, applied after the
matrix rather than instead of it.

**Service owner:** the Service Desk Manager, because they are the one who answers to executive stakeholders
when a VIP-reported issue is later found to have been deprioritised.

**Customer outcome:** an executive reporter's issue is guaranteed a P2 response even when its raw impact and
urgency look minor, so the desk's promise of visibility for VIP reporters is one that actually holds in every
case, not only when it happens to agree with the matrix.

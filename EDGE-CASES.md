---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 80% - Claude (AI assistant) drafted these six explanations and the gaming write-up from the counts our service reports; the student reviewed the reasoning and picked the gaming strategy. -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: three (commit, deployment) pairs where the commit's `at` is timestamped after the
  deployment that carried it to production, because the two machines that recorded the events disagreed about
  the time.
- What a default definition would have done: an assistant asked cold for "lead time" almost always emits
  `deployment.at - commit.at` with no floor, so these three pairs would either produce a negative duration (a
  nonsensical "delivered before it was written" reading on a dashboard) or get silently dropped from the sample
  because a negative number looks like a data error worth filtering out.
- Why the rule is defensible: clock skew is an infrastructure fact, not evidence that the change shipped
  instantly or that it should vanish from the sample; clamping to zero keeps the pair in the population (so the
  frequency and count of "fast" deliveries is not overstated by silent removal) while refusing to report a
  physically impossible negative number, and the clamped pairs are still visible in
  `anomalies.negative_lead_time_pairs` so nobody mistakes "clamped" for "genuinely instant".

## E2 - a revert of a revert

- What the log contains: two commits in the log whose `reverts` field points at another revert commit, so a
  chain of three commits (the original change, its revert, and the revert of that revert) exists for a single
  piece of work that was tried, backed out, and reinstated.
- What a default definition would have done: a naive count-the-commits approach would report three separate
  "changes" for what is, from the reporter's point of view, one piece of work landing once - inflating
  `deployment_frequency_per_day` and the change counts with churn that never reached a different end state than
  the original commit did.
- Why the rule is defensible: collapsing a revert chain to the identity of the original, non-revert commit
  means the metrics count units of delivered work, not units of git history; a team that reverts and reinstates
  a change while stabilising it should not look three times as productive as a team that lands the same change
  cleanly on the first try.

## E3 - a hotfix that never touched `main`

- What the log contains: four distinct commits that reached a production deployment without ever being
  recorded on the `main` branch - emergency hotfixes cut and shipped directly.
- What a default definition would have done: most delivery-metric write-ups (and most assistants) implicitly
  filter commits on `branch == "main"`, because that is how a typical trunk-based workflow is described; under
  that filter these four hotfixes would silently disappear from the lead-time sample even though they
  genuinely reached customers.
- Why the rule is defensible: DORA's metrics describe what happens to *production*, not what happens to a
  particular branch naming convention; a service desk being measured on real customer impact cannot have its
  fastest, highest-pressure deliveries excluded from the sample just because the emergency process skipped a
  branch that this specification never asked about in the first place.

## E4 - a deployment with zero linked commits

- What the log contains: four production deployments whose `commits` array is empty - infrastructure-only
  releases (a config flag flip, a restart-only rollout) that carried no application code.
- What a default definition would have done: a lead-time calculation that divides "total lead time" by "number
  of deployments" without checking for this case will either divide by a count that silently excludes these
  deployments (undercounting deployment frequency) or crash on an empty list when trying to compute a lead
  time for a deployment with nothing to time.
- Why the rule is defensible: an empty-commit deployment is still a real production change to the fleet, so it
  must still count toward deployment frequency and the two instability-rate denominators; it simply contributes
  no lead-time pair, because there is no commit to measure a lead time from - reporting it explicitly rather
  than crashing or silently dropping it keeps the denominators honest.

## E5 - a deployment that failed and never recovered

- What the log contains: one production deployment that failed and whose incident record was opened but never
  resolved anywhere in the log - the failure is still open at the end of the observation window.
- What a default definition would have done: a naive recovery-time calculation would either invent a recovery
  instant (using "now" or the window's end as a stand-in for `resolved_at`), which fabricates a number nobody
  measured, or it would throw the failure out of the sample entirely, which understates how much unresolved
  risk the team is actually carrying.
- Why the rule is defensible: an open failure has, by definition, no recovery time to report - reporting `null`
  in the median would be wrong (it is not "no data", it is "not done yet") and inventing a value would be
  worse, so the specification excludes it from the median honestly while still counting it in
  `counts.open_failures`, which is exactly the number a team lead needs to know is not reflected in the
  headline recovery-time figure.

## E6 - overlapping incidents

- What the log contains: eleven pairs of incidents in the log whose open-to-resolved (or open-to-window-end)
  intervals overlap in time - failures that were being investigated concurrently, sometimes because one
  incident's blast radius touched more than one failed deployment.
- What a default definition would have done: a definition that computes recovery time per incident and then
  merges or sums overlapping incident durations would double- or triple-count the same wall-clock time across
  several "recoveries", inflating the apparent scale of an outage that was, in reality, one team working one
  timeline.
- Why the rule is defensible: recovery time is computed per failed *deployment*, using whichever incident
  actually covers it, and overlapping incidents are never merged or summed; this keeps each failed deployment's
  recovery time anchored to a real, observable pair of instants (its own `at` and its covering incident's
  `resolved`) rather than to an artefact of how many incidents happened to be open at once.

## Gaming demonstration

We improved `deployment_frequency_per_day` (rule R-11) by adding fifteen new production deployments to the
practice log, each carrying an empty `commits` list - infrastructure-shaped releases that ship nothing and
touch no real code, exactly the kind of change E4 already tells us the metric cannot distinguish from
substantive work. This alone lifts the reported frequency from 2.0 to about 2.62 deployments per day, comfortably
past the +25% margin, without moving a single real commit or deployment earlier or later.

To make the harm concrete rather than assumed, we additionally moved two real deployments - the sole vehicles
that carried eight distinct changes to production in the base log - to the very end of the observation window,
so they fall outside it entirely. Filtered back down to only the original, real work (the checker's
`after_base_only` view), `ground_truth.changes_delivered` drops from 65 to 57: nearly 12% of the real work this
team actually shipped during the period simply stops counting, while the padded frequency number keeps climbing.

The incentive this rewards in a real team is obvious and well documented outside this course: once "ship
often" becomes the number a manager watches, the fastest way to move it is to multiply low-risk, no-op releases
(feature-flag toggles, config bumps, restart-only deploys) rather than to actually ship more real changes faster
- and the same slack that pads the count can be used to quietly hold back or batch the harder, riskier work that
does not move as easily. The people rewarded are whoever controls what gets labelled a "deployment": a team
lead who wants a green dashboard for a review, or an individual contributor who wants their name on more
release entries than their actual output justifies. The people who lose are whoever reads the dashboard and
believes it: a manager reporting "we deploy more than ever" to their own leadership, and, eventually, the
customers whose real fixes were the ones quietly delayed.

# WP02/WP12 work order · Time-weighted mission availability

R-MD-017 (MD-017, MIS-001) calls for time-weighted availability of defined mission functions. WP02 supplies mission membership under the scenario dependency model and WP12 measures exposure for SC-02 and SC-17. The existing guarded summary reports total unavailable mission-ticks. Two functions can exchange availability and leave that total unchanged. Reviewers need the identity and observed duration of each function. [Source ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

## Definition and eligibility

On a verified guarded episode with `required_dependencies_v1`, use every configured mission ID. The model propagates unavailable dependencies and evaluates service support for each mission. For each operational interval, credit its duration to every operational mission, irrespective of criticality or designation. Measure from tick zero to the verified horizon. The membership at a transition applies until the next transition. Same-tick transitions consume zero time and the last state persists to the horizon.

Each row gives the mission's available ticks, possible ticks (the horizon) and their ratio. Across missions, divide total available function-ticks by mission count times horizon. Zero possible ticks yields a null fraction at both levels. A known outage throughout a positive horizon yields measured zero. Omit the optional view when the episode lacks the verified dependency timeline. Preserve null metrics and their dispositions for failed, timed-out, incomplete and invalid attempts.

Use the existing `pacd-sim metrics` reader with `--function-availability` on a run directory, a digest-pinned plan or a digest-pinned register. The opt-in adds `guarded_review.function_availability`. Default reports and earlier option combinations retain their canonical output. A matching receipt alone cannot release a measurement when replay disagrees with the recorded identities.

## Development acceptance

1. Hand-integrate unequal intervals, initial outages, an identity swap with constant fleet counts, reversals at the same tick, a transition at the horizon and zero exposure. Check complements against MIS-002 unweighted exposure and MIS-003 outage duration.
2. On the existing matched critical-outage scenarios at horizon eight, expect mission A up for six ticks and B up for eight under static review, or 14/16 in aggregate. Switching the critical designation must produce the same MIS-001 values. Under corroborated review expect 16/16. An immediate rollback also preserves 16/16. Keep an unguarded control and one deliberately unlaunched slot.
3. Pin scenario, defender, revision, development seeds 424242 and 424243 and invocation IDs before launch. Compare verified episode, plan and register reads, including old options, and check that reading leaves the retained store intact. Exercise an authenticated false mission identity and missing outcomes.
4. Run the frozen tests and quality checks, retain exact commands and evidence, and submit the public feature branch for independent review. The current owner instruction authorizes the PR #26 merge and this public development draft under AGENTS.md, DEC-038 and D-017.

The binary dependency model limits interpretation. Graded service degradation, validation of dependency assumptions, attribution, failed-episode safety, reportable comparisons and the separate H6 human study retain their existing criteria. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Remaining implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

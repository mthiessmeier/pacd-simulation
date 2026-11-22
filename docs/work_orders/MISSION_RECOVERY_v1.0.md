# Mission recovery time in guarded diagnostics

R-MD-020 / MIS-004 calls for time from a specified minimum or containment to a restored threshold, with cause attribution and an explicit treatment of unresolved recovery. WP02 supplies the binary mission state and simulation clock. WP12 publishes the verified measure for SC-02 and SC-17. The owner's instruction following PR #23 authorizes this local, non-reportable development increment and a separate public draft under DEC-038 and D-017.

## Origin, threshold and denominator

Measure each mission separately. An observed change from operational to unavailable is the start of an outage at the binary minimum. The first subsequent operational state closes it. Each later entry into outage starts a separate interval. Use simulation ticks and retain replay order for transitions at the same tick. An execution and immediate rollback can therefore produce a completed recovery lasting zero ticks.

A mission already unavailable at the first observation has an unknown onset. A mission still unavailable at the verified horizon has an unknown restoration. For both, report the observed start, elapsed observation time and whichever endpoints are known. An exact recovery duration requires both endpoints. Compute the mean across fully observed completed outages, including same-tick recoveries, and report its sum and denominator. A zero denominator yields a null mean. An always-operational mission has an empty interval list.

The source allows multiple possible origins. This development definition selects entry into the binary minimum. Reuse the membership sequence that reconstructs MIS-002 from the initial environment and guarded defensive execution and rollback. The initial state has no observed cause. Scripted event labels supply no causal attribution. Recovery after containment, graded thresholds, attack-caused recovery and interactions between causes remain in R-MD-020. The conditional mean covers observed completions only.

## Public reader and matched cases

Release the optional `guarded_review.mission_recovery` view through `pacd-sim metrics --mission-recovery` for a verified guarded episode, a pinned plan or a pinned register. Reuse the existing replay and release checks, including when MIS-002 and MIS-004 are requested together. Withhold episode measurements for failed, invalid, timed-out and incomplete attempts. Preserve historical outputs under their original options.

Pair the approved two-subject retain scenario with a governed configuration that enables rollback. Its event sequence, seed, criticalities, review timing and defender are identical. Prespecify seeds 424242 and 424243, with static and corroborated review. Under static review, retaining isolation opens the first mission's outage at tick 6. Without rollback it stays open at horizon 8, giving two observed ticks and unknown recovery. With rollback, the outage opens and closes at tick 6, giving one measured recovery of zero ticks. The simulated veto and corroborated zero-admission cases provide no-outage controls.

## Acceptance

1. Hand-check multiple missions, repeated outages, differing onset ticks, positive elapsed times, same-tick transitions, initial outages, restoration or onset at the horizon, repeated snapshots and empty denominators. Reconcile the sum of observed outage time for each mission to MIS-002 on the same membership stream.
2. Independently compare run, pinned-plan and registered outputs on the matched cases. Verify historical options, an unguarded episode, retained failure statuses and a genuine receipt carrying incorrect transition evidence.
3. Exercise both frozen environments, source reconciliation and independent exact-head review. Record commands, configuration and invocation identities, results and residuals in the PR and evidence index. Reportable protocol decisions and the human-subject boundary remain in the [full plan](../REMAINING_IMPLEMENTATION_PLAN.md).

Classification `NON_REPORTABLE_DIAGNOSTIC`. [Requirement ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

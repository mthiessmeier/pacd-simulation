# Critical-function outage time in guarded diagnostics

R-MD-019 / MIS-003 asks how long a critical mission function stays below threshold, including crossings, restoration and outages open at the horizon. The original dictionary leaves the threshold unfrozen. WP02 provides the mission identities, dependency graph and simulation clock. WP12 measures the verified result for SC-02 and SC-17. The owner authorized the next public development draft after PR #25 under DEC-038 and D-017.

## Development definition

The scenario declares a nonempty set of unique mission IDs through `critical_mission_ids`. Each ID must identify a mission in that governed guarded scenario. The designation is part of the pinned configuration. Numeric criticalities retain their existing meaning as MIS-002 weights. Historical scenarios that omit the designation have no eligible MIS-003 view.

Use binary operational membership on the existing authenticated mission timeline. Operational membership is at the threshold. Absence is below it. A state applies from its observation tick up to the next tick, with the final interval ending at the verified horizon. Preserve replay order among transitions at the same tick. An immediate rollback can leave zero outage ticks. An outage beginning exactly at the horizon also contributes zero duration, while its final unavailable state remains visible. An initial outage contributes the time observed from tick zero.

For every designated mission, report outage ticks and whether it is unavailable at the horizon. Sum its duration once per affected function to obtain outage function-ticks. Separately count elapsed ticks with at least one designated function down. If two designated functions are both down for two ticks, the totals are four function-ticks and two elapsed ticks. Report possible function-ticks as the designated count times the horizon. Divide elapsed outage time by the horizon for the any-outage fraction. A zero horizon gives a null fraction. A verified always-up function has zero measured outage.

## Matched development controls

Start both fixtures from the accepted two-subject retain scenario. Keep the events, dependencies, review conditions, criticality weights and simulated actions identical. Designate mission A in one fixture and mission B in the other. Pin both on development seeds 424242 and 424243 with static and corroborated review. Static review isolates the session serving mission A at tick 6. At horizon 8, the A fixture has two outage ticks and is still down. The B fixture has zero and remains operational. The corroborated condition has zero outage for either designation. Include prior guarded, restored, sensing and unguarded fixtures and an unlaunched slot for historical and missing-data controls.

## Acceptance

1. Exercise multiple simultaneous and disjoint outages, unaffected functions, outage at the start or end, interrupted and restored intervals, same-tick transitions and a zero horizon. Compare per-function duration with MIS-002 exposure and summed MIS-004 observations. Check overlap separately against the clock.
2. Expose `guarded_review.critical_outage` through `pacd-sim metrics --critical-outage` for the verified episode and the existing pinned plan and register. Authenticate designation and function membership through the governed configuration and replay. A substituted designation or false transition with valid-looking counts must fail verification. Preserve all earlier reader options, status accounting and null measurements on non-completed attempts.
3. Run the frozen suites, compatibility, registration and source-reconciliation checks. Record commit, configuration, seed and invocation identities and separate independent review dispositions.

Graded states, empirically calibrated critical-function selection, sensitivity, failed-episode safety and reportable threshold choices retain their original criteria. This increment measures one binary development rule. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Source reconciliation](../../status/REMAINING_SCOPE_RECONCILIATION.csv) · [Remaining implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

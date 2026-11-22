# Session handoff · Criticality-weighted mission loss

[PR #19](https://github.com/mthiessmeier/pacd-simulation/pull/19) is the public development draft for WP02/WP12 on branch `codex/wp02-mission-impact`. It adds the [MIS-002 work order](../docs/work_orders/MISSION_LOSS_INTEGRAL_v1.0.md), a matched pair of two-mission configurations and an opt-in evaluator measurement. The PR records the exact candidate, full tests and independent dispositions.

| Record | Verified identity |
|---|---|
| [PR #18](https://github.com/mthiessmeier/pacd-simulation/pull/18) | The owner approved `8d5b9ab79f82c55c2b50c3a3c60afce5503b746d`. Both the GitHub PR and Git pull ref matched. Two independent review-only sessions passed it. |
| Verified merge on main | `b58c46e5a56bddc701b3e55c595885b6e6c429b1`. Ordered parents `61eb93e96369fc78decd03f9b8a2d846633bc314` and the approved #18 head. Merge tree `4e78439b7b7bd2d1a3b9b3ba947af4d78a7d9968` matched the approved tree. |
| Fresh feature branch | Work order `6b1c34839798cf772fe08bf9126b22b9e0ab6e19`, governed fixtures `9b82e60f8e9f998bad0288836086ff23fedf763e`, implementation `d6582f12ea2a4696523336f5c29885e4dcf56bb5`. The PR opened at the implementation commit. |
| Authority | The owner approved the exact PR #18 merge and a new public, unmerged increment. AGENTS.md, D-017 and DEC-038 govern local development work. Documentation drafts #9 and #11 were open at preflight. |
| Scope | MIS-002 / R-MD-018, SC-02 and SC-17. The [source ledger](REMAINING_SCOPE_RECONCILIATION.csv) retains the metric's draft classification and development sensitivity requirement. |

The existing availability report aggregates unavailable mission time. The optional `--mission-impact` view identifies the affected functions, their configured criticalities, their outage durations, the weighted loss and total exposure. All required state comes from the verifier's existing replay of the initial graph and guarded transitions. Same-tick execution and restoration contribute no elapsed outage. The run, plan and register readers share the same release and hashing path.

The two new fixtures swap only the criticality assignments and scenario name. Ten numerical unit cases and seven public-interface scenario cases passed before the review handoff. Historical checks reproduced eight guarded episodes and twelve sensing episodes against their original producer revisions, along with the earlier mixed-status register. The private workspace evidence index `review/pr19/final-evidence.json` and the PR carry the completed comparison, exact commands, configuration and invocation identities, tests and limitations. Development seeds are 424242 and 424243. The frozen runtime is CPython 3.13.15 with uv 0.12.5, lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`.

Independent review should challenge equal-count outages affecting different mission identities, weights and initial state, extreme and zero exposure, same-tick transitions, shared-reader digests and invalid evidence. A merge decision is separate and applies to the reviewed head. Graded mission degradation, calibrated and frozen weights, causal attribution, independent failed-episode safety evidence, the other work packages and the separate H6 study remain in the [full implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). Classification `NON_REPORTABLE_DIAGNOSTIC`.

[Previous CAL-006 handoff](https://github.com/mthiessmeier/pacd-simulation/blob/8d5b9ab79f82c55c2b50c3a3c60afce5503b746d/status/SESSION_HANDOFF.md)

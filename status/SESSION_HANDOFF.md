# Session handoff · Restrictive simulated review veto

[PR #23](https://github.com/mthiessmeier/pacd-simulation/pull/23) is the public development draft on `codex/wp06-review-veto`. Its description records the exact candidate, suite results, independent review dispositions and current merge state. The [work order](../docs/work_orders/SIMULATED_REVIEW_VETO_v1.0.md) specifies the opportunity, direction, rationale and accounting rules.

| Record | Identity or evidence |
|---|---|
| Approved PR #22 | `52d8278a77614459d20773b372a11651a3edbec8`. GitHub's head, the remote feature and pull refs and the clean local checkout agreed. Two independent review-only dispositions passed that revision. |
| Verified public main | Merge `31c1645ee28a7bbd2488dfb2d354be1fdea3fd25`. Ordered parents `fcfde7c30c820c463249a97d0dd4af75869a4923` and the approved #22 head. Tree `4eed4ef988d7ddd9647c40ed4f5c35d5bb21fa67` matches the reviewed tree. |
| Feature history | Work order `a9e4bc3382f66471bbb68c868523f461bf3793ef`, producer and independent replay `177c4c978a2271bc896ca4a768f3696dee5525a4`, metrics and CLI tests `6b3e60cf40b4dcdec932fc724ec585fea80ece51`. |
| Authority | The owner authorized the exact #22 merge and next public unmerged increment. AGENTS.md, D-017 and DEC-038 govern it. Documentation PRs #9 and #11 were open drafts at preflight. |
| Source | R-TM-019, R-MD-040 / GOV-003, R-MD-058 / OPS-003. WP05/06/12. The [scope reconciliation](REMAINING_SCOPE_RECONCILIATION.csv) retains the complete source inventory and reportable gates. |

Use `pacd-sim metrics --approval-burden` on a verified episode, pinned comparison plan or pinned register. For governed override cases, OPS-003 reports an exercised-veto count and GOV-003 reports the eligible denominator and associated review, authorization, dispatch and recovery events. A zero denominator yields a null rate. Older guarded contracts retain a null override count. Failed, invalid, timed-out and incomplete attempts retain their separate statuses and missing measurements.

The matched configurations use the same two subjects and events. Static review admits requests at ticks 2 and 5. At tick 6 the veto closes the first request with a denial. Retention permits the existing governor to reconsider the action. The second request remains pending at horizon 8. The corroborated control has zero opportunities. Development seeds are 424242 and 424243. The private workspace evidence index `review/pr23/final-evidence.json` records commands, commit, configuration and invocation identities, artifact hashes, suite results and review reports. Both frozen environments use CPython 3.13.15 and uv 0.12.5. Lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`.

Independent review should challenge the eligibility boundary, superseded state, receipt-backed decision substitution, and the distinction between zero exercised and unsupported overrides. A separate owner decision controls merge. Action modification, additional override rules, uncertainty, failure and safety measurements, fair comparisons and the H6 human study remain in the [full implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). Classification `NON_REPORTABLE_DIAGNOSTIC`. [Previous approval burden handoff](https://github.com/mthiessmeier/pacd-simulation/blob/52d8278a77614459d20773b372a11651a3edbec8/status/SESSION_HANDOFF.md)

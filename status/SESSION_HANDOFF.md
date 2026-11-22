# Session handoff · Mission recovery time

[PR #25](https://github.com/mthiessmeier/pacd-simulation/pull/25) is the public development draft on `codex/wp12-mission-recovery`. Its description identifies the current candidate, observed gate results, independent review dispositions and merge state. The [work order](../docs/work_orders/MISSION_RECOVERY_v1.0.md) defines the recovery population, clock, denominator and controls.

| Record | Identity or evidence |
|---|---|
| Approved PR #23 | `f4e945e4ed31faa3004c936e2784bdcc8d1a162d`. GitHub, the feature and pull refs and the clean local checkout agreed. Two independent reviewers passed this revision. |
| Verified public main | Merge `c413f3cbadf6d39a7ede3edefa002ed825bdc65f`. Ordered parents `31c1645ee28a7bbd2488dfb2d354be1fdea3fd25` and the approved #23 head. The reviewed and merged tree is `b1f4ce462edbbea0d8c6e206ce8cf221f7231b42`. |
| Feature history | Work order `e3667bd0317ea62138ae3b0531c7dada9ad98636`, recovery calculation and reader `06cc757fb766939e74ebeb6335614cc083d9db5a`, governed fixture and public-path tests `4bc25f5430d6cc87c1a98cc444c3aa33d7e316d5`. |
| Authority and scope | The owner authorized the exact #23 merge and next public draft. AGENTS.md, DEC-038 and D-017 govern it. R-MD-020 / MIS-004 maps to WP02/WP12 and SC-02/17. The [source ledger](REMAINING_SCOPE_RECONCILIATION.csv) retains the broader acceptance criteria. |
| Concurrent work | Documentation PRs #9, #11 and #24 were open drafts at preflight. PR #24 records progress through PR #22 and proposes updates to the plan and handoff. Reconcile those historical records with the current candidate when integrating that draft. |

Use `pacd-sim metrics --mission-recovery` with a verified episode, pinned plan or pinned register. Each mission has an ordered list of observed outages. An outage already present at tick zero has an unknown onset. An outage still open at the horizon has an unknown restoration. Elapsed observation time remains available for both. Only recoveries with two observed endpoints enter the reported sum, denominator and mean.

The retain fixture isolates a session at tick 6 under static review. At horizon 8 this gives two observed outage ticks and unknown recovery time. Its matched rollback fixture restores the mission at tick 6, yielding one completed recovery of zero ticks. The veto and corroborated zero-admission controls keep their missions operational. Development seeds are 424242 and 424243. The workspace evidence index `review/pr25/final-evidence.json` records the commands, fixtures, seeds, invocations, results and independent review reports. The two frozen environments use CPython 3.13.15, uv 0.12.5 and lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`.

A separate owner decision controls merge of the reviewed head. Positive-duration restoration by a later simulator action, recovery from containment, graded restoration thresholds, attack or mixed causal attribution, failed-episode safety, calibrated comparisons and H6 retain their separate requirements. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Remaining implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) · [Previous veto handoff](https://github.com/mthiessmeier/pacd-simulation/blob/f4e945e4ed31faa3004c936e2784bdcc8d1a162d/status/SESSION_HANDOFF.md)

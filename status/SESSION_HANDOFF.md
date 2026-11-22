# Session handoff · Critical-function outage time

[PR #26](https://github.com/mthiessmeier/pacd-simulation/pull/26) is the public development draft on `codex/wp12-critical-outage`. Its description records the exact candidate, test and independent review results and merge state. The [work order](../docs/work_orders/CRITICAL_FUNCTION_OUTAGE_v1.0.md) defines the designated population, outage clock and controls.

| Record | Identity or evidence |
|---|---|
| Approved PR #25 | `66b70fe531d6a5909e0d6d2c48d17021dd1800a5`. GitHub, its feature and pull refs and the clean local checkout matched the published candidate. Both independent sessions passed this revision. Its first coverage-run failure, isolated check and passing full repeat remain in the recorded PR #25 evidence. |
| Verified public main | Merge `0fb08d688a8acfd0cb4fe99c8c6b28550e25a8e8`. Ordered parents `c413f3cbadf6d39a7ede3edefa002ed825bdc65f` and the approved #25 head. Both the reviewed and merged trees are `db575d6fdbe7a19965a0295a95437095fcd05019`. |
| Feature history | Work order `f9bdb5b7015d9b0416029c5162db032f2fc2ef27`, governed designation and fixtures `c1543a0732d73f04e1c872c4a55d5428c6be36c6`, verified metric and reader `5038d33dc32250b3f0c77919e4bed928e5f18bcf`, public-path controls `71bc4edf79325c903a120cca22b778d6a481061d`. |
| Authority and source | The owner authorized the #25 merge and next public draft. AGENTS.md, DEC-038 and D-017 govern the work. R-MD-019 / MIS-003 maps to WP02/WP12 and SC-02/17. [Source ledger](REMAINING_SCOPE_RECONCILIATION.csv) |
| Concurrent work | Documentation PRs #9, #11 and #24 were open drafts at preflight. PR #24 describes the state through PR #22. Reconcile its historical plan and handoff edits when integrating that draft. |

Use `pacd-sim metrics --critical-outage` on a verified episode, pinned plan or pinned register. Only a scenario with declared `critical_mission_ids` supplies this measurement. Each designated function contributes its outage duration on the replayed clock. Overlaps count once per function in the sum and once across all functions in elapsed outage time.

On the matched static-review fixtures mission A loses availability at tick 6 and remains down at horizon 8. The designation of A gives two function-ticks and two elapsed ticks. Designating B instead gives measured zeros. Both conditions share weights and event inputs. Under corroborated review both missions remain available. A separate shared-dependency control checks overlapping outages. Development seeds are 424242 and 424243. The private workspace index `review/pr26/final-evidence.json` records commands, config/seed/invocation identities, tests, artifact hashes and both review reports. The frozen runtime uses CPython 3.13.15, uv 0.12.5 and lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`.

The first candidate `8248a13fba32e0a7e85dd77074cb056f1f7aa233` exposed a missing entry in the test that enumerates optional scenario fields. The corrected test checks the designation in both validation and serialization schemas, including its minimum length and mission ID type. The PR records the checks and independent dispositions for the corrected head.

A separate owner decision controls merge. The binary operational threshold is a development assumption. Graded or calibrated thresholds, criticality sensitivity, broader mission outcomes, failure and safety measurements, and H6 remain in the [full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). Classification `NON_REPORTABLE_DIAGNOSTIC`. [Previous recovery handoff](https://github.com/mthiessmeier/pacd-simulation/blob/66b70fe531d6a5909e0d6d2c48d17021dd1800a5/status/SESSION_HANDOFF.md)

# Session handoff · Per-function mission availability

[PR #27](https://github.com/mthiessmeier/pacd-simulation/pull/27) is the public development draft on `codex/wp12-mission-availability`. Its description records the candidate revision and the disposition of tests and independent reviews. A separate owner decision controls merge. [MIS-001 work order](../docs/work_orders/FUNCTION_AVAILABILITY_v1.0.md)

| Record | Identity or evidence |
|---|---|
| Accepted PR #26 | Approved head `ad0f80f993a78ce1a0241ab491291d91bb826ede`. Both private independent reviews passed that revision. The PR, feature ref, pull ref and local checkout matched. The published evidence index matched SHA-256 `d18d6e924ec13c90f895b5e50c587768a7a80b142d9893c2a2f4dcf40c699bab`. |
| Verified main | Merge `526bc4e4bc03eb0c05ee67d0695bd4bd405a26fd`. The parents are `0fb08d688a8acfd0cb4fe99c8c6b28550e25a8e8` and the approved #26 head, in that order. Reviewed and merged tree `39a5504b630f86b7dc45d6e969a4306f5c7d69d0`. |
| Current feature | Work order `79dcf67d5e68148adbde77cf16c61364629e3f6e`. Implementation and regression tests `2ee6140b0a4b3608bcf6628656e8e521027ada04`. The open PR supplies the precise review target. |
| Source and authority | MD-017 / R-MD-017 / MIS-001, SC-02/17 and WP02/WP12. The latest owner instruction authorizes the #26 merge and this next public draft. DEC-038 and AGENTS.md govern synthetic development. D-017 governs licensing. The separate documentation drafts #9, #11 and #24 were open at preflight. |
| Environment | CPython 3.13.15, uv 0.12.5, project lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. Use the workspace's populated `var/cache/uv-project` for frozen offline reconstruction. |

Use `pacd-sim metrics --function-availability` with a verified run, pinned plan or pinned register. The paired scenarios designate different critical functions and share an operational timeline. On the static fixture, the focused checks observed mission A operational for 6/8 ticks and B for 8/8. The corroborated and rollback controls gave 16/16 possible function-ticks. A zero horizon gives a null fraction. An unmeasured attempt retains its status. The private index `review/pr27/final-evidence.json` records final commands, run identities, hashes and review dispositions. The plan uses development seeds 424242 and 424243.

Dependency-model validation, graded mission states, defensive harm attribution, failed-episode safety accounting and the separate H6 human study remain in the [full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). The historical PR #19 discrepancy recorded under PR #26 remains unexplained. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Previous handoff](https://github.com/mthiessmeier/pacd-simulation/blob/ad0f80f993a78ce1a0241ab491291d91bb826ede/status/SESSION_HANDOFF.md)

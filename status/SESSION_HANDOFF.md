# Session handoff · Enterprise population endpoints

[PR #28](https://github.com/mthiessmeier/pacd-simulation/pull/28) is the public development draft on `codex/wp02-enterprise-populations`. Its description records the exact review commit, verification results and independent dispositions. A separate owner decision controls merge. [WP02 work order](../docs/work_orders/ENTERPRISE_POPULATIONS_v1.0.md)

| Record | Identity or evidence |
|---|---|
| Approved PR #27 | `6d838d8ff7f332801e8b9baa734dee939ef024ae`. Both independent reviews passed this revision. The PR head, feature ref, pull ref and local checkout matched. The private evidence index matched SHA-256 `84288f281e1781193f483f00f37e22e6c6cada2155c7e9470ccb82721cdf83c1`. |
| Verified main | Merge `8cda05df92c180a4c3c32e038534d061b55822bb`, with parents `526bc4e4bc03eb0c05ee67d0695bd4bd405a26fd` and `6d838d8ff7f332801e8b9baa734dee939ef024ae` in that order. Approved and merged tree `e1a0dd91ddd4d8befc84df07c6804e599d0b716b`. |
| Feature history | Work order `02df5f97cf77b823bb3f50936e1bb5040577edd4`, governed fixtures `a38e91165f6e6f89ac195936c719eeca725fb184`, reset and replay tests `4404a6ecdcb5789e9909cf2d7a3249b9121bc571`. |
| Source and authority | R-EC-020, R-WO-076, R-TM-013 under WP02 and SC-01/02/15. The owner authorized the #27 merge and next public draft. AGENTS.md, DEC-038 and D-017 govern this development work. Draft documentation PRs #9, #11 and #24 were open at preflight. |
| Reproduction | CPython 3.13.15, uv 0.12.5, lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. Offline reconstruction uses the dedicated workspace cache `var/cache/uv-project`. |

The two configurations define all identities, sessions, services and mandatory session-to-service dependencies explicitly. For each population, the final numbered subject supports the target mission. The other services support the reference mission. Nine focused cases passed for population integrity, reset, restoration, reference rejection, verified execution and replay. The static diagnostic preserved the reference mission for all eight ticks and the target for six. Under corroborated review both remained available throughout.

Use the existing `diagnostic` and `metrics --function-availability` readers. The private evidence index `review/pr28/final-evidence.json` records the exact candidate, test commands, hashes, review reports and the pinned plan. Development seeds are 424242 and 424243. Separately enrolled repeats at each size test determinism. The unlaunched slot retains its disposition.

These endpoints exercise one synthetic role and a bounded service graph. Richer role, privilege, trust-path, degradation, calibration and failed-episode safety criteria, and the separate H6 study, remain in the [full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). Classification `NON_REPORTABLE_DIAGNOSTIC`. [Previous handoff](https://github.com/mthiessmeier/pacd-simulation/blob/6d838d8ff7f332801e8b9baa734dee939ef024ae/status/SESSION_HANDOFF.md)

# PACD session handoff - WP07 sensing-profile operator

**Evidence class** `NON_REPORTABLE_DIAGNOSTIC`. Owner instruction authorized merging PR #14 at one exact head and then implementing the next authorized increment for independent review. The choice of a single development operator follows the sequencing in the [remaining implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). See the [WP07 work order](../docs/work_orders/SENSING_PROFILE_OPERATOR_v1.0.md) and the [source ledger](REMAINING_SCOPE_RECONCILIATION.csv).

## Verified starting state

| Record | Identity or disposition |
|---|---|
| Repository | Private `mthiessmeier/pacd-simulation`, default `main` |
| Approved PR #14 head | `18f3364775ad379b73b4b1ea958b125e4ace31cf`, checked via PR data and Git ref. Two independent scoped passes recorded in the [merged PR](https://github.com/mthiessmeier/pacd-simulation/pull/14). |
| Live merge | `814bb411bf1f9512950ecc715c1558ce8fc9aaa3`, first parent `b4609ac1c8d7f4631ad371edf81587aed313842e`, second parent the approved head, tree `2337758d1a77dd379ceb924b07bd2de54039f452`. |
| Concurrent work preserved | PR #13 had already merged the owner's license decision D-017. The twelve licensing, metadata and governance paths account for the merge's entire diff against the approved head. Docs PRs #9 and #11 remain separate. |
| Branch | Fresh ordinary clone `repo/wp07-governed-operator`, feature branch `codex/wp07-policy-variation` at the verified merge. |
| Governing controls | Current root AGENTS.md, decision log, DEC-037/038 continuation and owner instruction. The simulator license adopted on main is Apache-2.0 within LICENSING.md. |
| Inputs and environment | Frozen uv 0.12.5, CPython 3.13.15. The prior acceptance and all broader residuals remain available in the [WP05/WP06 handoff](https://github.com/mthiessmeier/pacd-simulation/blob/18f3364775ad379b73b4b1ea958b125e4ace31cf/status/SESSION_HANDOFF.md). |

Clean post-merge checkout `repo/wp14-merged-main-check` passed the full frozen suite with 442 passed and one Windows directory-symlink privilege skip. The lock SHA-256 was `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. The retained command output is `review/wp07-sensing/main-pytest.log`.

[Draft PR #15](https://github.com/mthiessmeier/pacd-simulation/pull/15) opened with implementation commit `ad16f1f27dfaad5aad967ad759575dfea5dfc6d4` following work order `bb211268ee7d069917f51e5a3b1df828199b547b`. This additive checkpoint identifies the code under review. The PR records the final candidate SHA, checks and disposition. Initial checks passed 71 domain tests, 62 governed configuration and sensing selector tests, 81 replay/metrics/comparison tests, and seven matched-integration and schema checks. Some tests overlap across these groups.

The first exact-head review candidate was `5cb1aa375c756f8d28ee6638e3c61731f5055a19`. Both full suites passed 480 tests with one skip. Its eight guarded compatibility cases and twelve new sensing cases completed. A separate reviewer reproduced two errors despite those passing checks. A clean older executable targeting another checkout produced a receipt claiming the target SHA, and a legacy isolation fixture could declare a reserved sensing scenario name. Private reproductions are under `t/ir7b`. A second review-only session independently checked timing, inactive siblings, budget, failure and invalid attempt denominators under `t/ir7a`.

Corrections were prepared in `repo/wp07-sensing-verified` on the same feature branch to preserve the exact first-candidate checkout and its active tests. The corrections reserve both sensing role identities and bind verified sensing measurements to the executing revision, including unplanned launches. The pull request records the corrected SHA and fresh review disposition. Archived unplanned non-sensing v1 artifacts retain their original provenance format.

## Checkpoint

The first deliverable is a synthetic, reversible sensing-profile switch with fixed, adaptive and disabled choices, one evaluator-owned decision opportunity, cost budget, clock, and a declared passive-observer knowledge model. Public execution and verification use the normal guarded, receipt-backed diagnostic infrastructure. Broader scope and separate reportable and human-study gates are retained.

Local commands, raw evidence and review outcomes belong under the dedicated workspace's `review/wp07-sensing` and candidate-specific review directories. The PR records the exact candidate SHA, gate results and independent disposition without requiring a self-referential commit. The candidate requires the scoped independent review and gate evidence recorded on its PR. Merge requires an exact-head owner decision. WP08 and WP09 retain portfolio and coordination work with the start and closure dependencies in the remaining plan.

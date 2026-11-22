# PACD session handoff - WP07 sensing-profile operator

**Evidence class** `NON_REPORTABLE_DIAGNOSTIC`. Owner instruction authorized merging PR #14 at one exact head and then implementing the next authorized increment for independent review. The release of a single development operator follows the sequencing in the [remaining implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). See the [WP07 work order](../docs/work_orders/SENSING_PROFILE_OPERATOR_v1.0.md) and the [source ledger](REMAINING_SCOPE_RECONCILIATION.csv).

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

## Checkpoint

The first deliverable is a synthetic, reversible sensing-profile switch with fixed, adaptive and disabled choices, one evaluator-owned decision opportunity, cost budget, clock, and a declared passive-observer knowledge model. Public execution and verification use the normal guarded, receipt-backed diagnostic infrastructure. Broader scope and separate reportable and human-study gates are retained.

Local commands, raw evidence and review outcomes belong under the dedicated workspace's `review/wp07-sensing` and candidate-specific review directories. The PR records the exact candidate SHA, gate results and independent disposition without requiring a self-referential commit. Next action is to finish the bounded implementation, run exact-head checks, and deliver an unmerged PR for independent review.

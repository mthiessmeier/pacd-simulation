# PACD session handoff · WP08 prospective selection and fallback

[Draft PR #17](https://github.com/mthiessmeier/pacd-simulation/pull/17) implements a contextual sensing selection and a matched scheduled control. The work order defines the inputs, calculation, fallback and acceptance checks. [Work order](../docs/work_orders/PROSPECTIVE_SENSING_SELECTION_v1.0.md)

## Source, authority and branch

| Record | Identity |
|---|---|
| Approved [PR #16](https://github.com/mthiessmeier/pacd-simulation/pull/16) | `eb19c2897d65fbf70a5f6420193a516b44932af1`. The remote PR ref and GitHub metadata agreed. Two independent review-only sessions passed that revision. |
| Verified merge on main | `74ac0b9a2a4deb10e77cab31db248eee19a7794a`. Ordered parents `05c45758cabba10a40aa1e15192b78edece3346a` and the approved head. Merge tree `79fe52775c872c77ebf479a7c3d748df5d352f9f` matches the approved head. |
| Visibility and delivery decision | GitHub reported `mthiessmeier/pacd-simulation` as public. The earlier handoff and AGENTS.md §6 described private development. The owner explicitly approved opening this WP08 PR publicly. That decision is scoped to this delivery. |
| Fresh branch | `codex/wp08-prospective-selection` in the dedicated workspace's ordinary clone `repo/wp08-prospective-selection`. Work order `2a4d533569e6b984e612104ddadf6a19107142e0`, implementation `2425897f2447c89845473438525f96e12436a3fc`. PR #17 opened at the implementation commit. The PR records the final candidate SHA and disposition. |
| Controls | Live AGENTS.md, D-017, the Phase 2 continuation decisions and the owner's exact-head merge and WP08 instruction. PRs #9 and #11 were still open drafts at preflight. [Prior WP03 handoff](https://github.com/mthiessmeier/pacd-simulation/blob/eb19c2897d65fbf70a5f6420193a516b44932af1/status/SESSION_HANDOFF.md) |

## Implementation and evidence

The third-delivery opportunity uses the same evidence, schedule, budget and safety policy in both conditions. Each decision retains its delivered-prefix digest, recommendation, reason and applicable score components. The simulator checks admissibility before referral and reevaluates authority before dispatch. Replay independently reconstructs selection from the governed sensor inputs. The selection window applies at referral. Candidate- and dispatch-level CAL-006 denominators remain open.

During implementation, 39 selector/evidence context tests, 36 writer/provenance tests and 14 cross-layer tests passed. These counts include overlaps. The cross-layer tests cover nominal/costly/delayed comparisons, prefix linkage, guarded outcomes and authentic local receipts for inconsistent decisions. Reconciliation preserved 558 source units, 47 metric IDs, 18 workstreams and 16 work packages.

Use the existing offline frozen uv 0.12.5 and CPython 3.13.15 environment. Lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. The PR and the dedicated workspace's `review/wp08-selection/final-evidence-index.json` retain exact commands, planned and observed configuration/seed/invocation identity, attempt dispositions, suite results and independent review. The two registered development seeds are 424242 and 424243.

For independent review, challenge matching against the WP03 prefix, delivery order, strict positivity at utility zero, stale and unavailable history, hard admission limits and receipt-backed rejection of incorrect choices. Contrast the recommendation with the actual verified switch, denied review and rollback. Keep incomplete attempts and failed or invalid evidence visible in their separate populations.

Merge of PR #17 requires an owner decision on its exact head. WP08 remains open for the other variation classes, broader utility, policy transitions and class coordination. WP09 retains specialist arbitration. The [full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) retains all residual work and the separate H6 study requirement. Classification `NON_REPORTABLE_DIAGNOSTIC`.

# PACD session handoff · WP03 evidence freshness

**Candidate.** [Draft PR #16](https://github.com/mthiessmeier/pacd-simulation/pull/16) adds a read-only `pacd-sim evidence-trace RUN_DIR` on `codex/wp03-evidence-freshness`. Its [work order](../docs/work_orders/VERIFIED_EVIDENCE_CONTEXT_v1.0.md) defines the delivered fields, assumptions and review challenges. All outputs are `NON_REPORTABLE_DIAGNOSTIC`.

## Merge verification

| Record | Verified identity |
|---|---|
| Repository and authority | Private `mthiessmeier/pacd-simulation`. The owner's latest instruction approved the specified head of PR #15 and one subsequent development increment. Current AGENTS.md, D-017 and the continuation decisions recorded in status/PHASE2_INCREMENT1.md apply. |
| Approved head of [PR #15](https://github.com/mthiessmeier/pacd-simulation/pull/15) | `8b724603d6bc92af03ac58733564495edc94b9cc`. PR data and the remote Git ref agreed. Prior independent dispositions are recorded on that PR. |
| Merged main | `05c45758cabba10a40aa1e15192b78edece3346a`, first parent `814bb411bf1f9512950ecc715c1558ce8fc9aaa3`, second parent the approved head. The GitHub response, remote main and clean clone agreed. |
| Tree | `10cbe39c60619af580ab2835f0ec0d94260f694f` on both merged main and the approved head. Whole-tree diff was empty. |
| Continuity | Previous [WP07 handoff](https://github.com/mthiessmeier/pacd-simulation/blob/8b724603d6bc92af03ac58733564495edc94b9cc/status/SESSION_HANDOFF.md). PR #9 and PR #11 were open drafts at preflight. Their historical package instructions do not supersede live authority. |

## Development checkpoint

Used the fresh ordinary clone `repo/wp03-evidence-freshness`. Work order `bac93ec3b115251ef68014fcbfeccabec316a22b` preceded implementation `b2c40355fb2b38ea79d93864d3a053c76b34c075`. PR #16 opened at that implementation commit. Its final body records the exact candidate SHA, full checks and independent disposition. The private evidence index is `review/wp03-evidence-freshness/final-evidence-index.json`.

WP03 supplies an input capability for WP08. The earlier planner's repeated readings can come from the same sensor. The new trace preserves that fact, distinguishes freshness from signal strength, and tracks fresh sensors separately for each subject. Event labels and generated latent signals are evaluator data. Use the actual delivered signal and an opaque episode-local key on the shared evidence boundary. In the v1 fixture the governed event tick models the sensor's acquisition time. The three-tick window is a development assumption.

The 22 domain tests passed. Another 13 CLI/replay tests passed, including the inclusive three-tick boundary, stale-at-four, tied readings, missing subjects, changed observations and missing receipts. The work order and plan link the source obligations. Reconciliation against the preserved handoff accounted for 558 source units, 47 metric IDs, 18 workstreams and 16 packages.

## Reproduction and review

Use CPython 3.13.15 and uv 0.12.5. The lock SHA-256 is `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. The [work order](../docs/work_orders/VERIFIED_EVIDENCE_CONTEXT_v1.0.md) gives the public entry point. Candidate evidence in the private workspace retains exact commands and results, including a clean merged-main check, candidate coverage, frozen reconstruction, separate review-only probes and a development comparison on seeds 424242 and 424243 with an unlaunched slot. Consult the PR's exact-SHA disposition before proceeding.

For independent review, challenge source linkage and age at delivery, the bound on retained inputs, missing/repeated sources, the separation between simulator truth and delivered observations, and release on invalid receipts. Compare unchanged v1 raw, summary and metric behavior. Keep failed or incomplete attempts outside the set of measured completions and retain their identities.

Only the owner can approve merging the candidate. A next WP08 slice can bind the accepted context to a prospective, governed selection and fallback under matched inputs. Source reliability, contradiction, competing beliefs, all six variation classes, portfolio weights, coordination and the remaining work packages continue under the [full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). CAL-005/CAL-006 still require decision-level definitions and denominators. H6 retains separate human-study authority.

# Current implementation and remaining scope

**Checkpoint: merged PR #22, 22 November 2026.** The implementation revision is [`31c1645ee28a7bbd2488dfb2d354be1fdea3fd25`](https://github.com/mthiessmeier/pacd-simulation/tree/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25). Its reviewed PR head was [`52d8278a77614459d20773b372a11651a3edbec8`](https://github.com/mthiessmeier/pacd-simulation/commit/52d8278a77614459d20773b372a11651a3edbec8). This record includes merged implementation through that checkpoint. PR #23 was an open draft when the checkpoint was checked; its proposed behavior is not counted here.

The simulator now follows a bounded decision from delivered evidence through a proposed action, simulated review, fresh authorization, in-memory execution, independent state verification and measured mission consequences. It also implements a reversible sensing change and four optional metric extensions. The broader original program remains incomplete. All output remains `NON_REPORTABLE_DIAGNOSTIC`.

[Public demonstration and reproduction guide](../docs/current_demo/README.md) · [Source-unit ledger](REMAINING_SCOPE_RECONCILIATION.csv) · [Complete remaining plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) · [Architecture](../docs/ARCHITECTURE.md)

## What is implemented at this checkpoint

| Capability | Merged behavior and evidence | Boundary that still matters |
|---|---|---|
| Planned development comparisons | [PR #12](https://github.com/mthiessmeier/pacd-simulation/pull/12) binds cells, conditions, scenario/configuration, clean code revision, development seeds, exogenous events and invocations. Launch and release check expected against observed identity; failed, timed-out, incomplete, invalid and retry slots remain visible. | `controlled` and `system_level` record intended mode. Neither that label nor identical seeds establishes fairness, trusted preregistration or protocol approval. |
| Guarded action through consequences | [PR #14](https://github.com/mthiessmeier/pacd-simulation/pull/14) binds concrete action, target, evidence, policy, pre-state and validity to a simulated review. Fresh governor authority precedes dispatch, independent full-state verification and optional recovery. | The current broker supports `isolate_session` and `switch_sensing_profile`. This is a local synthetic execution boundary; general authority envelopes, tiers and action semantics remain incomplete. |
| Substantive sensing variation | [PR #15](https://github.com/mthiessmeier/pacd-simulation/pull/15) changes subsequent delivered precision from one to two decimal places, with fixed/adaptive/disabled conditions and verified cost/duration. | One sensing class is integrated. The passive-observer knowledge proxy is a declared synthetic assumption and contains no adaptive attacker learning or decision mechanism. |
| Evidence-aware prospective selection | [PR #16](https://github.com/mthiessmeier/pacd-simulation/pull/16) verifies evidence age and source context. [PR #17](https://github.com/mthiessmeier/pacd-simulation/pull/17) uses the delivered prefix at one third-delivery opportunity for contextual versus scheduled sensing, exact utility arithmetic and explicit fallback. | Built-in episodes use one sensor, a three-tick freshness window and a bounded prefix. Temporal persistence is not independent corroboration. Richer beliefs, source reliability, contradiction and calibrated uncertainty remain open. |
| CAL-006 sensing freshness | [PR #18](https://github.com/mthiessmeier/pacd-simulation/pull/18) attributes referral and execution separately to the original supporting measurements, retaining unknowns and explicit denominators. | Applies to the two prospective sensing conditions. Fresh evidence can become stale during review; measurement does not add a dispatch freshness gate. Empty populations yield null. |
| MIS-002 mission loss | [PR #19](https://github.com/mthiessmeier/pacd-simulation/pull/19) integrates binary mission unavailability over verified simulated time, weighted by configured criticality, with per-mission contributions and exposure. | Uses `required_dependencies_v1` guarded episodes. Graded degradation, broader cause attribution and calibrated/frozen harm weights remain open. Zero exposure yields null. |
| GOV-002 review routing | [PR #20](https://github.com/mthiessmeier/pacd-simulation/pull/20) matches escalations to complete bound packages and terminal approval, denial or expiry. Refused and pending requests stay visible in the denominator. | Terminal review does not guarantee dispatch or execution. Zero escalations yields null. Current package completeness covers the implemented contract versions. |
| Operator brief at review admission | [PR #21](https://github.com/mthiessmeier/pacd-simulation/pull/21) adds the governor rationale, action/target, delivered reading and age, and a conditional immediate binary mission preview to the request digest. | Opt-in `operator-preview-v1` supports the two actions. Compromise probability is null; the preview is conditional on fresh authority and the submitted state, not a prediction of realized outage. |
| OPS-003 simulated approval burden | [PR #22](https://github.com/mthiessmeier/pacd-simulation/pull/22) matches each admitted request to approval, denial or expiry, or censors observed wait at the verified horizon while pending. It reports request-ticks, per-request rows and a resolved-only mean/denominator. | Capacity/refusal differs from admission. Pending terminal tick is null. Override count is null/unsupported. Queue time does not measure staff effort, human trust or calibrated operational cost. |

The four optional projections are available through individual-run, pinned-plan and pinned-register metrics paths. They require verified completed episodes. Failed or invalid attempt identities remain retained, while unavailable ordinary episode measurements remain null. Independently attributable safety observations from such failures are a separate unfinished requirement. The fixed v1 raw/flat-summary schemas have not acquired every proposed field merely because an optional projection exists.

## How to read the progress ledger

The ledger preserves **558 source units, 47 metric IDs, 18 workstreams and 16 work packages**. Source units include headings, cross-references, standing controls and overlapping requirements; they are not equally sized engineering tasks. A percentage obtained by dividing accepted rows by 558 would therefore misrepresent completion. This checkpoint does not publish an overall completion percentage.

The [historical CSV](history/REMAINING_SCOPE_RECONCILIATION_PR8.csv) is the exact pre-refresh ledger as carried at the PR #22 revision. It contains the **PR #8 baseline assessment originally introduced in PR #12**; it is not a file that existed at PR #8. Its SHA-256 is `f05ab2dfe7fc1273fc26c73b40462171107a06ae778c84ce13aabbc1438a44b8`.

The current ledger preserves its column schema, order, source IDs/text/export lines, original acceptance criteria, remaining-acceptance text, requirement/workstream/package allocations, dependencies and author dispositions. The refreshed fields separate current implementation evidence from original closure gates:

- **202 rows** have a `PR22_MERGED_EVIDENCE_REFRESH` marker, current code/test paths, pinned work-order links, PR records and specific residual behavior. For these rows, `accepted_commit` identifies the merged implementation inspected for the cited slice; it does not mean the whole requirement is accepted complete.
- **356 rows** carry `PR8_BASELINE_RETAINED`. Their evidence/status assessments remain historical baseline statements; no fresh PR22 full-row reassessment is claimed. The row's evidence revision and review reference retain their original meaning.
- **Two rows change from open to partial:** FM-010, because integrated sensing supplies a substantive single-layer adaptive slice; and MD-102, because development plans bind comparison-mode intention while the proposed manifest field and fairness review remain unfinished.
- **No row is newly declared accepted complete. All 47 metric IDs retain `draft methodology`.** Implementing a diagnostic projection does not freeze its definition, weights, thresholds or primary-outcome status.

| Source-unit status | Count at this checkpoint |
|---|---:|
| Accepted complete under the row's bounded criterion | 27 |
| Partial | 261 |
| Open | 50 |
| Not yet evidenced | 1 |
| Draft methodology | 119 |
| Source-explicitly deferred | 3 |
| Context | 97 |
| **Total** | **558** |

The original broader Phase 2 obligations remain in the ledger and plan. Subsequent sequencing does not remove scope or relabel it as optional. A removal, narrowing or new deferral requires an explicit author disposition identifying the affected source/requirement IDs and consequences.

## Remaining work and the next bounded increments

| Area | Remaining implementation and evidence |
|---|---|
| WP02–WP04: environment, evidence and adversary | Original enterprise scale/entity coverage; richer temporal/graded mission mechanics; multi-source reliability, contradictions, competing beliefs and calibration; adaptive synthetic adversary state machines. Current adversary events remain scripted. |
| WP05–WP06: authority and oversight | Remaining action contracts, contextual delegation, evidence levels and tiers 0–5; modification/override and their downstream accounting; richer uncertainty/impact packages; broad recovery and independently attributable failed-episode safety evidence. |
| WP07–WP09: polymorphism and coordination | Extend the implemented sensing slice to the other substantive classes, contextual multi-objective portfolios and integrated specialist proposal/arbitration/coordination. Six category labels and a proposal-sorting helper do not close these packages. |
| WP10–WP11: conditions and fairness | All eight original defender/reference conditions, authentic-system and controlled modes, and all sixteen fairness dimensions, including resource budgets and declared information/action asymmetries. |
| WP12–WP14: measurement and evaluation | Remaining metric/data contracts; failure/tail attribution and null semantics; all sixteen scenario families and ten control/failure cases; ten draft ablations, calibration/exposure records, sensitivity and generalization analysis. |
| WP15 and external gates | Independent reconstruction of the expanded program, source-by-source closure and protocol-readiness review. Reportable execution, hypothesis classification and freeze approval remain separately gated. H6 requires a separately authorized human-participant study. |

At this checkpoint, oversight modification/override is a concrete remaining WP06 item; any PR #23 proposal must be assessed and accepted separately. After each merged slice, update its source rows and the corresponding public evidence. Continue the other packages when their bounded start dependencies are available, while retaining every full-package closure requirement in the [remaining plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). The first guarded loop, first sensing operator, evidence-aware selection, operator brief and queue-time accounting are already implemented and should not be scheduled again as wholly future work.

## Merged implementation history and reported verification

This table records the **candidate-suite results reported in each public PR description**, with the merged revision and the separately reviewed candidate head. These are not new test executions from this documentation refresh. Public descriptions identify review-only sessions and private evidence indexes/hashes; the full private raw logs and review packets are not included in this repository. A review-session PASS is distinct from a GitHub account approval or an independent protocol verdict.

| PR and increment | Merged revision | Reviewed candidate | Reported full suite | Reported combined coverage |
|---|---|---|---|---:|
| [#12 · Development plans](https://github.com/mthiessmeier/pacd-simulation/pull/12) | [`f881f65`](https://github.com/mthiessmeier/pacd-simulation/commit/f881f6553e9210d84e8f009a9700c0ce65eceabd) | [`d70510d`](https://github.com/mthiessmeier/pacd-simulation/commit/d70510d8abb27d6d9729c402f06b0e69bc33c9f3) | 392 passed, 1 skipped | 80.59% |
| [#14 · Guarded isolation](https://github.com/mthiessmeier/pacd-simulation/pull/14) | [`814bb41`](https://github.com/mthiessmeier/pacd-simulation/commit/814bb411bf1f9512950ecc715c1558ce8fc9aaa3) | [`18f3364`](https://github.com/mthiessmeier/pacd-simulation/commit/18f3364775ad379b73b4b1ea958b125e4ace31cf) | 442 passed, 1 skipped | 81.76% |
| [#15 · Sensing operator](https://github.com/mthiessmeier/pacd-simulation/pull/15) | [`05c4575`](https://github.com/mthiessmeier/pacd-simulation/commit/05c45758cabba10a40aa1e15192b78edece3346a) | [`8b72460`](https://github.com/mthiessmeier/pacd-simulation/commit/8b724603d6bc92af03ac58733564495edc94b9cc) | 488 passed, 1 skipped | 82.53% |
| [#16 · Evidence context](https://github.com/mthiessmeier/pacd-simulation/pull/16) | [`74ac0b9`](https://github.com/mthiessmeier/pacd-simulation/commit/74ac0b9a2a4deb10e77cab31db248eee19a7794a) | [`eb19c28`](https://github.com/mthiessmeier/pacd-simulation/commit/eb19c2897d65fbf70a5f6420193a516b44932af1) | 514 passed, 1 skipped | 82.76% |
| [#17 · Prospective selection](https://github.com/mthiessmeier/pacd-simulation/pull/17) | [`61eb93e`](https://github.com/mthiessmeier/pacd-simulation/commit/61eb93e96369fc78decd03f9b8a2d846633bc314) | [`8111df4`](https://github.com/mthiessmeier/pacd-simulation/commit/8111df4de98e976f9d19d619145e913a723b2e13) | 564 passed, 1 skipped | 83.12% |
| [#18 · CAL-006](https://github.com/mthiessmeier/pacd-simulation/pull/18) | [`b58c46e`](https://github.com/mthiessmeier/pacd-simulation/commit/b58c46e5a56bddc701b3e55c595885b6e6c429b1) | [`8d5b9ab`](https://github.com/mthiessmeier/pacd-simulation/commit/8d5b9ab79f82c55c2b50c3a3c60afce5503b746d) | 587 passed, 1 skipped | 83.30% |
| [#19 · MIS-002](https://github.com/mthiessmeier/pacd-simulation/pull/19) | [`de09b3e`](https://github.com/mthiessmeier/pacd-simulation/commit/de09b3e66b653f58a4e18660195e3571e1bf28c5) | [`94fa413`](https://github.com/mthiessmeier/pacd-simulation/commit/94fa41363b21420dd7e3291b82017cd40cb6cb5d) | 604 passed, 1 skipped | 83.43% |
| [#20 · GOV-002](https://github.com/mthiessmeier/pacd-simulation/pull/20) | [`546005b`](https://github.com/mthiessmeier/pacd-simulation/commit/546005be5ee0fb2289ef639b58d7d8102e16ae70) | [`c90c55b`](https://github.com/mthiessmeier/pacd-simulation/commit/c90c55b1860430de033fef112a6ab04c7576f607) | 623 passed, 1 skipped | 83.67% |
| [#21 · Review brief](https://github.com/mthiessmeier/pacd-simulation/pull/21) | [`fcfde7c`](https://github.com/mthiessmeier/pacd-simulation/commit/fcfde7c30c820c463249a97d0dd4af75869a4923) | [`fb2476d`](https://github.com/mthiessmeier/pacd-simulation/commit/fb2476d07d2db3d99b1944a587d192467679d87f) | 655 passed, 1 skipped | 83.85% |
| [#22 · OPS-003](https://github.com/mthiessmeier/pacd-simulation/pull/22) | [`31c1645`](https://github.com/mthiessmeier/pacd-simulation/commit/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25) | [`52d8278`](https://github.com/mthiessmeier/pacd-simulation/commit/52d8278a77614459d20773b372a11651a3edbec8) | 669 passed, 1 skipped | 83.92% |

The PR descriptions identify the skip as a Windows directory-symlink privilege limitation. They also preserve unsuccessful and corrected attempts: PR #16 records a transient Git-state lookup timeout and retry; PR #17 records arithmetic/provenance corrections, failed or interrupted attempts and final review; PR #21 records an observation-provenance defect found by two review sessions and its correction. Passing final suites do not erase those records. Coverage is a test metric, not a completion percentage or an assurance of safety.

PR #13 adopted Apache-2.0 licensing; it is not an additional simulation capability. The [older application demonstration](../docs/application_demo/README.md) and original scope/acceptance records remain historical evidence. Consult the current demonstration guide for expected acceptance oracles and the outcome of any newly attempted reproduction; historical reported tests must not be presented as a new local run.

## Local documentation-refresh verification

The [2026-11-22 validation record](../docs/current_demo/VALIDATION.md) records 49 passing existing unit tests and successful source-reconciliation, helper syntax, lint and format checks. The full public CLI walkthrough stopped at the unmodified doctor's free-space gate (about 4.2 GiB available versus 20 GiB required) before any diagnostic case was launched. The guide's numeric observations remain expected fixture results; no new four-run result is claimed here.

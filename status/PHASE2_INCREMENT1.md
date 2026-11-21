# Phase 2 Increment 1 candidate · 21 November 2026

## Preflight and decision log

The supplied Downloads folder contains the bootstrap handoff and historical review material. The approved simulator workspace is `%USERPROFILE%\PACD-Workspaces\PACD-Simulation`. Read-only discovery found a clean original checkout on `codex/environment-bootstrap-v1` at `d3d63bc213c386a7839bb7a2f05cfdafa3ca5eb3`. Its local main reference is stale. Private GitHub PR #1 merged into `main` at `a09991a3a6ed6ff3889138a787c61c8c545c1cd0`. The live annotated `pacd-bootstrap-v1.0` object is `cbd9517cb86888243ff6b02551aab6af3202c0c9` and peels to that merge. No later remote branch or pending increment was visible at discovery. A new, separate clone at `repo/pacd-phase2-i1` starts the candidate branch from that verified main. The old checkout, Downloads and publication files remain inputs.

DEC-037 records acceptance of the bootstrap. DEC-038 permits Phase 2 development and calibration with the evidence label `NON_REPORTABLE_DIAGNOSTIC`. The attached continuation limits immediate work to Increment 1 with a separate PR and independent review before merge. The selected change types the existing five diagnostic inputs and the remaining §7 audit, summary and manifest records. It uses the current evaluation harness, serialization and evidence pipeline. Cutoff for feature work was set at 13:05 Eastern on November 21. Application deadline recorded by the handoff is November 22 at 23:59 Pacific / November 23 at 02:59 Eastern.

| Pre-edit check | Evidence |
|---|---|
| Governing instructions | Repository root `AGENTS.md`, also present in supplied bootstrap package. No deeper tracked agent instructions. CPU-only, workspace-local, synthetic, no external execution adapter. |
| Accepted capabilities | Immutable domain state, component-local telemetry RNG, scripted candidate generation, independent governor, in-memory broker, exact state verification and cooperative local run receipts. A null defender and a diagnostic PACD path exist. |
| Gaps selected | Config shapes spread across manual checks. Raw audit rows, episode totals and the manifest assembled from dictionaries. |
| Deferred | Core environment expansion, red agent/scenarios, comparison baselines, integrated polymorphism and research metrics. No empirical comparison authorized for this increment. |
| Toolchain | Existing verified uv 0.12.5, CPython 3.13.15, clean isolated environment. Offline lock check and frozen sync. `uv.lock` SHA-256 `12372a81d459ec112417b7a76b7fc65a32f5e0da865b39a466c443563a28f290`. Dependency delta is zero. |
| Starting observations | Doctor passed on the base. A fresh audit of the accepted locked environment returned exit 1 (83 advisory entries, six distributions). Advisory disposition and new validation belong to this increment's reviewer packet. |
| Reproduction route | First reproduce the accepted fixture. Then run the component tests and same-seed CLI twice from a recorded clean development commit, verify each retained run and regenerate both derived files from raw Parquet. |

## Development snapshot

The selected condition is the shipped `diagnostic_identity_smoke` scenario with the existing diagnostic policy, baseline descriptor, metrics and registered development seed 424242. The fixed scenario schedules benign administration at tick 1 and a synthetic adversary event at tick 2. Noise and delivery use the telemetry stream keyed by sensor and event ID. Use 424243 only as a registered sensitivity-to-seed check. Both seeds are development-exposed. No hidden holdout or comparison condition is assigned.

The single case contains three proposals, selected in advance from the accepted scenario. The questions are whether wire compatibility survives the schema change, whether the governor dispositions are retained separately from executed transitions, and whether replay and raw-to-derived regeneration agree. Neither independent sampling nor an effectiveness score is involved. Any failed invocation or inconsistent digest must be retained and explained. The snapshot is the code commit, five checked-in configs, `uv.lock`, `metrics/summarize.py`, `reproducibility/manifest.py`, and the regeneration script in the same tree. The retained manifest binds the exact run inputs. Separate gate runs are recorded locally under `review/phase2-i1-20261121`.

## Source reconciliation

| Requested source | Located record or gap | Consequence |
|---|---|---|
| Project charter | Older v0.9 located. Current requested version unavailable. | Current repository controls and explicit continuation govern the bounded work. |
| Decision register and canonical manifest | v1.9 members of the final EPUB freeze package. Later-dated v1.1 copies have a package-adoption caveat. DEC-037/038 agree. Publication decision numbers in these copies diverge outside simulator scope. | Use the common simulator decisions, remote tag and exact closeout evidence. |
| Source conflict register | v1.4 in the same archive. Local `reviews/governance-closeout-a09991a` indexes and hashes SC-002 through SC-004. | Exact imported reports and annotated-tag reread support closure. |
| Bootstrap acceptance record | Standalone named file unavailable. DEC-037, original PR, tag, post-merge verification and independent closeout identify the accepted commit. | Sufficient provenance for branching. |
| Bootstrap known limitations | v1.0 located in the local PACD project sources. | Local receipts, reusable identical-prestate authorization, shared verification code and host-dependent checks limit claims. |
| Phase 2 work order and architecture-to-code traceability | Originals unavailable in the reachable supplied materials at preflight. The November continuation quotes the increment sequence. Accepted architecture §§4 and 7 lists modules and typed objects. | Reconcile the candidate against the original rows or author-designated equivalents before signing off all of Increment 1. |
| Technical Report 001 experimental charter | Draft v0.1 located in PACD project sources. | Development only. DEC-006/008 retain the separate report and protocol gates. |
| Baseline fairness matrix | Draft v0.1 located in PACD project sources. | No baseline comparison under this increment. |
| Metric dictionary and data schema | Named draft unavailable. Checked-in metrics config, Arrow schemas and raw-to-derived implementation define the existing diagnostic counts. | No new research metric or mission-harm claim. |

The local reviewer packet carries exact command outcomes, independent-review disposition, diagnostic observations, dependency findings, and application wording. No research approval or project-register decision was created.

The author subsequently supplied the “Execute PACD bootstrap” chat. Its post-merge handoff identifies the same accepted commit and tag object, gives the seed-424242 semantic digests, and explicitly lists all Phase 2 development as unexecuted at that point. The last recorded action delivered the four Markdown governance closeout files. The private repository's live refs and merged PR corroborate this history.

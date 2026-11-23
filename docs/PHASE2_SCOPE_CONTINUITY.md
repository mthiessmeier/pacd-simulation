# PACD scope continuity: original Phase 2 and subsequent implementation

**Date:** 2026-11-21  
**Status:** Scope-preservation record and proposed sequencing; no new implementation or experimental acceptance  
**Owner:** Michael Thiessmeier  
**Reviewed repository baseline:** df33295469094a5ed9aa26fcc4b1fa1d019d3e5c  
**Accepted diagnostic implementation:** d5a29699e14409bfd54d30c51117c81077639ee6  
**Evidence classification:** NON_REPORTABLE_DIAGNOSTIC

## 1. Purpose and current instruction

Michael asked whether the proposed "Phase 3 — Closed-loop guarded agency and comparative evaluation" was already part of the broader original Phase 2 scope, and instructed that the original work items must not be lost.

**Yes: that decision-to-outcome loop was already required.** The proposal is a useful first integrated implementation slice. It is not a replacement for the original backlog. In particular, one polymorphic mechanism first does not replace six-class polymorphism, policy portfolios, multi-agent arbitration, the full comparator suite, or the wider evaluation program.

This record preserves the original scope and identifies a proposed sequence. The phase number remains a scheduling label. No original item is removed, waived, closed, or automatically deferred by renaming a phase or accepting a smaller demonstration.

## 2. Accepted milestone and original scope

[PR #8 acceptance](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861) explicitly accepts six bounded Phase 2 engineering increments and their synthetic reproducibility package at d5a29699e14409bfd54d30c51117c81077639ee6. [PR #10](https://github.com/mthiessmeier/pacd-simulation/pull/10) pins the evaluator README; its merge is the reviewed repository baseline above.

Preserve that acceptance. The original August work order has broader substantive implementation and completion criteria in sections 6 and 11. Those criteria require individual evidence or an explicit author disposition. Their completion cannot be inferred from the six increment names.

The [Increment 1 owner-equivalence decision](../status/PHASE2_INCREMENT1.md) is specifically for Increment 1. It is not a blanket waiver of the original requirements for subsequent increments.

The current root AGENTS.md, latest explicit author instructions, applicable decisions and accepted reviews continue to govern. The preserved August sources contain historical bootstrap starting instructions and status columns. Do not reset a newer accepted checkout to the bootstrap tag, repeat completed work, or treat an August "not implemented" status as a November finding.

## 3. Preserved sources and item inventory

The complete retrieved texts of five original documents are retained as UTF-8 text exports under [reference/phase2-original-2026-08-23](reference/phase2-original-2026-08-23/README.md). The reference index records original identity, date, version and export hashes. These are content-preserving text exports, not a claim of byte-identical archival originals.

| Alias | Original source | Role |
|---|---|---|
| WO | [Phase 2 Work Order v1.0](reference/phase2-original-2026-08-23/PACD_Simulator_Phase2_Work_Order_v1.0.md) | Original implementation scope, reviews, constraints and completion criteria |
| TM | [Architecture-to-Code Traceability v0.1](reference/phase2-original-2026-08-23/PACD_Simulator_Phase2_Architecture_to_Code_Traceability_v0.1.md) | Eleven layers, formal constructs, algorithms, evaluation and minimum acceptance evidence |
| EC | [Experimental Charter Draft v0.1](reference/phase2-original-2026-08-23/PACD_Technical_Report_001_Experimental_Charter_Draft_v0.1.md) | Research program, scenarios, conditions, outcomes and later freeze gate |
| FM | [Baseline Fairness Matrix v0.1](reference/phase2-original-2026-08-23/PACD_Baseline_Fairness_Matrix_v0.1.md) | Comparison conditions, equalization dimensions, ablations and fairness review |
| MD | [Metric Dictionary and Data Schema v0.1](reference/phase2-original-2026-08-23/PACD_Metric_Dictionary_and_Data_Schema_v0.1.md) | Named metric definitions and raw/derived/manifest contracts |

[The source-unit inventory](PHASE2_ORIGINAL_SCOPE_INVENTORY.csv) retains every non-heading body paragraph, list item and table row from those exports, including controls and source table headers. Table separator rows and blank lines are excluded. It deliberately retains overlaps and historical context. Its row count is a count of source units, not a claim about the number of unique requirements.

Each unit has a stable ID, source, original section and export line, original text, current reconciliation state, evidence field, remaining-acceptance field, proposed-increment field and scope disposition. All units begin PRESERVED_PENDING_RECONCILIATION: that status means item-level evidence mapping has not yet been completed. It does not invalidate accepted code or establish that a requirement is absent.

Keep source units immutable. Record subsequent evidence and disposition in the inventory. If an item is split, give children IDs and retain their parent. A title, module, schema, passing smoke fixture or favorable aggregate is insufficient to close a broader behavioral requirement.

## 4. Full workstream crosswalk

The table retains the complete workstream breadth. "Partial" describes the bounded reviewed baseline; "not fully reconciled" means no exhaustive requirement-level acceptance audit was performed in this documentation task. The original source remains the detailed requirement and acceptance reference.

Proposed delivery groups: A contracts and evaluation design; B environment, telemetry, adversary and beliefs; C guarded action loop; D full polymorphism, policy selection and orchestration; E full comparator suite and fair comparisons; F robustness, analysis and reproducibility. These groups are proposals, not execution approvals.

| ID | Workstream and original requirements to retain | Reviewed baseline and remaining acceptance | Sources | Proposed group |
|---|---|---|---|---|
| SC-01 | Domain/configuration models: immutable or versioned state, distinct identifiers, strict bounded scenario/topology/mission/adversary/defender/policy/metric/seed schemas, canonical hashes, evidence metadata, action preconditions/effects/cost/authority/reversibility/verification/rollback; schema catalog, implementation boundary and traceability or accepted equivalents. | Partial. Increment 1 accepted five governed inputs and typed records. Reconcile the broader families and every required field against accepted equivalents; retain parsing, property, negative and compatibility checks. | WO 5.1–5.3; TM 3–5 | A |
| SC-02 | Enterprise/mission environment: configurable 30–100 synthetic identities; normal/privileged/service/vendor identities; credentials, sessions, privileges, trust paths, endpoints, SaaS/cloud services, mission graphs and criticality; reset, degradation, recovery, collateral cost and immutable snapshots. | Partial. Directed dependencies and binary availability/continuity are accepted. Reconcile scale, entity semantics, time-dependent consequences, recovery and action-attributable cost. A binary continuity transition does not close duration or calibrated-harm requirements. | WO 6.1; TM layer 3 and 5; EC 4 | B |
| SC-03 | Synthetic identity, endpoint, SaaS, cloud-service, deception and mission telemetry; source/time/coverage/delay/noise/loss/integrity/degradation, detector reliability, provenance and deterministic generation. | Partial. Current live fixtures use a bounded sensor pathway. Establish configured multi-source behavior and boundary tests for degradation and provenance. Repeated readings from one source do not establish independent corroboration. | TM layer 1 and 6; EC 4,8 | B |
| SC-04 | Evidence fabric and beliefs: normalize/correlate, freshness, source reliability, contradiction, integrity and chain of custody; competing hypotheses, provenance-weighted updates, uncertainty representations and calibration. | Partial. An observation-only temporal review rule is accepted. Reconcile the richer evidence-to-belief behavior, stale/conflicting inputs and calibration rather than equating the rule with the full belief architecture. | WO 6.4; TM layers 2,4 and 5–6 | B |
| SC-05 | Bounded abstract adversary: reconnaissance, credential acquisition, session reuse, discovery, escalation, lateral movement, data/mission-resource access, persistence, adaptation and stealth/speed/mission/deception-sensitive variants. | Partial. Scripted fixtures exist. Carry forward state-machine coverage, impossible-transition denial, adaptive policies and controlled drift. All behavior remains synthetic; no real offensive commands, targets or integrations. | WO 6.2; TM layer 4 and 5; EC 5 | B |
| SC-06 | Expanded action ontology: sensing, deception, infrastructure/network, identity/access, response and coordination actions with explicit targets, preconditions, expected effects, costs, authority, reversibility, verification and rollback. | Partial. Narrow isolation and human-review pathways exist. Add/reconcile allowlisted simulated handlers and complete contracts for every selected class; reject unknown, prohibited and unauthorized non-reversible automatic actions. | WO 5.2,6.4; TM layer 5 and 5–6 | C,D |
| SC-07 | Substantive six-class polymorphism: typed candidate/operator portfolio, attacker-knowledge effects, mission cost, diversity, switching cost, detectability, reversibility and policy constraints. | Helpers exist; integrated polymorphism is identified as future work in the architecture. One integrated mechanism is a first milestone only. Preserve the remaining classes and coordinated behavior, admissibility, no-op and hostile-cost cases. | WO 6.4; TM layer 6 and 5–6; EC 6,10 | D |
| SC-08 | Policy portfolio and multi-objective selection: contextual mode selection and fallback; explicit security benefit, information gain, attacker cost, mission effects, operational burden, reversibility, uncertainty and safety terms. | Not fully reconciled; the accepted temporal threshold does not establish a substantive portfolio. Require inspectable component scores, parameter rationale, extreme-value tests and sensitivity to weights. | WO 6.4; TM 5–6 | D |
| SC-09 | Multi-agent orchestration: specialist proposal contracts, conflicts, precedence, sequencing, arbitration rationale, duplicate-action denial, role boundaries, order independence, deadlock handling and safe fallback. | A coordinator seam is not acceptance of integrated multi-agent behavior. Retain conflict matrices, ordering and fallback tests and the coordinated-versus-uncoordinated evaluation. | WO 6.4; TM layer 7 and 6 | D |
| SC-10 | Contextual governance: consequence, confidence, reversibility, mission criticality, evidence quality, policy coverage, authority envelope and portfolio bindings; independent reevaluation; autonomy tiers 0–5; evidence levels 0–5 distinct from confidence. | The independent governor and narrow authorization boundaries are accepted. Reconcile contextual tier transitions, evidence gates, catastrophic/prohibited-action denial and policy-service failures. No tier may bypass hard prohibitions. | TM layer 8 and 5–6; MD 5 | C,D |
| SC-11 | Human oversight and mission command: queues, latency, timeouts, approval/denial/modification/override, complete rationale and uncertainty/impact packages, mission intent, command envelopes, escalation and accountability. | Partial. Prospective policies stop at referral; an approval helper is not an integrated review lifecycle. Require terminal outcomes, missing/late-approval denial, override audit and simulated burden measurements. Human-subject trust remains separately deferred. | TM layer 9 and 5–6; EC 4; MD GOV/OPS | C |
| SC-12 | Execution/verification/recovery: multiple simulated handlers, decision/action/target/pre-state binding, one-shot stateful authorization, independent expected-state reconstruction, collateral checks, partial failure, rollback reliability and safe degradation. | Partial. The in-memory broker and exact-state checks support the narrow diagnostic. Reconcile per-handler effects, replay protection, rollback attempts/success/failure and uncertain outcomes. | WO 6.1,6.4; TM layer 10 and 5–6 | C |
| SC-13 | Full condition suite: static, deterministic SOAR-style automation, delayed human response, random polymorphism, single-layer adaptive, full PACD, oracle reference and internal unbounded simulated diagnostic. | Partial. A static review rule and a corroborated review rule are integrated. They do not close the entire suite. Oracle and unbounded references remain explicitly non-deployable and within the simulator boundary. | WO 6.3; EC 6; FM 2 | E |
| SC-14 | Both authentic system-level and equalized controlled comparisons; all 16 fairness dimensions, declared intrinsic asymmetries, comparable tuning, resources, failures, missingness, oversight and rollback semantics. | Shared observations/governor support a narrow contrast. Reconcile every comparison cell and the full fairness matrix. Keep oracle privileges explicit and prohibit deliberately weakened straw comparators. | WO 11; EC 7; FM 1–4,6 | A,E |
| SC-15 | Independent harness, event scheduler and protocol/config controls: lifecycle/reset, scenario/defender selection, faults, bounded queues, termination/timeout, deterministic ordering, multi-actor events and finalization; no defender modification of evaluation controls. | Partial. Deterministic runs and registered-attempt accounting exist. Reconcile generalized episodes, faults and planned-cell bindings. Preserve the reportable interlock and local receipt assurance limits. | TM 1,4; WO 7–9 | A,B,E |
| SC-16 | All named scenario families, mandatory negative controls, hostile regimes and control-plane challenges: telemetry/evidence/policy/mission corruption, unreliable rollback, strong static controls, low attacker adaptability, rapid humans and high variation cost. | Partial. Identity, maintenance and repeated-reading fixtures exist. Retain all EC 8 and 11 cases individually; assess plausible adverse and no-benefit behavior without selecting a favorable PACD outcome. | WO 6.2,6.5,11; EC 8,11; TM 7 | B,F |
| SC-17 | Full metric/data scope: security, mission, polymorphism, safety, governance, uncertainty/calibration, generalization and operational burden; all 47 metric IDs, event/episode/run contracts, raw derivation, explicit denominators, distributions/tails and failure visibility. | Partial. Verified dispositions, registered completions and regeneration are accepted. Retain all MD definitions and reconcile numerator, denominator, unit, eligibility, timing/censoring, missingness, source and uncertainty before claiming a metric is implemented. | WO 6.5; TM layer 11 and 7; EC 10–11; MD 1–12 | A,F |
| SC-18 | Calibration, ten proposed ablations, sensitivity/analysis tooling, unseen topology and drift, all seed classes, manifests, one-command tables/figures, independent exact-commit reconstruction, limitations, review records and draft-protocol readiness. | Partial. Replay/regeneration and reviewed diagnostic evidence are accepted. Reconcile the broader controls, all named ablations and original WO 11 completion criteria. Analysis choices remain draft until an approved freeze. | WO 4,7–13; TM 7–10; EC 9,12–16; FM 5–7; MD 10–12 | A,F |

## 5. Specific inventories that remain in scope

### 5.1 Eight defender/reference conditions

Static defense; deterministic SOAR-style automation; delayed human-centered response; random polymorphism; single-layer adaptive defense; full PACD; oracle upper bound; internal unbounded agentic diagnostic with simulated tools only. Their exact source definitions remain in FM section 2 and EC section 6. The oracle and unbounded conditions are reference conditions, not ordinary deployable recommendations.

### 5.2 Ten proposed ablations

The FM section 5 inventory remains: without mission model; without uncertainty input; without reversibility input; without multi-agent orchestration; one polymorphism class; without policy portfolio; without human-oversight delay; degraded safety-governor service; inaccurate dependency map; unreliable rollback.

These are retained draft ablations. They are not frozen comparisons. An ablation must not remove host isolation, the simulation-only broker boundary, audit integrity or the reportability interlock. A simulated safety-policy variation requires an explicit design and applicable authorization.

### 5.3 Sixteen fairness dimensions

Preserve scenario allocation, telemetry, state knowledge, mission knowledge, action catalog, safety rules, oversight, compute budget, retry/timeout, rollback, randomness, failure handling, metrics, tuning, negative controls and missing data. FM section 3 retains the exact required controls and evidence.

### 5.4 Forty-seven named metrics

The original IDs remain individually present in MD and the source-unit inventory:

| Family | IDs | Count |
|---|---|---:|
| Security | SEC-001–SEC-007 | 7 |
| Mission | MIS-001–MIS-006 | 6 |
| Polymorphism | POL-001–POL-007 | 7 |
| Safety | SAF-001–SAF-006 | 6 |
| Governance | GOV-001–GOV-005 | 5 |
| Calibration | CAL-001–CAL-006 | 6 |
| Generalization | GEN-001–GEN-005 | 5 |
| Operational burden | OPS-001–OPS-005 | 5 |

A proposed formula is not a validated measure or a frozen primary outcome. Do not automatically add inferential statistics to deterministic development repetitions. Define an appropriate sampling unit and assumptions before reporting uncertainty estimates.

### 5.5 Mandatory negative-control and hard-failure cases

EC section 11 individually preserves benign administration, prohibited candidates, non-reversible automatic actions, corrupted mission data, policy-service failure, failed rollback, telemetry outage/degradation, duplicate or stale authorization, out-of-distribution topology and attempted external actions denied by the simulation boundary. Preserve all sixteen scenario families in EC section 8 as well.

### 5.6 Scope and evidence boundaries

H6 human trust/performance requires human participants and remains outside simulation-only testing. Retain interface data and simulated latency without claiming human-study evidence. H1–H5 remain unclassified during development. RQ4 and empirical/operational conclusions require the separately approved evaluation program.

No reportable seeds, primary outcomes, exclusions, statistical methods, frozen thresholds or empirical approval are established by preserving these drafts. Real targets, production integrations, external-action capability, public release and manuscript modification remain outside this task.

## 6. Relationship to the earlier Phase 3 proposal

| Earlier proposed step | Relationship to original scope | Carry-forward safeguard |
|---|---|---|
| Fair comparison and planned attempt accounting | WO 6.3/11, TM 4/7, FM and MD | Complete both comparison modes and the full fairness suite. A deduplicating static rule or stronger cell binding is a proposed refinement, not a replacement requirement. |
| Guarded review-to-action-to-mission loop | WO 6.1/6.4, TM layers 2–11 and algorithms | First integrated slice. Include belief, authority, oversight, state consequences and verification; retain the broader environment and action requirements. |
| One integrated polymorphic mechanism | Initial milestone within WO 6.4 and TM layers 5–7 | Preserve six-class coverage, portfolio selection, coordinated behavior and the full action/metric contracts. |
| Robustness and protocol preparation | WO 6.5/11, EC 8–16, FM 5–7, MD | Preserve every named scenario, ablation and metric; protocol readiness and reportable authorization are distinct gates. |

## 7. Closure and change rules

1. Keep the accepted bounded Phase 2 diagnostic milestone recorded separately from completion of the original broader program.
2. Reconcile each inventory unit against exact implementation, tests, acceptance records and limitations. Cite the approved commit and reviewer outcome before marking a behavioral requirement accepted complete.
3. Accepted equivalents must name their author decision and the scope it covers. An equivalence for one increment does not waive unrelated items.
4. An unimplemented item stays open even when it is not on the next increment's critical path. Proposed delivery groups can change without deleting scope.
5. Removal, narrowing or deferral requires an explicit author disposition that identifies the affected unit IDs and reason. This document records no such removal.
6. Preserve original draft status. A draft metric, ablation or hypothesis does not become an approved protocol through copying or scheduling.
7. Every implementation PR should list affected unit/workstream IDs, changed behavior, observed tests, independent review, remaining work and the current evidence classification.
8. Each session handoff should carry the open IDs, next authorized increment, current branch/HEAD, accepted baseline, PR status, evidence paths and unresolved source decisions. PR #9 supplies the separately proposed AGENTS.md handoff policy; this record does not merge it.
9. The next work order must allocate the entire remaining original scope, including later increments. Its first slice may be small; its completion definition must preserve the full carry-forward requirements.
10. Preserve host protection, the simulated-only execution boundary, evidence retention, independent review and reportable-mode interlocks throughout.

## 8. Next concrete documentation task

Reconcile the inventory to the current accepted source at requirement level, using SC-01–SC-18 to organize the review. Attach an implementation plan that assigns all remaining IDs to bounded increments and identifies exact completion evidence. Keep the phase name provisional until that complete plan is adopted.

This preservation PR does not rerun simulator tests, claim independent implementation acceptance, authorize reportable execution, or merge itself. Source-copy integrity and inventory completeness are the relevant documentation checks.


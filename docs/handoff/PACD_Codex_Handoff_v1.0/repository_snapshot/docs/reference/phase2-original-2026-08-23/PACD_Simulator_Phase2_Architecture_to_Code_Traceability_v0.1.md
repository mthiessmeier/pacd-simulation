# PACD Simulator Phase 2 Architecture-to-Code Traceability Matrix

**Document ID:** PACD-SIM-TRACE-002  
**Version:** 0.1  
**Status:** Working control; not a frozen specification  
**Date:** 2026-08-23  
**Governing baseline:** `pacd-bootstrap-v1.0` / merge commit `a09991a3a6ed6ff3889138a787c61c8c545c1cd0`  
**Governing decision:** PACD-DEC-038  
**Evidence class:** Non-reportable development; existing accepted evidence remains Level 1

## 1. Purpose

This matrix maps the monograph's formal, architectural, algorithmic, governance, and evaluation constructs to the accepted code scaffold and the work required for Phase 2. It distinguishes implemented bootstrap plumbing from substantive PACD capability.

The evaluation harness remains outside the eleven-layer system under test. It controls configuration, reset, scheduling, faults, termination, artifact finalization, and replay. Defenders may not modify the harness, metrics, seed registry, policy, or protocol during a run.

## 2. Status Vocabulary

| Status | Meaning |
|---|---|
| Accepted scaffold | Independently accepted at Level 1 for the stated plumbing or boundary. |
| Partial diagnostic | Executable only as a narrow diagnostic; not substantive PACD capability. |
| Interface only | Module or schema seam exists without sufficient behavior. |
| Not implemented | Required Phase 2 behavior is absent. |
| Deferred | Intentionally outside Phase 2 or requires a later author decision. |
| Draft control | Proposed requirement that is not frozen for reportable work. |

## 3. Eleven-Layer Architecture Traceability

| Layer | Monograph responsibility | Current module(s) | Current evidence/status | Phase 2 implementation requirement | Minimum acceptance evidence |
|---|---|---|---|---|---|
| 1. Telemetry and sensor ingestion | Observations with source, time, coverage, delay, integrity, and degradation | `pacd_sim.telemetry` | Partial diagnostic synthetic generator | Add identity, endpoint, SaaS, cloud-service, deception, and mission telemetry; noise, delay, loss, sensor coverage, detector reliability, and provenance | Unit and property tests for deterministic generation, bounds, delay/loss, provenance, and same-seed replay |
| 2. Normalization and evidence fabric | Normalize, correlate, retain provenance, avoid premature certainty | `pacd_sim.evidence` | Partial diagnostic normalization | Add typed evidence records, corroboration, freshness, source reliability, contradiction, integrity, and chain-of-custody fields | Duplicate/conflicting evidence tests, nonfinite/oversized input denial, provenance preservation, evidence-to-belief trace |
| 3. Enterprise state and mission model | Dynamic identities, sessions, credentials, assets, services, dependencies, mission criticality, governance context | `pacd_sim.environment`, `pacd_sim.state` | Minimal synthetic graph; accepted immutability and exact-state verification | Implement 30–100-identity synthetic enterprise; sessions, credentials, privileges, trust paths, endpoints, SaaS/cloud services, mission functions, dependencies, continuity, degradation, recovery, and collateral cost | Schema tests, graph invariants, reset determinism, mission-dependency propagation, rollback and immutable snapshot tests |
| 4. Adversary modeling and threat hypotheses | Synthetic red behavior plus defender-side competing hypotheses | `pacd_sim.agents.red`, `pacd_sim.hypotheses` | Fixed red fixture; toy belief update | Implement bounded attack state machine: reconnaissance, credential acquisition, session reuse, discovery, escalation, lateral movement, data access, persistence; add competing hypotheses and uncertainty updates | State-machine coverage, impossible-transition denial, policy variants, drift scenarios, belief calibration records |
| 5. Defensive knowledge and action ontology | Typed actions, preconditions, effects, mission cost, reversibility, authority, verification, rollback | `pacd_sim.actions`, `pacd_sim.schema` | Narrow `isolate_session` diagnostic; strong binding checks | Expand simulated action classes for sensing, deception, infrastructure/network, identity/access, response, and coordination; explicit preconditions, targets, expected effects, cost, authority, reversibility, rollback | Exact schema and precondition tests; prohibited/unknown/non-reversible denial; target, effect, rollback, and collateral-state verification |
| 6. Polymorphism management | Generate and score six classes of governed variation | `pacd_sim.polymorphism` | Interface/helpers only; not integrated | Implement candidate portfolio, operator metadata, attacker-knowledge effect, mission cost, diversity, switching cost, detectability, reversibility, and policy constraints | Unit/property tests; no-op and hostile-cost regimes; operator admissibility; deterministic candidate generation |
| 7. Multi-agent orchestration | Reconcile specialized proposals, sequence actions, resolve conflict, preserve role boundaries | `pacd_sim.orchestration` | Unused coordinator seam | Implement typed specialist proposals, conflict detection, precedence, sequencing, arbitration rationale, duplicate action denial, and safe fallback | Proposal-contract tests, conflict matrices, order-independence tests, deadlock/fallback tests, audit completeness |
| 8. Safety, policy, and governance | Hard admissibility, prohibited actions, contextual autonomy, policy versioning, fail-closed behavior | `pacd_sim.governance` | Accepted safety/authorization scaffold; mission and uncertainty reasoning not substantive | Add consequence, confidence, reversibility, mission criticality, evidence quality, policy coverage, authority envelope, autonomy tier, and policy-portfolio bindings; preserve independent reevaluation | Authorization mutation matrix, policy/context/state binding, autonomy-tier transitions, catastrophic-action denial, policy-service failure tests |
| 9. Human oversight and mission command | Approval delay, decision packages, approve/deny/modify/override, accountability | `pacd_sim.oversight` | Simulated placeholder | Implement simulated approval queues, latency, timeout, override, rationale package, uncertainty/impact preview, and escalation outcomes | Queue/latency tests, missing/late approval denial, override audit, operator burden metrics; no H6 claim |
| 10. Controlled execution and integration | Scoped simulated state transitions only | `pacd_sim.execution` | Accepted simulated broker and exact-state verification; one action | Add simulated action handlers only; pre-state binding, one-shot authorization nonce for stateful actions, rollback outcome, partial failure, and safe degradation | One-shot/replay tests, handler allowlist, no external capability scan, complete-state verification, rollback success/failure, transaction tests |
| 11. Learning, evaluation, and audit | Raw records, verification, calibration, metrics, analysis, reproducibility | `pacd_sim.audit`, `pacd_sim.metrics`, `pacd_sim.analysis`, `pacd_sim.reproducibility` | Accepted diagnostic evidence plumbing; metrics minimal | Add episode/run/action schemas, calibration records, mission/security/safety/governance metrics, raw-to-derived regeneration, ablations, sensitivity tooling, failure visibility | One-command regeneration, exact schemas, metric-from-raw tests, negative controls, tail metrics, no hidden prohibited action, reproducibility manifest |

## 4. Independent Harness and Configuration Control

| Construct | Current module | Current status | Phase 2 requirement |
|---|---|---|---|
| Evaluation harness | `pacd_sim.harness` | Accepted scaffold outside system under test | Generalize defender selection, scenario families, episode lifecycle, fault injection, controlled comparison modes, and artifact finalization without allowing defender mutation |
| Discrete-event scheduling | `pacd_sim.engine` | Deterministic diagnostic | Support bounded event/action queues, episode termination, timeout, reproducible ordering, and multi-actor events |
| Configuration control | `configs/`, strict loaders | Accepted strict diagnostic configs | Versioned scenario/topology/mission/adversary/defender/policy/metric/seed schemas; draft/frozen separation; exact hashes |
| Reportable interlock | `configs/protocol/frozen/`, `pacd_sim.reproducibility.reportable` | Accepted fail-closed; no approval | Preserve denial. Phase 2 may not create `APPROVAL.json` or weaken any binding. |
| Raw evidence and receipts | workspace `var/`, reproducibility modules | Accepted Level 1 local cooperative binding | Retain every development run as non-reportable; keep local assurance scope explicit; no WORM/signing claim |

## 5. Formal-Construct Traceability

| Monograph construct | Code representation | Current status | Phase 2 action |
|---|---|---|---|
| Partially observable state | Environment snapshots, telemetry, evidence, hypotheses | Partial diagnostic | Define explicit state, observation, belief, and transition schemas; preserve uncertainty |
| Belief state | `pacd_sim.hypotheses` | Toy probability update | Add competing hypotheses, provenance-weighted evidence, calibration, contradiction, and confidence intervals/distributions |
| Mission model | Environment/state snapshots | Structural only | Add mission functions, dependencies, criticality, availability, degradation, recovery, and mission-cost propagation |
| Adversary model | `agents.red` and scenario events | Fixed fixture | Implement bounded adaptive policies and controlled drift without real offensive capability |
| Action ontology | Actions/schema | One supported action | Expand six polymorphism classes and defensive action metadata |
| Admissible policy set | Governance policy | Narrow allow/prohibit logic | Add contextual authority, autonomy tiers 0–5, prohibited sets, escalation, policy portfolios, and fail-closed fallback |
| Multi-objective utility | Diagnostic heuristic | Not substantive | Define security benefit, information gain, attacker cost, mission effect, operational burden, reversibility, uncertainty, and safety terms as draft metrics |
| Reversibility and rollback | Action flags and execution verification | Accepted narrow scaffold | Add action-specific rollback models, partial failure, rollback reliability, and tail outcomes |
| Guarded agency | Harness/governor/execution separation | Structurally accepted | Preserve reason/propose broadly and execute only inside explicit authority; add decision packages and evidence thresholds |
| Mission command | Oversight/governance | Placeholder | Implement human-defined mission, command envelope, intent, boundaries, escalation, and accountability as simulated controls |
| Evidence levels 0–5 | Governance/evidence metadata | Not implemented | Add evidence-level field and gates; do not equate evidence level with confidence |
| Autonomy tiers 0–5 | Governance | Not substantive | Implement contextual tier selection and transitions; no tier may bypass prohibited actions |

## 6. Algorithmic-Function Traceability

| Function | Current status | Phase 2 implementation requirement | Required tests |
|---|---|---|---|
| Observe and normalize | Partial | Multi-source synthetic telemetry and bounded normalization | Determinism, delay/loss, malformed source, provenance |
| Update beliefs | Toy | Competing hypotheses, source reliability, freshness, contradiction, calibration | Monotonicity where appropriate, contradictory evidence, calibration |
| Generate candidate actions | Minimal | Typed portfolio across six classes | Completeness for scenario, preconditions, duplicates, bounds |
| Select policy mode | Not substantive | Policy portfolio with contextual mode and safe fallback | Mode-switching, failure, hostile mission data |
| Score candidates | Minimal | Multi-objective draft utility with explicit components and no hidden weights | Component isolation, extreme values, sensitivity, no magic defaults |
| Arbitrate agents | Not implemented | Proposal conflict resolution and sequence plan | Conflict matrix, deadlock, ordering, role boundary |
| Apply safety governor | Accepted scaffold | Contextual consequence/authority/autonomy rules | Full mutation matrix, prohibited actions, degraded policy service |
| Route oversight | Placeholder | Approval queues, delays, timeouts, overrides | Missing/late approval, override, burden |
| Execute simulated action | Narrow accepted | Multiple simulated handlers, one-shot permit, partial failure | Replay, rollback, exact state, no external path |
| Verify and recover | Narrow accepted | Handler-specific expected-state reconstruction and safe degradation | Collateral mutation, failed rollback, uncertain outcome |
| Audit and measure | Accepted plumbing | Complete event/action/mission/calibration schemas and metric regeneration | Raw-to-derived equality, tail visibility, negative controls |

## 7. Chapter 6 Evaluation Traceability

| Evaluation requirement | Current status | Phase 2 deliverable | Reportable gate |
|---|---|---|---|
| Security effectiveness | Not established | Draft metrics and synthetic objective states | Frozen baseline/scenario protocol and reportable runs |
| Mission resilience | Not established | Mission model and continuity/degradation metrics | Independent review of mission assumptions |
| Polymorphism quality | Not established | Diversity, switching cost, attacker-knowledge, mission-cost metrics | Sensitivity and ablation |
| Safety | Level 1 boundary tests only | Expanded benign/prohibited/catastrophic-tail tests | Sector consequence model and frozen exclusions |
| Governance | Level 1 authorization tests | Autonomy, escalation, approval, override, policy-failure metrics | Author-approved governance protocol |
| Uncertainty calibration | Not established | Brier/calibration/error metrics on development episodes | Frozen estimator and evaluation regime |
| Operational burden | Not established | Action count, churn, user friction, approval burden, compute cost | Fair baseline accounting |
| Generalization | Not established | Unseen topology, telemetry degradation, policy drift scenarios | Held-out frozen scenario families |
| Human performance and trust | Deferred | Interface data fields and simulated latency only | Separate human-subject protocol; H6 not simulation-testable |
| Control-plane security | Level 1 bootstrap controls | Phase 2 attack surfaces, policy/mission/evidence corruption scenarios | Independent red-team/challenge review |

## 8. Research Question and Hypothesis Mapping

| Item | Phase 2 role | Evidence boundary |
|---|---|---|
| RQ1 | Preserve canonical taxonomy and implement representable six-class action schemas | Conceptual/implementation coherence only |
| RQ2 | Implement and trace the eleven-layer architecture | Architecture traceability and component behavior only |
| RQ3 | Build candidate generation, constrained selection, policy portfolios, uncertainty and mission inputs | Development and ablation mechanics; no comparative conclusion |
| RQ4 | Prepare fair baseline and coordinated-polymorphism capability | Remains open until reportable controlled comparison |
| RQ5 | Implement metric, robustness, safety, drift, and generalization machinery | Methodological and development evidence only |
| RQ6 | Implement safety-governor, autonomy, oversight, and audit behaviors | Proposed governance architecture; operational validity remains open |
| H1–H4 | Design implementations and tests | No support/rejection during Phase 2 development |
| H5 | Build alternative evaluation regimes and hostile scenarios | No hypothesis result before frozen reportable comparison |
| H6 | Data/interface preparation only | Requires human participants; deferred |

## 9. Phase 2 Increment Map

| Increment | Branch | Primary traceability rows | Merge condition |
|---|---|---|---|
| 1. Models and schemas | `codex/phase2-model-and-schemas-v1` | Layers 1–5, formal state/action/evidence/mission contracts | Independent review of schemas, invariants, strict parsing, and no behavioral claims |
| 2. Core environment | `codex/phase2-core-environment-v1` | Layer 3, harness, engine | Deterministic reset, mission graph, propagation, tests, non-reportable diagnostic |
| 3. Red agent and scenarios | `codex/phase2-red-agent-and-scenarios-v1` | Layer 4, telemetry | Bounded state machine, drift, negative controls, no real actions |
| 4. Baselines | `codex/phase2-baselines-v1` | Defender interface, fairness matrix | Authentic and equalized modes, resource accounting, fairness review |
| 5. PACD defender | `codex/phase2-pacd-defender-v1` | Layers 5–10 | Candidate, policy, orchestration, governance, oversight, execution tests |
| 6. Metrics and reproducibility | `codex/phase2-metrics-and-reproducibility-v1` | Layer 11, Chapter 6 | Raw-to-derived regeneration, sensitivity tooling, draft protocol readiness |

## 10. Traceability Rule

Every Phase 2 pull request must update this matrix on a new version. A status may advance only when the exact module, tests, commit, validation record, and known limitations are identified. No row may advance directly from “not implemented” to “empirically supported” during Phase 2.

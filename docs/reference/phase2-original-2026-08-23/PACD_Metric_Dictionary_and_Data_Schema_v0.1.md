# PACD Metric Dictionary and Data Schema

**Document ID:** PACD-SIM-METRICS-001  
**Version:** 0.1  
**Status:** Draft methodological and data-contract control; not frozen  
**Date:** 2026-08-23  
**Evidence status:** Author-proposed definitions for Phase 2 implementation

## 1. Metric Rules

- Every metric must be generated from retained raw records.
- No metric may hide prohibited, catastrophic, rollback, or invalid-episode outcomes.
- Rates require explicit denominators.
- Means must be accompanied by distribution and tail information where consequences are asymmetric.
- Metrics must be computed identically across defender conditions.
- Units, direction, aggregation, missing-data handling, and exclusions must be explicit.
- No metric in this draft is a primary outcome until protocol freeze.

## 2. Security Metrics

| ID | Name | Proposed definition | Direction | Raw sources | Required companion reporting |
|---|---|---|---|---|---|
| SEC-001 | Attacker objective completion rate | Episodes with defined terminal attacker objective achieved / eligible episodes | Lower is better | attacker state, episode status | Count, denominator, scenario family, confidence interval |
| SEC-002 | Attack progression depth | Maximum ordered attack-stage index reached per episode | Lower is better | red-agent transitions | Distribution and stage-specific rates |
| SEC-003 | Time to objective | Simulated time from first adversary event to objective completion | Higher is better for defender; censored when incomplete | event timestamps | Completion rate and censoring policy |
| SEC-004 | Time to detection | First retained adversary event to first qualifying defensive belief/detection | Lower is better | observation, evidence, hypothesis | Missed-detection count |
| SEC-005 | Time to containment | First qualifying detection to verified containment state | Lower is better | safety, execution, verification | Failure and rollback counts |
| SEC-006 | Compromised-entity exposure | Integral or sum of compromised identities/sessions/assets over simulated time | Lower is better | state snapshots | Peak and tail values |
| SEC-007 | Attack-path disruption | Fraction of feasible attack paths removed or made nonviable by verified defense | Higher is better | graph snapshots | Initial/final path counts and model assumptions |

## 3. Mission Resilience Metrics

| ID | Name | Proposed definition | Direction | Raw sources | Caveat |
|---|---|---|---|---|---|
| MIS-001 | Mission availability | Time-weighted availability of defined mission functions | Higher is better | mission state | Dependency model quality governs validity |
| MIS-002 | Mission loss integral | Integral of weighted mission degradation below nominal state | Lower is better | mission snapshots | Weights must be frozen and sensitivity-tested |
| MIS-003 | Critical-function outage time | Simulated time a critical mission function is below threshold | Lower is better | mission state | Threshold not yet frozen |
| MIS-004 | Recovery time | Time from minimum mission state or containment to restored threshold | Lower is better | mission state, recovery events | Distinguish defense-caused and attack-caused recovery |
| MIS-005 | Defensive collateral mission cost | Weighted mission degradation attributable to defensive actions | Lower is better | action, execution, mission delta | Attribution model requires explicit assumptions |
| MIS-006 | User/service friction | Weighted interruption, reauthentication, isolation, or access-denial burden | Lower is better | action and service events | Not a substitute for human-subject burden |

## 4. Polymorphism Metrics

| ID | Name | Proposed definition | Direction | Raw sources | Caveat |
|---|---|---|---|---|---|
| POL-001 | Polymorphism class coverage | Number/share of six classes used in an episode or run | Descriptive | action records | Higher is not automatically better |
| POL-002 | Action diversity | Diversity index over verified polymorphic actions | Context-dependent | action records | Must not reward unnecessary churn |
| POL-003 | Switching frequency | Policy/operator changes per unit simulated time | Context-dependent | policy/action audit | Report mission and operational cost |
| POL-004 | Switching cost | Sum of explicit operational/mission costs from variation | Lower for equal benefit | action cost records | Cost model not frozen |
| POL-005 | Attacker knowledge reliability | Modeled accuracy of attacker beliefs about current defensive state | Lower is better | red-agent knowledge state | Model-dependent proxy |
| POL-006 | Attacker knowledge decay | Change in attacker-state reliability after defensive variation | More decay may be beneficial | red-agent state, action events | Must pair with mission cost |
| POL-007 | Coordination gain | Difference between coordinated and matched uncoordinated variants under controlled conditions | Higher is better | paired episodes | Reportable only after fair-baseline freeze |

## 5. Safety and Governance Metrics

| ID | Name | Proposed definition | Required direction | Raw sources | Hard rule |
|---|---|---|---|---|---|
| SAF-001 | Prohibited action execution count | Verified executions whose governing disposition is prohibited | Exactly zero | decision/execution/audit | Never average away |
| SAF-002 | Escalated action execution count without approval | Executed escalated actions lacking valid approval | Exactly zero | oversight/execution | Never average away |
| SAF-003 | Catastrophic safety violation rate | Episodes meeting a frozen catastrophic consequence predicate | Zero target; report tail | state/mission/audit | Predicate must be frozen |
| SAF-004 | Non-reversible automatic action count | Automatic executions of actions marked non-reversible | Exactly zero unless separately authorized | action/execution | Phase 2 should deny |
| SAF-005 | Rollback failure rate | Failed rollback attempts / rollback attempts | Lower is better | execution/verification | Include no-attempt and partial failure |
| SAF-006 | Collateral-state verification failure | Executions rejected because after-state differs from exact allowed transformation | Lower is better; count all | verification | Diagnostic failures remain visible |
| GOV-001 | Policy compliance rate | Decisions and executions satisfying exact current policy bindings / eligible events | Higher is better | policy, decision, execution | Missing policy is fail-closed |
| GOV-002 | Escalation routing completeness | Escalations with complete decision package and terminal outcome / escalations | Higher is better | oversight/audit | Timeout outcome must remain visible |
| GOV-003 | Override rate and outcome | Human/simulated overrides, direction, rationale, and downstream outcome | Descriptive | oversight/audit | Not a trust metric |
| GOV-004 | Autonomy-tier distribution | Time/events spent in tiers 0–5 by context | Descriptive | governance state | Tier is contextual, not maturity |
| GOV-005 | Authority-envelope violation attempts | Candidate actions outside delegated class/target/context | Descriptive; executed count zero | candidate/decision/audit | Distinguish attempted and executed |

## 6. Uncertainty and Calibration Metrics

| ID | Name | Proposed definition | Direction | Raw sources | Caveat |
|---|---|---|---|---|---|
| CAL-001 | Brier score | Mean squared error between probability estimate and defined binary outcome | Lower is better | hypotheses, ground-truth state | Outcome and timing must be fixed |
| CAL-002 | Calibration error | Weighted gap between predicted probability bins and observed frequency | Lower is better | hypotheses, outcomes | Bin policy not frozen |
| CAL-003 | Log loss | Negative log probability assigned to realized state/outcome | Lower is better | hypotheses, outcomes | Clip policy must be frozen |
| CAL-004 | Confidence-coverage curve | Performance/abstention across confidence thresholds | Descriptive | hypotheses, decisions | Avoid selecting threshold after reportable outcomes |
| CAL-005 | Evidence contradiction rate | Episodes/events with materially conflicting evidence sources | Descriptive | evidence records | Requires contradiction definition |
| CAL-006 | Stale-evidence action rate | Candidate or executed actions relying on evidence beyond freshness policy | Executed count target zero | evidence, decision | Freshness policy versioned |

## 7. Generalization, Robustness, and Burden Metrics

| ID | Name | Proposed definition | Direction |
|---|---|---|---|
| GEN-001 | Unseen-topology performance delta | Metric difference between development topology and held-out topology families | Smaller degradation is better |
| GEN-002 | Adversarial-drift performance delta | Difference under changed attacker policy/distribution | Smaller degradation is better |
| GEN-003 | Telemetry-degradation curve | Outcome as delay, loss, noise, or corruption increases | Descriptive robustness curve |
| GEN-004 | Mission-model error sensitivity | Outcome across dependency/criticality error levels | Descriptive |
| GEN-005 | Policy-service failure safety | Safe-denial/degradation behavior under policy unavailability | Fail-closed required |
| OPS-001 | Defensive action count | Verified defensive actions per episode | Context-dependent |
| OPS-002 | Proposal and arbitration burden | Candidate/proposal/conflict counts and processing time | Lower for equivalent outcomes |
| OPS-003 | Approval burden | Approval requests, wait time, timeout, and override count | Lower for equivalent safety/outcomes |
| OPS-004 | Compute time | CPU time per episode and decision | Lower is better for equivalent capability |
| OPS-005 | Peak memory | Maximum process memory during episode/run | Lower is better within bounds |

## 8. Core Raw Event Schema

Proposed common fields for every raw event:

| Field | Type | Requirement |
|---|---|---|
| `schema_version` | string | Exact controlled schema |
| `evidence_label` | string | `NON_REPORTABLE_DIAGNOSTIC` during Phase 2 unless later changed by decision |
| `run_id` | string | Bound to local receipt/manifest |
| `episode_id` | string | Unique within run |
| `sequence` | integer | Contiguous within event stream |
| `tick` | finite number | Nonnegative, nondecreasing within stream |
| `seed` | integer | Registered development seed |
| `scenario_id` | string | Versioned scenario |
| `condition_id` | string | Versioned defender condition |
| `event_type` | controlled string | Exact event ontology |
| `entity_id` | string or empty | Subject/target entity |
| `action_id` | string or empty | Required for action-chain events |
| `policy_version` | string or empty | Required for governed actions |
| `configuration_hash` | SHA-256 | Exact canonical configuration |
| `payload_json` | canonical JSON string | Duplicate-free, depth/size bounded |
| `source_module` | controlled string | Emitting component |
| `created_at` | timestamp | Wall-clock provenance; excluded from semantic hash where appropriate |

## 9. Episode Summary Schema

Proposed fields:

- run and episode identifiers;
- scenario and condition;
- seed;
- completion status;
- attacker objective and progression;
- mission availability/loss/recovery;
- approved, escalated, denied, and prohibited actions;
- simulated executions and verified outcomes;
- rollback attempts/failures;
- benign negative-control status;
- safety and catastrophic flags;
- calibration aggregates;
- operational burden;
- raw semantic hash;
- summary semantic hash;
- configuration and code identity.

Every summary must regenerate solely from raw event records. Summary files are derivatives, not authoritative raw evidence.

## 10. Run Manifest Additions for Phase 2

Proposed additions:

- experimental-charter version and status;
- scenario/topology/mission/adversary registries and hashes;
- defender/baseline definitions and hashes;
- fairness mode;
- metric dictionary version/hash;
- development/calibration/holdout seed-class label;
- Python and dependency lock identity;
- code commit and dirty state;
- test/validation status;
- artifact allowlist and hashes;
- limitations applicable to the run;
- reportable flag fixed false.

## 11. Missing and Invalid Data

Draft rule:

- invalid episodes remain retained and counted;
- corrupted or incomplete records are not silently excluded;
- exclusion reason and stage are explicit;
- denominators include/exclude only according to a frozen rule;
- catastrophic, prohibited, and rollback failures remain separate counts even if the episode is otherwise invalid;
- development runs may be rerun for debugging, but the original failed evidence is retained.

## 12. Current Disposition

This dictionary is an implementation draft. Metric IDs and data contracts may be implemented and tested in Phase 2, but no metric is primary, no threshold is frozen, and no value supports a research finding until a later approved reportable protocol.

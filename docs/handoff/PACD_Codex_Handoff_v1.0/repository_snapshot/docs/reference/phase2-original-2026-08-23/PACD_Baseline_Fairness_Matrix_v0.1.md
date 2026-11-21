# PACD Baseline Fairness Matrix

**Document ID:** PACD-SIM-FAIRNESS-001  
**Version:** 0.1  
**Status:** Draft methodological control; not approved or frozen  
**Date:** 2026-08-23  
**Governing decisions:** PACD-DEC-008 and PACD-DEC-038

## 1. Fairness Principle

PACD may not be given better telemetry, state knowledge, action access, mission information, execution reliability, compute accounting, or scenario allocation while comparison systems are intentionally deprived of equivalent inputs unless the comparison is explicitly classified as a system-level comparison and the asymmetry is intrinsic to the compared system.

Every report must distinguish:

- **system-level comparison:** authentic complete-system capabilities and costs;
- **controlled comparison:** equalized information/action resources intended to isolate decision policy or coordination.

## 2. Planned Defender Matrix

| Condition | Authentic system description | Controlled-comparison form | Information access | Action access | Mission information | Oversight | Status |
|---|---|---|---|---|---|---|---|
| Static defense | Fixed controls and rules; no adaptive policy | Same telemetry and action catalog, fixed immutable policy | Equalized telemetry in controlled mode | Fixed subset or equalized full set with fixed policy | None or equalized depending comparison | None | Not implemented |
| Deterministic SOAR automation | Rule/playbook triggers and deterministic actions | Same observations/actions; deterministic mapping | Equalized | Equalized where appropriate | Same mission features if controlled | Optional fixed approval rules | Not implemented |
| Delayed human-centered response | Recommendations or alerts routed through human delay | Same observations/actions; simulated human decision policy | Equalized | Equalized | Equalized in controlled mode | Mandatory simulated delay | Not implemented |
| Random polymorphism | Random admissible variation without adaptive reasoning | Same admissible polymorphism actions and budget | Equalized | Equalized | Equalized or excluded in paired ablation | Same safety governor | Not implemented |
| Single-layer adaptive defense | Adaptation in one polymorphism class | Same telemetry/actions for selected layer | Equalized | Equalized within selected layer | Equalized | Same safety/oversight rules | Not implemented |
| Full PACD | Coordinated belief, policy, polymorphism, governance, oversight | Same information/action budget as controlled baselines | Defined by mode | Defined by mode | Defined by mode | Contextual | Diagnostic threshold only |
| Unbounded agentic diagnostic | Simulated action selection without normal safety constraints | Internal diagnostic only; no real tools | Same synthetic inputs | Simulated only | Same synthetic mission data | None | Not implemented; must remain non-deployable |
| Oracle upper bound | Perfect or near-perfect state/adversary knowledge | Reference bound, excluded from ordinary fairness claims | Privileged by definition | Controlled reference set | Perfect/defined mission model | None | Not implemented |

## 3. Equalization Dimensions

| Dimension | Required control | Evidence |
|---|---|---|
| Scenario allocation | Identical scenario/seed allocation or documented paired design | Run manifest and allocation table |
| Telemetry | Same sensor coverage, delay, noise, loss, and integrity unless authentic-system comparison | Canonical config hashes |
| State knowledge | Same normalized evidence and state fields in controlled mode | Interface contract tests |
| Mission knowledge | Same mission model and error profile in controlled mode | Mission-config hashes |
| Action catalog | Same action types, targets, preconditions, execution reliability, and costs where comparison intends policy isolation | Action-catalog hash |
| Safety rules | Same prohibited actions and hard consequence limits unless safety architecture itself is the variable | Policy hash and decision audit |
| Oversight | Same approval delay/error model unless human routing is the variable | Oversight-config hash |
| Compute budget | Record CPU time, memory, proposal count, and planning budget | Resource records |
| Retry and timeout | Same episode limits and worker behavior | Harness config |
| Rollback | Same rollback probability/cost where action semantics are equalized | Execution config |
| Randomness | Registered seeds and deterministic streams | Seed registry |
| Failure handling | Identical invalid/corrupt episode rules | Frozen exclusions |
| Metrics | Single frozen metric implementation for all conditions | Metric hash and raw regeneration |
| Tuning | Comparable development budgets; all tuned parameters retained | Calibration log |
| Negative controls | Same benign and hostile controls | Scenario registry |
| Missing data | Same handling and visibility | Frozen protocol |

## 4. Permitted Asymmetries

An asymmetry is permissible only when:

1. it is intrinsic to the complete system being compared;
2. it is declared before reportable runs;
3. it is measured as a resource or capability difference;
4. the report does not attribute the entire system-level difference to one algorithmic component;
5. a controlled equalized comparison is also provided where feasible.

Examples include PACD's mission model, multi-agent coordination, or policy portfolio. These may be system capabilities, but their contribution should be isolated through ablations and equalized comparisons.

## 5. Required Ablations

Draft ablations:

- PACD without mission model;
- PACD without uncertainty input;
- PACD without reversibility input;
- PACD without multi-agent orchestration;
- PACD with one polymorphism class;
- PACD without policy portfolio;
- PACD without human oversight delay;
- PACD with degraded safety-governor service;
- PACD with inaccurate dependency map;
- PACD with unreliable rollback.

No ablation is final until protocol freeze.

## 6. Fairness Review Gate

Before any reportable run, a reviewer independent from the primary implementation task must verify:

- baseline definitions are substantive and not straw systems;
- configuration hashes are fixed;
- authentic and controlled comparison labels are accurate;
- information/action asymmetries are declared;
- resource budgets are recorded;
- negative controls and hostile regimes are present;
- tuning and calibration exposure is comparable;
- the oracle and unbounded diagnostic are not presented as ordinary deployable baselines.

## 7. Current Disposition

The matrix guides Phase 2 implementation. It does not establish that any baseline is complete or fair. Fairness is not established until each baseline is implemented, tested, configured, and independently reviewed at an exact commit.

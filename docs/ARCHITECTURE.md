# PACD Local Simulation Code Architecture

## Current implementation through PR #22

This overview describes merged implementation
[`31c1645`](https://github.com/mthiessmeier/pacd-simulation/commit/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25),
including [PR #22](https://github.com/mthiessmeier/pacd-simulation/pull/22).
Use the [current demonstration](current_demo/README.md) to reproduce bounded guarded
execution, sensing changes and their measurements. The
[current progress record](../status/CURRENT_PROGRESS.md) separates merged capabilities
from residual requirements. The [earlier Phase 2 demonstration](application_demo/README.md)
remains a historical, revision-pinned work sample.

The simulator implements a decision-to-consequence loop for two synthetic actions:
`isolate_session` and `switch_sensing_profile`. All current outputs are
`NON_REPORTABLE_DIAGNOSTIC`. This architecture supports implementation and diagnostic
checks; it does not establish PACD effectiveness, safety, generalization or readiness
for operational deployment.

### Separation of responsibilities

The independent evaluation harness owns configuration loading, scheduling, termination, and
artifact finalization. Prospective review and sensing policies consume their specified
observation interfaces; architecture tests check the separation of responsibilities. This
cooperative local Python implementation does not provide hostile-code isolation. The legacy
diagnostic classification and belief paths are unblinded fixtures, rather than evidence of
an observation-blinded learned defender.

| PACD responsibility | Current implementation and boundary |
|---|---|
| Telemetry ingestion | `telemetry/generator.py` generates synthetic observations. Sensing state changes the precision of subsequent delivered signals. |
| Evidence fabric | `evidence/normalize.py` retains evidence records; `evidence/context.py` tracks delivered measurements, age, duplicates and distinct source presence. Repeated readings from one sensor do not become independent sources. |
| Enterprise and mission state | `environment/model.py`, `environment/availability.py` and `state/snapshot.py` represent immutable entities, directed dependencies, binary availability and bound snapshots. |
| Threat hypotheses and synthetic red behavior | `hypotheses/update.py` retains typed belief records. `agents/red/diagnostic.py` and governed event sequences provide scripted behavior; integrated adaptive adversary reasoning remains open. |
| Action ontology | `actions/models.py` and `schema.py` define typed proposals and dispositions. The broker implements session isolation and sensing-profile switching. |
| Polymorphism and policy selection | `polymorphism/sensing.py` implements the first sensing-class operator. `polymorphism/selection.py` selects a profile prospectively from the delivered evidence prefix, age, cost and budget, with an explicit fallback. |
| Orchestration | `orchestration/coordinator.py` supplies a proposal-ordering and duplicate-suppression seam. Integrated specialist-agent arbitration and coordinated portfolios remain open. |
| Independent safety and governance | `governance/governor.py` evaluates admissibility. Dispatch checks the exact action, policy and current-state binding through a fresh governor evaluation. |
| Simulated human oversight | `oversight/guarded.py` handles admission, capacity, delay, approval, denial and expiry. `oversight/review_brief.py` supplies the optional bound operator brief. Review responses are simulated. |
| Simulated execution and verification | `execution/broker.py` applies allowlisted in-memory changes. `execution/verification.py` checks the complete resulting state and supports restoration. |
| Audit, metrics and analysis | `audit/writer.py` retains raw events. `metrics/` projects verified episode and attempted-set measurements. `reproducibility/` independently checks retained semantics, artifacts and execution bindings. Broader analysis remains in the implementation plan. |

`pacd_sim.harness` is outside the system under test. The only execution adapter is
`SimulatedExecutionBroker`; it performs in-memory state transitions and has no production API,
socket, shell, credential, cloud, endpoint, or network capability.

### Guarded execution and review

A prospective defender proposes an action using its permitted observations. The governor
evaluates the proposal. For an eligible escalation, queue admission binds the originating
referral, subject, evidence, concrete action, policy, pre-state and validity interval into a
request. Capacity refusal, other admission refusal, pending review, denial and expiry remain
distinct outcomes. An approved request must still pass a fresh governor evaluation and
state-binding check before the broker can execute it.

With `guarded_review.decision_brief: operator-preview-v1`, the admitted request also binds
an operator brief. It includes the governor's rationale, concrete action and target,
the delivered signal and its age, and a conditional preview of immediate binary mission
availability. The evidence-creation commitment and independent replay bind the brief to
the actual delivered observation. Compromise probability is null; hidden truth labels and
future observations are outside the reviewer's information set. The preview assumes that
the submitted state still holds and fresh execution authority is obtained. Actual state
verification and elapsed mission loss remain separate measurements.

Successful execution records before/after state. Verification checks expected effects and
collateral changes; configured restoration records the recovery outcome. Independent
retained-run replay reconstructs governed behavior before releasing completed-episode
measurements. A receipt alone cannot make semantically incorrect records valid.

See the [guarded loop](work_orders/GUARDED_REVIEW_ISOLATION_v1.0.md),
[sensing operator](work_orders/SENSING_PROFILE_OPERATOR_v1.0.md),
[prospective selection](work_orders/PROSPECTIVE_SENSING_SELECTION_v1.0.md) and
[operator brief](work_orders/OPERATOR_REVIEW_BRIEF_v1.0.md) work orders.

### Verified measurements and attempted-set accounting

Run artifacts are written under the bounded workspace and never committed. Each manifest
binds code, configuration, seed, interpreter, lockfile, raw records, derived records and
hashes. Per-run, pinned comparison-plan and pinned attempt-register reads use the same
verification boundary. Failed, timed-out, invalid and incomplete attempts retain their
dispositions and missing episode measurements. Missing measurements remain null.

| Optional metrics view | Implemented interpretation |
|---|---|
| `--sensing-freshness` · CAL-006 | Attributes the original supporting measurements at referral and at actual execution for the two prospective sensing policies. Evidence may age during review; a later observation does not retrospectively refresh the original support. |
| `--mission-impact` · MIS-002 | Integrates binary mission unavailability over simulated time, weighted by governed criticality. Per-mission durations and contributions remain visible. |
| `--review-routing` · GOV-002 | Reconciles every actual governor escalation to a matched bound request and terminal approval, denial or expiry. Capacity failures, refused admissions and unresolved requests remain in the denominator. |
| `--approval-burden` · OPS-003 | Measures elapsed queue time per admitted request, including observed wait for requests pending at the episode horizon. It reports request-ticks and a resolved-request mean with its denominator. Override count is null because the implemented contracts do not support overrides. |

These optional views compose without changing default report representations. Empty
measurement denominators produce null rates or means. Approval burden measures simulated
queue time, not staff effort, human trust or calibrated operational cost. Failed-episode
safety and tail observations require their own broader evidence contracts. See the
[freshness](work_orders/SENSING_FRESHNESS_ATTRIBUTION_v1.0.md),
[mission loss](work_orders/MISSION_LOSS_INTEGRAL_v1.0.md),
[routing](work_orders/ESCALATION_ROUTING_v1.0.md) and
[approval burden](work_orders/APPROVAL_BURDEN_v1.0.md) work orders.

### Scope still open

The current runtime uses deterministic coded policies and scripted synthetic events, with
no live LLM inference. The integrated polymorphic behavior is one sensing-class operator;
the remaining classes, broader portfolios and substantive multi-agent coordination are
retained in the [implementation plan](REMAINING_IMPLEMENTATION_PLAN.md). Built-in sensing
episodes use one sensor and stipulated freshness rules. Richer source reliability,
contradiction handling, calibrated belief updates, adaptive adversaries and the complete
baseline/scenario suite remain open.

Mission availability is binary. Duration and criticality-weighted loss are implemented,
while graded degradation, calibrated timing and weights, and broader causal harm attribution
remain open. Review is simulated; action modification, overrides and calibrated human burden
are not established through PR #22. The H6 human-participant study retains its separate
protocol and authority. Reportable execution requires an author-approved frozen protocol
matching the exact governed revision and configuration.

## Historical Increment 1 traceability

The accepted architecture's sections 4 and 7 supply the layer and object names below.
This table preserves the first increment's typed-record mapping. Current integrated
behavior and residual scope are described above.

| Architecture responsibility | Typed records and code path |
|---|---|
| Telemetry and evidence | `telemetry/generator.py` defines sensor, detector profile and observation. `evidence/normalize.py` defines EvidenceItem. |
| Enterprise and mission state | `environment/model.py` defines Asset, Identity, Session, Credential, Service, MissionFunction and Dependency. `state/snapshot.py` binds a snapshot to its canonical digest. |
| Threat hypotheses and belief | `hypotheses/update.py` defines ThreatHypothesis, AdversaryState and BeliefState. |
| Candidate action, polymorphism and orchestration | `actions/models.py`, `polymorphism/operators.py` and `orchestration/coordinator.py` supplied the proposal types and coordinator seam. The integrated sensing operator was added subsequently in PR #15. |
| Governance and oversight | `governance/governor.py` defines Constraint and PolicyDecision. `oversight/approval.py` defines ApprovalRecord. |
| Execution and verification | `execution/broker.py` defines ExecutionRecord. `execution/verification.py` defines VerificationRecord and RollbackRecord. |
| Audit, metrics and analysis | AuditEvent enters the raw audit writer. MetricRecord supplies the existing counts on EpisodeRecord. RunManifest binds code and inputs to the raw and derived files. See `audit/writer.py`, `metrics/summarize.py` and `reproducibility/manifest.py`. |
| Evaluation harness outside the eleven layers | `configuration.py` types the scenario, policy, baseline, metric selection and seed registry. The shared gate in `harness/run.py` validates the bundle before diagnostic allocation. |

See the [wire contracts](../schemas/README.md) and
[historical Phase 2 reproduction guide](application_demo/README.md).

## Historical Increment 2 · core environment topology

The harness reads optional dependency rows from the governed scenario into
immutable `Dependency` records in `EnvironmentState`. A state snapshot binds
the endpoints, weights and IDs to its digest. The diagnostic writer and the
retained-run verifier count relationships using `to_graph(multigraph=True)`.
This detached directed multigraph preserves a built-in relationship and any
separately declared dependencies between the same two entities. Existing
callers can use `to_graph()` for the simple directed projection.

With the two service-to-mission dependencies in the [scenario example](../schemas/README.md#optional-dependencies-in-the-synthetic-scenario),
the synthetic fixture has five nodes and five edges. Session isolation changes
the session state while preserving the dependencies. Scenarios can opt into
the availability rule below to observe effects of that state change.

Run `uv run --frozen --no-sync pytest -q tests/scenario/test_environment_dependencies.py`
in the project environment to exercise the graph projections, run and verify
the populated fixture, and check rejection before diagnostic allocation.

## Historical Increment 2 · availability and mission continuity

`environment/availability.py` evaluates each immutable state from its intrinsic
flags. Assets and services use `available`, identities use `enabled`, credentials
use `active`, and a session must be both active and unisolated. A mission must
be intrinsically operational and have at least one effectively available
supporting service. Every entity must also have its positive-weight declared
prerequisites available. The evaluator propagates failures downstream until
no further entity changes. Parallel prerequisites count once. A healthy cycle
remains available until an intrinsic or upstream failure reaches it.
Re-evaluating a restored snapshot recomputes availability from that state.

With `required_dependencies_v1` enabled, each state update records availability
counts and a digest of entity membership. A separate `mission_effect` record
links a verified execution to its before/after state digests. It classifies each
mission across that transition as continued, interrupted, restored or unavailable
throughout. The four counts sum to the mission population. The continuity digest
binds classifications to mission IDs. The effect record lets reviewers inspect
service and mission consequences alongside the earlier approval and execution
records. This remains a binary synthetic rule. PR #19 subsequently added elapsed,
criticality-weighted mission loss as described above. Calibrated harm, graded degradation
and real-world service-level performance remain outside the implemented model.

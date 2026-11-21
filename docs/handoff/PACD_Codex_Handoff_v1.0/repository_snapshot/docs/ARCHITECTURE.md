# PACD Local Simulation Code Architecture

The independent evaluation harness owns configuration loading, scheduling, termination, and
artifact finalization. Defender modules receive immutable observations and cannot import or
mutate harness, metric, seed, policy, or configuration state.

| PACD layer | Module |
|---|---|
| Telemetry ingestion | `pacd_sim.telemetry` |
| Evidence fabric | `pacd_sim.evidence` |
| Enterprise and mission state | `pacd_sim.environment`, `pacd_sim.state` |
| Threat hypotheses and synthetic red behavior | `pacd_sim.hypotheses`, `pacd_sim.agents.red` |
| Action ontology | `pacd_sim.actions`, `pacd_sim.schema` |
| Polymorphism | `pacd_sim.polymorphism` |
| Orchestration | `pacd_sim.orchestration` |
| Independent safety and governance | `pacd_sim.governance` |
| Simulated human oversight | `pacd_sim.oversight` |
| Simulated execution and verification | `pacd_sim.execution` |
| Audit, metrics, and analysis | `pacd_sim.audit`, `pacd_sim.metrics`, `pacd_sim.analysis` |

`pacd_sim.harness` is outside the system under test. The only execution adapter is
`SimulatedExecutionBroker`; it performs in-memory state transitions and has no production API,
socket, shell, credential, cloud, endpoint, or network capability.

Run artifacts are written under the bounded workspace and never committed. Metrics accept only
completed raw artifact paths. Each manifest binds code, configuration, seed, interpreter,
lockfile, raw records, derived records, and hashes.

## Increment 1 traceability

The accepted architecture's sections 4 and 7 supply the layer and object names below.
The first six rows describe existing typed domain records. The last two cover the new
v1 evidence contracts and the input boundary. Each remains in the module that owns it.

| Architecture responsibility | Typed records and code path |
|---|---|
| Telemetry and evidence | `telemetry/generator.py` defines sensor, detector profile and observation. `evidence/normalize.py` defines EvidenceItem. |
| Enterprise and mission state | `environment/model.py` defines Asset, Identity, Session, Credential, Service, MissionFunction and Dependency. `state/snapshot.py` binds a snapshot to its canonical digest. |
| Threat hypotheses and belief | `hypotheses/update.py` defines ThreatHypothesis, AdversaryState and BeliefState. |
| Candidate action, polymorphism and orchestration | `actions/models.py`, `polymorphism/operators.py` and `orchestration/coordinator.py` retain the existing proposal types and coordinator. Integrated polymorphism remains future work. |
| Governance and oversight | `governance/governor.py` defines Constraint and PolicyDecision. `oversight/approval.py` defines ApprovalRecord. |
| Execution and verification | `execution/broker.py` defines ExecutionRecord. `execution/verification.py` defines VerificationRecord and RollbackRecord. |
| Audit, metrics and analysis | AuditEvent enters the raw audit writer. MetricRecord supplies the existing counts on EpisodeRecord. RunManifest binds code and inputs to the raw and derived files. See `audit/writer.py`, `metrics/summarize.py` and `reproducibility/manifest.py`. |
| Evaluation harness outside the eleven layers | `configuration.py` types the scenario, policy, baseline, metric selection and seed registry. The shared gate in `harness/run.py` validates the bundle before diagnostic allocation. |

See the [wire contracts](../schemas/README.md) and [reproduction guide](application_demo/README.md).

## Increment 2 opening · core environment topology

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

## Increment 2 · availability and mission continuity

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
records. This is a binary synthetic rule. Duration, calibrated harm and
real-world service-level performance remain outside this model.

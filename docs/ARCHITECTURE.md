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

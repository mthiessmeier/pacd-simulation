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

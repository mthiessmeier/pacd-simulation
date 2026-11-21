# Diagnostic schemas

The version 1.0 identity diagnostic takes five governed files. Each requires
`schema_version: "1.0"` and `evidence_label: NON_REPORTABLE_DIAGNOSTIC`. The
strict, frozen Pydantic models in `src/pacd_sim/configuration.py` reject extra
fields at every level. Each decoded array becomes a tuple and retains its order.

| File under `configs/` | Model | Constraints exercised by the diagnostic |
|---|---|---|
| `scenarios/diagnostic_identity_smoke.yaml` | `ScenarioConfig` | Synthetic scenario, 1–100 events and actions each, nonempty identity/session/service/mission collections, bounded telemetry noise and delay. |
| `policies/diagnostic_safety.yaml` | `PolicyConfig` | Simulated adapter, disabled network, explicit allowed/escalated/prohibited classes. The existing governor policy checks that the classes are disjoint. |
| `seeds/diagnostic_seeds.json` | `SeedRegistryConfig` | 1–100 distinct nonnegative signed 64-bit integers. The harness checks membership of the default and selected seeds. |
| `defenders/diagnostic_baseline.yaml` | `BaselineConfig` | Named baseline, synthetic-only observations and no actions. |
| `metrics/diagnostic_metrics.yaml` | `MetricConfig` | One entry each for event, approved-action and prohibited-action counts. Comparative claims must be disabled. |

From the project checkout and its locked environment, these read-only commands
describe the input models and validate the checked-in bundle.

```powershell
uv run --frozen --no-sync python -c "import json; from pacd_sim.configuration import DiagnosticInputs; print(json.dumps(DiagnosticInputs.model_json_schema(), indent=2))"
uv run --frozen --no-sync python -c "from pacd_sim.harness.run import validate_diagnostic_configuration_files as validate; print(validate('.'))"
```

The first command emits JSON Schema for field shapes. The second also enforces
file, uniqueness, reference and cross-input rules and returns individual and
aggregate canonical digests. Doctor, diagnostic invocation and retained-run
verification use the same typed input check. Shape inspection alone cannot
establish that a bundle is executable.

### File boundaries and compatibility

The loader reads at most 1 MiB plus one sentinel byte per UTF-8 file. The
decoded tree admits at most 10,000 values including containers, with root
depth zero and maximum depth 40. JSON has an additional string-aware lexical
nesting check ahead of the decoder. Duplicate mapping keys, recursive aliases,
nonfinite numbers and text that cannot be represented as UTF-8 fail validation.

YAML composition rejects explicit tags and caps source nodes, including keys,
at 20,000. The default alias limit is 20. Before merge-key expansion and value
construction, a tree walk charges each alias use against the same 20,000-node
limit and a 1 MiB expanded scalar-byte limit. Bounded, unambiguous aliases
and mappings with a single merge key remain supported.

Accepted bootstrap files retain their semantic hashes. Hashing uses the
original validated wire values so an integral numeric field retains its
original JSON spelling as an integer when that was its decoded type.
The stricter input path rejects repeated YAML merge keys, escaped unpaired
surrogates and over-budget YAML expansions. Telemetry bounds now fail in the
parent's input check, before invocation allocation. Schema version and
classification are mandatory, including for older retained configurations.

### Record types

Shared version, provenance and numeric types live in `src/pacd_sim/schema.py`.
The environment, actions, decisions and verification records stay in their
own architecture modules. The audit writer, metric summary and manifest
modules expose `AuditEvent`, `MetricRecord`, `EpisodeRecord` and `RunManifest`
for their wire contracts. The bootstrap raw, summary and manifest formats
remain version 1.0. These schemas carry no approval for reportable execution.

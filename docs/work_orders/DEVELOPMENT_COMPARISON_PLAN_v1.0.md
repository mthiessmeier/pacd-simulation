# WP01 · Bind development comparison cells to retained invocations

The evaluator needs to know whether an episode belongs to the cell declared before launch. An accepted v1 register binds an attempt label, invocation ID and seed. A verified episode supplies its configuration retrospectively. Two cells can therefore request the same seed and still differ in scenario, condition, revision or intended comparison.

## Authority and inputs

Michael’s November 21 continuation directs the next increment wherever authorized. DEC-038 permits Phase 2 development and calibration. WP01 implements the development subset of WO §§6.5 and 7, TM §4, FM §3 and MD §§8–11 within that authority. The August bootstrap starting instruction has been superseded by the accepted merge. Runtime and review start from `df33295469094a5ed9aa26fcc4b1fa1d019d3e5c` with implementation `d5a29699e14409bfd54d30c51117c81077639ee6`. Independent exact-head review and the owner's merge decision follow separately. [Increment 1 decision](../../status/PHASE2_INCREMENT1.md) · [Accepted implementation](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861)

## Contract and entry points

Use `pacd-development-comparison-plan-v1` at the existing `diagnostic` and `metrics` entry points. The evaluator owns the workspace-local JSON file. Put it outside the Git checkout to keep the launch revision clean. The ordered `attempts` array has 1–100 entries and the file has a 65,536-byte ceiling. The existing strict JSON reader checks depth, duplicate keys and nonfinite values. All model fields are mandatory. The model rejects unknown keys and coerced values.

| Level | Fields | Meaning |
|---|---|---|
| Plan | `format`, `evidence_label`, `attempts` | Use the format above and `NON_REPORTABLE_DIAGNOSTIC`. Canonical SHA-256 binds the full ordered membership. |
| Attempt | `cell_id`, `comparison_mode`, `attempt_id`, `invocation_id`, `seed`, `expected` | Mode is `controlled` or `system_level`. Each slot has a unique attempt ID and lowercase 32-hex invocation ID. Repetitions or reserved retries of a cell share its inputs, mode and seed. |
| Expected inputs | `scenario`, `condition`, `code_commit`, `config_sha256`, `seed_registry_sha256`, `events_sha256` | Actual scenario and baseline names, clean 40-hex revision, canonical aggregate configuration, development seed registry and ordered configured source events. |

The aggregate covers scenario, safety, baseline, metric definition and protocol. The registry digest covers the separate seed file. The event digest identifies the **configured exogenous script**. The concrete development seed, script, sensor settings in the scenario and revision identify the existing per-sensor/per-event random streams. Identical script membership does not assert identical delivered observations after interventions. The comparison mode records the evaluator’s intention. WP11 must demonstrate fairness in each mode.

### Prepare and read a plan

The following Python example, run in the frozen editable checkout, prepares a single default cell and an optional retry. Run it in a fresh Python process from the repository root. It exclusively creates the file in the dedicated workspace. Record the printed digest and invocation ID for the commands below.

```python
import json
from pathlib import Path
from uuid import uuid4
from pacd_sim.comparison import ComparisonPlan
from pacd_sim.constants import DEFAULT_SCENARIO_FILE
from pacd_sim.harness.run import load_yaml_config, validate_diagnostic_configuration_files
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.reportable import git_commit

repo = Path.cwd()
hashes = validate_diagnostic_configuration_files(repo)
scenario = load_yaml_config(repo / "configs/scenarios" / DEFAULT_SCENARIO_FILE)
expected = dict(scenario=scenario["name"], condition="null_diagnostic_baseline",
                code_commit=git_commit(repo), config_sha256=hashes["config_hash"],
                seed_registry_sha256=hashes["seed_registry_hash"],
                events_sha256=canonical_sha256(scenario["events"]))
attempts = [dict(cell_id="identity-default", attempt_id=label, invocation_id=uuid4().hex,
                 seed=424242, comparison_mode="controlled", expected=expected)
            for label in ("first", "reserved-retry")]
plan = ComparisonPlan.model_validate(dict(format="pacd-development-comparison-plan-v1",
    evidence_label="NON_REPORTABLE_DIAGNOSTIC", attempts=attempts))
path = repo.parent.parent / "var/tmp" / f"plan-{attempts[0]['invocation_id']}.json"
with path.open("x", encoding="utf-8") as out:
    json.dump(plan.model_dump(mode="json"), out, indent=2)
print(path, canonical_sha256(plan), attempts[0]["invocation_id"], sep="\n")
```

With `$plan`, `$pin` and `$invocation` set to those three outputs, use the existing frozen environment:

```powershell
pacd-sim metrics --plan $plan --plan-sha256 $pin
pacd-sim diagnostic --plan $plan --plan-sha256 $pin --invocation-id $invocation --seed 424242
pacd-sim metrics --plan $plan --plan-sha256 $pin
```

The verifier compares the manifest with the clean checkout used to read the evidence. Use one revision per batch to release every matching completion in one read. The initial read can display the canonical digest without a supplied pin. Launch requires the pin and the declared invocation. The harness resolves the usual scenario/policy/seeds/baseline/metrics options, validates actual governed files and checks seed and clean executing checkout before claiming ownership. It checks the worker's loaded bundle again. Marker version 1.1 adds the batch digest, which the existing completion receipt binds through the marker hash. A v1 unplanned launch keeps marker version 1.0. No action or defender receives the plan.

### Measurement and acceptance

The same receipt/content verifier supplies the observed inputs from its validated snapshot. The report exposes expected and observed identities, observed marker digest, row disposition and, where available, the retained evidence disposition. Mismatched plans, unplanned invocations and changed inputs withhold counts. Zero verified completions yields null observed counts. The completion denominator is every declared slot, including reserved but unused retries. The escalation denominator is candidate actions from eligible verified completions. Missing actions or safety outcomes from a failed episode remain unknown. WP12 owns separate failed-episode attribution and tail accounting.

| Challenge | Required observation |
|---|---|
| Formatting, array reordering, new cell or mode | Whitespace/key order preserve the digest. Changes to membership, ordering or semantic identity change it. A changed pin refuses launch/read. |
| Scenario/condition/code/config/registry/script/seed substitution, wrong checkout | Refuse before allocating the invocation. A change after that check must fail worker checks or fail verified release. |
| Occupied invocation or retry collision | Exclusive allocation refuses the collision. The existing slot survives. |
| Wrong cell, unplanned completion, contradictory status or late failure | Preserve the terminal evidence, withhold cell metrics and show invalid/failed state and reason. |
| Failed, timed-out, staged or absent | One row per declared attempt in source order. Only verified matches enter observed counts. |
| Oversized, deep, duplicate-key, extra-field, duplicate-ID or indirect-path plan | Refuse through strict existing bounds before reading or writing run evidence. |
| Compatibility and authority | Re-read without changes to stores, reproduce v1 output/diagnostic replay, exercise expected reportability denial with stores unchanged, then challenge the exact candidate independently. |

Implementation touches `comparison.py`, `cli.py`, `harness/run.py`, `metrics/registered.py` and the existing receipt and verifier modules under `src/pacd_sim`. The targeted regression file is `tests/scenario/test_comparison_plan.py`. Run the established frozen suite, formatting, lint, typing, audit, coverage, safety and compatibility gates on the review head. Local cooperating-process evidence has the assurance limits of the accepted receipts. Membership hashes establish content identity. Trusted time, reportable preregistration, H6, hypothesis classification, guard changes and protocol freeze remain separate.

"""Contract checks for governed inputs before an invocation may be allocated."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import CONFIG_ROOT, IsolatedWorkspace, controlled_config_files
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from pacd_sim.configuration import DiagnosticInputs, SeedRegistryConfig
from pacd_sim.harness.run import (
    ConfigurationError,
    _load_json_config,
    _run_diagnostic_in_process,
    load_yaml_config,
    run_diagnostic,
    validate_diagnostic_configuration_files,
)
from pacd_sim.reproducibility.canonical import canonical_sha256


def _wire_inputs() -> dict[str, object]:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(CONFIG_ROOT)
    return {
        "scenario": load_yaml_config(scenario),
        "policy": load_yaml_config(policy),
        "seeds": _load_json_config(seeds),
        "baseline": load_yaml_config(baseline),
        "metrics": load_yaml_config(metrics),
    }


def test_bootstrap_wire_identity_and_immutable_nested_arrays() -> None:
    wire = _wire_inputs()
    inputs = DiagnosticInputs.model_validate(wire)
    assert canonical_sha256(inputs) == canonical_sha256(wire)
    assert DiagnosticInputs.model_validate_json(inputs.model_dump_json()) == inputs
    assert isinstance(inputs.scenario.actions, tuple)
    with pytest.raises(ValidationError):
        inputs.scenario.actions[0].id = "changed"
    hashes = validate_diagnostic_configuration_files(CONFIG_ROOT.parent)
    # Computed from the accepted bootstrap inputs and canonical representation.
    assert hashes["config_hash"] == (
        "54e7a429b27bf94deeefe22f79ba22fff7ce36ae35dc6647b02784008ef10364"
    )
    assert hashes["seed_registry_hash"] == (
        "b0fcdad5ae664958afddb79f950d4a812d7dc066a218bee3245444e83d57c312"
    )


@pytest.mark.property
@given(
    st.lists(st.integers(min_value=0, max_value=2**63 - 1), min_size=1, max_size=20, unique=True)
)
@settings(max_examples=30, deadline=None)
def test_seed_registry_roundtrip_preserves_values_and_wire_hash(values: list[int]) -> None:
    wire = {"evidence_label": "NON_REPORTABLE_DIAGNOSTIC", "schema_version": "1.0", "seeds": values}
    registry = SeedRegistryConfig.model_validate(wire)
    assert SeedRegistryConfig.model_validate_json(registry.model_dump_json()) == registry
    assert registry.seeds == tuple(values)
    assert canonical_sha256(registry) == canonical_sha256(wire)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("index", "old", "new"),
    [
        (0, "delay_ticks: 1", "delay_ticks: 101"),
        (0, "criticality: 0.8", "criticality: 0.8\n    unrecognized: false"),
        (0, "delay_ticks: 1", "delay_ticks: 2\n  delay_ticks: 1"),
        (0, "noise_standard_deviation: 0.05", "noise_standard_deviation: .nan"),
        (0, "event-benign-admin", "event-simulated-adversary"),
        (0, "event-benign-admin", "e" * 200),
        (0, "identity-synthetic-user", "i" * 235),
        (0, "action-allowed", "a" * 234),
        (0, "action-prohibited", "p" * 241),
        (0, "session-synthetic-001", "s" * 235),
        (0, "identity-synthetic-user", "界" * 167),
        (0, "action-prohibited", "界" * 167),
        (0, "synthetic-denied-target", "界" * 167),
        (1, "network_enabled: false", "network_enabled: 0"),
        (2, '"seeds":', '"unexpected": [], "seeds":'),
        (2, '"seeds":', '"seeds": [0], "seeds":'),
        (2, "[424242, 424243]", "[424242, 1e400]"),
        (3, "synthetic_only", "evaluation_truth"),
        (4, "comparative_claims: false", "comparative_claims: 0"),
        (4, "- approved_action_count", "- event_count"),
    ],
)
def test_invalid_config_stops_public_harness_before_ownership(
    isolated_workspace: IsolatedWorkspace, index: int, old: str, new: str
) -> None:
    files = controlled_config_files(isolated_workspace.config_root)
    source = files[index].read_text(encoding="utf-8")
    assert old in source
    files[index].write_text(source.replace(old, new), encoding="utf-8")
    scenario, policy, seeds, baseline, metrics = files
    with pytest.raises(ConfigurationError):
        validate_diagnostic_configuration_files(isolated_workspace.repo_root)
    with pytest.raises(ConfigurationError):
        run_diagnostic(
            scenario,
            policy,
            seeds,
            isolated_workspace.output_root,
            baseline_path=baseline,
            metric_path=metrics,
            repo_root=isolated_workspace.repo_root,
            workspace_root=isolated_workspace.root,
        )
    assert list(isolated_workspace.output_root.iterdir()) == []
    assert not (isolated_workspace.root / "var" / "invocations").exists()
    assert not (isolated_workspace.root / "var" / "receipts").exists()


def test_configuration_check_validates_the_second_governed_scenario(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    path = isolated_workspace.config_root / "scenarios/diagnostic_maintenance_window.yaml"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\nunknown_scenario_field: true\n")
    with pytest.raises(ConfigurationError, match="unknown_scenario_field"):
        validate_diagnostic_configuration_files(isolated_workspace.repo_root)


def test_derived_id_limits_preserve_executable_boundary_cases(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    source = scenario.read_text(encoding="utf-8")
    for previous, replacement in (
        ("event-benign-admin", "e" * 199),
        ("identity-synthetic-user", "i" * 234),
        ("action-allowed", "a" * 233),
        # This fits both the 240-character bound and the 500-byte audit column.
        ("action-prohibited", "界" * 130 + "p" * 110),
        ("session-synthetic-001", "s" * 234),
    ):
        source = source.replace(previous, replacement)
    scenario.write_text(source, encoding="utf-8")
    validate_diagnostic_configuration_files(isolated_workspace.repo_root)
    result = _run_diagnostic_in_process(
        scenario,
        policy,
        seeds,
        isolated_workspace.output_root,
        baseline_path=baseline,
        metric_path=metrics,
        repo_root=isolated_workspace.repo_root,
        workspace_root=isolated_workspace.root,
    )
    assert result.run_dir.is_dir()


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
def test_input_byte_limit_applies_before_parsing(suffix: str, tmp_path: Path) -> None:
    source = tmp_path / f"config{suffix}"
    blob = b'{"a":123}'
    maximum = 1024 * 1024
    load = _load_json_config if suffix == ".json" else load_yaml_config
    with source.open("wb") as handle:
        handle.write(blob + b" " * (maximum - len(blob)))
    assert load(source) == {"a": 123}
    with source.open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ConfigurationError, match="1 MiB"):
        load(source)


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
@pytest.mark.parametrize("nesting", [41, 1200])
def test_nested_sources_raise_configuration_error_before_recursion(
    suffix: str, nesting: int, tmp_path: Path
) -> None:
    source = tmp_path / f"config{suffix}"
    source.write_text('{"key":' + "[" * nesting + "0" + "]" * nesting + "}", encoding="utf-8")
    load = _load_json_config if suffix == ".json" else load_yaml_config
    with pytest.raises(ConfigurationError):
        load(source)


def test_bounded_yaml_alias_and_merge_preserve_canonical_content(tmp_path: Path) -> None:
    source = tmp_path / "config.yaml"
    source.write_text("base: &base {v: 1}\nother: {<<: *base, b: true}\n", encoding="utf-8")
    assert load_yaml_config(source) == {"base": {"v": 1}, "other": {"b": True, "v": 1}}


@pytest.mark.parametrize(
    "body",
    [
        "a: &a [*a]",
        "a: {<<: {a: 0}, <<: {b: 0}}",
        "a: &a " + "z" * (600 * 1024) + "\nb: *a",
        "a: &a [" + ",".join("z" for _ in range(1000)) + "]\nb: [" + ",".join(["*a"] * 10) + "]",
        "a: '\\ud800'".replace("'", '"'),
    ],
    ids=["cycle", "duplicate-merge", "scalar-expansion", "expanded-nodes", "escaped-surrogate"],
)
def test_yaml_expansion_rejected_before_canonicalization(body: str, tmp_path: Path) -> None:
    source = tmp_path / "config.yaml"
    source.write_text(body, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_yaml_config(source)


def test_json_surrogate_is_rejected_before_canonicalization(tmp_path: Path) -> None:
    source = tmp_path / "config.json"
    source.write_text(json.dumps({"value": "\ud800"}), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        _load_json_config(source)

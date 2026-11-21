"""Retrospective sequence inspection uses verified delivery order and source ticks."""

import hashlib
import json

import pytest
import yaml
from conftest import (
    DiagnosticRuns,
    IsolatedWorkspace,
    controlled_config_files,
    run_committed_scenario,
)

from pacd_sim import cli
from pacd_sim.harness.run import load_yaml_config
from pacd_sim.reproducibility.verify import verify_run


@pytest.mark.scenario
def test_sequence_orders_tied_ticks_and_keeps_source_identity(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario_file = controlled_config_files(isolated_workspace.config_root)[0]
    scenario = load_yaml_config(scenario_file)
    first = {
        "id": "event-m",
        "tick": 1,
        "kind": "benign_administrative",
        "identity_id": "identity-synthetic-admin",
    }
    tied_a = {"id": "event-a", "tick": 2, "kind": "benign_administrative", "identity_id": None}
    tied_z = {
        "id": "event-z",
        "tick": 2,
        "kind": "simulated_adversary",
        "identity_id": "identity-synthetic-user",
    }
    scenario["events"] = [tied_z, tied_a, first]
    scenario_file.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    run = run_committed_scenario(isolated_workspace)
    result = verify_run(
        run.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
        include_event_sequence=True,
    )
    assert result.valid, result.errors
    ordered = [first, tied_a, tied_z]
    material = {"format": "pacd-scripted-events-v1", "events": ordered}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = {**material, "event_count": 3, "sha256": hashlib.sha256(encoded).hexdigest()}
    assert json.dumps(result.to_dict()["event_sequence"], sort_keys=True) == json.dumps(
        expected, sort_keys=True
    )


@pytest.mark.reproducibility
def test_sequence_is_opt_in_and_independent_of_observation_noise(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "_emit_json", emitted.append)
    first = diagnostic_runs.same_seed_a
    assert cli.main(["verify", str(first.run_dir)]) == 0
    assert emitted[-1]["valid"] is True and "event_sequence" not in emitted[-1]

    assert first.raw_semantic_hash != diagnostic_runs.different_seed.raw_semantic_hash
    for run in (first, diagnostic_runs.same_seed_b, diagnostic_runs.different_seed):
        assert cli.main(["verify", str(run.run_dir), "--show-event-sequence"]) == 0
        assert emitted[-1]["valid"] is True
    assert (
        emitted[1]["event_sequence"] == emitted[2]["event_sequence"] == emitted[3]["event_sequence"]
    )


@pytest.mark.negative
def test_sequence_withheld_when_only_receipt_verification_fails(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    receipt = run.receipt_path
    assert receipt is not None
    held = receipt.with_suffix(".held")
    assert not held.exists()
    receipt.rename(held)
    try:
        result = verify_run(
            run.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
            include_event_sequence=True,
        )
    finally:
        held.rename(receipt)
    assert result.semantic_content_valid and not result.execution_identity_assured
    assert not result.valid and any("receipt" in error.lower() for error in result.errors)
    assert "event_sequence" not in result.to_dict()

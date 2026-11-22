"""Cross-condition checks on the single governed sensing decision and its observed effects."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.canonical import canonical_sha256


def run_episode(
    ws: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    scenario: Path,
    condition: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    outputs: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda data, **_: outputs.append(data))
    assert (
        cli.main(
            [
                "diagnostic",
                "--scenario",
                str(scenario),
                "--baseline",
                str(ws.config_root / f"defenders/sensing_{condition}.yaml"),
                "--seed",
                "424242",
            ]
        )
        == 0
    ), outputs
    run = Path(outputs[-1]["run_dir"])
    assert cli.main(["metrics", str(run)]) == 0, outputs[-1:]
    report = outputs[-1]
    assert report["execution_identity_assured"] and report["metrics_sha256"] == canonical_sha256(
        report["metrics"]
    )
    rows = [json.loads(line) for line in (run / "raw/events.jsonl").read_bytes().splitlines()]
    for row in rows:
        row["payload"] = json.loads(row["payload_json"])
    return rows, report["metrics"]["guarded_review"]


@pytest.mark.scenario
@pytest.mark.parametrize("fixture,cost", [("nominal", 0.25), ("costly", 0.95)])
def test_sensing_conditions_share_inputs_and_charge_only_verified_switches(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    cost: float,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / f"scenarios/diagnostic_sensing_{fixture}.yaml"
    inputs = []
    for condition in ("fixed", "adaptive", "disabled"):
        rows, review = run_episode(ws, monkeypatch, scenario, condition)
        switched = condition == "fixed" or (condition == "adaptive" and fixture == "nominal")
        reads = [r for r in rows if r["event_type"] == "observation"]
        inputs.append(
            [(r["tick"], r["payload"]["event_id"], r["payload"]["latent_signal"]) for r in reads]
        )
        assert [r["payload"]["signal"] for r in reads] == [0.9, 0.9, 0.9, 0.86 if switched else 0.9]
        lifecycle = [r for r in rows if r["event_type"] == "guarded_review"]
        if switched:
            assert [r["outcome"] for r in lifecycle] == [
                "pending",
                "approved",
                "executed",
                "verified",
                "mission_effect",
            ]
            assert [r["tick"] for r in lifecycle] == [2, 4, 4, 4, 4]
            binding = lifecycle[0]["payload"]["binding"]
            assert binding["action"]["action_type"] == "switch_sensing_profile"
            assert binding["action"]["mission_cost"] == cost
            assert binding["action_digest"] == canonical_sha256(binding["action"])
        else:
            assert not lifecycle
        operator = review["sensing_operator"]
        assert operator["verified_switch_count"] == int(switched)
        assert operator["switch_cost_spent"] == (cost if switched else 0)
        assert operator["alternate_profile_ticks"] == (4 if switched else 0)
        assert operator["expected_known_profile_ticks"] == (5 if switched else 8)
        assert review["mission_availability"]["unavailable_mission_ticks"] == 0
    assert inputs[0] == inputs[1] == inputs[2]


@pytest.mark.scenario
@pytest.mark.parametrize(
    "original,replacement,outcome",
    [
        ("rollback: false", "rollback: true", "rolled_back"),
        ("response: approve", "response: deny", "denied"),
        ("response: approve", "response: no_response", "expired"),
        ("budget: 1.0", "budget: 0.0", None),
    ],
)
def test_recovery_and_withheld_dispatch_preserve_default_sensing(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    original: str,
    replacement: str,
    outcome: str | None,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    source = scenario.read_text(encoding="utf-8")
    assert source.count(original) == 1
    scenario.write_text(source.replace(original, replacement), encoding="utf-8")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "-qm",
            "pin controlled sensing variant",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    rows, review = run_episode(ws, monkeypatch, scenario, "fixed")
    lifecycle = [r["outcome"] for r in rows if r["event_type"] == "guarded_review"]
    if outcome is None:
        assert not lifecycle
    else:
        assert outcome in lifecycle
    assert [r["payload"]["signal"] for r in rows if r["event_type"] == "observation"] == [0.9] * 4
    operator = review["sensing_operator"]
    assert operator["alternate_profile_ticks"] == 0
    assert operator["expected_known_profile_ticks"] == 8
    assert operator["switch_cost_spent"] == (0.25 if outcome == "rolled_back" else 0)

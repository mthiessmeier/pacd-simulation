"""Exercise governed review from a prospective observation through verified public reports."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.canonical import canonical_sha256


def evaluate(
    ws: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    condition: str,
    settings: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scenario = ws.config_root / f"scenarios/diagnostic_guarded_{fixture}.yaml"
    if settings:
        source = scenario.read_text(encoding="utf-8")
        for original, replacement in settings.items():
            assert source.count(original) == 1
            source = source.replace(original, replacement)
        scenario.write_text(source, encoding="utf-8")
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=PACD Test",
                "-c",
                "user.email=pacd-test@example.invalid",
                "commit",
                "-qm",
                "record synthetic review controls",
                "--",
                str(scenario.relative_to(ws.repo_root)),
            ],
            cwd=ws.repo_root,
            check=True,
        )
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda data, **_: output.append(data))
    assert (
        cli.main(
            [
                "diagnostic",
                "--scenario",
                str(scenario),
                "--baseline",
                str(ws.config_root / f"defenders/{condition}.yaml"),
                "--seed",
                "424242",
            ]
        )
        == 0
    ), output[-1:]
    run_dir = Path(output[-1]["run_dir"])
    assert cli.main(["metrics", str(run_dir)]) == 0, output[-1:]
    report = output[-1]
    assert report["execution_identity_assured"]
    assert report["metrics_sha256"] == canonical_sha256(report["metrics"])
    rows = [json.loads(line) for line in (run_dir / "raw/events.jsonl").read_bytes().splitlines()]
    for row in rows:
        row["payload"] = json.loads(row["payload_json"])
    return rows, report["metrics"]


@pytest.mark.scenario
@pytest.mark.parametrize(
    "condition,arrival,raw_proposals",
    [
        ("static_review", 2, 4),
        ("pacd_corroborated_review", 3, 2),
    ],
)
def test_matched_guarded_controls(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
    arrival: int,
    raw_proposals: int,
) -> None:
    observed = []
    for fixture in ("benign", "adverse"):
        rows, metrics = evaluate(isolated_workspace, monkeypatch, fixture, condition)
        decisions = [
            r for r in rows if r["event_type"] in {"baseline_decision", "defender_decision"}
        ]
        observed.append([r["payload"]["observation_sha256"] for r in decisions])
        assert [r["tick"] for r in decisions] == [2, 2, 3, 5]
        assert (
            sum(bool(r["payload"]["raw_candidate_action_id"]) for r in decisions) == raw_proposals
        )
        assert sum(r["payload"]["duplicate_suppressed"] for r in decisions) == raw_proposals - 1
        lifecycle = [r for r in rows if r["event_type"] == "guarded_review"]
        assert [(r["tick"], r["outcome"]) for r in lifecycle] == [
            (arrival, "pending"),
            (arrival + 2, "approved"),
            (arrival + 2, "executed"),
            (arrival + 2, "verified"),
            (arrival + 2, "mission_effect"),
        ]
        binding = lifecycle[0]["payload"]["binding"]
        assert binding["action"]["target_id"] == "session-guarded-user"
        assert binding["action"]["action_type"] == "isolate_session"
        assert binding["action_digest"] == canonical_sha256(binding["action"])
        assert all(r["payload"]["request_digest"] == canonical_sha256(binding) for r in lifecycle)
        assert lifecycle[-1]["payload"]["mission_continuity"]["interrupted_mission_count"] == 1
        reviewed = metrics["guarded_review"]
        assert reviewed["clock_unit"] == "simulation_ticks"
        assert reviewed["horizon_tick"] == 8
        availability = reviewed["mission_availability"]
        assert availability["unavailable_mission_ticks"] == 8 - (arrival + 2)
        assert availability["possible_mission_ticks"] == 8
        assert metrics["counts"]["candidate_action_count"] == 2
        assert metrics["counts"]["approved_action_count"] == 1
        assert metrics["counts"]["escalated_action_count"] == 1
        assert metrics["counts"]["simulated_execution_count"] == 1
        assert reviewed["mean_resolved_wait_ticks"] == 2
        assert reviewed["verified_execution_fraction"]["value"] == 1
        assert reviewed["rollback_success_fraction"]["value"] is None
    assert observed[0] == observed[1]


@pytest.mark.scenario
@pytest.mark.parametrize(
    "settings, outcomes, pending",
    [
        ({"response: approve": "response: deny"}, ["pending", "denied"], 0),
        ({"response: approve": "response: no_response"}, ["pending", "expired"], 0),
        (
            {"delay_ticks: 2": "delay_ticks: 9", "validity_ticks: 4": "validity_ticks: 9"},
            ["pending"],
            1,
        ),
        ({"capacity: 1": "capacity: 0"}, ["capacity"], 0),
        (
            {"rollback: false": "rollback: true"},
            [
                "pending",
                "approved",
                "executed",
                "verified",
                "mission_effect",
                "rolled_back",
                "mission_effect",
            ],
            0,
        ),
    ],
)
def test_guarded_dispositions_in_retained_episode(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    settings: dict[str, str],
    outcomes: list[str],
    pending: int,
) -> None:
    rows, metrics = evaluate(isolated_workspace, monkeypatch, "benign", "static_review", settings)
    lifecycle = [r for r in rows if r["event_type"] == "guarded_review"]
    assert [r["outcome"] for r in lifecycle] == outcomes
    observed = metrics["guarded_review"]
    assert observed["pending_at_horizon_count"] == pending
    assert observed["mission_availability"]["unavailable_mission_ticks"] == 0
    assert observed["mission_availability"]["possible_mission_ticks"] == 8
    if "rolled_back" in outcomes:
        assert lifecycle[-1]["payload"]["mission_continuity"]["restored_mission_count"] == 1
        assert observed["rollback_success_fraction"]["value"] == 1
    else:
        assert observed["verified_execution_fraction"]["value"] is None
        assert observed["rollback_success_fraction"]["value"] is None

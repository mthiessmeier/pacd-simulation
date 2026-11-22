"""Read-only CAL-006 attribution on verified prospective sensing episodes."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.evidence.context import EvidenceReading
from pacd_sim.harness import run as harness
from pacd_sim.polymorphism.selection import select_profile
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit


@pytest.fixture
def reports(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> list[dict[str, Any]]:
    ws = isolated_workspace
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda value, **kwargs: output.append(value))
    return output


def _read(reports: list[dict[str, Any]], *args: str, code: int = 0) -> dict[str, Any]:
    assert cli.main(list(args)) == code, reports[-1:]
    return reports[-1]


def _launch(
    ws: IsolatedWorkspace, reports: list[dict[str, Any]], fixture: str, condition: str, *args: str
) -> dict[str, Any]:
    return _read(
        reports,
        "diagnostic",
        "--seed",
        "424242",
        "--scenario",
        str(ws.config_root / f"scenarios/diagnostic_sensing_{fixture}.yaml"),
        "--baseline",
        str(ws.config_root / f"defenders/sensing_{condition}.yaml"),
        *args,
    )


def _check_stage(stage: dict[str, Any], fresh: int, stale: int) -> None:
    measured = fresh + stale
    assert stage["total_count"] == measured
    assert (stage["fresh_count"], stage["stale_count"], stage["unknown_count"]) == (fresh, stale, 0)
    fraction = stage["stale_fraction"]
    assert (fraction["numerator"], fraction["denominator"]) == (stale, measured)
    assert fraction["value"] == (stale / measured if measured else None)


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("scenario", "condition", "candidate", "fresh_execution", "stale_execution"),
    [
        ("nominal", "contextual", 1, 0, 1),
        ("nominal", "scheduled", 1, 1, 0),
        ("delayed", "contextual", 0, 0, 0),
    ],
)
def test_verified_referral_and_dispatch_use_their_own_clocks(
    isolated_workspace: IsolatedWorkspace,
    reports: list[dict[str, Any]],
    scenario: str,
    condition: str,
    candidate: int,
    fresh_execution: int,
    stale_execution: int,
) -> None:
    run = _launch(isolated_workspace, reports, scenario, condition)
    default = _read(reports, "metrics", run["run_dir"])
    enabled = _read(reports, "metrics", run["run_dir"], "--sensing-freshness")
    assert enabled["metrics_sha256"] == canonical_sha256(enabled["metrics"])
    guarded = enabled["metrics"]["guarded_review"].copy()
    measurement = guarded.pop("sensing_freshness")
    assert guarded == default["metrics"]["guarded_review"]
    assert measurement["metric_id"] == "CAL-006"
    _check_stage(measurement["candidate"], candidate, 0)
    _check_stage(measurement["execution"], fresh_execution, stale_execution)
    if candidate:
        raw = Path(run["run_dir"]) / "raw/events.jsonl"
        rows = [json.loads(line) for line in raw.read_bytes().splitlines()]
        decision = next(
            row
            for row in rows
            if row["outcome"] == "proposed" and row["event_type"] == "baseline_decision"
        )
        pending = next(row for row in rows if row["outcome"] == "pending")
        executed = next(row for row in rows if row["outcome"] == "executed")
        (candidate_row,) = measurement["candidate"]["actions"]
        (execution_row,) = measurement["execution"]["actions"]
        assert candidate_row["action_id"] == execution_row["referral_id"] == pending["action_id"]
        assert (
            execution_row["action_id"]
            == json.loads(pending["payload_json"])["binding"]["action"]["id"]
        )
        assert execution_row["execution_id"] == json.loads(executed["payload_json"])["execution_id"]
        prefix = json.loads(decision["payload_json"])["selection"]["prefix_trace_sha256"]
        assert (
            candidate_row["prefix_trace_sha256"] == execution_row["prefix_trace_sha256"] == prefix
        )
        assert (candidate_row["stage_tick"], execution_row["stage_tick"]) == (3, 5)
        assert (candidate_row["current_age_ticks"], execution_row["current_age_ticks"]) == (1, 3)
        assert (candidate_row["reference_age_ticks"], execution_row["reference_age_ticks"]) == (
            (2, 4) if condition == "contextual" else (None, None)
        )


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("source", "replacement", "outcome", "executions"),
    [
        ("response: approve", "response: deny", "denied", 0),
        ("rollback: false", "rollback: true", "rolled_back", 1),
    ],
)
def test_denial_and_restoration_preserve_the_observed_execution_denominator(
    isolated_workspace: IsolatedWorkspace,
    reports: list[dict[str, Any]],
    source: str,
    replacement: str,
    outcome: str,
    executions: int,
) -> None:
    ws = isolated_workspace
    fixture = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    text = fixture.read_text(encoding="utf-8")
    assert text.count(source) == 1
    fixture.write_text(text.replace(source, replacement), encoding="utf-8")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "-qm",
            "pin review lifecycle",
            "--",
            str(fixture.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    run = _launch(ws, reports, "nominal", "contextual")
    guarded = _read(reports, "metrics", run["run_dir"], "--sensing-freshness")["metrics"][
        "guarded_review"
    ]
    assert guarded["outcome_event_counts"][outcome] == 1
    _check_stage(guarded["sensing_freshness"]["candidate"], 1, 0)
    _check_stage(guarded["sensing_freshness"]["execution"], 0, executions)


@pytest.mark.reproducibility
def test_planned_and_registered_reads_match_episode_and_leave_unlaunched_null(
    isolated_workspace: IsolatedWorkspace, reports: list[dict[str, Any]]
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    defender = ws.config_root / "defenders/sensing_contextual.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file=defender.name
    )
    attempts = [
        {"attempt_id": name, "invocation_id": f"{i:032x}", "seed": 424242}
        for i, name in enumerate(("launched", "unlaunched"), start=1)
    ]
    expected = {
        "scenario": "diagnostic_sensing_nominal",
        "condition": "sensing_contextual_v1",
        "code_commit": git_commit(ws.repo_root),
        "config_sha256": hashes["config_hash"],
        "seed_registry_sha256": hashes["seed_registry_hash"],
        "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
    }
    plan = {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            {**a, "cell_id": "nominal", "comparison_mode": "controlled", "expected": expected}
            for a in attempts
        ],
    }
    register = {"format": "pacd-attempt-register-v1", "attempts": attempts}
    plan_path, register_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    register_path.write_bytes(canonical_json_bytes(register))
    binding = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    run = _launch(
        ws,
        reports,
        "nominal",
        "contextual",
        *binding,
        "--invocation-id",
        str(attempts[0]["invocation_id"]),
    )
    episode = _read(reports, "metrics", run["run_dir"], "--sensing-freshness")
    for args in (
        binding,
        ["--register", str(register_path), "--register-sha256", canonical_sha256(register)],
    ):
        report = _read(reports, "metrics", *args, "--sensing-freshness")
        completed, absent = report["attempts"]
        assert completed["status"] == "COMPLETED" and completed["metrics"] == episode["metrics"]
        assert completed["metrics_sha256"] == episode["metrics_sha256"]
        assert (
            absent["status"] == "INCOMPLETE"
            and absent["metrics"] is absent["metrics_sha256"] is None
        )


@pytest.mark.negative
def test_receipted_false_reference_time_withholds_freshness(
    isolated_workspace: IsolatedWorkspace,
    reports: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace

    def false_reference(
        condition: str, prefix: tuple[EvidenceReading, ...], cost: float, budget: float
    ) -> tuple[str, dict[str, object]]:
        reason, detail = select_profile(condition, prefix, cost, budget)
        if reason == "proposed":
            detail["reference_measured_tick"] = prefix[-1].measured_tick
        return reason, detail

    monkeypatch.setattr(harness, "select_profile", false_reference)
    run = _launch(ws, reports, "nominal", "contextual")
    run_dir = Path(run["run_dir"])
    receipt = verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=run_dir,
        manifest=json.loads((run_dir / "manifest.json").read_bytes()),
    )
    assert receipt.identity_assured
    rejected = _read(reports, "metrics", run["run_dir"], "--sensing-freshness", code=1)
    assert rejected["status"] == "INVALID" and not rejected["semantic_content_valid"]
    assert "metrics" not in rejected
    register = {
        "format": "pacd-attempt-register-v1",
        "attempts": [
            {
                "attempt_id": "false-reference",
                "invocation_id": run["invocation_id"],
                "seed": 424242,
            },
        ],
    }
    path = ws.root / "register.json"
    path.write_bytes(canonical_json_bytes(register))
    report = _read(reports, "metrics", "--register", str(path), "--sensing-freshness")
    (attempt,) = report["attempts"]
    assert (
        attempt["status"] == "INVALID" and attempt["metrics"] is attempt["metrics_sha256"] is None
    )


@pytest.mark.reproducibility
def test_opt_in_keeps_legacy_sensing_metrics_unchanged(
    isolated_workspace: IsolatedWorkspace, reports: list[dict[str, Any]]
) -> None:
    run = _launch(isolated_workspace, reports, "nominal", "fixed")
    default = _read(reports, "metrics", run["run_dir"])
    assert "sensing_freshness" not in default["metrics"]["guarded_review"]
    assert _read(reports, "metrics", run["run_dir"], "--sensing-freshness") == default

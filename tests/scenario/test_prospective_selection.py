"""Prospective profile selection, independent replay and guarded outcomes."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.comparison import RegisteredAttempt
from pacd_sim.evidence.context import EvidenceReading, evidence_trace
from pacd_sim.harness import run as harness
from pacd_sim.metrics.registered import AttemptRegister, registered_metrics
from pacd_sim.polymorphism.selection import select_profile
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.verify import verify_run_with_summary


def _launch(ws: IsolatedWorkspace, scenario: str, condition: str) -> harness.RunResult:
    _, _, seeds, _, metrics = controlled_config_files(ws.config_root)
    return harness._run_diagnostic_in_process(
        ws.config_root / f"scenarios/diagnostic_sensing_{scenario}.yaml",
        ws.config_root / "policies/diagnostic_sensing.yaml",
        seeds,
        ws.output_root,
        workspace_root=ws.root,
        repo_root=ws.repo_root,
        seed=424242,
        baseline_path=ws.config_root / f"defenders/sensing_{condition}.yaml",
        metric_path=metrics,
    )


def _rows(run_dir: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (run_dir / "raw/events.jsonl").read_bytes().splitlines()]
    for row in rows:
        row["payload"] = json.loads(row["payload_json"])
    return rows


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("scenario", "condition", "reason", "benefit"),
    [
        ("nominal", "contextual", "proposed", 0.675),
        ("costly", "contextual", "no_positive_gain", 0.675),
        ("delayed", "contextual", "stale_evidence", None),
        ("nominal", "scheduled", "proposed", None),
        ("costly", "scheduled", "proposed", None),
        ("delayed", "scheduled", "stale_evidence", None),
    ],
)
def test_third_delivery_uses_only_its_verified_prefix_and_governed_opportunity(
    isolated_workspace: IsolatedWorkspace,
    scenario: str,
    condition: str,
    reason: str,
    benefit: float | None,
) -> None:
    ws = isolated_workspace
    run = _launch(ws, scenario, condition)
    verification, material = verify_run_with_summary(
        run.run_dir, ws.root, repo_root=ws.repo_root, include_evidence_readings=True
    )
    assert verification.valid and material is not None and material.guarded_review is not None, (
        verification.errors
    )
    rows = _rows(run.run_dir)
    decisions = [r for r in rows if r["event_type"] == "baseline_decision"]
    assert [r["outcome"] for r in decisions] == [
        "outside_opportunity",
        "outside_opportunity",
        reason,
        "outside_opportunity",
    ]
    for ordinal, row in enumerate(decisions, 1):
        detail = row["payload"]["selection"]
        prefix = evidence_trace(material.evidence_readings[:ordinal])
        assert detail["prefix_trace_sha256"] == prefix["trace_sha256"]
        assert row["payload"]["opportunity"] is (ordinal == 3)
        assert detail["selection_reason"] == row["outcome"]
        assert detail["age_ticks"] == (4 if scenario == "delayed" else 1)
        assert detail["eligible_distinct_source_count"] == (0 if scenario == "delayed" else 1)
        if ordinal != 3:
            assert detail["selected_profile"] is None and detail["utility"] is None
    choice = decisions[2]["payload"]["selection"]
    switched = reason == "proposed"
    assert choice["selected_profile"] == ("alternate" if switched else "default")
    cost = 0.95 if scenario == "costly" else 0.25
    if benefit is None:
        assert choice["benefit"] is None and choice["utility"] is None
        assert choice["reference_measured_tick"] is None and choice["reference_signal"] is None
    else:
        assert choice["reference_measured_tick"] == 1 and choice["reference_signal"] == 0.9
        assert choice["benefit"] == pytest.approx(benefit)
        assert choice["utility"] == pytest.approx(benefit - cost)
    lifecycle = [r for r in rows if r["event_type"] == "guarded_review"]
    if switched:
        assert [(r["tick"], r["outcome"]) for r in lifecycle] == [
            (3, "pending"),
            (5, "approved"),
            (5, "executed"),
            (5, "verified"),
            (5, "mission_effect"),
        ]
    else:
        assert not lifecycle
    assert [r.signal for r in material.evidence_readings] == [
        0.9,
        0.9,
        0.9,
        0.86 if switched else 0.9,
    ]
    metrics = material.guarded_review["sensing_operator"]
    assert isinstance(metrics, dict)
    assert metrics["switch_cost_spent"] == (cost if switched else 0)
    assert metrics["alternate_profile_ticks"] == (3 if switched else 0)


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("old", "new", "reason", "terminal"),
    [
        ("tick: 2\n    kind:", "tick: 1\n    kind:", "insufficient_history", None),
        ("switch_cost: 0.25", "switch_cost: 0.675", "no_positive_gain", None),
        ("budget: 1.0", "budget: 0.0", "over_budget", None),
        ("response: approve", "response: deny", "proposed", "denied"),
        ("rollback: false", "rollback: true", "proposed", "rolled_back"),
    ],
)
def test_safe_fallback_and_review_outcomes_keep_the_observed_default(
    isolated_workspace: IsolatedWorkspace, old: str, new: str, reason: str, terminal: str | None
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    data = scenario.read_text(encoding="utf-8")
    assert data.count(old) == 1
    scenario.write_text(data.replace(old, new), encoding="utf-8")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "-qm",
            "pin prospective choice fixture",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    run = _launch(ws, "nominal", "contextual")
    verification, material = verify_run_with_summary(
        run.run_dir, ws.root, repo_root=ws.repo_root, include_evidence_readings=True
    )
    assert verification.valid and material is not None and material.guarded_review is not None, (
        verification.errors
    )
    rows = _rows(run.run_dir)
    assert [r["outcome"] for r in rows if r["event_type"] == "baseline_decision"][2] == reason
    lifecycle = [r["outcome"] for r in rows if r["event_type"] == "guarded_review"]
    if terminal is None:
        assert not lifecycle
    else:
        assert terminal in lifecycle
    assert all(r.signal == 0.9 for r in material.evidence_readings)
    metrics = material.guarded_review["sensing_operator"]
    assert isinstance(metrics, dict)
    assert metrics["alternate_profile_ticks"] == 0
    assert metrics["switch_cost_spent"] == (0.25 if terminal == "rolled_back" else 0)


@pytest.mark.negative
@pytest.mark.parametrize("fault", ["prefix", "utility", "choice"])
def test_semantic_replay_withholds_receipted_incorrect_selection(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    ws = isolated_workspace

    def corrupt(
        policy: str, prefix: tuple[EvidenceReading, ...], cost: float, budget: float
    ) -> tuple[str, dict[str, object]]:
        reason, detail = select_profile(policy, prefix, cost, budget)
        if len(prefix) == 3:
            if fault == "prefix":
                detail["prefix_trace_sha256"] = evidence_trace(prefix[:2])["trace_sha256"]
            elif fault == "utility":
                detail["utility"] = 0.89
            else:
                reason = "no_positive_gain"
                detail.update(selection_reason=reason, selected_profile="default", utility=0.0)
        return reason, detail

    monkeypatch.setattr(harness, "select_profile", corrupt)
    run = _launch(ws, "nominal", "contextual")
    manifest = json.loads((run.run_dir / "manifest.json").read_bytes())
    assert verify_execution_receipt(
        workspace_root=ws.root, run_dir=run.run_dir, manifest=manifest
    ).identity_assured
    result, material = verify_run_with_summary(
        run.run_dir, ws.root, repo_root=ws.repo_root, include_evidence_readings=True
    )
    assert not result.semantic_content_valid and material is None
    register = AttemptRegister(
        format="pacd-attempt-register-v1",
        attempts=(
            RegisteredAttempt(attempt_id="choice", invocation_id=run.invocation_id, seed=run.seed),
        ),
    )
    path = ws.root / "register.json"
    path.write_bytes(canonical_json_bytes(register))
    report = registered_metrics(path, ws.root, ws.repo_root, canonical_sha256(register))
    attempts = report["attempts"]
    assert isinstance(attempts, list) and len(attempts) == 1
    assert attempts[0]["status"] == "INVALID" and attempts[0]["metrics"] is None

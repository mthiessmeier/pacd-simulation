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
from pacd_sim.reproducibility.evidence_validation import _expected_profile_selection
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.verify import verify_run_with_summary


@pytest.mark.parametrize("condition", ["sensing_contextual_v1", "sensing_scheduled_v1"])
def test_replay_handles_repeated_delivery_and_unknown_subject(condition: str) -> None:
    first = EvidenceReading(
        observation_key=1,
        source_key=1,
        subject_id="session",
        measured_tick=1,
        delivered_tick=2,
        signal=0.9,
    )
    second = first.model_copy(update={"observation_key": 2})
    late = second.model_copy(update={"measured_tick": 5, "delivered_tick": 6})
    unknown = late.model_copy(update={"observation_key": 3, "subject_id": "synthetic-unknown"})
    for prefix, reason, age in (
        ((first, second, first), "duplicate_evidence", 1),
        ((first, late, first), "stale_evidence", 5),
        ((first, second, unknown), "no_subject", 1),
    ):
        observed = _expected_profile_selection(condition, list(prefix), 0.25, 1.0)
        assert observed[0] == reason and observed[1]["age_ticks"] == age
        assert observed == select_profile(condition, prefix, 0.25, 1.0)


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


def _pin_nominal_fixture(ws: IsolatedWorkspace, changes: dict[str, str]) -> None:
    scenario = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    data = scenario.read_text(encoding="utf-8")
    for old, new in changes.items():
        assert data.count(old) == 1
        data = data.replace(old, new)
    scenario.write_text(data, encoding="utf-8")
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
    _pin_nominal_fixture(ws, {old: new})
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


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("signal", "cost", "reason", "margin"),
    [
        ("0.1", "0.07499999999999998", "proposed", "1/50000000000000000"),
        ("0.1", "0.075", "no_positive_gain", "0"),
        ("0.1", "0.07500000000000001", "no_positive_gain", "-1/100000000000000000"),
        ("0.7", "0.5249999999999999", "proposed", "1/10000000000000000"),
    ],
)
def test_exact_decimal_margin_controls_the_verified_switch(
    isolated_workspace: IsolatedWorkspace, signal: str, cost: str, reason: str, margin: str
) -> None:
    ws = isolated_workspace
    _pin_nominal_fixture(
        ws,
        {
            "matched_signal_mean: 0.86": f"matched_signal_mean: {signal}",
            "switch_cost: 0.25": f"switch_cost: {cost}",
        },
    )
    run = _launch(ws, "nominal", "contextual")
    verified, material = verify_run_with_summary(run.run_dir, ws.root, repo_root=ws.repo_root)
    assert verified.valid and material is not None and material.guarded_review is not None
    row = next(
        r
        for r in _rows(run.run_dir)
        if r["event_type"] == "baseline_decision" and r["payload"]["opportunity"]
    )
    assert row["outcome"] == reason and row["payload"]["selection"]["utility_exact"] == margin
    operator = material.guarded_review["sensing_operator"]
    assert isinstance(operator, dict)
    assert operator["verified_switch_count"] == int(reason == "proposed")


@pytest.mark.negative
@pytest.mark.parametrize("fault", ["prefix", "utility", "choice", "rounded_tie", "exact_margin"])
def test_semantic_replay_withholds_receipted_incorrect_selection(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    ws = isolated_workspace
    if fault == "rounded_tie":
        _pin_nominal_fixture(
            ws,
            {
                "matched_signal_mean: 0.86": "matched_signal_mean: 0.1",
                "switch_cost: 0.25": "switch_cost: 0.075",
            },
        )

    def corrupt(
        policy: str, prefix: tuple[EvidenceReading, ...], cost: float, budget: float
    ) -> tuple[str, dict[str, object]]:
        reason, detail = select_profile(policy, prefix, cost, budget)
        if len(prefix) == 3:
            if fault == "prefix":
                detail["prefix_trace_sha256"] = evidence_trace(prefix[:2])["trace_sha256"]
            elif fault == "utility":
                detail["utility"] = 0.89
            elif fault == "exact_margin":
                detail["utility_exact"] = "1/3"
            elif fault == "rounded_tie":
                reason = "proposed"
                detail.update(
                    selection_reason=reason, selected_profile="alternate", utility=0.1 * 0.75 - cost
                )
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

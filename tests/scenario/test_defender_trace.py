"""Delivery-time memory and authenticated replay of synthetic PACD review proposals."""

from math import nextafter
from typing import Any

import pytest
from conftest import DiagnosticRuns

from pacd_sim import cli
from pacd_sim.defenders.observations import BaselineObservation, ReviewProposal
from pacd_sim.defenders.pacd.corroboration import CorroboratedReviewPlanner
from pacd_sim.reproducibility import verify
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.receipts import ReceiptVerification


def reading(tick: int, subject: str | None = "alpha", signal: float = 0.75) -> BaselineObservation:
    return BaselineObservation(tick=tick, subject_id=subject, signal=signal)


def test_planner_records_only_one_referral_per_sustained_subject_episode() -> None:
    planner = CorroboratedReviewPlanner()
    delivered = [
        reading(0),
        reading(0),
        reading(1, "beta"),
        reading(3),
        reading(3),
        reading(6),
        reading(7, signal=nextafter(0.75, 0.0)),
        reading(7),
        reading(8, "beta"),
        reading(9),
        reading(13),
    ]
    decisions = [planner.observe(item) for item in delivered]
    assert [(d.outcome, d.previous_elevated_tick) for d in decisions] == [
        ("awaiting_corroboration", None),
        ("awaiting_corroboration", 0),
        ("awaiting_corroboration", None),
        ("proposed", 0),
        ("already_referred", 3),
        ("already_referred", 3),
        ("below_threshold", 6),
        ("awaiting_corroboration", None),
        ("awaiting_corroboration", None),
        ("proposed", 7),
        ("awaiting_corroboration", None),
    ]
    assert [d.proposal for d in decisions if d.proposal] == [ReviewProposal(target_id="alpha")] * 2
    assert [d.observation for d in decisions] == delivered


@pytest.mark.parametrize("subject", [None, "synthetic-unknown"])
def test_unidentified_readings_cannot_confirm_or_clear_another_subject(subject: str | None) -> None:
    planner = CorroboratedReviewPlanner()
    planner.observe(reading(2))
    for signal in (0.0, 1.0):
        step = planner.observe(reading(3, subject, signal))
        assert (step.outcome, step.previous_elevated_tick, step.proposal) == (
            "no_subject",
            None,
            None,
        )
    assert planner.observe(reading(5)).outcome == "proposed"


def test_late_input_is_rejected_before_memory_can_change() -> None:
    planner = CorroboratedReviewPlanner()
    planner.observe(reading(4))
    with pytest.raises(ValueError, match="nondecreasing"):
        planner.observe(reading(3, signal=0.0))
    assert planner.observe(reading(6)).outcome == "proposed"
    assert CorroboratedReviewPlanner().observe(reading(6)).outcome == "awaiting_corroboration"


@pytest.mark.reproducibility
def test_cli_binds_trace_to_verified_readings_and_resets_per_run(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    traces = []
    for run in (
        diagnostic_runs.same_seed_a,
        diagnostic_runs.same_seed_b,
        diagnostic_runs.different_seed,
    ):
        assert cli.main(["defender-trace", str(run.run_dir)]) == 0
        report = output[-1]
        assert report["valid"] and report["execution_identity_assured"]
        assert report["raw_semantic_hash"] == run.raw_semantic_hash
        trace = report["defender_trace"]
        assert trace["observation_count"] == 2 and trace["proposal_count"] == 0
        assert trace["mode"] == "retrospective_proposals"
        assert [step["outcome"] for step in trace["decisions"]] == [
            "below_threshold",
            "awaiting_corroboration",
        ]
        assert trace["observation_sha256"] == canonical_sha256(
            [step["observation"] for step in trace["decisions"]]
        )
        assert trace["trace_sha256"] == canonical_sha256(
            {k: v for k, v in trace.items() if k != "trace_sha256"}
        )
        traces.append(trace)
    assert traces[0] == traces[1]
    assert traces[2]["trace_sha256"] != traces[0]["trace_sha256"]


@pytest.mark.negative
def test_failed_receipt_withholds_every_planner_decision(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    monkeypatch.setattr(
        verify,
        "verify_execution_receipt",
        lambda **_: ReceiptVerification(False, ("missing receipt",), None),
    )
    monkeypatch.setattr(
        cli, "_defender_trace", lambda _: pytest.fail("Unverified observations reached planner")
    )
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    assert cli.main(["defender-trace", str(diagnostic_runs.same_seed_a.run_dir)]) == 1
    assert output[-1]["status"] == "INVALID" and "defender_trace" not in output[-1]

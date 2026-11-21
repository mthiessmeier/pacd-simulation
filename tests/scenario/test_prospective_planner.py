"""The PACD planner sees one delivery at a time and forwards only its actual proposals."""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim import cli
from pacd_sim.actions.models import DefensiveAction
from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.defenders.pacd.corroboration import POLICY, CorroboratedReviewPlanner, ReviewStep
from pacd_sim.engine.scheduler import ScheduledEvent
from pacd_sim.governance.governor import GovernanceContext, PolicyDecision, SafetyGovernor
from pacd_sim.harness.run import (
    ConfigurationError,
    _run_diagnostic_in_process,
    validate_diagnostic_configuration_files,
)
from pacd_sim.hypotheses.update import BeliefState
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import PolicyDisposition
from pacd_sim.state.snapshot import StateSnapshot
from pacd_sim.telemetry.generator import Observation, SyntheticTelemetryGenerator


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("identity_smoke", [(2, "below_threshold"), (3, "awaiting_corroboration")]),
        (
            "maintenance_window",
            [(5, "below_threshold"), (8, "awaiting_corroboration"), (11, "below_threshold")],
        ),
        (
            "repeated_readings",
            [
                (2, "below_threshold"),
                (3, "awaiting_corroboration"),
                (3, "awaiting_corroboration"),
                (4, "proposed"),
                (5, "already_referred"),
            ],
        ),
    ],
)
def test_live_planner_decisions_and_governor_order_match_verified_cli(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    expected: list[tuple[int, str]],
) -> None:
    ws = isolated_workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    monkeypatch.setattr(cli, "run_diagnostic", _run_diagnostic_in_process)
    reports: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", reports.append)
    events: list[tuple[str, int]] = []
    original_generate = SyntheticTelemetryGenerator.generate
    original_observe = CorroboratedReviewPlanner.observe
    original_evaluate = SafetyGovernor.evaluate

    def generate(sensor: SyntheticTelemetryGenerator, event: ScheduledEvent) -> Observation:
        reading = original_generate(sensor, event)
        assert reading is not None
        events.append(("sensor", reading.tick))
        return reading

    def observe(planner: CorroboratedReviewPlanner, reading: BaselineObservation) -> ReviewStep:
        assert set(reading.model_dump()) == {"tick", "subject_id", "signal"}
        events.append(("planner", reading.tick))
        return original_observe(planner, reading)

    def evaluate(
        governor: SafetyGovernor,
        action: DefensiveAction,
        belief_state: BeliefState | None = None,
        mission_state: StateSnapshot | None = None,
        context: GovernanceContext | None = None,
    ) -> PolicyDecision:
        if action.id.startswith("action-pacd-review-"):
            assert context is not None and mission_state is not None and belief_state is not None
            events.append(("governor", action.tick))
        return original_evaluate(governor, action, belief_state, mission_state, context)

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("A held planner request reached dispatch or another defender was called")

    with monkeypatch.context() as live:
        live.setattr(SyntheticTelemetryGenerator, "generate", generate)
        live.setattr(CorroboratedReviewPlanner, "observe", observe)
        live.setattr(SafetyGovernor, "evaluate", evaluate)
        live.setattr("pacd_sim.harness.run.static_review_candidate", unexpected)
        live.setattr("pacd_sim.harness.run.DiagnosticPACDDefender.decide", unexpected)
        live.setattr("pacd_sim.harness.run.SimulatedExecutionBroker.execute", unexpected)
        assert (
            cli.main(
                [
                    "diagnostic",
                    "--scenario",
                    str(ws.config_root / f"scenarios/diagnostic_{fixture}.yaml"),
                    "--baseline",
                    str(ws.config_root / "defenders/pacd_corroborated_review.yaml"),
                    "--seed",
                    "424242",
                ]
            )
            == 0
        )
    expected_calls = []
    for tick, outcome in expected:
        expected_calls.extend([("sensor", tick), ("planner", tick)])
        if outcome == "proposed":
            expected_calls.append(("governor", tick))
    assert events == expected_calls
    run = Path(reports[-1]["run_dir"])
    assert cli.main(["verify", str(run), "--show-event-sequence"]) == 0
    assert reports[-1]["execution_identity_assured"]
    assert cli.main(["defender-trace", str(run)]) == 0
    steps = reports[-1]["defender_trace"]["decisions"]
    rows = [json.loads(line) for line in (run / "raw/events.jsonl").read_bytes().splitlines()]
    decisions = [row for row in rows if row["event_type"] == "defender_decision"]
    assert [(row["tick"], row["outcome"]) for row in decisions] == expected
    for i, (row, step) in enumerate(zip(decisions, steps, strict=True), 1):
        payload = json.loads(row["payload_json"])
        assert payload["policy"] == POLICY and row["outcome"] == step["outcome"]
        assert payload["previous_elevated_tick"] == step["previous_elevated_tick"]
        assert payload["observation_sha256"] == canonical_sha256(step["observation"])
        assert payload["candidate_action_id"] == (
            f"action-pacd-review-{i}" if step["proposal"] else None
        )
    action_rows = [row for row in rows if row["action_id"]]
    if fixture == "repeated_readings":
        assert [row["event_type"] for row in action_rows] == [
            "candidate_action",
            "safety_decision",
            "verification",
            "audit",
        ]
        assert {row["action_id"] for row in action_rows} == {"action-pacd-review-4"}
        candidate, decision, held, _ = action_rows
        assert json.loads(candidate["payload_json"])["proposer"] == POLICY
        assert (decision["disposition"], held["outcome"]) == ("ESCALATE", "not_executed")
        withheld = json.loads(held["payload_json"])
        assert (
            withheld["state_before_digest"]
            == withheld["state_after_digest"]
            == json.loads(decision["payload_json"])["state_digest"]
        )
    else:
        assert action_rows == []


@pytest.mark.negative
def test_unexpected_planner_approval_fails_before_dispatch(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace
    _, policy, seeds, _, metrics = controlled_config_files(ws.config_root)
    evaluate = SafetyGovernor.evaluate

    def unexpected_approval(
        governor: SafetyGovernor, action: DefensiveAction, **kwargs: Any
    ) -> PolicyDecision:
        decision = evaluate(governor, action, **kwargs)
        if action.id.startswith("action-pacd-review-"):
            return decision.model_copy(update={"disposition": PolicyDisposition.APPROVE})
        return decision

    monkeypatch.setattr(SafetyGovernor, "evaluate", unexpected_approval)
    monkeypatch.setattr(
        "pacd_sim.harness.run.SimulatedExecutionBroker.execute",
        lambda *a: pytest.fail("Unexpected dispatch"),
    )
    with pytest.raises(RuntimeError, match="Human review requires a withheld execution"):
        _run_diagnostic_in_process(
            ws.config_root / "scenarios/diagnostic_repeated_readings.yaml",
            policy,
            seeds,
            ws.output_root,
            repo_root=ws.repo_root,
            workspace_root=ws.root,
            metric_path=metrics,
            baseline_path=ws.config_root / "defenders/pacd_corroborated_review.yaml",
        )


@pytest.mark.negative
@pytest.mark.parametrize(
    ("old", "new"), [(POLICY, "unregistered_planner"), ("require_human_review", "none")]
)
def test_doctor_rejects_mislabeled_planner_config(
    isolated_workspace: IsolatedWorkspace,
    old: str,
    new: str,
) -> None:
    path = isolated_workspace.config_root / "defenders/pacd_corroborated_review.yaml"
    path.write_text(path.read_text().replace(old, new))
    with pytest.raises(ConfigurationError):
        validate_diagnostic_configuration_files(isolated_workspace.repo_root)

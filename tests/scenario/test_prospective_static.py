"""Live decisions must be made and governed before the next synthetic reading."""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim import cli
from pacd_sim.defenders.base import BaselineObservation
from pacd_sim.defenders.baselines.static import ReviewProposal, propose_review
from pacd_sim.engine.scheduler import ScheduledEvent
from pacd_sim.harness import static_review
from pacd_sim.harness.run import (
    ConfigurationError,
    _run_diagnostic_in_process,
    validate_diagnostic_configuration_files,
)
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.verify import verify_run
from pacd_sim.telemetry.generator import Observation, SyntheticTelemetryGenerator


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("fixture", "ticks"), [("identity_smoke", [2, 3]), ("maintenance_window", [5, 8, 11])]
)
def test_governed_review_replays_from_the_current_sensor_reading(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    ticks: list[int],
) -> None:
    workspace = isolated_workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    monkeypatch.setattr(cli, "run_diagnostic", _run_diagnostic_in_process)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda data, **_: output.append(data))
    seen: list[tuple[str, int]] = []
    original_generate = SyntheticTelemetryGenerator.generate

    def generate(sensor: SyntheticTelemetryGenerator, event: ScheduledEvent) -> Observation | None:
        observation = original_generate(sensor, event)
        assert observation is not None
        seen.append(("sensor", observation.tick))
        return observation

    def decide(reading: BaselineObservation) -> ReviewProposal | None:
        seen.append(("decision", reading.tick))
        return propose_review(reading)

    def unexpected_call(*args: object, **kwargs: object) -> None:
        pytest.fail("Static review called the PACD defender or dispatched to the broker")

    def invoke(*args: str) -> dict[str, Any]:
        assert cli.main(list(args)) == 0, output[-1:]
        return output[-1]

    with monkeypatch.context() as live:
        live.setattr(SyntheticTelemetryGenerator, "generate", generate)
        live.setattr(static_review, "propose_review", decide)
        live.setattr("pacd_sim.harness.run.DiagnosticPACDDefender.decide", unexpected_call)
        live.setattr("pacd_sim.harness.run.SimulatedExecutionBroker.execute", unexpected_call)
        result = invoke(
            "diagnostic",
            "--scenario",
            str(workspace.config_root / f"scenarios/diagnostic_{fixture}.yaml"),
            "--baseline",
            str(workspace.config_root / "defenders/static_review.yaml"),
            "--seed",
            "424242",
        )
    assert seen == [(stage, tick) for tick in ticks for stage in ("sensor", "decision")]
    run = Path(result["run_dir"])
    verified = invoke("verify", str(run), "--show-event-sequence")
    assert verified["valid"] and verified["execution_identity_assured"]
    replay = invoke("baseline", str(run))["baseline"]
    rows = [json.loads(line) for line in (run / "raw/events.jsonl").read_text().splitlines()]
    decisions = [row for row in rows if row["event_type"] == "baseline_decision"]
    assert [row["tick"] for row in decisions] == ticks
    for row, step in zip(decisions, replay["decisions"], strict=True):
        payload = json.loads(row["payload_json"])
        assert payload["observation_sha256"] == canonical_sha256(step["observation"])
        assert row["outcome"] == ("proposed" if step["proposal"] else "abstained")
        assert payload["candidate_action_id"] == (
            "action-static-review-2" if step["proposal"] else None
        )
    assert replay["proposal_count"] == 1
    action_rows = [row for row in rows if row["action_id"]]
    assert [row["event_type"] for row in action_rows] == [
        "candidate_action",
        "safety_decision",
        "verification",
        "audit",
    ]
    assert {row["action_id"] for row in action_rows} == {"action-static-review-2"}
    _, safety, verification, _ = action_rows
    assert (safety["disposition"], verification["outcome"]) == ("ESCALATE", "not_executed")
    withheld = json.loads(verification["payload_json"])
    assert withheld["state_before_digest"] == withheld["state_after_digest"]
    assert withheld["state_after_digest"] == json.loads(safety["payload_json"])["state_digest"]


@pytest.mark.scenario
@pytest.mark.parametrize(("signal", "expected_count"), [(0.0, 0), (0.75, 3)])
def test_every_reading_can_abstain_or_request_review(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    signal: float,
    expected_count: int,
) -> None:
    # Clamp the synthetic sensor for both production and reconstruction. The
    # benign and indicator labels stay intact as the observable signal changes.
    original = SyntheticTelemetryGenerator.generate

    def clamped(sensor: SyntheticTelemetryGenerator, event: ScheduledEvent) -> Observation:
        reading = original(sensor, event)
        assert reading is not None
        return reading.model_copy(update={"signal": signal})

    monkeypatch.setattr(SyntheticTelemetryGenerator, "generate", clamped)
    workspace = isolated_workspace
    _, policy, seeds, _, metrics = controlled_config_files(workspace.config_root)
    run = _run_diagnostic_in_process(
        workspace.config_root / "scenarios/diagnostic_maintenance_window.yaml",
        policy,
        seeds,
        workspace.output_root,
        baseline_path=workspace.config_root / "defenders/static_review.yaml",
        metric_path=metrics,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
    )
    verification = verify_run(run.run_dir, workspace.root, repo_root=workspace.repo_root)
    assert verification.valid, verification.errors
    rows = [
        json.loads(line) for line in (run.run_dir / "raw/events.jsonl").read_text().splitlines()
    ]
    decisions = [row for row in rows if row["event_type"] == "baseline_decision"]
    requests = [row for row in rows if row["event_type"] == "safety_decision"]
    assert len(decisions) == 3
    assert sum(row["outcome"] == "proposed" for row in decisions) == expected_count
    assert [row["action_id"] for row in requests] == [
        f"action-static-review-{i + 1}" for i in range(expected_count)
    ]
    assert all(row["disposition"] == "ESCALATE" for row in requests)
    assert all(row["event_type"] != "simulated_execution" for row in rows)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("old", "new"), [("require_human_review", "none"), ("static_signal_review_v1", "unknown")]
)
def test_doctor_rejects_mislabeled_static_config(
    isolated_workspace: IsolatedWorkspace, old: str, new: str
) -> None:
    config = isolated_workspace.config_root / "defenders/static_review.yaml"
    config.write_text(config.read_text().replace(old, new))
    with pytest.raises(ConfigurationError):
        validate_diagnostic_configuration_files(isolated_workspace.repo_root)

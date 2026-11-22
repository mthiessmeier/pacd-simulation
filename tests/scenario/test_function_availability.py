"""Read per-function availability from authenticated episode and comparison evidence."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.comparison import ComparisonPlan
from pacd_sim.constants import CRITICAL_OUTAGE_FILES, MISSION_RECOVERY_ROLLBACK_FILE
from pacd_sim.harness import run as harness
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewEvent
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit

from .test_approval_burden import Command


def _launch(ws: IsolatedWorkspace, filename: str, defender: str) -> list[str]:
    return [
        "diagnostic",
        "--scenario",
        str(ws.config_root / "scenarios" / filename),
        "--baseline",
        str(ws.config_root / "defenders" / defender),
        "--seed",
        "424242",
    ]


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("filename", "defender", "available_a"),
    [
        (CRITICAL_OUTAGE_FILES[0], "static_review.yaml", 6),
        (CRITICAL_OUTAGE_FILES[1], "static_review.yaml", 6),
        (CRITICAL_OUTAGE_FILES[0], "pacd_corroborated_review.yaml", 8),
        (MISSION_RECOVERY_ROLLBACK_FILE, "static_review.yaml", 8),
    ],
)
def test_all_functions_have_a_clock_even_when_only_one_is_designated(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    filename: str,
    defender: str,
    available_a: int,
) -> None:
    run = command(*_launch(isolated_workspace, filename, defender))["run_dir"]
    default = command("metrics", run)
    assert "function_availability" not in default["metrics"]["guarded_review"]
    legacy_flags = ["--mission-impact", "--critical-outage", "--mission-recovery"]
    earlier = command("metrics", run, *legacy_flags)
    measured = command("metrics", run, *legacy_flags, "--function-availability")
    assert measured["metrics_sha256"] == canonical_sha256(measured["metrics"])
    report = measured["metrics"]["guarded_review"]
    availability = report.pop("function_availability")
    assert canonical_json_bytes(measured["metrics"]) == canonical_json_bytes(earlier["metrics"])
    assert availability["metric_id"] == "MIS-001" and availability["horizon_ticks"] == 8
    assert availability["per_mission"] == [
        {
            "mission_id": mission,
            "available_ticks": ticks,
            "possible_ticks": 8,
            "availability_fraction": ticks / 8,
        }
        for mission, ticks in (("mission-a", available_a), ("mission-b", 8))
    ]
    total_up = available_a + 8
    assert availability["available_function_ticks"] == total_up
    assert availability["possible_function_ticks"] == 16
    assert availability["availability_fraction"] == total_up / 16
    legacy = default["metrics"]["guarded_review"]["mission_availability"]
    assert legacy["possible_mission_ticks"] - legacy["unavailable_mission_ticks"] == total_up
    weighted = report["mission_impact"]["per_mission"]
    for up, loss in zip(availability["per_mission"], weighted, strict=True):
        assert up["mission_id"] == loss["mission_id"]
        assert up["available_ticks"] + loss["unavailable_ticks"] == up["possible_ticks"]
    assert command("metrics", run) == default


@pytest.mark.reproducibility
def test_pinned_availability_withholds_mistimed_and_missing_measurements(
    isolated_workspace: IsolatedWorkspace, command: Command, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / CRITICAL_OUTAGE_FILES[0]
    defender = "static_review.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file=defender
    )
    expected = {
        "scenario": scenario.stem,
        "condition": "static_signal_review_v1",
        "code_commit": git_commit(ws.repo_root),
        "config_sha256": hashes["config_hash"],
        "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
        "seed_registry_sha256": hashes["seed_registry_hash"],
    }
    slots = [
        {"attempt_id": name, "invocation_id": f"{i:032x}", "seed": 424242}
        for i, name in enumerate(("valid", "late", "failed", "timed-out", "unlaunched"), 1)
    ]
    plan = ComparisonPlan.model_validate(
        {
            "format": "pacd-development-comparison-plan-v1",
            "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
            "attempts": [
                dict(s, cell_id="availability", comparison_mode="controlled", expected=expected)
                for s in slots
            ],
        }
    )
    register = {"format": "pacd-attempt-register-v1", "attempts": slots}
    plan_path, reg_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    reg_path.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    reg_args = ["--register", str(reg_path), "--register-sha256", canonical_sha256(register)]
    launch = [*_launch(ws, scenario.name, defender), *plan_args, "--invocation-id"]
    valid = command(*launch, plan.attempts[0].invocation_id)["run_dir"]

    record = GuardedReviewQueue._record

    def later_loss(queue: GuardedReviewQueue, event: ReviewEvent) -> ReviewEvent:
        if event.outcome == "mission_effect" and event.payload["stage"] == "execution":
            event = replace(event, tick=event.tick + 1)
        return record(queue, event)

    with monkeypatch.context() as producer:
        producer.setattr(GuardedReviewQueue, "_record", later_loss)
        invalid = Path(command(*launch, plan.attempts[1].invocation_id)["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=invalid,
        manifest=json.loads((invalid / "manifest.json").read_bytes()),
    ).identity_assured
    rejected = command("metrics", str(invalid), "--function-availability", code=1)
    assert rejected["status"] == "INVALID" and "metrics" not in rejected

    for slot, reason in zip(
        plan.attempts[2:4],
        (RuntimeError("synthetic failure"), harness.DiagnosticTimeoutError("synthetic timeout")),
        strict=True,
    ):
        owned = harness._create_invocation_ownership(
            ws.output_root, ws.root, slot.seed, invocation_id=slot.invocation_id, plan=plan
        )
        harness._retain_interrupted_evidence(ws.root, owned, reason)

    direct = command("metrics", valid, "--function-availability")
    assert (
        direct["metrics"]["guarded_review"]["function_availability"]["available_function_ticks"]
        == 14
    )
    for inlet in (plan_args, reg_args):
        report = command("metrics", *inlet, "--function-availability")
        rows = report["attempts"]
        assert [row["status"] for row in rows] == [
            "COMPLETED",
            "INVALID",
            "FAILED",
            "TIMED_OUT",
            "INCOMPLETE",
        ]
        assert rows[0]["metrics"] == direct["metrics"]
        assert rows[0]["metrics_sha256"] == direct["metrics_sha256"]
        assert all(row["metrics"] is row["metrics_sha256"] is None for row in rows[1:])
        assert report["completion_fraction"]["value"] == 1 / 5


@pytest.mark.reproducibility
def test_unguarded_option_preserves_default_report_bytes(command: Command) -> None:
    run = command("diagnostic", "--seed", "424242")["run_dir"]
    previous = command("metrics", run)
    assert "guarded_review" not in previous["metrics"]
    assert canonical_json_bytes(command("metrics", run, "--function-availability")) == (
        canonical_json_bytes(previous)
    )

"""Measure and withhold mission recovery through the verified public readers."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.constants import MISSION_RECOVERY_ROLLBACK_FILE
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.harness import run as harness
from pacd_sim.oversight import guarded
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit

from .test_approval_burden import Command


@pytest.mark.scenario
def test_governed_recovery_fixture_differs_only_in_rollback_and_identity(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    root = isolated_workspace.config_root / "scenarios"
    reference = harness.load_yaml_config(root / "diagnostic_review_override_retain.yaml")
    recovery = harness.load_yaml_config(root / MISSION_RECOVERY_ROLLBACK_FILE)
    assert reference.pop("name") == "diagnostic_review_override_retain"
    assert recovery.pop("name") == "diagnostic_mission_recovery_rollback"
    for config, rollback in ((reference, False), (recovery, True)):
        review = config["guarded_review"]
        assert isinstance(review, dict) and review.pop("rollback") is rollback
    assert recovery == reference


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("filename", "has_outage", "restored"),
    [
        ("diagnostic_review_override_retain.yaml", True, False),
        (MISSION_RECOVERY_ROLLBACK_FILE, True, True),
        ("diagnostic_review_override_veto.yaml", False, False),
    ],
)
def test_censored_immediate_and_absent_recovery_are_distinct(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    filename: str,
    has_outage: bool,
    restored: bool,
) -> None:
    ws = isolated_workspace
    run = command(
        "diagnostic",
        "--scenario",
        str(ws.config_root / "scenarios" / filename),
        "--baseline",
        str(ws.config_root / "defenders/static_review.yaml"),
        "--seed",
        "424242",
    )["run_dir"]
    previous = command("metrics", run, "--mission-impact", "--approval-burden")
    augmented = command(
        "metrics", run, "--mission-impact", "--approval-burden", "--mission-recovery"
    )
    assert augmented["metrics_sha256"] == canonical_sha256(augmented["metrics"])
    metric = augmented["metrics"]["guarded_review"].pop("mission_recovery")
    assert augmented["metrics"] == previous["metrics"]
    spells = []
    if has_outage:
        spells.append(
            {
                "observed_from_tick": 6,
                "onset_tick": 6,
                "restored_tick": 6 if restored else None,
                "observed_ticks": 0 if restored else 2,
                "recovery_ticks": 0 if restored else None,
            }
        )
    assert metric["per_mission"] == [
        {"mission_id": "mission-a", "spells": spells},
        {"mission_id": "mission-b", "spells": []},
    ]
    assert metric["horizon_ticks"] == 8
    assert metric["completed_recovery_count"] == int(restored)
    assert metric["completed_recovery_sum_ticks"] == 0
    assert metric["mean_completed_recovery_ticks"] == (0.0 if restored else None)


@pytest.mark.reproducibility
def test_partial_or_false_restoration_cannot_release_a_recovery_measurement(
    isolated_workspace: IsolatedWorkspace, command: Command, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / MISSION_RECOVERY_ROLLBACK_FILE
    defender = ws.config_root / "defenders/static_review.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file=defender.name
    )
    expected = {
        "scenario": scenario.stem,
        "condition": "static_signal_review_v1",
        "code_commit": git_commit(ws.repo_root),
        "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
        "config_sha256": hashes["config_hash"],
        "seed_registry_sha256": hashes["seed_registry_hash"],
    }
    slots = [
        {"attempt_id": name, "invocation_id": f"{number:032x}", "seed": 424243}
        for number, name in enumerate(("restored", "mistimed", "partial", "unlaunched"), 1)
    ]
    plan = {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            dict(slot, cell_id="recovery", comparison_mode="controlled", expected=expected)
            for slot in slots
        ],
    }
    register = {"format": "pacd-attempt-register-v1", "attempts": slots}
    plan_path, register_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    register_path.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    launch = [
        "diagnostic",
        "--scenario",
        str(scenario),
        "--baseline",
        str(defender),
        "--seed",
        "424243",
        *plan_args,
        "--invocation-id",
    ]
    valid = command(*launch, str(slots[0]["invocation_id"]))["run_dir"]
    record = guarded.GuardedReviewQueue._record

    def mistime_restoration(
        queue: guarded.GuardedReviewQueue, event: guarded.ReviewEvent
    ) -> guarded.ReviewEvent:
        if event.outcome == "mission_effect" and event.payload["stage"] == "rollback":
            event = replace(event, tick=event.tick + 1)
        return record(queue, event)

    with monkeypatch.context() as altered:
        altered.setattr(guarded.GuardedReviewQueue, "_record", mistime_restoration)
        invalid = Path(command(*launch, str(slots[1]["invocation_id"]))["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=invalid,
        manifest=json.loads((invalid / "manifest.json").read_bytes()),
    ).identity_assured
    withheld = command("metrics", str(invalid), "--mission-recovery", code=1)
    assert withheld["status"] == "INVALID" and "metrics" not in withheld

    measure = guarded.mission_effect

    def fail_restoration_measurement(
        before: EnvironmentState, after: EnvironmentState
    ) -> dict[str, object]:
        if before.sessions[0].isolated and not after.sessions[0].isolated:
            raise RuntimeError("synthetic failure while observing restored availability")
        return measure(before, after)

    with monkeypatch.context() as interrupted:
        interrupted.setattr(guarded, "mission_effect", fail_restoration_measurement)
        failed = command(*launch, str(slots[2]["invocation_id"]), code=1)
    assert failed["status"] == "FAILED"
    (partial,) = ws.output_root.glob(f"*-{slots[2]['invocation_id']}")
    partial_rows = [
        json.loads(line) for line in (partial / "raw/events.jsonl").read_bytes().splitlines()
    ]
    stages = [r for r in partial_rows if r["event_type"] == "guarded_review"]
    assert [r["outcome"] for r in stages[-3:]] == [
        "mission_effect",
        "rolled_back",
        "mission_measurement_failed",
    ]
    assert json.loads(stages[-1]["payload_json"])["stage"] == "rollback"
    solo = command("metrics", valid, "--mission-recovery")
    assert solo["metrics"]["guarded_review"]["mission_recovery"]["completed_recovery_count"] == 1
    for inlet in (
        plan_args,
        ["--register", str(register_path), "--register-sha256", canonical_sha256(register)],
    ):
        rows = command("metrics", *inlet, "--mission-recovery")["attempts"]
        assert [row["status"] for row in rows] == ["COMPLETED", "INVALID", "FAILED", "INCOMPLETE"]
        assert rows[0]["metrics"] == solo["metrics"]
        assert rows[0]["metrics_sha256"] == solo["metrics_sha256"]
        assert all(row["metrics"] is row["metrics_sha256"] is None for row in rows[1:])


@pytest.mark.reproducibility
def test_recovery_option_preserves_the_legacy_unguarded_report(command: Command) -> None:
    run = command("diagnostic", "--seed", "424242")["run_dir"]
    previous = command("metrics", run)
    assert "guarded_review" not in previous["metrics"]
    assert command("metrics", run, "--mission-recovery") == previous

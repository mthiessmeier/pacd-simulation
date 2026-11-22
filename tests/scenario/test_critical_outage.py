"""Verify evaluator-owned critical function selection and its authenticated public measures."""

import json
import subprocess
from pathlib import Path

import pytest
from conftest import CONFIG_ROOT, IsolatedWorkspace
from pydantic import ValidationError

from pacd_sim.configuration import ScenarioConfig
from pacd_sim.constants import CRITICAL_OUTAGE_FILES, DEFAULT_SCENARIO_FILE
from pacd_sim.environment.availability import continuity_transition, evaluate_availability
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.harness import run as harness
from pacd_sim.oversight import guarded
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit

from .test_approval_burden import Command


def test_critical_designation_is_optional_and_pinned_to_configured_missions() -> None:
    original = harness.load_yaml_config(
        CONFIG_ROOT / "scenarios/diagnostic_review_override_retain.yaml"
    )
    assert canonical_sha256(ScenarioConfig.model_validate(original)) == canonical_sha256(original)
    for filename, mission in zip(CRITICAL_OUTAGE_FILES, ("mission-a", "mission-b"), strict=True):
        config = harness.load_yaml_config(CONFIG_ROOT / "scenarios" / filename)
        assert config == {
            **original,
            "name": Path(filename).stem,
            "critical_mission_ids": [mission],
        }
        model = ScenarioConfig.model_validate(config)
        assert model.critical_mission_ids == (mission,)
        assert canonical_sha256(model) == canonical_sha256(config)
        assert canonical_sha256(config) != canonical_sha256(
            {**config, "critical_mission_ids": ["mission-a", "mission-b"]}
        )

    for value in (None, [], ["mission-a", "mission-a"], ["session-a"], [False], "mission-a"):
        with pytest.raises(ValidationError):
            ScenarioConfig.model_validate({**original, "critical_mission_ids": value})
    legacy = harness.load_yaml_config(CONFIG_ROOT / "scenarios" / DEFAULT_SCENARIO_FILE)
    with pytest.raises(ValidationError, match="requires guarded review"):
        ScenarioConfig.model_validate({**legacy, "critical_mission_ids": ["mission-a"]})


def _launch(ws: IsolatedWorkspace, scenario: Path) -> list[str]:
    return [
        "diagnostic",
        "--scenario",
        str(scenario),
        "--baseline",
        str(ws.config_root / "defenders/static_review.yaml"),
        "--seed",
        "424242",
    ]


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("filename", "mission", "ticks"),
    [
        (CRITICAL_OUTAGE_FILES[0], "mission-a", 2),
        (CRITICAL_OUTAGE_FILES[1], "mission-b", 0),
        ("diagnostic_review_override_retain.yaml", None, None),
    ],
)
def test_selection_controls_exposure_on_the_same_mission_timeline(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    filename: str,
    mission: str | None,
    ticks: int | None,
) -> None:
    ws = isolated_workspace
    run = command(*_launch(ws, ws.config_root / "scenarios" / filename))["run_dir"]
    earlier = command("metrics", run, "--mission-recovery", "--mission-impact")
    measured = command(
        "metrics", run, "--mission-recovery", "--mission-impact", "--critical-outage"
    )
    if mission is None:
        assert measured == earlier
        return
    assert ticks is not None
    assert measured["metrics_sha256"] == canonical_sha256(measured["metrics"])
    view = measured["metrics"]["guarded_review"].pop("critical_outage")
    assert measured["metrics"] == earlier["metrics"]
    assert view == {
        "format": "pacd-critical-outage-v1",
        "metric_id": "MIS-003",
        "clock_unit": "simulation_ticks",
        "threshold_rule": "binary_unavailable",
        "horizon_ticks": 8,
        "per_mission": [
            {"mission_id": mission, "outage_ticks": ticks, "unavailable_at_horizon": bool(ticks)}
        ],
        "outage_function_ticks": ticks,
        "possible_function_ticks": 8,
        "any_outage_ticks": ticks,
        "any_outage_fraction": ticks / 8,
    }


@pytest.mark.scenario
def test_two_critical_functions_sharing_a_required_dependency(
    isolated_workspace: IsolatedWorkspace, command: Command
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / CRITICAL_OUTAGE_FILES[0]
    config = harness.load_yaml_config(scenario)
    config["critical_mission_ids"] = ["mission-b", "mission-a"]
    deps = config["dependencies"]
    assert isinstance(deps, list)
    deps.append(
        {
            "id": "dependency-shared",
            "upstream_id": "session-a",
            "downstream_id": "service-b",
            "weight": 1.0,
        }
    )
    scenario.write_bytes(canonical_json_bytes(config))
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "-qm",
            "pin shared mission dependency",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    run = command(*_launch(ws, scenario))["run_dir"]
    reports = command(
        "metrics", run, "--critical-outage", "--mission-impact", "--mission-recovery"
    )["metrics"]["guarded_review"]
    view = reports["critical_outage"]
    assert view["per_mission"] == [
        {"mission_id": key, "outage_ticks": 2, "unavailable_at_horizon": True}
        for key in ("mission-a", "mission-b")
    ]
    assert (view["outage_function_ticks"], view["possible_function_ticks"]) == (4, 16)
    assert (view["any_outage_ticks"], view["any_outage_fraction"]) == (2, 0.25)
    assert [
        (m["mission_id"], m["unavailable_ticks"]) for m in reports["mission_impact"]["per_mission"]
    ] == [("mission-a", 2), ("mission-b", 2)]
    for item in reports["mission_recovery"]["per_mission"]:
        (spell,) = item["spells"]
        assert (spell["onset_tick"], spell["observed_ticks"], spell["restored_tick"]) == (
            6,
            2,
            None,
        )


@pytest.mark.reproducibility
def test_pinned_readers_reject_count_preserving_mission_substitution(
    isolated_workspace: IsolatedWorkspace, command: Command, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / CRITICAL_OUTAGE_FILES[0]
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file="static_review.yaml"
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
        {"attempt_id": name, "invocation_id": f"{i:032x}", "seed": 424242}
        for i, name in enumerate(("valid", "other-mission", "unlaunched"), 1)
    ]
    plan = {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            dict(s, cell_id="critical-a", comparison_mode="controlled", expected=expected)
            for s in slots
        ],
    }
    register = {"format": "pacd-attempt-register-v1", "attempts": slots}
    plan_file, reg_file = ws.root / "plan.json", ws.root / "register.json"
    plan_file.write_bytes(canonical_json_bytes(plan))
    reg_file.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_file), "--plan-sha256", canonical_sha256(plan)]
    launch = [*_launch(ws, scenario), *plan_args, "--invocation-id"]
    valid = command(*launch, str(slots[0]["invocation_id"]))["run_dir"]
    real_effect = guarded.mission_effect

    def other_mission(before: EnvironmentState, after: EnvironmentState) -> dict[str, object]:
        effect = real_effect(before, after)
        current = evaluate_availability(after)
        assert current.operational_mission_ids == ("mission-b",)
        # Reverse which service supports which mission while preserving the unavailable count.
        swapped = {"mission-b": "mission-a", "mission-a": "mission-b"}
        services = tuple(
            s.model_copy(update={"mission_id": swapped[s.mission_id]}) for s in after.services
        )
        substituted = evaluate_availability(after.model_copy(update={"services": services}))
        assert substituted.operational_mission_ids == ("mission-a",)
        effect["availability_after"] = substituted.audit_summary()
        effect["mission_continuity"] = continuity_transition(
            evaluate_availability(before), substituted
        )
        return effect

    with monkeypatch.context() as producer:
        producer.setattr(guarded, "mission_effect", other_mission)
        invalid = Path(command(*launch, str(slots[1]["invocation_id"]))["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=invalid,
        manifest=json.loads((invalid / "manifest.json").read_bytes()),
    ).identity_assured
    rejected = command("metrics", str(invalid), "--critical-outage", code=1)
    assert rejected["status"] == "INVALID" and "metrics" not in rejected
    public = command("metrics", valid, "--critical-outage")
    assert public["metrics"]["guarded_review"]["critical_outage"]["outage_function_ticks"] == 2
    for args in (
        plan_args,
        ["--register", str(reg_file), "--register-sha256", canonical_sha256(register)],
    ):
        rows = command("metrics", *args, "--critical-outage")["attempts"]
        assert [row["status"] for row in rows] == ["COMPLETED", "INVALID", "INCOMPLETE"]
        assert (
            rows[0]["metrics"] == public["metrics"]
            and rows[0]["metrics_sha256"] == public["metrics_sha256"]
        )
        assert all(row["metrics"] is row["metrics_sha256"] is None for row in rows[1:])

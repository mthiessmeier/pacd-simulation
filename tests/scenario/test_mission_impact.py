"""Mission-weighted exposure on the authenticated guarded review timeline."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.harness import run as harness
from pacd_sim.oversight import guarded
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit


@pytest.fixture
def command(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., dict[str, Any]]:
    ws = isolated_workspace
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda value, **kwargs: output.append(value))

    def run(*args: str, code: int = 0) -> dict[str, Any]:
        assert cli.main(list(args)) == code, output[-1:]
        return output[-1]

    return run


@pytest.mark.scenario
def test_public_weight_fixtures_match_on_all_other_inputs(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ws = isolated_workspace
    common = []
    for variant, core, aux in (("high", 0.8, 0.2), ("low", 0.2, 0.8)):
        name = f"diagnostic_mission_core_{variant}"
        filename = f"{name}.yaml"
        config = harness.load_yaml_config(ws.config_root / "scenarios" / filename)
        assert config.pop("name") == name
        assert config.pop("missions") == [
            {"id": "mission-guarded-core", "criticality": core},
            {"id": "mission-guarded-aux", "criticality": aux},
        ]
        common.append(config)
        for policy in ("static_review.yaml", "pacd_corroborated_review.yaml"):
            harness.validate_diagnostic_configuration_files(
                ws.repo_root, scenario_file=filename, defender_file=policy
            )
        for policy, error in (
            ("diagnostic_baseline.yaml", "review-proposing baseline"),
            ("sensing_contextual.yaml", "Sensing inputs"),
        ):
            with pytest.raises(harness.ConfigurationError, match=error):
                harness.validate_diagnostic_configuration_files(
                    ws.repo_root, scenario_file=filename, defender_file=policy
                )
    assert common[0] == common[1]


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("affected", "rollback", "unavailable_ticks", "other_down_ticks", "loss"),
    [
        ("mission-guarded-core", False, 4, 0, 3.2),
        ("mission-spare", False, 4, 0, 0.8),
        ("mission-guarded-core", True, 0, 0, 0.0),
        ("mission-guarded-core", False, 4, 8, 4.8),
    ],
)
def test_service_membership_determines_the_weight_of_each_outage(
    isolated_workspace: IsolatedWorkspace,
    command: Callable[..., dict[str, Any]],
    affected: str,
    rollback: bool,
    unavailable_ticks: int,
    other_down_ticks: int,
    loss: float,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_guarded_benign.yaml"
    config = harness.load_yaml_config(scenario)
    other = "mission-spare" if affected == "mission-guarded-core" else "mission-guarded-core"
    config["missions"] = [
        {"id": "mission-spare", "criticality": 0.2},
        {"id": "mission-guarded-core", "criticality": 0.8},
    ]
    services = [{"id": "service-guarded-console", "mission_id": affected}]
    if other_down_ticks == 0:
        services.append({"id": "service-spare", "mission_id": other})
    config["services"] = services
    review = config["guarded_review"]
    assert isinstance(review, dict)
    review["rollback"] = rollback
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
            "pin the mission membership and rollback fixture",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    run_dir = command(
        "diagnostic",
        "--scenario",
        str(scenario),
        "--baseline",
        str(ws.config_root / "defenders/static_review.yaml"),
        "--seed",
        "424242",
    )["run_dir"]
    default = command("metrics", run_dir)
    enabled = command("metrics", run_dir, "--mission-impact")
    assert enabled["metrics_sha256"] == canonical_sha256(enabled["metrics"])
    assert enabled == command("metrics", run_dir, "--mission-impact")
    measurements = enabled["metrics"]["guarded_review"].copy()
    impact = measurements.pop("mission_impact")
    assert measurements == default["metrics"]["guarded_review"]
    assert (
        measurements["mission_availability"]["unavailable_mission_ticks"]
        == unavailable_ticks + other_down_ticks
    )
    assert impact["metric_id"] == "MIS-002" and impact["horizon_ticks"] == 8
    assert impact["weighted_loss"] == pytest.approx(loss)
    assert impact["possible_weighted_ticks"] == 8.0
    assert impact["loss_fraction"] == pytest.approx(loss / 8)
    rows = impact["per_mission"]
    assert [row["mission_id"] for row in rows] == ["mission-guarded-core", "mission-spare"]
    for row, weight in zip(rows, (0.8, 0.2), strict=True):
        down = unavailable_ticks if row["mission_id"] == affected else other_down_ticks
        assert row["criticality"] == weight and row["unavailable_ticks"] == down
        assert row["weighted_loss"] == pytest.approx(weight * down)
    events = [
        json.loads(line) for line in (Path(run_dir) / "raw/events.jsonl").read_bytes().splitlines()
    ]
    effects = [
        r
        for r in events
        if r["event_type"] == "guarded_review" and r["outcome"] == "mission_effect"
    ]
    assert [(r["tick"], json.loads(r["payload_json"])["stage"]) for r in effects] == (
        [(4, "execution"), (4, "rollback")] if rollback else [(4, "execution")]
    )


@pytest.mark.reproducibility
def test_opt_in_plan_and_register_release_only_verified_mission_impact(
    isolated_workspace: IsolatedWorkspace,
    command: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml"
    defender = ws.config_root / "defenders/sensing_contextual.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root,
        scenario_file=scenario.name,
        defender_file=defender.name,
    )
    expected = {
        "scenario": "diagnostic_sensing_nominal",
        "condition": "sensing_contextual_v1",
        "code_commit": git_commit(ws.repo_root),
        "config_sha256": hashes["config_hash"],
        "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
        "seed_registry_sha256": hashes["seed_registry_hash"],
    }
    attempts = [
        {"attempt_id": name, "invocation_id": f"{i:032x}", "seed": 424243}
        for i, name in enumerate(("valid", "wrong-membership", "unlaunched"), 1)
    ]
    plan = {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            {**a, "cell_id": "nominal", "comparison_mode": "controlled", "expected": expected}
            for a in attempts
        ],
    }
    plan_path, register_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    register = {"format": "pacd-attempt-register-v1", "attempts": attempts}
    register_path.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    run = [
        "diagnostic",
        "--seed",
        "424243",
        "--scenario",
        str(scenario),
        "--baseline",
        str(defender),
        *plan_args,
    ]
    valid = command(*run, "--invocation-id", str(attempts[0]["invocation_id"]))
    real_effect = guarded.mission_effect

    def altered_membership(before: EnvironmentState, after: EnvironmentState) -> dict[str, object]:
        data = real_effect(before, after)
        availability = data["availability_after"]
        assert isinstance(availability, dict)
        availability["availability_digest"] = "f" * 64
        return data

    with monkeypatch.context() as producer:
        producer.setattr(guarded, "mission_effect", altered_membership)
        invalid = command(*run, "--invocation-id", str(attempts[1]["invocation_id"]))
    path = Path(invalid["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=path,
        manifest=json.loads((path / "manifest.json").read_bytes()),
    ).identity_assured
    flags = ["--mission-impact", "--sensing-freshness"]
    withheld = command("metrics", str(path), *flags, code=1)
    assert withheld["status"] == "INVALID" and "metrics" not in withheld
    enabled = command("metrics", valid["run_dir"], *flags)
    assert enabled["metrics_sha256"] == canonical_sha256(enabled["metrics"])
    metrics = enabled["metrics"]["guarded_review"]
    for option, field in (
        ("--mission-impact", "mission_impact"),
        ("--sensing-freshness", "sensing_freshness"),
    ):
        single = command("metrics", valid["run_dir"], option)["metrics"]["guarded_review"]
        assert single[field] == metrics[field]
    assert metrics["mission_impact"]["weighted_loss"] == 0.0
    assert metrics["mission_impact"]["possible_weighted_ticks"] == 6.4
    assert metrics["mission_impact"]["loss_fraction"] == 0.0
    for args in (
        plan_args,
        ["--register", str(register_path), "--register-sha256", canonical_sha256(register)],
    ):
        verified, rejected, absent = command("metrics", *args, *flags)["attempts"]
        assert verified["status"] == "COMPLETED" and verified["metrics"] == enabled["metrics"]
        assert verified["metrics_sha256"] == enabled["metrics_sha256"]
        assert [rejected["status"], absent["status"]] == ["INVALID", "INCOMPLETE"]
        assert all(a["metrics"] is a["metrics_sha256"] is None for a in (rejected, absent))


@pytest.mark.reproducibility
def test_legacy_unguarded_episode_omits_mission_projection(
    isolated_workspace: IsolatedWorkspace, command: Callable[..., dict[str, Any]]
) -> None:
    run = command("diagnostic", "--seed", "424242")
    default = command("metrics", run["run_dir"])
    assert "guarded_review" not in default["metrics"]
    assert command("metrics", run["run_dir"], "--mission-impact") == default

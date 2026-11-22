"""Exercise operator previews at guarded review admission through the public diagnostic CLI."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.constants import REVIEW_BRIEF_ISOLATION_FILE, REVIEW_BRIEF_SENSING_FILE
from pacd_sim.harness import run as harness
from pacd_sim.oversight import guarded
from pacd_sim.oversight.review_brief import operator_brief
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt

type Command = Callable[..., dict[str, Any]]


def _launch(ws: IsolatedWorkspace, command: Command, scenario: Path, defender: str) -> Path:
    result = command(
        "diagnostic",
        "--scenario",
        str(scenario),
        "--baseline",
        str(ws.config_root / "defenders" / f"{defender}.yaml"),
        "--seed",
        "424242",
    )
    return Path(result["run_dir"])


def _reviews(run: Path) -> list[dict[str, Any]]:
    rows = (json.loads(line) for line in (run / "raw/events.jsonl").read_bytes().splitlines())
    return [row for row in rows if row["event_type"] == "guarded_review"]


def _pending(rows: list[dict[str, Any]]) -> dict[str, Any]:
    (row,) = (r for r in rows if r["outcome"] == "pending")
    payload: dict[str, Any] = json.loads(row["payload_json"])
    assert payload["request_digest"] == canonical_sha256(payload["binding"])
    return payload


def _pin(ws: IsolatedWorkspace, scenario: Path, config: dict[str, Any]) -> None:
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
            "pin synthetic preview control",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("name", "base", "defender", "action", "version", "cost", "mission_states"),
    [
        (
            REVIEW_BRIEF_ISOLATION_FILE,
            "diagnostic_mission_core_high.yaml",
            "static_review",
            "isolate_session",
            "isolation",
            0.0,
            {"mission-guarded-aux": True, "mission-guarded-core": False},
        ),
        (
            REVIEW_BRIEF_SENSING_FILE,
            "diagnostic_sensing_nominal.yaml",
            "sensing_contextual",
            "switch_sensing_profile",
            "sensing",
            0.25,
            {"mission-guarded-core": True},
        ),
    ],
)
def test_bound_preview_is_consumed_by_verified_review(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    name: str,
    base: str,
    defender: str,
    action: str,
    version: str,
    cost: float,
    mission_states: dict[str, bool],
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / name
    regular = ws.config_root / "scenarios" / base
    config = harness.load_yaml_config(scenario)
    assert config.pop("name") == scenario.stem
    settings = config["guarded_review"]
    assert isinstance(settings, dict) and settings.pop("decision_brief") == "operator-preview-v1"
    assert dict(config, name=regular.stem) == harness.load_yaml_config(regular)
    run = _launch(ws, command, scenario, defender)
    rows = _reviews(run)
    pending = _pending(rows)
    binding = pending["binding"]
    assert binding["contract"] == f"guarded-review-{version}-v2"
    brief = binding["operator_brief"]
    assert brief["format"] == "operator-preview-v1"
    assert brief["rationale"] == "action type requires simulated human review"
    assert brief["action_type"] == action and brief["target_id"] == binding["action"]["target_id"]
    assert brief["expected_effect"] == binding["action"]["expected_effect"]
    reading = brief["triggering_reading"]
    assert reading["delivered_tick"] == binding["submitted_tick"]
    assert reading["measured_tick"] + 1 == reading["delivered_tick"]
    assert reading["subject_id"] == binding["subject_id"] and reading["source_key"] == 1
    assert brief["uncertainty"] == {
        "age_ticks": 1,
        "freshness": "fresh",
        "compromise_probability": None,
    }
    preview = brief["impact_preview"]
    assert preview["mission_cost"] == cost
    assert preview["missions"] == [
        {"mission_id": mission, "operational_before": True, "operational_if_applied": available}
        for mission, available in sorted(mission_states.items())
    ]
    (approved,) = (r for r in rows if r["outcome"] == "approved")
    assert json.loads(approved["payload_json"])["request_digest"] == pending["request_digest"]
    assert command("verify", str(run))["status"] == "VERIFIED"
    routing = command("metrics", str(run), "--review-routing")["metrics"]["guarded_review"][
        "review_routing"
    ]
    assert routing["routing_completeness"]["value"] == routing["package_count"] == 1

    previous = _launch(ws, command, regular, defender)
    original = _pending(_reviews(previous))["binding"]
    assert (
        original["contract"] == f"guarded-review-{version}-v1" and "operator_brief" not in original
    )
    assert (
        command("metrics", str(previous), "--review-routing")["metrics"]["guarded_review"][
            "review_routing"
        ]
        == routing
    )


@pytest.mark.reproducibility
def test_operator_sees_only_information_available_at_admission(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_BRIEF_ISOLATION_FILE
    control = _launch(ws, command, scenario, "static_review")
    expected = _pending(_reviews(control))["binding"]["operator_brief"]
    assert command("verify", str(control))["status"] == "VERIFIED"
    config: dict[str, Any] = harness.load_yaml_config(scenario)
    config["guarded_review"]["response"] = "deny"
    for event in config["events"]:
        event["kind"] = "simulated_adversary"
    config["events"].pop()
    _pin(ws, scenario, config)
    changed = _launch(ws, command, scenario, "static_review")
    rows = _reviews(changed)
    assert [r["outcome"] for r in rows] == ["pending", "denied"]
    assert _pending(rows)["binding"]["operator_brief"] == expected
    assert command("verify", str(changed))["status"] == "VERIFIED"

    config["telemetry"]["delay_ticks"] = 4
    _pin(ws, scenario, config)
    delayed = _launch(ws, command, scenario, "static_review")
    brief = _pending(_reviews(delayed))["binding"]["operator_brief"]
    assert brief["uncertainty"] == {
        "age_ticks": 4,
        "freshness": "stale",
        "compromise_probability": None,
    }
    assert brief["impact_preview"] == expected["impact_preview"]
    assert command("verify", str(delayed))["status"] == "VERIFIED"


@pytest.mark.scenario
@pytest.mark.parametrize("variant", ["capacity", "ineligible", "oversized"])
def test_unscheduled_review_never_receives_an_operator_brief(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    variant: str,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_BRIEF_ISOLATION_FILE
    config: dict[str, Any] = harness.load_yaml_config(scenario)
    if variant == "capacity":
        config["guarded_review"]["capacity"] = 0
    elif variant == "ineligible":
        config["identities"].append({"id": "unobserved", "role": "synthetic_user"})
        config["sessions"][0]["identity_id"] = "unobserved"
    else:
        # The predicted mission rows exceed the pending event's UTF-8 payload budget.
        config["missions"].extend(
            {"id": f"mission-{n}-" + "界" * 110, "criticality": 0.2} for n in range(220)
        )
    _pin(ws, scenario, config)
    run = _launch(ws, command, scenario, "static_review")
    (row,) = _reviews(run)
    assert row["outcome"] == ("capacity" if variant == "capacity" else "refused")
    refusal = json.loads(row["payload_json"])
    assert "binding" not in refusal and "operator_brief" not in refusal
    if variant == "oversized":
        assert refusal["reason"] == "review brief exceeds the audit payload limit"
    report = command("metrics", str(run), "--review-routing")["metrics"]["guarded_review"]
    assert report["review_routing"]["package_count"] == 0


@pytest.mark.reproducibility
@pytest.mark.parametrize("false_field", ["mission_state", "signal"])
def test_replay_withholds_authentic_but_false_preview(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    monkeypatch: pytest.MonkeyPatch,
    false_field: str,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_BRIEF_ISOLATION_FILE

    def incorrect(*args: Any, **kwargs: Any) -> dict[str, Any]:
        brief: dict[str, Any] = operator_brief(*args, **kwargs)
        if false_field == "mission_state":
            brief["impact_preview"]["missions"][0]["operational_if_applied"] = False
        else:
            brief["triggering_reading"]["signal"] = 0.15
        return brief

    with monkeypatch.context() as producer:
        producer.setattr(guarded, "operator_brief", incorrect)
        run = _launch(ws, command, scenario, "static_review")
    _pending(_reviews(run))
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=run,
        manifest=json.loads((run / "manifest.json").read_bytes()),
    ).identity_assured
    assert command("verify", str(run), code=1)["status"] == "INVALID"
    result = command("metrics", str(run), "--review-routing", code=1)
    assert result["status"] == "INVALID" and "metrics" not in result

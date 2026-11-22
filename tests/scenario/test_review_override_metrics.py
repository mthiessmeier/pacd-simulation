"""Observe only modeled review opportunities in authenticated OPS-003/GOV-003 output."""

import json
import subprocess
from pathlib import Path

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256

from .test_approval_burden import Command


def _launch(ws: IsolatedWorkspace, scenario: Path, command: Command) -> str:
    return str(
        command(
            "diagnostic",
            "--scenario",
            str(scenario),
            "--baseline",
            str(ws.config_root / "defenders/static_review.yaml"),
            "--seed",
            "424242",
        )["run_dir"]
    )


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("policy", "response", "direction", "rationale", "events"),
    [
        (
            "retain",
            "approve",
            "none",
            "retain_planned_response",
            ["approved", "executed", "verified"],
        ),
        ("veto", "deny", "approve_to_deny", "preserve_mission_continuity", ["denied"]),
    ],
)
def test_verified_opportunities_link_to_their_observed_downstream_events(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    policy: str,
    response: str,
    direction: str,
    rationale: str,
    events: list[str],
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / f"scenarios/diagnostic_review_override_{policy}.yaml"
    run = _launch(ws, scenario, command)
    previous = command("metrics", run, "--review-routing")
    result = command("metrics", run, "--review-routing", "--approval-burden")
    assert result["metrics_sha256"] == canonical_sha256(result["metrics"])
    guarded = result["metrics"]["guarded_review"]
    burden = guarded.pop("approval_burden")
    overrides = guarded.pop("review_overrides")
    assert result["metrics"] == previous["metrics"]
    assert burden["request_count"] == 2
    assert burden["override_status"] == "measured"
    assert burden["override_count"] == int(policy == "veto")
    assert overrides["format"] == "pacd-review-overrides-v1" and overrides["metric_id"] == "GOV-003"
    assert overrides["override_policy"] == policy + "_approval"
    assert overrides["override_rate"] == {
        "numerator": int(policy == "veto"),
        "denominator": 1,
        "value": float(policy == "veto"),
        "unit": "fraction_of_timely_planned_approvals",
    }
    counts = overrides["downstream_event_counts"]
    assert {name: count for name, count in counts.items() if count} == dict.fromkeys(events, 1)
    raw = [json.loads(line) for line in (Path(run) / "raw/events.jsonl").read_bytes().splitlines()]
    first, pending_at_horizon = [
        r for r in raw if r["event_type"] == "guarded_review" and r["outcome"] == "pending"
    ]
    digest = canonical_sha256(json.loads(first["payload_json"])["binding"])
    assert overrides["opportunities"] == [
        {
            "referral_id": first["action_id"],
            "subject_id": first["entity_id"],
            "request_digest": digest,
            "assessment_tick": 6,
            "original_response": "approve",
            "final_response": response,
            "direction": direction,
            "rationale": rationale,
            "downstream_events": events,
        }
    ]
    assert burden["requests"][0]["request_digest"] == digest
    assert burden["requests"][0]["outcome"] == events[0]
    assert burden["requests"][1]["outcome"] == "pending_at_horizon"
    assert burden["requests"][1]["request_digest"] == canonical_sha256(
        json.loads(pending_at_horizon["payload_json"])["binding"]
    )


def _pin(ws: IsolatedWorkspace, scenario: Path, settings: dict[str, object]) -> None:
    config = harness.load_yaml_config(scenario)
    review = config["guarded_review"]
    assert isinstance(review, dict)
    review.update(settings)
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
            "pin synthetic review control",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("settings", "outcome", "count"),
    [
        ({"capacity": 0}, "capacity", 2),
        ({"response": "deny"}, "denied", 1),
        ({"response": "no_response"}, "expired", 1),
        ({"delay_ticks": 10, "validity_ticks": 10}, "pending_at_horizon", 2),
    ],
)
def test_modeled_but_ineligible_reviews_have_zero_count_and_unknown_rate(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    settings: dict[str, object],
    outcome: str,
    count: int,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_review_override_veto.yaml"
    _pin(ws, scenario, settings)
    run = _launch(ws, scenario, command)
    guarded = command("metrics", run, "--approval-burden", "--review-routing")["metrics"][
        "guarded_review"
    ]
    assert guarded["review_routing"]["outcome_counts"][outcome] == count
    burden, overrides = guarded["approval_burden"], guarded["review_overrides"]
    assert burden["override_count"] == 0 and burden["override_status"] == "measured"
    assert overrides["opportunities"] == []
    assert overrides["override_rate"]["numerator"] == overrides["override_rate"]["denominator"] == 0
    assert overrides["override_rate"]["value"] is None
    assert sum(overrides["downstream_event_counts"].values()) == 0


@pytest.mark.scenario
@pytest.mark.parametrize("rollback", [False, True])
def test_each_retained_approval_has_its_own_observed_governor_outcome(
    isolated_workspace: IsolatedWorkspace, command: Command, rollback: bool
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_review_override_retain.yaml"
    _pin(ws, scenario, {"end_tick": 10, "rollback": rollback})
    run = _launch(ws, scenario, command)
    guarded = command("metrics", run, "--approval-burden")["metrics"]["guarded_review"]
    assert guarded["approval_burden"]["override_count"] == 0
    overrides = guarded["review_overrides"]
    assert overrides["override_rate"]["denominator"] == 2
    first, second = overrides["opportunities"]
    assert (first["subject_id"], first["assessment_tick"]) == ("identity-a", 6)
    assert (second["subject_id"], second["assessment_tick"]) == ("identity-b", 9)
    assert first["request_digest"] != second["request_digest"]
    expected = ["approved", "executed", "verified"]
    if rollback:
        assert (
            first["downstream_events"] == second["downstream_events"] == [*expected, "rolled_back"]
        )
    else:
        assert first["downstream_events"] == expected
        assert second["downstream_events"] == ["approved", "unauthorized"]

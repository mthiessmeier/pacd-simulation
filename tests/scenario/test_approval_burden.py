"""Reconcile observed approval waiting time with the verified queue lifecycle."""

import json
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.comparison import ComparisonPlan
from pacd_sim.constants import REVIEW_BURDEN_FILE
from pacd_sim.harness import run as harness
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewEvent
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit

type Command = Callable[..., dict[str, Any]]
type Wait = tuple[str, int, int | None, str, int]


def _launch(ws: IsolatedWorkspace, condition: str, *extra: str) -> list[str]:
    return [
        "diagnostic",
        "--scenario",
        str(ws.config_root / "scenarios" / REVIEW_BURDEN_FILE),
        "--baseline",
        str(ws.config_root / "defenders" / f"{condition}.yaml"),
        "--seed",
        "424242",
        *extra,
    ]


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("condition", "settings", "expected", "capacity_rejections"),
    [
        (
            "static_review",
            {},
            [("identity-a", 2, 6, "approved", 4), ("identity-b", 5, None, "pending_at_horizon", 3)],
            0,
        ),
        (
            "static_review",
            {"response": "deny"},
            [("identity-a", 2, 6, "denied", 4), ("identity-b", 5, None, "pending_at_horizon", 3)],
            0,
        ),
        (
            "static_review",
            {"response": "no_response"},
            [("identity-a", 2, 7, "expired", 5), ("identity-b", 5, None, "pending_at_horizon", 3)],
            0,
        ),
        (
            "static_review",
            {"delay_ticks": 0},
            [("identity-a", 2, 2, "approved", 0), ("identity-b", 5, 5, "approved", 0)],
            0,
        ),
        ("static_review", {"capacity": 1}, [("identity-a", 2, 6, "approved", 4)], 1),
        ("pacd_corroborated_review", {}, [], 0),
    ],
)
def test_elapsed_waits_and_visible_censoring(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    condition: str,
    settings: dict[str, object],
    expected: list[Wait],
    capacity_rejections: int,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_BURDEN_FILE
    if settings:
        config = harness.load_yaml_config(scenario)
        review = config["guarded_review"]
        assert isinstance(review, dict)
        review.update(settings)
        # Execute the same accounting against the original guarded package for each control.
        del review["decision_brief"]
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
                "pin synthetic waiting-time controls",
                "--",
                str(scenario.relative_to(ws.repo_root)),
            ],
            cwd=ws.repo_root,
            check=True,
        )

    run = command(*_launch(ws, condition))["run_dir"]
    events = [
        json.loads(line) for line in (Path(run) / "raw/events.jsonl").read_bytes().splitlines()
    ]
    lifecycle = [event for event in events if event["event_type"] == "guarded_review"]
    admissions = [event for event in lifecycle if event["outcome"] == "pending"]
    assert sum(event["outcome"] == "capacity" for event in lifecycle) == capacity_rejections
    assert len(admissions) == len(expected)

    previous = command("metrics", run, "--review-routing")
    result = command("metrics", run, "--review-routing", "--approval-burden")
    assert result["metrics_sha256"] == canonical_sha256(result["metrics"])
    metric = result["metrics"]["guarded_review"].pop("approval_burden")
    assert result["metrics"] == previous["metrics"]
    assert metric["format"] == "pacd-approval-burden-v1" and metric["metric_id"] == "OPS-003"
    assert metric["clock_unit"] == "simulation_ticks" and metric["horizon_tick"] == 8
    assert metric["request_count"] == len(expected)
    assert metric["escalation_count"] == len(expected) + capacity_rejections
    assert metric["admission_outcomes"] == {
        "capacity": capacity_rejections,
        "refused": 0,
        "unrouted": 0,
    }
    assert metric["override_count"] is None and metric["override_status"] == "unsupported"
    assert metric["observed_request_ticks"] == sum(wait for *_, wait in expected)
    resolved = [wait for _, _, terminal, _, wait in expected if terminal is not None]
    assert metric["resolved_wait_denominator"] == len(resolved)
    assert metric["resolved_wait_sum_ticks"] == sum(resolved)
    assert metric["mean_resolved_wait_ticks"] == (
        sum(resolved) / len(resolved) if resolved else None
    )
    for outcome in ("approved", "denied", "expired", "pending_at_horizon"):
        waits = [wait for _, _, _, end, wait in expected if end == outcome]
        assert metric["wait_by_outcome"][outcome] == {
            "count": len(waits),
            "observed_wait_sum_ticks": sum(waits),
        }
    for request, event, (subject, start, end, outcome, wait) in zip(
        metric["requests"], admissions, expected, strict=True
    ):
        payload = json.loads(event["payload_json"])
        version = "v1" if settings else "v2"
        assert payload["binding"]["contract"] == f"guarded-review-isolation-{version}"
        digest = canonical_sha256(payload["binding"])
        assert digest == payload["request_digest"]
        assert (event["entity_id"], event["tick"]) == (subject, start)
        assert request == {
            "referral_id": event["action_id"],
            "subject_id": subject,
            "request_digest": digest,
            "submitted_tick": start,
            "terminal_tick": end,
            "outcome": outcome,
            "observed_wait_ticks": wait,
        }


@pytest.mark.reproducibility
def test_pinned_burden_preserves_each_attempt_and_withholds_false_waits(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_BURDEN_FILE
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root,
        scenario_file=REVIEW_BURDEN_FILE,
        defender_file="static_review.yaml",
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
        for i, name in enumerate(("valid", "false-wait", "failed", "timed-out", "unlaunched"), 1)
    ]
    plan = ComparisonPlan.model_validate(
        {
            "format": "pacd-development-comparison-plan-v1",
            "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
            "attempts": [
                dict(s, cell_id="staggered", comparison_mode="controlled", expected=expected)
                for s in slots
            ],
        }
    )
    register = {"format": "pacd-attempt-register-v1", "attempts": slots}
    plan_path, register_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    register_path.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    reg_args = ["--register", str(register_path), "--register-sha256", canonical_sha256(register)]
    launch = _launch(ws, "static_review", *plan_args, "--invocation-id")
    run = command(*launch, plan.attempts[0].invocation_id)["run_dir"]
    record = GuardedReviewQueue._record

    def early_approval(queue: GuardedReviewQueue, event: ReviewEvent) -> ReviewEvent:
        if event.outcome == "approved":
            event = replace(event, tick=event.tick - 1)
        return record(queue, event)

    with monkeypatch.context() as producer:
        producer.setattr(GuardedReviewQueue, "_record", early_approval)
        false_run = Path(command(*launch, plan.attempts[1].invocation_id)["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=false_run,
        manifest=json.loads((false_run / "manifest.json").read_bytes()),
    ).identity_assured
    invalid = command("metrics", str(false_run), "--approval-burden", code=1)
    assert invalid["status"] == "INVALID" and "metrics" not in invalid
    for slot, reason in zip(
        plan.attempts[2:4],
        (
            RuntimeError("simulated interruption"),
            harness.DiagnosticTimeoutError("synthetic deadline"),
        ),
        strict=True,
    ):
        owned = harness._create_invocation_ownership(
            ws.output_root,
            ws.root,
            424242,
            invocation_id=slot.invocation_id,
            plan=plan,
        )
        harness._retain_interrupted_evidence(ws.root, owned, reason)
    flags = ["--approval-burden", "--review-routing", "--mission-impact", "--sensing-freshness"]
    single = command("metrics", run, *flags)
    assert single["metrics"]["guarded_review"]["approval_burden"]["observed_request_ticks"] == 7
    for inlet in (plan_args, reg_args):
        attempts = command("metrics", *inlet, *flags)["attempts"]
        assert [a["status"] for a in attempts] == [
            "COMPLETED",
            "INVALID",
            "FAILED",
            "TIMED_OUT",
            "INCOMPLETE",
        ]
        assert attempts[0]["metrics"] == single["metrics"]
        assert attempts[0]["metrics_sha256"] == single["metrics_sha256"]
        assert all(a["metrics"] is a["metrics_sha256"] is None for a in attempts[1:])


@pytest.mark.reproducibility
def test_unguarded_burden_keeps_default_report(command: Command) -> None:
    run = command("diagnostic", "--seed", "424242")["run_dir"]
    assert command("metrics", run, "--approval-burden") == command("metrics", run)

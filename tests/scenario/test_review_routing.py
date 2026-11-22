"""Reconcile GOV-002 with actual referrals through the governed metrics interfaces."""

import json
import subprocess
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.constants import REVIEW_CONTENTION_FILE, diagnostic_pair_supported
from pacd_sim.harness import run as harness
from pacd_sim.oversight import guarded
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.reportable import git_commit


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("condition", "variant", "terminal_counts", "packages", "numerator", "denominator"),
    [
        ("static_review", "unchanged", {"approved": 1, "capacity": 1}, 1, 1, 2),
        ("pacd_corroborated_review", "unchanged", {}, 0, 0, 0),
        ("static_review", "deny", {"denied": 1, "capacity": 1}, 1, 1, 2),
        ("static_review", "no_response", {"expired": 1, "capacity": 1}, 1, 1, 2),
        ("static_review", "pending", {"pending_at_horizon": 1, "capacity": 1}, 1, 0, 2),
        ("static_review", "ineligible", {"approved": 1, "refused": 1}, 1, 1, 2),
        ("static_review", "two_slots", {"approved": 2}, 2, 2, 2),
    ],
)
def test_routing_by_referral_through_the_review_horizon(
    isolated_workspace: IsolatedWorkspace,
    command: Callable[..., dict[str, Any]],
    condition: str,
    variant: str,
    terminal_counts: dict[str, int],
    packages: int,
    numerator: int,
    denominator: int,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_CONTENTION_FILE
    defender = ws.config_root / "defenders" / f"{condition}.yaml"
    assert diagnostic_pair_supported(scenario.name, defender.name)
    for unsupported in ("diagnostic_baseline.yaml", "sensing_contextual.yaml"):
        assert not diagnostic_pair_supported(scenario.name, unsupported)
        with pytest.raises(harness.ConfigurationError):
            harness.validate_diagnostic_configuration_files(
                ws.repo_root, scenario_file=scenario.name, defender_file=unsupported
            )
    if variant != "unchanged":
        config = harness.load_yaml_config(scenario)
        review = config["guarded_review"]
        assert isinstance(review, dict)
        if variant == "ineligible":
            sessions, dependencies = config["sessions"], config["dependencies"]
            assert isinstance(sessions, list) and isinstance(dependencies, list)
            config["sessions"] = [s for s in sessions if s["id"] != "session-b"]
            config["dependencies"] = [
                dep for dep in dependencies if dep["upstream_id"] != "session-b"
            ]
        elif variant == "pending":
            review.update(delay_ticks=9, validity_ticks=9)
        elif variant == "two_slots":
            review["capacity"] = 2
        else:
            review["response"] = variant
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
                "pin review controls",
                "--",
                str(scenario.relative_to(ws.repo_root)),
            ],
            cwd=ws.repo_root,
            check=True,
        )

    run_dir = command(
        "diagnostic", "--scenario", str(scenario), "--baseline", str(defender), "--seed", "424242"
    )["run_dir"]
    events = [
        json.loads(line) for line in (Path(run_dir) / "raw/events.jsonl").read_bytes().splitlines()
    ]
    escalations = [
        row
        for row in events
        if row["event_type"] == "safety_decision" and row["disposition"] == "ESCALATE"
    ]
    assert len(escalations) == denominator
    if denominator:
        assert {row["entity_id"] for row in escalations} == {"identity-a", "identity-b"}
        assert len({row["action_id"] for row in escalations}) == 2
        assert {row["tick"] for row in escalations} == {2}
    lifecycle = Counter(row["outcome"] for row in events if row["event_type"] == "guarded_review")
    assert lifecycle["pending"] == packages
    for outcome in ("approved", "denied", "expired", "capacity", "refused"):
        assert lifecycle[outcome] == terminal_counts.get(outcome, 0)
    if variant == "two_slots":
        # Both reviews finish. The first execution changes the second action's bound state.
        assert lifecycle["executed"] == lifecycle["unauthorized"] == 1

    default = command("metrics", run_dir)
    enabled = command("metrics", run_dir, "--review-routing")
    assert enabled["metrics_sha256"] == canonical_sha256(enabled["metrics"])
    reviewed = enabled["metrics"]["guarded_review"].copy()
    routing = reviewed.pop("review_routing")
    assert reviewed == default["metrics"]["guarded_review"]
    assert routing["metric_id"] == "GOV-002" and routing["format"] == "pacd-review-routing-v1"
    assert routing["routing_completeness"] == {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "unit": "fraction_of_escalations",
    }
    assert routing["package_count"] == packages
    assert {k: v for k, v in routing["outcome_counts"].items() if v} == terminal_counts


@pytest.mark.reproducibility
def test_pinned_interfaces_withhold_invalid_and_missing_routing(
    isolated_workspace: IsolatedWorkspace,
    command: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios" / REVIEW_CONTENTION_FILE
    defender = ws.config_root / "defenders/static_review.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file=defender.name
    )
    expected = {
        "scenario": scenario.stem,
        "condition": "static_signal_review_v1",
        "code_commit": git_commit(ws.repo_root),
        "config_sha256": hashes["config_hash"],
        "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
        "seed_registry_sha256": hashes["seed_registry_hash"],
    }
    attempts = [
        {"attempt_id": name, "invocation_id": f"{index:032x}", "seed": 424243}
        for index, name in enumerate(("valid", "wrong-evidence", "unlaunched"), 1)
    ]
    plan = {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            dict(a, cell_id="contested", comparison_mode="controlled", expected=expected)
            for a in attempts
        ],
    }
    register = {"format": "pacd-attempt-register-v1", "attempts": attempts}
    plan_path, register_path = ws.root / "plan.json", ws.root / "register.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    register_path.write_bytes(canonical_json_bytes(register))
    plan_args = ["--plan", str(plan_path), "--plan-sha256", canonical_sha256(plan)]
    register_args = [
        "--register",
        str(register_path),
        "--register-sha256",
        canonical_sha256(register),
    ]
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
    run_dir = command(*launch, str(attempts[0]["invocation_id"]))["run_dir"]
    bind = guarded.review_binding

    def wrong_evidence(*args: Any, **kwargs: Any) -> dict[str, object]:
        return dict(bind(*args, **kwargs), evidence_digest="0" * 64)

    with monkeypatch.context() as producer:
        producer.setattr(guarded, "review_binding", wrong_evidence)
        invalid_dir = Path(command(*launch, str(attempts[1]["invocation_id"]))["run_dir"])
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=invalid_dir,
        manifest=json.loads((invalid_dir / "manifest.json").read_bytes()),
    ).identity_assured
    invalid = command("metrics", str(invalid_dir), "--review-routing", code=1)
    assert invalid["status"] == "INVALID" and "metrics" not in invalid
    flags = ["--review-routing", "--mission-impact", "--sensing-freshness"]
    enabled = command("metrics", run_dir, *flags)
    single = command("metrics", run_dir, "--review-routing")
    assert (
        single["metrics"]["guarded_review"]["review_routing"]
        == enabled["metrics"]["guarded_review"]["review_routing"]
    )
    for args in (plan_args, register_args):
        default = command("metrics", *args)
        assert "review_routing" not in default["attempts"][0]["metrics"]["guarded_review"]
        verified, rejected, absent = command("metrics", *args, *flags)["attempts"]
        assert verified["status"] == "COMPLETED" and verified["metrics"] == enabled["metrics"]
        assert verified["metrics_sha256"] == enabled["metrics_sha256"]
        assert [rejected["status"], absent["status"]] == ["INVALID", "INCOMPLETE"]
        assert all(a["metrics"] is a["metrics_sha256"] is None for a in (rejected, absent))


@pytest.mark.reproducibility
def test_unguarded_episode_keeps_its_default_metrics(
    command: Callable[..., dict[str, Any]],
) -> None:
    run_dir = command("diagnostic", "--seed", "424242")["run_dir"]
    assert command("metrics", run_dir, "--review-routing") == command("metrics", run_dir)

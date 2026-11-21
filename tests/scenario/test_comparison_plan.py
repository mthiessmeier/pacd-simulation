"""Plan membership, immutable launch inputs and verified metric release."""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim import cli
from pacd_sim.comparison import ComparisonPlan
from pacd_sim.harness import run as harness
from pacd_sim.metrics.registered import load_register, registered_metrics
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.reportable import git_commit


def example(ws: IsolatedWorkspace) -> dict[str, Any]:
    scenario, _, _, _, _ = controlled_config_files(ws.config_root)
    inputs = harness.validate_diagnostic_configuration_files(ws.repo_root)
    return {
        "format": "pacd-development-comparison-plan-v1",
        "evidence_label": "NON_REPORTABLE_DIAGNOSTIC",
        "attempts": [
            {
                "attempt_id": f"attempt-{i}",
                "invocation_id": f"{i:032x}",
                "seed": 424242,
                "cell_id": "original",
                "comparison_mode": "controlled",
                "expected": {
                    "scenario": "diagnostic_identity_smoke",
                    "condition": "null_diagnostic_baseline",
                    "code_commit": git_commit(ws.repo_root),
                    "config_sha256": inputs["config_hash"],
                    "seed_registry_sha256": inputs["seed_registry_hash"],
                    "events_sha256": canonical_sha256(harness.load_yaml_config(scenario)["events"]),
                },
            }
            for i in range(1, 6)
        ],
    }


@pytest.mark.reproducibility
def test_planned_attempts_share_verifier_and_retain_failures(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = isolated_workspace
    # The fixture supplies the checkout and governed inputs. CLI replay exercises the real worker.
    monkeypatch.setattr(harness, "__file__", str(ws.repo_root / "src/pacd_sim/harness/run.py"))
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    outputs: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda value, **kw: outputs.append(value))
    doc = example(ws)
    plan = ComparisonPlan.model_validate(doc)
    pin = canonical_sha256(plan)
    path = ws.root / "plan.json"
    path.write_text(json.dumps(doc, indent=3), encoding="utf-8")
    read = ["metrics", "--plan", str(path), "--plan-sha256", pin]
    launch = [
        "diagnostic",
        "--plan",
        str(path),
        "--plan-sha256",
        pin,
        "--invocation-id",
        plan.attempts[0].invocation_id,
    ]
    assert cli.main(read) == 0 and outputs[-1]["observed_counts"] is None
    assert not (ws.root / "var/invocations").exists()
    for field, wrong in (
        ("scenario", "different"),
        ("condition", "other"),
        ("code_commit", "0" * 40),
        ("config_sha256", "1" * 64),
        ("events_sha256", "2" * 64),
        ("seed_registry_sha256", "3" * 64),
    ):
        changed = json.loads(json.dumps(doc))
        for attempt in changed["attempts"]:
            attempt["expected"][field] = wrong
        path.write_bytes(canonical_json_bytes(changed))
        assert cli.main([*launch[:4], canonical_sha256(changed), *launch[5:]]) == 2
        assert not (ws.root / "var/invocations").exists()
    path.write_bytes(canonical_json_bytes(doc))
    for extra in (["--seed", "424243"], ["--invocation-id", "9" * 32], ["--plan-sha256", "0" * 64]):
        assert cli.main(launch + extra) == 2
        assert not (ws.root / "var/invocations").exists()
    assert cli.main(launch) == 0, outputs[-1]
    result = outputs[-1]
    assert cli.main(launch) != 0
    for i, error in (
        (1, RuntimeError("test interruption")),
        (2, harness.DiagnosticTimeoutError("test deadline")),
    ):
        owned = harness._create_invocation_ownership(
            ws.output_root, ws.root, 424242, invocation_id=plan.attempts[i].invocation_id, plan=plan
        )
        harness._retain_interrupted_evidence(ws.root, owned, error)
    # A legacy launch with the same inputs and planned ID cannot contribute to the plan.
    assert cli.main(["diagnostic", "--invocation-id", plan.attempts[4].invocation_id]) == 0
    assert cli.main(read) == cli.main(read) == 0
    report = outputs[-1]
    assert report == outputs[-2]
    assert report["plan_sha256"] == pin
    rows = report["attempts"]
    assert [r["status"] for r in rows] == [
        "COMPLETED",
        "FAILED",
        "TIMED_OUT",
        "INCOMPLETE",
        "INVALID",
    ]
    assert [r["attempt_id"] for r in rows] == [r.attempt_id for r in plan.attempts]
    assert rows[0]["observed"] == rows[0]["expected"]
    assert rows[0]["observed_seed"] == rows[0]["seed"]
    assert rows[0]["observed_plan_sha256"] == pin
    assert rows[-1]["retained_status"] == "COMPLETED" and rows[-1]["observed_plan_sha256"] is None
    assert all(row["metrics"] is None for row in rows[1:])
    assert report["completion_fraction"]["value"] == 1 / 5
    for attempt in doc["attempts"]:
        attempt["cell_id"] = "replacement"
    path.write_bytes(canonical_json_bytes(doc))
    assert cli.main(read) == 2
    assert cli.main(read[:3]) == 0
    assert outputs[-1]["attempts"][0]["reason"] == "plan_binding_mismatch"
    assert outputs[-1]["observed_counts"] is None
    path.write_bytes(canonical_json_bytes(plan))
    status = Path(result["run_dir"]) / "status.json"
    value = json.loads(status.read_bytes())
    value.update(completion_status="FAILED", error_type="RuntimeError")
    status.write_bytes(canonical_json_bytes(value))
    assert cli.main(read) == 0
    assert outputs[-1]["attempts"][0]["status"] == "INVALID"
    assert outputs[-1]["observed_counts"] is None


@pytest.mark.negative
def test_plan_schema_and_order(isolated_workspace: IsolatedWorkspace) -> None:
    ws = isolated_workspace
    doc = example(ws)
    path = ws.root / "plan.json"
    path.write_bytes(canonical_json_bytes(doc))
    plan, digest = load_register(path, ws.root, ComparisonPlan, None)
    doc["attempts"].reverse()
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert load_register(path, ws.root, ComparisonPlan, None)[1] != digest
    for field in ("attempt_id", "invocation_id", "seed", "comparison_mode"):
        changed = plan.model_dump()
        if field in ("attempt_id", "invocation_id"):
            changed["attempts"][0][field] = changed["attempts"][1][field]
        else:
            changed["attempts"][0][field] = 424243 if field == "seed" else "system_level"
        with pytest.raises(ValueError):
            ComparisonPlan.model_validate(changed)
    for data in (
        b"[" * 500 + b"]" * 500,
        b" " * 65537,
        b'{"format":"x","format":"y"}',
        canonical_json_bytes({**doc, "unknown": 0}),
    ):
        path.write_bytes(data)
        with pytest.raises(ValueError):
            registered_metrics(path, ws.root, ws.repo_root, None, planned=True)


@pytest.mark.reproducibility
def test_distinct_controlled_cells_on_the_same_script(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = isolated_workspace
    monkeypatch.setattr(harness, "__file__", str(ws.repo_root / "src/pacd_sim/harness/run.py"))
    doc = example(ws)
    doc["attempts"] = doc["attempts"][:2]
    scenario, policy, seeds, _, metrics = controlled_config_files(ws.config_root)
    defenders = [
        ws.config_root / "defenders" / filename
        for filename in ("static_review.yaml", "pacd_corroborated_review.yaml")
    ]
    for attempt, defender in zip(doc["attempts"], defenders, strict=True):
        hashes = harness.validate_diagnostic_configuration_files(
            ws.repo_root, scenario_file=scenario.name, defender_file=defender.name
        )
        attempt["cell_id"] = defender.stem
        attempt["expected"]["condition"] = harness.load_yaml_config(defender)["name"]
        attempt["expected"]["config_sha256"] = hashes["config_hash"]
    path = ws.root / "plan.json"
    path.write_bytes(canonical_json_bytes(doc))
    plan, pin = load_register(path, ws.root, ComparisonPlan, canonical_sha256(doc))
    for attempt, defender in zip(plan.attempts, defenders, strict=True):
        harness._run_diagnostic_in_process(
            scenario,
            policy,
            seeds,
            ws.output_root,
            seed=attempt.seed,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            baseline_path=defender,
            metric_path=metrics,
            invocation_id=attempt.invocation_id,
            plan=plan,
        )
    report: Any = registered_metrics(path, ws.root, ws.repo_root, pin, planned=True)
    first, second = report["attempts"]
    assert first["status"] == second["status"] == "COMPLETED"
    assert first["observed"]["events_sha256"] == second["observed"]["events_sha256"]
    assert first["observed"]["config_sha256"] != second["observed"]["config_sha256"]
    assert [r["observed"] for r in report["attempts"]] == [
        a.expected.model_dump() for a in plan.attempts
    ]

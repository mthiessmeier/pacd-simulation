"""Check per-episode metrics, their denominator and the verified release boundary."""

import json
from typing import Any

import pytest
from conftest import DiagnosticRuns, IsolatedWorkspace, controlled_config_files

from pacd_sim import cli
from pacd_sim.harness.run import _run_diagnostic_in_process
from pacd_sim.metrics.dispositions import episode_dispositions
from pacd_sim.reproducibility import verify
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.receipts import ReceiptVerification


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("fixture", "defender", "approvals", "escalations", "prohibitions"),
    [
        ("identity_smoke", "diagnostic_baseline", 1, 1, 1),
        ("identity_smoke", "pacd_corroborated_review", 0, 0, 0),
        ("repeated_readings", "pacd_corroborated_review", 0, 1, 0),
        ("repeated_readings", "static_review", 0, 4, 0),
    ],
)
def test_metrics_report_from_verified_run(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    defender: str,
    approvals: int,
    escalations: int,
    prohibitions: int,
) -> None:
    ws = isolated_workspace
    _, policy, seeds, _, metrics = controlled_config_files(ws.config_root)
    result = _run_diagnostic_in_process(
        ws.config_root / f"scenarios/diagnostic_{fixture}.yaml",
        policy,
        seeds,
        ws.output_root,
        baseline_path=ws.config_root / f"defenders/{defender}.yaml",
        metric_path=metrics,
        repo_root=ws.repo_root,
        workspace_root=ws.root,
        seed=424242,
    )
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    reports: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", reports.append)
    assert cli.main(["metrics", str(result.run_dir), "--workspace-root", str(ws.root)]) == 0
    report = reports[0]
    assert report["execution_identity_assured"] and report["status"] == "VERIFIED"
    assert (
        report["run_id"] == result.run_id
        and report["raw_semantic_hash"] == result.raw_semantic_hash
    )
    assert report["summary_semantic_hash"] == result.summary_semantic_hash
    expected_candidates = approvals + escalations + prohibitions
    expected = {
        "format": "pacd-episode-dispositions-v1",
        "seed": 424242,
        "config_hash": result.config_hash,
        "completion_status": "EVENT_CHAIN_COMPLETED",
        "counts": {
            "candidate_action_count": expected_candidates,
            "approved_action_count": approvals,
            "escalated_action_count": escalations,
            "prohibited_action_count": prohibitions,
            "simulated_execution_count": approvals,
            "verified_execution_count": approvals,
            "prohibited_execution_count": 0,
        },
        "escalation_fraction": {
            "numerator": escalations,
            "denominator": expected_candidates,
            "unit": "fraction_of_candidate_actions",
            "value": escalations / expected_candidates if expected_candidates else None,
        },
    }
    assert report["metrics"] == expected and report["metrics_sha256"] == canonical_sha256(expected)
    raw = [
        json.loads(line) for line in (result.run_dir / "raw/events.jsonl").read_bytes().splitlines()
    ]
    assert (
        len({r["action_id"] for r in raw if r["event_type"] == "candidate_action"})
        == expected_candidates
    )


@pytest.mark.reproducibility
def test_metrics_digest_is_stable_across_run_ids_and_bound_to_seed(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    for run in (
        diagnostic_runs.same_seed_a,
        diagnostic_runs.same_seed_b,
        diagnostic_runs.different_seed,
    ):
        assert cli.main(["metrics", str(run.run_dir)]) == 0
    assert len({r["run_id"] for r in output}) == 3
    assert output[0]["metrics_sha256"] == output[1]["metrics_sha256"]
    assert output[0]["metrics_sha256"] != output[2]["metrics_sha256"]


@pytest.mark.negative
def test_invalid_receipt_withholds_metrics(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    monkeypatch.setattr(
        verify,
        "verify_execution_receipt",
        lambda **_: ReceiptVerification(False, ("missing receipt",), None),
    )
    monkeypatch.setattr(
        cli, "episode_dispositions", lambda _: pytest.fail("Released invalid summary")
    )
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    run = diagnostic_runs.same_seed_a
    assert cli.main(["metrics", str(run.run_dir)]) == 1
    assert output[0]["status"] == "INVALID" and not output[0]["execution_identity_assured"]
    assert output[0]["run_dir"] == str(run.run_dir) and output[0]["errors"]
    assert {"metrics", "metrics_sha256", "run_id"}.isdisjoint(output[0])


def test_incomplete_and_unaccounted_counts_fail_and_zero_escalations_is_measurable(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    ws = diagnostic_runs.workspace
    verified, material = verify.verify_run_with_summary(
        run.run_dir, ws.root, repo_root=ws.repo_root
    )
    assert verified.valid and material is not None
    episode = material.episode
    with pytest.raises(ValueError, match="completed episode"):
        episode_dispositions(episode.model_copy(update={"completion_status": "INCOMPLETE"}))
    with pytest.raises(ValueError, match="every candidate"):
        episode_dispositions(episode.model_copy(update={"candidate_action_count": 8}))
    result = episode_dispositions(
        episode.model_copy(update={"approved_action_count": 2, "escalated_action_count": 0})
    )
    assert result["escalation_fraction"] == {
        "numerator": 0,
        "denominator": 3,
        "unit": "fraction_of_candidate_actions",
        "value": 0.0,
    }

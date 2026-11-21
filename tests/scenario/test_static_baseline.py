"""The fixed triage rule sees only the verified delivery-time projection."""

import json
from math import inf, nextafter

import pytest
from conftest import DiagnosticRuns
from pydantic import ValidationError

from pacd_sim import cli
from pacd_sim.defenders.base import BaselineObservation
from pacd_sim.defenders.baselines.static import propose_review
from pacd_sim.reproducibility import verify
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.receipts import ReceiptVerification


@pytest.mark.parametrize(
    ("signal", "subject", "expected_target"),
    [
        (nextafter(0.75, 0.0), "observed-subject", None),
        (0.75, "observed-subject", "observed-subject"),
        (nextafter(0.75, inf), "observed-subject", "observed-subject"),
        (1.0, None, None),
    ],
)
def test_fixed_review_threshold(
    signal: float, subject: str | None, expected_target: str | None
) -> None:
    proposal = propose_review(BaselineObservation(tick=4, subject_id=subject, signal=signal))
    if expected_target is None:
        assert proposal is None
    else:
        assert proposal is not None
        assert proposal.model_dump() == {
            "action_type": "require_human_review",
            "requested_authority": "human",
            "target_id": expected_target,
        }


def test_projection_excludes_evaluator_fields() -> None:
    with pytest.raises(ValidationError, match="event_kind"):
        BaselineObservation.model_validate(
            {
                "tick": 2,
                "subject_id": "subject",
                "signal": 0.99,
                "event_kind": "simulated_adversary",
            }
        )


@pytest.mark.reproducibility
def test_baseline_cli_replays_only_verified_sensor_fields(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    output: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    traces = []
    for run in (
        diagnostic_runs.same_seed_a,
        diagnostic_runs.same_seed_b,
        diagnostic_runs.different_seed,
    ):
        assert cli.main(["baseline", str(run.run_dir)]) == 0
        report = output[-1]
        assert report["raw_semantic_hash"] == run.raw_semantic_hash and report["valid"] is True
        raw = [
            json.loads(line)
            for line in (run.run_dir / "raw/events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        observed = [
            {
                "tick": int(row["tick"]),
                "subject_id": row["entity_id"],
                "signal": json.loads(row["payload_json"])["signal"],
            }
            for row in raw
            if row["event_type"] == "observation"
        ]
        trace = report["baseline"]
        assert isinstance(trace, dict)
        assert trace["observation_sha256"] == canonical_sha256(observed)
        assert (trace["mode"], trace["observation_count"], trace["proposal_count"]) == (
            "retrospective_proposals",
            2,
            1,
        )
        assert trace["decisions"] == [
            {"observation": observed[0], "proposal": None},
            {
                "observation": observed[1],
                "proposal": {
                    "target_id": "identity-synthetic-user",
                    "action_type": "require_human_review",
                    "requested_authority": "human",
                },
            },
        ]
        traces.append(trace)
    assert traces[0] == traces[1]
    assert traces[0]["observation_sha256"] != traces[2]["observation_sha256"]


@pytest.mark.negative
def test_invalid_receipt_withholds_baseline_and_skips_policy(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    monkeypatch.setattr(
        verify,
        "verify_execution_receipt",
        lambda **_: ReceiptVerification(False, ("missing receipt",), None),
    )
    monkeypatch.setattr(cli, "propose_review", lambda _: pytest.fail("evaluated an unverified run"))
    output: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "_emit_json", output.append)
    assert cli.main(["baseline", str(diagnostic_runs.same_seed_a.run_dir)]) == 1
    assert output[0]["status"] == "INVALID" and "baseline" not in output[0]

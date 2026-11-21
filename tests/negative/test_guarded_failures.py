"""Retain guarded dispatch faults in the normal invocation and comparison ledger."""

import json

import pyarrow.parquet as pq
import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.comparison import ComparisonInputs, ComparisonPlan, PlannedAttempt, RegisteredAttempt
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.harness import run as harness
from pacd_sim.metrics.registered import AttemptRegister, registered_metrics
from pacd_sim.oversight import guarded
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.receipts import receipt_path_for
from pacd_sim.reproducibility.reportable import git_commit
from pacd_sim.state.snapshot import StateSnapshot, create_snapshot


@pytest.mark.negative
@pytest.mark.parametrize(
    ("fault", "outcomes"),
    [
        ("authorization_exception", ["pending", "approved", "authorization_failed"]),
        (
            "measurement_exception",
            [
                "pending",
                "approved",
                "executed",
                "verified",
                "mission_measurement_failed",
                "rolled_back",
                "mission_measurement_failed",
            ],
        ),
        ("broker_refusal", ["pending", "approved", "execution_failed"]),
        ("broker_exception", ["pending", "approved", "execution_failed"]),
        (
            "verifier_exception",
            ["pending", "approved", "executed", "verification_failed", "rolled_back"],
        ),
        (
            "recovery_exception",
            ["pending", "approved", "executed", "verification_failed", "rollback_failed"],
        ),
    ],
)
def test_guarded_fault_retains_partial_ledger_and_withholds_measurements(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    outcomes: list[str],
) -> None:
    ws = isolated_workspace
    _, policy, seeds, _, metrics = controlled_config_files(ws.config_root)
    scenario = ws.config_root / "scenarios/diagnostic_guarded_adverse.yaml"
    baseline = ws.config_root / "defenders/static_review.yaml"
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=scenario.name, defender_file=baseline.name
    )
    attempt = RegisteredAttempt(attempt_id="attempt-fault", invocation_id="a" * 32, seed=424242)
    planned_attempt = PlannedAttempt(
        **attempt.model_dump(),
        cell_id="guarded-adverse-static",
        comparison_mode="controlled",
        expected=ComparisonInputs(
            scenario="diagnostic_guarded_adverse",
            condition="static_signal_review_v1",
            code_commit=git_commit(ws.repo_root),
            config_sha256=hashes["config_hash"],
            seed_registry_sha256=hashes["seed_registry_hash"],
            events_sha256=canonical_sha256(harness.load_yaml_config(scenario)["events"]),
        ),
    )
    plan = ComparisonPlan(
        format="pacd-development-comparison-plan-v1",
        evidence_label="NON_REPORTABLE_DIAGNOSTIC",
        attempts=(planned_attempt,),
    )
    # The hermetic fixture contains its own committed copy of the controlled inputs.
    monkeypatch.setattr(harness, "__file__", str(ws.repo_root / "src/pacd_sim/harness/run.py"))

    def raise_fault(*_args: object) -> None:
        raise TypeError("injected simulated operation failure")

    if fault == "authorization_exception":

        def fault_at_dispatch(state: EnvironmentState) -> StateSnapshot:
            if state.tick == 4:
                raise TypeError("injected simulated operation failure")
            return create_snapshot(state)

        monkeypatch.setattr(guarded, "create_snapshot", fault_at_dispatch)
    elif fault == "measurement_exception":
        monkeypatch.setattr(guarded, "mission_effect", raise_fault)
    elif fault == "broker_refusal":
        monkeypatch.setattr(SimulatedExecutionBroker, "supported_action_types", frozenset())
    elif fault == "broker_exception":
        monkeypatch.setattr(SimulatedExecutionBroker, "execute", raise_fault)
    else:
        monkeypatch.setattr(guarded, "verify_execution", raise_fault)
        if fault == "recovery_exception":
            monkeypatch.setattr(guarded, "rollback_execution", raise_fault)

    with pytest.raises(RuntimeError, match="Guarded review failed"):
        harness._run_diagnostic_in_process(
            scenario,
            policy,
            seeds,
            ws.output_root,
            repo_root=ws.repo_root,
            workspace_root=ws.root,
            baseline_path=baseline,
            metric_path=metrics,
            seed=attempt.seed,
            invocation_id=attempt.invocation_id,
            plan=plan,
        )
    (run,) = ws.output_root.iterdir()
    assert json.loads((run / "status.json").read_text())["completion_status"] == "FAILED"
    assert not receipt_path_for(ws.root, attempt.invocation_id).exists()
    assert not (run / "derived/episode_summary.parquet").exists()
    rows = pq.read_table(run / "raw/events.parquet").to_pylist()
    assert rows == [
        json.loads(line) for line in (run / "raw/events.jsonl").read_text().splitlines()
    ]
    ledger = [row for row in rows if row["event_type"] == "guarded_review"]
    assert [row["outcome"] for row in ledger] == outcomes
    assert [row["tick"] for row in ledger] == [2] + [4] * (len(ledger) - 1)
    last = json.loads(ledger[-1]["payload_json"])
    if fault == "broker_exception":
        assert last["state_after_digest"] is None
    elif fault == "broker_refusal":
        assert last["state_after_digest"] == last["state_before_digest"]
    elif fault in {"verifier_exception", "recovery_exception"}:
        assert last["exact_prestate_restored"] is (fault == "verifier_exception")
    if fault != "broker_refusal":
        assert any(
            json.loads(row["payload_json"]).get("error_type") == "TypeError" for row in ledger
        )
    assert rows[-1] == ledger[-1]

    register = AttemptRegister(format="pacd-attempt-register-v1", attempts=(attempt,))
    for name, definition in (("register", register), ("plan", plan)):
        path = ws.root / f"{name}.json"
        path.write_bytes(canonical_json_bytes(definition))
        report = registered_metrics(
            path, ws.root, ws.repo_root, canonical_sha256(definition), planned=name == "plan"
        )
        statuses = report["status_counts"]
        fraction = report["completion_fraction"]
        attempts = report["attempts"]
        assert isinstance(statuses, dict) and statuses["FAILED"] == 1
        assert isinstance(fraction, dict) and isinstance(attempts, list) and len(attempts) == 1
        assert fraction["denominator"] == 1
        assert fraction["numerator"] == 0
        assert report["observed_counts"] is None
        (observed,) = attempts
        assert observed["metrics"] is None and observed["metrics_sha256"] is None
        if name == "plan":
            assert observed["observed_plan_sha256"] == canonical_sha256(plan)
            assert observed["retained_status"] == "FAILED"


@pytest.mark.negative
def test_scripted_baseline_rejected_before_guarded_invocation(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ws = isolated_workspace
    _, policy, seeds, baseline, _ = controlled_config_files(ws.config_root)
    with pytest.raises(harness.ConfigurationError, match="requires a review-proposing baseline"):
        harness.run_diagnostic(
            ws.config_root / "scenarios/diagnostic_guarded_benign.yaml",
            policy,
            seeds,
            ws.output_root,
            repo_root=ws.repo_root,
            workspace_root=ws.root,
            baseline_path=baseline,
        )
    assert list(ws.output_root.iterdir()) == []
    assert not (ws.root / "var/invocations").exists()
    assert not (ws.root / "var/receipts").exists()

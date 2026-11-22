"""Selection boundaries for matched policies and the independent review configuration."""

import json
import subprocess

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.comparison import ComparisonInputs, ComparisonPlan, PlannedAttempt
from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.environment.model import EnvironmentState, Identity, MissionFunction, Service, Session
from pacd_sim.evidence.context import EvidenceReading
from pacd_sim.harness import run as harness
from pacd_sim.harness.run import ConfigurationError, _run_diagnostic_in_process
from pacd_sim.polymorphism.selection import select_profile
from pacd_sim.polymorphism.sensing import project_sensing_observation, sensing_decision
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.receipts import receipt_path_for
from pacd_sim.reproducibility.reportable import git_commit
from pacd_sim.telemetry.generator import Observation


@pytest.mark.parametrize(
    ("policy", "subject", "signal", "ordinal", "cost", "budget", "expected"),
    [
        ("fixed", "s", 0.2, 1, 0.75, 1.0, "proposed"),
        ("adaptive", "s", 0.2, 1, 0.75, 1.0, "no_positive_gain"),
        ("adaptive", "s", 0.5, 1, 0.5, 0.5, "no_positive_gain"),
        ("adaptive", "s", 0.75, 1, 0.5, 0.5, "proposed"),
        ("disabled", "s", 1.0, 1, 0.0, 1.0, "disabled"),
        ("fixed", "s", 1.0, 1, 0.75, 0.5, "over_budget"),
        ("adaptive", "s", 1.0, 1, 0.75, 0.5, "over_budget"),
        ("fixed", None, 1.0, 1, 0.0, 1.0, "no_subject"),
        ("adaptive", "s", 1.0, 2, 0.0, 1.0, "outside_opportunity"),
    ],
)
def test_one_opportunity_and_zero_cost_reference(
    policy: str,
    subject: str | None,
    signal: float,
    ordinal: int,
    cost: float,
    budget: float,
    expected: str,
) -> None:
    reading = BaselineObservation(tick=1, subject_id=subject, signal=signal)
    assert sensing_decision(f"sensing_{policy}_v1", reading, ordinal, cost, budget) == expected


@pytest.mark.parametrize(
    ("subject", "sibling_active", "expected"),
    [
        ("user", False, 0.86),
        ("main-session", True, 0.86),
        ("user", True, 0.9),
    ],
)
def test_precision_uses_the_same_eligible_subject_as_admission(
    subject: str, sibling_active: bool, expected: float
) -> None:
    state = EnvironmentState(
        identities=(Identity(id="user", role="user"),),
        sessions=(
            Session(
                id="main-session",
                identity_id="user",
                service_id="service",
                sensing_profile="alternate",
            ),
            Session(id="sibling", identity_id="user", service_id="service", active=sibling_active),
        ),
        services=(Service(id="service", mission_id="mission"),),
        mission_functions=(MissionFunction(id="mission", criticality=0.5),),
    )
    raw = Observation(
        id="reading",
        event_id="event",
        event_tick=0,
        event_kind="benign_administrative",
        sensor_id="sensor",
        target_id=subject,
        signal=0.86,
    )
    delivered, details = project_sensing_observation(raw, state)
    assert delivered.signal == expected and details["latent_signal"] == raw.signal
    assert details["sensing_profile"] == ("alternate" if expected == 0.86 else "default")


@pytest.mark.negative
@pytest.mark.parametrize(
    ("scenario", "baseline", "policy"),
    [
        ("diagnostic_sensing_nominal", "static_review", "diagnostic_sensing"),
        ("diagnostic_guarded_benign", "sensing_fixed", "diagnostic_safety"),
        ("diagnostic_sensing_nominal", "sensing_fixed", "diagnostic_safety"),
        ("diagnostic_identity_smoke", "diagnostic_baseline", "diagnostic_sensing"),
        ("diagnostic_sensing_delayed", "sensing_fixed", "diagnostic_sensing"),
    ],
)
def test_sensing_controls_must_match_before_invocation(
    isolated_workspace: IsolatedWorkspace,
    scenario: str,
    baseline: str,
    policy: str,
) -> None:
    ws = isolated_workspace
    _, _, seeds, _, metrics = controlled_config_files(ws.config_root)
    with pytest.raises(ConfigurationError):
        _run_diagnostic_in_process(
            ws.config_root / f"scenarios/{scenario}.yaml",
            ws.config_root / f"policies/{policy}.yaml",
            seeds,
            ws.output_root,
            baseline_path=ws.config_root / f"defenders/{baseline}.yaml",
            metric_path=metrics,
            seed=424242,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
        )
    assert not any(ws.output_root.iterdir())
    assert not (ws.root / "var/invocations").exists()


@pytest.mark.negative
@pytest.mark.parametrize(
    ("role", "mutation", "route"),
    [
        ("scenario", "alias", "planned"),
        ("baseline", "alias", "normal"),
        ("policy", "wrong_directory", "denial"),
        ("scenario", "wrong_directory", "normal"),
        ("baseline", "different_condition", "planned"),
        ("scenario", "different_condition", "denial"),
    ],
)
def test_copied_or_relabelled_sensing_controls_cannot_allocate(
    isolated_workspace: IsolatedWorkspace,
    role: str,
    mutation: str,
    route: str,
) -> None:
    ws = isolated_workspace
    paths = {
        "scenario": ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml",
        "baseline": ws.config_root / "defenders/sensing_fixed.yaml",
        "policy": ws.config_root / "policies/diagnostic_sensing.yaml",
    }
    _, _, seeds, _, metrics = controlled_config_files(ws.config_root)
    hashes = harness.validate_diagnostic_configuration_files(
        ws.repo_root, scenario_file=paths["scenario"].name, defender_file=paths["baseline"].name
    )
    invocation = "b" * 32
    attempt = PlannedAttempt(
        attempt_id="source",
        invocation_id=invocation,
        seed=424242,
        cell_id="fixed-nominal",
        comparison_mode="controlled",
        expected=ComparisonInputs(
            scenario="diagnostic_sensing_nominal",
            condition="sensing_fixed_v1",
            code_commit=git_commit(ws.repo_root),
            config_sha256=hashes["config_hash"],
            seed_registry_sha256=hashes["seed_registry_hash"],
            events_sha256=canonical_sha256(harness.load_yaml_config(paths["scenario"])["events"]),
        ),
    )
    plan = ComparisonPlan(
        format="pacd-development-comparison-plan-v1",
        evidence_label="NON_REPORTABLE_DIAGNOSTIC",
        attempts=(attempt,),
    )
    original = paths[role]
    if mutation == "different_condition":
        other = original.name.replace("fixed", "adaptive").replace("nominal", "costly")
        original.write_bytes(original.with_name(other).read_bytes())
    else:
        shadow = ws.config_root / "copies"
        shadow.mkdir()
        paths[role] = shadow / (original.name if mutation == "wrong_directory" else "alias.yaml")
        paths[role].write_bytes(original.read_bytes())
    with pytest.raises(ConfigurationError, match="governed filenames"):
        harness.run_diagnostic(
            paths["scenario"],
            paths["policy"],
            seeds,
            ws.output_root,
            baseline_path=paths["baseline"],
            metric_path=metrics,
            seed=424242,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            plan=plan if route == "planned" else None,
            reportable=route == "denial",
            invocation_id=invocation,
        )
    assert not any(ws.output_root.iterdir())
    assert not (ws.root / "var/invocations").exists()
    assert not (ws.root / "var/receipts").exists()


@pytest.mark.negative
@pytest.mark.parametrize(
    ("violation", "condition", "reason"),
    [
        ("disabled", "disabled", "operator disabled by ablation"),
        ("budget", "fixed", "switch cost exceeds the episode budget"),
        ("late", "adaptive", "decision opportunity consumed"),
        ("early", "contextual", "decision opportunity consumed"),
        ("stale", "scheduled", "evidence is outside the selection freshness window"),
        ("mismatch", "contextual", "selection does not identify the proposed profile"),
    ],
)
def test_faulty_proposal_cannot_spend_outside_evaluator_envelope(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    violation: str,
    condition: str,
    reason: str,
) -> None:
    ws = isolated_workspace
    fixture = "delayed" if violation == "stale" else "nominal"
    scenario = ws.config_root / f"scenarios/diagnostic_sensing_{fixture}.yaml"
    if violation == "budget":
        scenario.write_text(
            scenario.read_text().replace("budget: 1.0", "budget: 0.0"), encoding="utf-8"
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=PACD Test",
                "-c",
                "user.email=pacd-test@example.invalid",
                "commit",
                "-qm",
                "zero diagnostic budget",
                "--",
                str(scenario.relative_to(ws.repo_root)),
            ],
            cwd=ws.repo_root,
            check=True,
        )

    def faulty(
        policy: str, reading: BaselineObservation, ordinal: int, cost: float, budget: float
    ) -> str:
        return "no_positive_gain" if violation == "late" and ordinal == 1 else "proposed"

    monkeypatch.setattr(harness, "sensing_decision", faulty)

    def faulty_selection(
        policy: str, prefix: tuple[EvidenceReading, ...], cost: float, budget: float
    ) -> tuple[str, dict[str, object]]:
        outcome, detail = select_profile(policy, prefix, cost, budget)
        if violation == "early" or len(prefix) == 3:
            detail["selection_reason"] = "proposed"
            detail["selected_profile"] = "default" if violation == "mismatch" else "alternate"
            return "proposed", detail
        return outcome, detail

    monkeypatch.setattr(harness, "select_profile", faulty_selection)
    _, _, seeds, _, metrics = controlled_config_files(ws.config_root)
    invocation = "a" * 32
    with pytest.raises(RuntimeError, match="exceeded evaluator authority"):
        _run_diagnostic_in_process(
            scenario,
            ws.config_root / "policies/diagnostic_sensing.yaml",
            seeds,
            ws.output_root,
            baseline_path=ws.config_root / f"defenders/sensing_{condition}.yaml",
            metric_path=metrics,
            seed=424242,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            invocation_id=invocation,
        )
    (run,) = ws.output_root.iterdir()
    rows = [json.loads(line) for line in (run / "raw/events.jsonl").read_bytes().splitlines()]
    assert rows[-1]["outcome"] == "inadmissible_proposal"
    assert json.loads(rows[-1]["payload_json"])["reason"] == reason
    assert all(row["event_type"] not in {"candidate_action", "guarded_review"} for row in rows)
    assert json.loads((run / "status.json").read_bytes())["completion_status"] == "FAILED"
    assert not receipt_path_for(ws.root, invocation).exists()

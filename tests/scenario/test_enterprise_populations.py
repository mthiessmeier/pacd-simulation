"""Exercise the configured enterprise population endpoints on the governed mission clock."""

import json
from pathlib import Path

import pytest
from conftest import CONFIG_ROOT, IsolatedWorkspace

from pacd_sim.configuration import ScenarioConfig
from pacd_sim.environment.availability import evaluate_availability
from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256

from .test_approval_burden import Command


@pytest.mark.scenario
@pytest.mark.parametrize("size", [30, 100])
def test_enterprise_population_reset_and_reference_integrity(size: int) -> None:
    scenario = CONFIG_ROOT / f"scenarios/diagnostic_enterprise_{size}.yaml"
    config = ScenarioConfig.model_validate(harness.load_yaml_config(scenario))
    state = harness._build_environment(config, config.protocol_version)
    initial_digest = canonical_sha256(state)
    labels = [f"{index:03d}" for index in range(1, size + 1)]
    assert [identity.id for identity in state.identities] == [f"identity-{i}" for i in labels]
    assert [(s.id, s.identity_id, s.service_id) for s in state.sessions] == [
        (f"session-{i}", f"identity-{i}", f"service-{i}") for i in labels
    ]
    assert [(s.id, s.mission_id) for s in state.services] == [
        (f"service-{i}", "mission-target" if i == labels[-1] else "mission-reference")
        for i in labels
    ]
    assert [(d.upstream_id, d.downstream_id, d.weight) for d in state.dependencies] == [
        (f"session-{i}", f"service-{i}", 1.0) for i in labels
    ]
    assert [(event.tick, event.identity_id) for event in config.events] == [
        (1, f"identity-{size:03d}"),
        (4, "identity-001"),
    ]

    target = state.sessions[-1]
    isolated = state.isolate_session(target.id)
    assert set(evaluate_availability(isolated).unavailable_entity_ids) == {
        target.id,
        target.service_id,
        "mission-target",
    }
    assert canonical_sha256(isolated.restore_session(target)) == initial_digest
    reset = harness._build_environment(harness.load_yaml_config(scenario), config.protocol_version)
    assert reset == state and canonical_sha256(reset) == initial_digest


@pytest.mark.negative
@pytest.mark.parametrize(
    ("collection", "field", "substitute", "reason"),
    [
        ("sessions", "identity_id", "identity-101", "unknown identity"),
        ("services", "mission_id", "mission-unknown", "unknown mission"),
        ("dependencies", "id", "identity-100", "globally unique"),
    ],
)
def test_invalid_last_population_member_is_rejected(
    isolated_workspace: IsolatedWorkspace, collection: str, field: str, substitute: str, reason: str
) -> None:
    path = isolated_workspace.config_root / "scenarios/diagnostic_enterprise_100.yaml"
    config = harness.load_yaml_config(path)
    rows = config[collection]
    assert isinstance(rows, list) and len(rows) == 100
    rows[-1][field] = substitute
    path.write_bytes(canonical_json_bytes(config))
    with pytest.raises(harness.ConfigurationError, match=reason):
        harness.validate_diagnostic_configuration_files(
            isolated_workspace.repo_root,
            scenario_file=path.name,
            defender_file="static_review.yaml",
        )


@pytest.mark.reproducibility
@pytest.mark.parametrize("size", [30, 100])
@pytest.mark.parametrize("condition", ["static_review", "pacd_corroborated_review"])
def test_population_guarded_mission_and_replay(
    isolated_workspace: IsolatedWorkspace, command: Command, size: int, condition: str
) -> None:
    ws = isolated_workspace
    launch = [
        "diagnostic",
        "--scenario",
        str(ws.config_root / f"scenarios/diagnostic_enterprise_{size}.yaml"),
        "--baseline",
        str(ws.config_root / f"defenders/{condition}.yaml"),
        "--seed",
        "424242",
    ]
    run = command(*launch)
    verified = command("metrics", run["run_dir"], "--function-availability")
    assert verified["semantic_content_valid"] and verified["execution_identity_assured"]
    raw = Path(run["run_dir"]) / "raw/events.jsonl"
    reviews = [
        r
        for line in raw.read_bytes().splitlines()
        if (r := json.loads(line))["event_type"] == "guarded_review"
    ]
    isolated = condition == "static_review"
    executions = [r for r in reviews if r["outcome"] == "executed"]
    assert [(e["tick"], e["entity_id"]) for e in executions] == (
        [(6, f"identity-{size:03d}")] if isolated else []
    )
    if isolated:
        pending = next(r for r in reviews if r["outcome"] == "pending")
        assert json.loads(pending["payload_json"])["binding"]["action"]["target_id"] == (
            f"session-{size:03d}"
        )
        replay = command(*launch)
        assert run["run_id"] != replay["run_id"]
        for field in ("config_hash", "raw_semantic_hash", "summary_semantic_hash"):
            assert run[field] == replay[field]
        repeated = command("metrics", replay["run_dir"], "--function-availability")
        assert repeated["execution_identity_assured"]
        assert repeated["metrics_sha256"] == verified["metrics_sha256"]
    availability = verified["metrics"]["guarded_review"]["function_availability"]
    assert [
        (m["mission_id"], m["available_ticks"], m["possible_ticks"])
        for m in availability["per_mission"]
    ] == [
        ("mission-reference", 8, 8),
        ("mission-target", 6 if isolated else 8, 8),
    ]

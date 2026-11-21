"""Configured synthetic dependencies survive state transitions and diagnostic verification."""

import json
import subprocess
from sys import float_info

import pytest
import yaml
from conftest import CONFIG_ROOT, IsolatedWorkspace, controlled_config_files

from pacd_sim.configuration import ScenarioConfig
from pacd_sim.environment.model import (
    Dependency,
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.harness.run import (
    ConfigurationError,
    RunResult,
    _run_diagnostic_in_process,
    load_yaml_config,
    run_diagnostic,
    validate_diagnostic_configuration_files,
)
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.verify import verify_run

SERVICE = "service-synthetic-saas"
MISSION = "mission-synthetic-core"
SESSION = "session-synthetic-001"
USER = "identity-synthetic-user"
EDGE = {"id": "dependency-a", "upstream_id": SERVICE, "downstream_id": MISSION, "weight": 0.0}


def _write_dependencies(workspace: IsolatedWorkspace, dependencies: object) -> None:
    scenario = controlled_config_files(workspace.config_root)[0]
    with scenario.open("a", encoding="utf-8") as stream:
        stream.write("\n")
        yaml.safe_dump({"dependencies": dependencies}, stream, sort_keys=False)


def _run(workspace: IsolatedWorkspace, *, in_process: bool = False) -> RunResult:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    # The spawned worker is bound to the author workspace. Run the positive fixture
    # in process so the normal allocation, finalization and verification stay hermetic.
    runner = _run_diagnostic_in_process if in_process else run_diagnostic
    return runner(
        scenario,
        policy,
        seeds,
        workspace.output_root,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
        seed=424242,
    )


def _expected_state(weight: int | float = 2.5) -> EnvironmentState:
    return EnvironmentState(
        identities=(
            Identity(id="identity-synthetic-admin", role="synthetic_administrator"),
            Identity(id=USER, role="synthetic_user"),
        ),
        sessions=(Session(id=SESSION, identity_id=USER, service_id=SERVICE),),
        services=(Service(id=SERVICE, mission_id=MISSION),),
        mission_functions=(MissionFunction(id=MISSION, criticality=0.8),),
        dependencies=(
            Dependency(
                id="dependency-z", upstream_id=SERVICE, downstream_id=MISSION, weight=weight
            ),
            Dependency(id="dependency-a", upstream_id=SERVICE, downstream_id=MISSION, weight=0.0),
        ),
    )


@pytest.mark.scenario
@pytest.mark.parametrize("weight", [2.5, 2**53 + 2], ids=["fractional", "exact-large-integer"])
def test_parallel_dependencies_reach_verified_state_updates(
    isolated_workspace: IsolatedWorkspace,
    weight: int | float,
) -> None:
    _write_dependencies(
        isolated_workspace, [{**EDGE, "id": "dependency-z", "weight": weight}, EDGE]
    )
    # Verification binds the retained configuration to a clean, committed fixture.
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "synthetic parallel dependency fixture",
            "--",
            "configs/scenarios/diagnostic_identity_smoke.yaml",
        ],
        cwd=isolated_workspace.repo_root,
        check=True,
    )
    result = _run(isolated_workspace, in_process=True)
    verified = verify_run(
        result.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    )
    assert verified.valid, verified.errors
    assert verified.semantic_content_valid and verified.execution_identity_assured
    assert verified.raw_semantic_hash == result.raw_semantic_hash

    retained = json.loads((result.run_dir / "canonical_config.json").read_text(encoding="utf-8"))
    wire_weight = retained["scenario"]["dependencies"][0]["weight"]
    assert canonical_sha256(wire_weight) == canonical_sha256(weight)
    state = _expected_state(weight)
    assert state.dependencies[1].weight == weight
    events = (result.run_dir / "raw" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    updates = [row for line in events if (row := json.loads(line))["event_type"] == "state_update"]
    assert len(updates) == 2
    for tick, row in zip((2, 3), updates, strict=True):
        assert row["tick"] == tick
        assert json.loads(row["payload_json"]) == {
            "graph_node_count": 5,
            "graph_edge_count": 5,
            "snapshot_digest": canonical_sha256(state.at_tick(tick)),
        }


def test_parallel_relationships_survive_transition_and_graph_mutation() -> None:
    state = _expected_state()
    assert tuple(d.id for d in state.dependencies) == ("dependency-a", "dependency-z")
    digest = canonical_sha256(state)
    isolated = state.isolate_session(SESSION)
    assert isolated.dependencies == state.dependencies
    graph = isolated.to_graph(multigraph=True)
    assert graph.is_directed() and graph.is_multigraph()
    overlap = list(graph[SERVICE][MISSION].values())
    assert sorted(edge["relationship"] for edge in overlap) == [
        "depends_on",
        "depends_on",
        "supports_mission",
    ]
    assert {
        edge["dependency_id"]: edge["weight"] for edge in overlap if "dependency_id" in edge
    } == {"dependency-a": 0.0, "dependency-z": 2.5}
    graph.remove_node(SERVICE)
    assert isolated.to_graph(multigraph=True).number_of_edges() == 5
    assert canonical_sha256(state) == digest
    assert isolated.restore_session(state.sessions[0]) == state


@pytest.mark.parametrize("count", [0, 100])
def test_explicit_dependency_list_boundaries(
    isolated_workspace: IsolatedWorkspace, count: int
) -> None:
    _write_dependencies(
        isolated_workspace,
        [{**EDGE, "id": f"dependency-{i}", "weight": i} for i in range(count)],
    )
    hashes = validate_diagnostic_configuration_files(isolated_workspace.repo_root)
    assert hashes["config_hash"]


def test_optional_edges_preserve_scenario_wire_hash_and_schema() -> None:
    original = load_yaml_config(controlled_config_files(CONFIG_ROOT)[0])
    schema = ScenarioConfig.model_json_schema(mode="serialization")
    assert set(original) | {"dependencies"} == set(schema["properties"])
    assert "dependencies" not in schema["required"]
    wire_hashes = set()
    variations: tuple[dict[str, object], ...] = (
        {},
        {"dependencies": []},
        {"dependencies": [{**EDGE, "weight": 2}]},
    )
    for fields in variations:
        wire = {**original, **fields}
        model = ScenarioConfig.model_validate(wire)
        restored = ScenarioConfig.model_validate_json(model.model_dump_json())
        wire_hashes.add(canonical_sha256(wire))
        assert canonical_sha256(model) == canonical_sha256(restored) == canonical_sha256(wire)
    assert len(wire_hashes) == 3


@pytest.mark.negative
@pytest.mark.parametrize(
    "dependencies",
    [
        None,
        [{**EDGE, "upstream_id": "missing-entity"}],
        [{**EDGE, "downstream_id": "missing-entity"}],
        [{**EDGE, "id": SERVICE}],
        [EDGE, EDGE],
        [{**EDGE, "weight": -0.5}],
        [{**EDGE, "weight": True}],
        [{**EDGE, "weight": "2.5"}],
        [{**EDGE, "weight": float("inf")}],
        [{**EDGE, "weight": float("nan")}],
        [{**EDGE, "weight": 10**400}],
        [{**EDGE, "weight": int(float_info.max) + 1}],
        [{**EDGE, "weight": 2**53 + 1}],
        [{k: v for k, v in EDGE.items() if k != "weight"}],
        [{**EDGE, "undeclared": True}],
        [{**EDGE, "id": f"dependency-{i}"} for i in range(101)],
    ],
    ids=[
        "null-list",
        "unknown-upstream",
        "unknown-downstream",
        "entity-id-collision",
        "duplicate-edge-id",
        "negative-weight",
        "boolean-weight",
        "string-weight",
        "infinite-weight",
        "nan-weight",
        "weight-overflow",
        "just-above-maximum-float",
        "integer-rounding",
        "missing-weight",
        "unknown-field",
        "too-many-edges",
    ],
)
def test_invalid_dependencies_fail_before_ownership(
    isolated_workspace: IsolatedWorkspace, dependencies: object
) -> None:
    _write_dependencies(isolated_workspace, dependencies)
    with pytest.raises(ConfigurationError):
        _run(isolated_workspace)
    assert not list(isolated_workspace.output_root.iterdir())
    assert not (isolated_workspace.root / "var" / "invocations").exists()
    assert not (isolated_workspace.root / "var" / "receipts").exists()

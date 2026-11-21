"""The maintenance-window script keeps its benign control active across isolation."""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.environment.model import EnvironmentState, Identity, MissionFunction, Service, Session
from pacd_sim.harness.run import _run_diagnostic_in_process
from pacd_sim.reproducibility.canonical import canonical_sha256

ADMIN = "identity-maint-admin"
USER = "identity-maint-user"
ADMIN_SESSION = "session-maint-admin"
USER_SESSION = "session-maint-user"
SERVICE = "service-maint-console"
MISSION = "mission-maint-core"


def _expected_state(*, isolated_user: bool) -> EnvironmentState:
    return EnvironmentState(
        identities=(
            Identity(id=ADMIN, role="synthetic_administrator"),
            Identity(id=USER, role="synthetic_user"),
        ),
        sessions=(
            Session(id=ADMIN_SESSION, identity_id=ADMIN, service_id=SERVICE, active=True),
            Session(
                id=USER_SESSION,
                identity_id=USER,
                service_id=SERVICE,
                active=not isolated_user,
                isolated=isolated_user,
            ),
        ),
        services=(Service(id=SERVICE, mission_id=MISSION),),
        mission_functions=(MissionFunction(id=MISSION, criticality=0.8),),
    )


@pytest.mark.scenario
def test_maintenance_script_replays_with_its_benign_control_intact(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = isolated_workspace
    scenario = workspace.config_root / "scenarios" / "diagnostic_maintenance_window.yaml"
    monkeypatch.setattr(cli, "_default_repo_root", lambda: workspace.repo_root)
    monkeypatch.setattr(
        "pacd_sim.reproducibility.paths.default_workspace_root", lambda: workspace.root
    )
    # Keep the hermetic workspace boundary in process for this CLI integration test.
    monkeypatch.setattr(cli, "run_diagnostic", _run_diagnostic_in_process)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda data, **_: output.append(data))

    def invoke(*argv: str) -> dict[str, Any]:
        assert cli.main(list(argv)) == 0, output[-1]
        return output[-1]

    first = invoke("diagnostic", "--scenario", str(scenario), "--seed", "424242")
    replay = invoke("diagnostic", "--scenario", str(scenario), "--seed", "424242")
    assert first["run_id"] != replay["run_id"]
    for key in ("config_hash", "raw_semantic_hash", "summary_semantic_hash"):
        assert first[key] == replay[key]
    expected_events = [
        {
            "id": "event-maintenance-start",
            "tick": 3,
            "kind": "benign_administrative",
            "identity_id": ADMIN,
        },
        {
            "id": "event-maintenance-indicator",
            "tick": 6,
            "kind": "simulated_adversary",
            "identity_id": USER,
        },
        {
            "id": "event-maintenance-finish",
            "tick": 9,
            "kind": "benign_administrative",
            "identity_id": ADMIN,
        },
    ]
    wire = {"format": "pacd-scripted-events-v1", "events": expected_events}
    for run in (first, replay):
        report = invoke("verify", run["run_dir"], "--show-event-sequence")
        assert report["valid"] and report["execution_identity_assured"]
        assert report["event_sequence"] == {
            **wire,
            "event_count": 3,
            "sha256": canonical_sha256(wire),
        }

    raw = Path(first["run_dir"]) / "raw" / "events.jsonl"
    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    observed = [row for row in rows if row["event_type"] == "observation"]
    assert [(row["tick"], row["entity_id"]) for row in observed] == [
        (5, ADMIN),
        (8, USER),
        (11, ADMIN),
    ]
    for kind in ("evidence", "hypothesis"):
        control = [row for row in rows if row["event_type"] == kind and row["entity_id"] == ADMIN]
        assert [(row["tick"], row["outcome"]) for row in control] == [
            (5, "not_compromised"),
            (11, "not_compromised"),
        ]
        assert all(
            json.loads(row["payload_json"])["classification"] == "benign_negative_control"
            for row in control
        )

    executions = [row for row in rows if row["event_type"] == "simulated_execution"]
    assert [(row["tick"], row["entity_id"], row["action_id"]) for row in executions] == [
        (8, USER_SESSION, "action-maint-isolate")
    ]
    after = _expected_state(isolated_user=True)
    transition = json.loads(executions[0]["payload_json"])
    assert transition["state_before_digest"] == canonical_sha256(
        _expected_state(isolated_user=False).at_tick(8)
    )
    assert transition["state_after_digest"] == canonical_sha256(after.at_tick(8))
    final_update = [row for row in rows if row["event_type"] == "state_update"][-1]
    assert final_update["tick"] == 11
    assert json.loads(final_update["payload_json"])["snapshot_digest"] == canonical_sha256(
        after.at_tick(11)
    )

"""Matched dependency scenarios and verified mission effects for configured entities."""

from pathlib import Path

import pytest
from conftest import CONFIG_ROOT, IsolatedWorkspace

from pacd_sim.constants import ASSET_CREDENTIAL_SCENARIO_FILES
from pacd_sim.environment.availability import evaluate_availability
from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256

from .test_approval_burden import Command

NOMINAL, ASSET_DOWN, CREDENTIAL_INACTIVE = ASSET_CREDENTIAL_SCENARIO_FILES


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("filename", "available", "active", "initially_down"),
    [
        (NOMINAL, True, True, set()),
        (ASSET_DOWN, False, True, {"asset-a", "service-a", "mission-a"}),
        (CREDENTIAL_INACTIVE, True, False, {"credential-b", "service-b", "mission-b"}),
    ],
)
def test_one_configured_failure_changes_only_its_dependency_path(
    filename: str, available: bool, active: bool, initially_down: set[str]
) -> None:
    root = CONFIG_ROOT / "scenarios"
    nominal = harness.load_yaml_config(root / NOMINAL)
    config = harness.load_yaml_config(root / filename)
    expected = {
        **nominal,
        "name": Path(filename).stem,
        "assets": [{"id": "asset-a", "kind": "synthetic_endpoint", "available": available}],
        "credentials": [{"id": "credential-b", "identity_id": "identity-b", "active": active}],
    }
    assert config == expected
    state = harness._build_environment(config, str(config["protocol_version"]))
    digest = canonical_sha256(state)
    assert set(evaluate_availability(state).unavailable_entity_ids) == initially_down

    session = state.sessions[0]
    assert session.id == "session-a"
    after = state.isolate_session(session.id)
    assert set(evaluate_availability(after).unavailable_entity_ids) == initially_down | {
        "session-a",
        "asset-a",
        "service-a",
        "mission-a",
    }
    # Isolation changes the session. Propagated unavailability leaves intrinsic flags intact.
    assert (after.assets, after.credentials, after.services) == (
        state.assets,
        state.credentials,
        state.services,
    )
    assert canonical_sha256(after.restore_session(session)) == digest


@pytest.mark.scenario
@pytest.mark.parametrize(
    ("filename", "upstream"), [(ASSET_DOWN, "asset-a"), (CREDENTIAL_INACTIVE, "credential-b")]
)
def test_zero_weight_dependency_preserves_the_downstream_mission(
    filename: str, upstream: str
) -> None:
    config = harness.load_yaml_config(CONFIG_ROOT / "scenarios" / filename)
    edges = config["dependencies"]
    assert isinstance(edges, list)
    (edge,) = (e for e in edges if e["upstream_id"] == upstream)
    edge["weight"] = 0
    state = harness._build_environment(config, str(config["protocol_version"]))
    report = evaluate_availability(state)
    assert report.unavailable_entity_ids == (upstream,)
    assert report.operational_mission_ids == ("mission-a", "mission-b")


@pytest.mark.negative
@pytest.mark.parametrize(
    ("collection", "field", "replacement", "reason"),
    [
        ("credentials", "identity_id", "identity-missing", "unknown identity"),
        ("credentials", "id", "asset-a", "globally unique"),
        ("assets", "id", "session-a", "globally unique"),
        ("dependencies", "downstream_id", "asset-missing", "unknown downstream entity"),
    ],
)
def test_invalid_entity_references_fail_controlled_configuration_validation(
    isolated_workspace: IsolatedWorkspace,
    collection: str,
    field: str,
    replacement: str,
    reason: str,
) -> None:
    path = isolated_workspace.config_root / "scenarios" / NOMINAL
    config = harness.load_yaml_config(path)
    rows = config[collection]
    assert isinstance(rows, list)
    rows[0][field] = replacement
    path.write_bytes(canonical_json_bytes(config))
    with pytest.raises(harness.ConfigurationError, match=reason):
        harness.validate_diagnostic_configuration_files(
            isolated_workspace.repo_root, scenario_file=NOMINAL, defender_file="static_review.yaml"
        )


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("filename", "defender", "ticks_a", "ticks_b"),
    [
        (NOMINAL, "static_review", 6, 8),
        (NOMINAL, "pacd_corroborated_review", 8, 8),
        (ASSET_DOWN, "static_review", 0, 8),
        (ASSET_DOWN, "pacd_corroborated_review", 0, 8),
        (CREDENTIAL_INACTIVE, "static_review", 6, 0),
        (CREDENTIAL_INACTIVE, "pacd_corroborated_review", 8, 0),
    ],
)
def test_verified_mission_exposure_includes_outages_present_at_reset(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    filename: str,
    defender: str,
    ticks_a: int,
    ticks_b: int,
) -> None:
    run = command(
        "diagnostic",
        "--scenario",
        str(isolated_workspace.config_root / "scenarios" / filename),
        "--baseline",
        str(isolated_workspace.config_root / "defenders" / f"{defender}.yaml"),
        "--seed",
        "424242",
    )
    result = command("metrics", run["run_dir"], "--function-availability", "--mission-recovery")
    assert result["semantic_content_valid"] and result["execution_identity_assured"]
    guarded = result["metrics"]["guarded_review"]
    assert guarded["outcome_event_counts"].get("verified", 0) == int(defender == "static_review")
    view = guarded["function_availability"]
    assert view["per_mission"] == [
        dict(
            mission_id=key, available_ticks=ticks, possible_ticks=8, availability_fraction=ticks / 8
        )
        for key, ticks in (("mission-a", ticks_a), ("mission-b", ticks_b))
    ]
    assert (view["available_function_ticks"], view["possible_function_ticks"]) == (
        ticks_a + ticks_b,
        16,
    )
    for row, ticks in zip(
        guarded["mission_recovery"]["per_mission"], (ticks_a, ticks_b), strict=True
    ):
        if ticks == 8:
            assert row["spells"] == []
        else:
            (spell,) = row["spells"]
            assert spell["observed_ticks"] == 8 - ticks
            assert spell["onset_tick"] == (None if ticks == 0 else ticks)
            assert spell["restored_tick"] is None

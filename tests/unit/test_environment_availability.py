"""Synthetic dependency failure, service redundancy and continuity across a transition."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.environment.availability import continuity_transition, evaluate_availability
from pacd_sim.environment.model import (
    Asset,
    Credential,
    Dependency,
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.reproducibility.canonical import canonical_sha256


def edge(name: str, upstream: str, downstream: str, weight: float = 1.0) -> Dependency:
    return Dependency(id=name, upstream_id=upstream, downstream_id=downstream, weight=weight)


def test_intrinsic_flags_and_absent_service_support() -> None:
    state = EnvironmentState(
        assets=(Asset(id="off", available=False), Asset(id="compromised", compromised=True)),
        credentials=(Credential(id="credential", identity_id="user", exposed=True),),
        identities=(Identity(id="user", role="test", enabled=False),),
        sessions=(
            Session(id="isolated", identity_id="user", service_id="svc", isolated=True),
            Session(id="session", identity_id="user", service_id="svc"),
        ),
        services=(Service(id="svc", mission_id="mission"),),
        mission_functions=(
            MissionFunction(id="mission", criticality=0.0),
            MissionFunction(id="orphan", criticality=1.0),
        ),
    )
    report = evaluate_availability(state)
    assert report.unavailable_entity_ids == ("isolated", "off", "orphan", "user")
    assert report.available_entity_ids == ("compromised", "credential", "mission", "session", "svc")
    assert report.audit_summary() == {
        "entity_count": 9,
        "available_entity_count": 5,
        "service_count": 1,
        "available_service_count": 1,
        "mission_count": 2,
        "operational_mission_count": 1,
        "availability_digest": canonical_sha256(report),
    }


@pytest.mark.parametrize("redundant", [False, True])
def test_isolation_and_restoration_recompute_from_immutable_state(redundant: bool) -> None:
    session = Session(id="session", identity_id="user", service_id="primary")
    services: tuple[Service, ...] = (Service(id="primary", mission_id="mission"),)
    if redundant:
        services += (Service(id="standby", mission_id="mission"),)
    state = EnvironmentState(
        identities=(Identity(id="user", role="test"),),
        sessions=(session,),
        services=services,
        mission_functions=(MissionFunction(id="mission", criticality=1.0),),
        dependencies=(
            edge("mandatory", "session", "primary", 2.5),
            edge("duplicate", "session", "primary"),
            edge("advisory", "session", "mission", 0.0),
        ),
    )
    before = evaluate_availability(state)
    isolated = state.isolate_session(session.id)
    after = evaluate_availability(isolated)
    assert before.operational_mission_ids == ("mission",)
    assert after.available_service_ids == (("standby",) if redundant else ())
    assert after.operational_mission_ids == (("mission",) if redundant else ())
    transition = continuity_transition(before, after)
    assert transition["continued_mission_count"] == int(redundant)
    assert transition["interrupted_mission_count"] == int(not redundant)
    restored = evaluate_availability(isolated.restore_session(session))
    assert restored == before
    assert continuity_transition(after, restored)["restored_mission_count"] == int(not redundant)


def test_healthy_cycles_are_stable_and_a_seeded_cycle_fails() -> None:
    state = EnvironmentState(
        assets=(
            Asset(id="a"),
            Asset(id="b"),
            Asset(id="c", available=False),
            Asset(id="d"),
            Asset(id="e"),
        ),
        dependencies=(
            edge("ab", "a", "b"),
            edge("ba", "b", "a"),
            edge("bc", "b", "c"),
            edge("cd", "c", "d"),
            edge("dc", "d", "c"),
            edge("de", "d", "e"),
            edge("ea", "e", "a", 0.0),
            edge("aa", "a", "a"),
        ),
    )
    report = evaluate_availability(state)
    assert report.available_entity_ids == ("a", "b")
    assert report.unavailable_entity_ids == ("c", "d", "e")


def test_transition_digests_bind_equal_counts_to_their_actual_missions() -> None:
    missions = tuple(MissionFunction(id=m, criticality=1.0) for m in ("a", "b", "c", "d"))

    def state_for(available: str) -> EnvironmentState:
        return EnvironmentState(
            mission_functions=missions,
            services=tuple(
                Service(id=f"service-{m.id}", mission_id=m.id, available=m.id in available)
                for m in missions
            ),
        )

    before = evaluate_availability(state_for("ab"))
    after = evaluate_availability(state_for("ac"))
    transition = continuity_transition(before, after)
    assert transition == {
        "continued_mission_count": 1,
        "interrupted_mission_count": 1,
        "restored_mission_count": 1,
        "unavailable_throughout_mission_count": 1,
        "continuity_digest": canonical_sha256(
            {"a": "continued", "b": "interrupted", "c": "restored", "d": "unavailable_throughout"}
        ),
    }
    assert (
        before.audit_summary()["availability_digest"]
        != after.audit_summary()["availability_digest"]
    )
    assert (
        transition["continuity_digest"] != continuity_transition(after, before)["continuity_digest"]
    )
    with pytest.raises(ValueError, match="same mission IDs"):
        continuity_transition(before, evaluate_availability(EnvironmentState()))


@given(
    service_flags=st.tuples(st.booleans(), st.booleans(), st.booleans()),
    mission_flags=st.tuples(st.booleans(), st.booleans()),
    edges=st.lists(st.tuples(st.integers(0, 4), st.integers(0, 4), st.booleans()), max_size=12),
)
@settings(max_examples=70, deadline=None)
def test_propagation_matches_simultaneous_fixed_point(
    service_flags: tuple[bool, bool, bool],
    mission_flags: tuple[bool, bool],
    edges: list[tuple[int, int, bool]],
) -> None:
    ids = ("s0", "s1", "s2", "m0", "m1")
    assigned = ("m0", "m0", "m1")
    services = tuple(
        Service(id=f"s{i}", mission_id=assigned[i], available=flag)
        for i, flag in enumerate(service_flags)
    )
    missions = tuple(
        MissionFunction(id=f"m{i}", criticality=0.5, operational=flag)
        for i, flag in enumerate(mission_flags)
    )
    dependencies = tuple(
        edge(f"dep-{i}", ids[u], ids[v], float(required))
        for i, (u, v, required) in enumerate(edges)
    )
    state = EnvironmentState(
        services=services, mission_functions=missions, dependencies=dependencies
    )
    working = {
        name for name, flag in zip(ids, (*service_flags, *mission_flags), strict=True) if flag
    }
    while True:
        stranded = {ids[v] for u, v, required in edges if required and ids[u] not in working}
        unsupported = {
            mission.id
            for mission in missions
            if not any(s.mission_id == mission.id and s.id in working for s in services)
        }
        next_working = working - stranded - unsupported
        if next_working == working:
            break
        working = next_working
    assert evaluate_availability(state).available_entity_ids == tuple(sorted(working))

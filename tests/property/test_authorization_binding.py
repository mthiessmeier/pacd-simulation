"""Broker-level properties against post-authorization action substitution."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.model import (
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.governance.governor import PolicyDecision, SafetyGovernor, SafetyPolicy
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.state.snapshot import create_snapshot

_DIGEST_BOUND_FIELDS = (
    "tick",
    "schema_version",
    "configuration_version",
    "source",
    "reversible",
    "requested_authority",
    "expected_effect",
    "mission_cost",
    "preconditions",
    "verification",
    "rollback",
)


def _state_with_two_authorizable_targets() -> EnvironmentState:
    mission = MissionFunction(id="mission-synthetic", criticality=1.0)
    service = Service(id="service-synthetic", mission_id=mission.id)
    identity = Identity(id="identity-synthetic", role="synthetic_user")
    return EnvironmentState(
        identities=(identity,),
        services=(service,),
        mission_functions=(mission,),
        sessions=(
            Session(
                id="session-authorized",
                identity_id=identity.id,
                service_id=service.id,
            ),
            Session(
                id="session-substituted",
                identity_id=identity.id,
                service_id=service.id,
            ),
        ),
    )


def _authorized_action(
    state: EnvironmentState,
) -> tuple[DefensiveAction, PolicyDecision, SafetyGovernor]:
    action = DefensiveAction(
        id="action-authorized",
        tick=2,
        action_type="isolate_session",
        target_id="session-authorized",
        reversible=True,
        requested_authority="automatic",
    )
    governor = SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=("isolate_session",),
            escalated_action_types=("require_human_review",),
            prohibited_action_types=("external_network_scan",),
        )
    )
    decision = governor.evaluate(action, mission_state=create_snapshot(state))
    return action, decision, governor


def _assert_sessions_remain_active(state: EnvironmentState) -> None:
    for session_id in ("session-authorized", "session-substituted"):
        session = state.get_session(session_id)
        assert session is not None
        assert session.active
        assert not session.isolated


@pytest.mark.property
def test_approved_decision_cannot_be_retargeted_to_another_valid_session() -> None:
    state = _state_with_two_authorizable_targets()
    action, decision, governor = _authorized_action(state)
    substituted = action.model_copy(update={"target_id": "session-substituted"})

    result = SimulatedExecutionBroker(governor).execute(substituted, decision, state)

    assert decision.target_id == action.target_id
    assert decision.action_digest == canonical_sha256(action)
    assert not result.executed
    assert result.state is state
    assert result.record.reason == "policy decision target does not match the candidate action"
    assert result.record.authorized_action_digest == decision.action_digest
    _assert_sessions_remain_active(state)


@pytest.mark.property
@given(st.sampled_from(_DIGEST_BOUND_FIELDS))
@settings(max_examples=30, deadline=None)
def test_every_nonidentity_action_field_is_bound_by_governor_digest(field: str) -> None:
    state = _state_with_two_authorizable_targets()
    action, decision, governor = _authorized_action(state)
    substituted_values: dict[str, object] = {
        "tick": 3,
        "schema_version": "tampered-schema",
        "configuration_version": "tampered-config",
        "source": "tampered-source",
        "reversible": False,
        "requested_authority": "human",
        "expected_effect": "substituted effect",
        "mission_cost": 1.0,
        "preconditions": ("substituted precondition",),
        "verification": "substituted verification",
        "rollback": "substituted rollback",
    }
    substituted = action.model_copy(update={field: substituted_values[field]})

    result = SimulatedExecutionBroker(governor).execute(substituted, decision, state)

    assert substituted.id == action.id
    assert substituted.action_type == action.action_type
    assert substituted.target_id == action.target_id
    assert canonical_sha256(substituted) != decision.action_digest
    assert not result.executed
    assert result.state is state
    assert result.record.reason == "candidate action digest does not match governor authorization"
    assert result.record.authorized_action_digest == decision.action_digest
    _assert_sessions_remain_active(state)

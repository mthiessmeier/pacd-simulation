"""Pure in-memory simulated execution and verification checks."""

from __future__ import annotations

import pytest

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.model import (
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.execution.verification import rollback_execution, verify_execution
from pacd_sim.governance.governor import SafetyGovernor, SafetyPolicy
from pacd_sim.schema import (
    PolicyDisposition,
    RollbackDisposition,
    VerificationDisposition,
)


@pytest.fixture
def synthetic_state() -> EnvironmentState:
    mission = MissionFunction(id="mission-synthetic", criticality=1.0)
    service = Service(id="service-synthetic", mission_id=mission.id)
    identity = Identity(id="identity-synthetic", role="synthetic_user")
    session = Session(
        id="session-synthetic",
        identity_id=identity.id,
        service_id=service.id,
    )
    return EnvironmentState(
        identities=(identity,),
        sessions=(session,),
        services=(service,),
        mission_functions=(mission,),
    )


@pytest.fixture
def governor() -> SafetyGovernor:
    return SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=("isolate_session",),
            escalated_action_types=("require_human_review",),
            prohibited_action_types=("external_network_scan",),
        )
    )


def _action(action_type: str, authority: str, target_id: str) -> DefensiveAction:
    return DefensiveAction.model_validate(
        {
            "id": f"action-{action_type}",
            "tick": 2,
            "action_type": action_type,
            "target_id": target_id,
            "reversible": True,
            "requested_authority": authority,
        }
    )


def test_approved_action_is_only_an_immutable_simulated_transition(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = governor.evaluate(action)
    broker = SimulatedExecutionBroker()

    result = broker.execute(action, decision, synthetic_state)
    verification = verify_execution(action, result)

    assert decision.disposition is PolicyDisposition.APPROVE
    assert result.executed
    assert result.state is not synthetic_state
    assert synthetic_state.get_session(action.target_id).active  # type: ignore[union-attr]
    assert not result.state.get_session(action.target_id).active  # type: ignore[union-attr]
    assert result.state.get_session(action.target_id).isolated  # type: ignore[union-attr]
    assert verification.disposition is VerificationDisposition.VERIFIED
    assert broker.adapter_name == "simulated_only"
    assert broker.network_enabled is False


@pytest.mark.parametrize(
    ("action_type", "authority", "expected"),
    [
        ("require_human_review", "human", PolicyDisposition.ESCALATE),
        ("external_network_scan", "prohibited", PolicyDisposition.PROHIBIT),
    ],
)
def test_nonapproved_actions_cannot_change_even_simulated_state(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
    action_type: str,
    authority: str,
    expected: PolicyDisposition,
) -> None:
    action = _action(action_type, authority, "synthetic-target")
    decision = governor.evaluate(action)

    result = SimulatedExecutionBroker().execute(action, decision, synthetic_state)

    assert decision.disposition is expected
    assert not result.executed
    assert result.state is synthetic_state
    assert result.record.state_before_digest == result.record.state_after_digest


@pytest.mark.parametrize(
    ("field", "value", "expected_exception"),
    [
        ("id", "unknown-session", KeyError),
        ("configuration_version", "different-config", ValueError),
        ("schema_version", "different-schema", ValueError),
        ("identity_id", "unknown-identity", ValueError),
        ("service_id", "unknown-service", ValueError),
    ],
)
def test_restore_session_rejects_unknown_or_context_altering_replacements(
    synthetic_state: EnvironmentState,
    field: str,
    value: str,
    expected_exception: type[Exception],
) -> None:
    original = synthetic_state.get_session("session-synthetic")
    assert original is not None
    replacement = original.model_copy(update={field: value})

    with pytest.raises(expected_exception):
        synthetic_state.restore_session(replacement)

    assert synthetic_state.get_session("session-synthetic") is original


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity_id", "identity-secondary"),
        ("service_id", "service-secondary"),
    ],
)
def test_restore_session_rejects_rebinding_to_different_valid_relationships(
    synthetic_state: EnvironmentState,
    field: str,
    value: str,
) -> None:
    original = synthetic_state.get_session("session-synthetic")
    assert original is not None
    secondary_identity = Identity(id="identity-secondary", role="synthetic_user")
    secondary_service = Service(
        id="service-secondary",
        mission_id="mission-synthetic",
    )
    expanded_state = EnvironmentState(
        identities=(*synthetic_state.identities, secondary_identity),
        sessions=synthetic_state.sessions,
        services=(*synthetic_state.services, secondary_service),
        mission_functions=synthetic_state.mission_functions,
    )
    replacement = original.model_copy(update={field: value})

    with pytest.raises(ValueError):
        expanded_state.restore_session(replacement)

    assert expanded_state.get_session(original.id) is original


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "different-action"),
        ("action_type", "different-action-type"),
        ("target_id", "different-target"),
        ("configuration_version", "different-config"),
    ],
)
def test_verification_and_rollback_require_exact_action_binding(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
    field: str,
    value: str,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker().execute(action, governor.evaluate(action), synthetic_state)
    mismatched_action = action.model_copy(update={field: value})

    verification = verify_execution(mismatched_action, result)
    rollback = rollback_execution(mismatched_action, result)

    assert verification.disposition is VerificationDisposition.FAILED
    assert rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
    assert rollback.state is result.state


def test_verification_and_rollback_validate_every_retained_state_hash(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker().execute(action, governor.evaluate(action), synthetic_state)
    original_session = result.record.state_before.get_session(action.target_id)
    assert original_session is not None
    corrupt_results = (
        result.model_copy(
            update={"record": result.record.model_copy(update={"state_before_digest": "0" * 64})}
        ),
        result.model_copy(
            update={"record": result.record.model_copy(update={"state_after_digest": "0" * 64})}
        ),
        result.model_copy(
            update={
                "record": result.record.model_copy(
                    update={"state_before": result.record.state_before.at_tick(1)}
                )
            }
        ),
        result.model_copy(
            update={
                "record": result.record.model_copy(
                    update={
                        "state_after": result.record.state_after.restore_session(original_session)
                    }
                )
            }
        ),
        result.model_copy(update={"state": result.record.state_before}),
    )

    for corrupt_result in corrupt_results:
        verification = verify_execution(action, corrupt_result)
        rollback = rollback_execution(action, corrupt_result)
        assert verification.disposition is VerificationDisposition.FAILED
        assert rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
        assert rollback.state is corrupt_result.state


def test_corrupt_nonexecuted_record_fails_verification_instead_of_being_not_applicable(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("external_network_scan", "prohibited", "synthetic-target")
    result = SimulatedExecutionBroker().execute(action, governor.evaluate(action), synthetic_state)

    clean_verification = verify_execution(action, result)
    corrupt_result = result.model_copy(
        update={"record": result.record.model_copy(update={"state_after_digest": "0" * 64})}
    )
    corrupt_verification = verify_execution(action, corrupt_result)
    corrupt_rollback = rollback_execution(action, corrupt_result)

    assert clean_verification.disposition is VerificationDisposition.NOT_APPLICABLE
    assert corrupt_verification.disposition is VerificationDisposition.FAILED
    assert corrupt_rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
    assert corrupt_rollback.state is corrupt_result.state

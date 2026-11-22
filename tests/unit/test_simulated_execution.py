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
from pacd_sim.governance.governor import PolicyDecision, SafetyGovernor, SafetyPolicy
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import (
    PolicyDisposition,
    RollbackDisposition,
    VerificationDisposition,
)
from pacd_sim.state.snapshot import create_snapshot


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


def _authorize(
    governor: SafetyGovernor,
    action: DefensiveAction,
    state: EnvironmentState,
) -> PolicyDecision:
    return governor.evaluate(action, mission_state=create_snapshot(state))


def test_sensing_verification_rejects_collateral_even_with_coherent_hashes(
    synthetic_state: EnvironmentState, monkeypatch: pytest.MonkeyPatch
) -> None:
    governor = SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=("switch_sensing_profile",),
            escalated_action_types=(),
            prohibited_action_types=(),
        )
    )
    action = _action("switch_sensing_profile", "automatic", "session-synthetic")
    original = EnvironmentState.switch_sensing_profile

    def collateral(state: EnvironmentState, session_id: str) -> EnvironmentState:
        changed = original(state, session_id)
        damaged = changed.mission_functions[0].model_copy(update={"operational": False})
        return changed.model_copy(update={"mission_functions": (damaged,)})

    monkeypatch.setattr(EnvironmentState, "switch_sensing_profile", collateral)
    broker = SimulatedExecutionBroker(governor)
    result = broker.execute(action, _authorize(governor, action, synthetic_state), synthetic_state)
    assert result.executed and result.record.state_after_digest == canonical_sha256(result.state)
    checked = verify_execution(action, result, governor)
    assert checked.state_hashes_valid and checked.disposition is VerificationDisposition.FAILED
    assert (
        rollback_execution(action, result, governor).record.disposition
        is RollbackDisposition.NOT_ROLLED_BACK
    )


def test_approved_action_is_only_an_immutable_simulated_transition(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = _authorize(governor, action, synthetic_state)
    broker = SimulatedExecutionBroker(governor)

    result = broker.execute(action, decision, synthetic_state)
    verification = verify_execution(action, result, governor)

    assert decision.disposition is PolicyDisposition.APPROVE
    assert result.executed
    assert result.state is not synthetic_state
    assert synthetic_state.get_session(action.target_id).active  # type: ignore[union-attr]
    assert not result.state.get_session(action.target_id).active  # type: ignore[union-attr]
    assert result.state.get_session(action.target_id).isolated  # type: ignore[union-attr]
    assert verification.disposition is VerificationDisposition.VERIFIED
    assert broker.adapter_name == "simulated_only"
    assert broker.network_enabled is False


def test_verification_detects_collateral_in_the_production_transition(
    synthetic_state: EnvironmentState, governor: SafetyGovernor, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolate = EnvironmentState.isolate_session

    def isolate_with_collateral(state: EnvironmentState, target_id: str) -> EnvironmentState:
        isolated = isolate(state, target_id)
        mission = state.mission_functions[0].model_copy(update={"operational": False})
        return isolated.model_copy(update={"mission_functions": (mission,)})

    monkeypatch.setattr(EnvironmentState, "isolate_session", isolate_with_collateral)
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = _authorize(governor, action, synthetic_state)
    result = SimulatedExecutionBroker(governor).execute(action, decision, synthetic_state)
    assert result.executed and not result.state.mission_functions[0].operational
    verification = verify_execution(action, result, governor)
    assert verification.state_hashes_valid
    assert verification.disposition == VerificationDisposition.FAILED
    assert not verification.expected_effect_observed


def test_canonical_type_change_is_collateral_even_when_models_compare_equal(
    synthetic_state: EnvironmentState, governor: SafetyGovernor
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = _authorize(governor, action, synthetic_state)
    result = SimulatedExecutionBroker(governor).execute(action, decision, synthetic_state)
    malformed = result.state.identities[0].model_copy(update={"enabled": 1})
    after = result.state.model_copy(update={"identities": (malformed,)})
    assert after == result.state
    with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
        digest = canonical_sha256(after)
        assert digest != result.record.state_after_digest
        record = result.record.model_copy(
            update={"state_after": after, "state_after_digest": digest}
        )
        forged = result.model_copy(update={"record": record, "state": after})
        verification = verify_execution(action, forged, governor)
        recovery = rollback_execution(action, forged, governor)
    assert verification.state_hashes_valid and not verification.expected_effect_observed
    assert verification.disposition == VerificationDisposition.FAILED
    assert recovery.record.disposition == RollbackDisposition.NOT_ROLLED_BACK


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
    decision = _authorize(governor, action, synthetic_state)

    result = SimulatedExecutionBroker(governor).execute(action, decision, synthetic_state)

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
    result = SimulatedExecutionBroker(governor).execute(
        action, _authorize(governor, action, synthetic_state), synthetic_state
    )
    mismatched_action = action.model_copy(update={field: value})

    verification = verify_execution(mismatched_action, result, governor)
    rollback = rollback_execution(mismatched_action, result, governor)

    assert verification.disposition is VerificationDisposition.FAILED
    assert rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
    assert rollback.state is result.state


def test_verification_and_rollback_validate_every_retained_state_hash(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker(governor).execute(
        action, _authorize(governor, action, synthetic_state), synthetic_state
    )
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
        verification = verify_execution(action, corrupt_result, governor)
        rollback = rollback_execution(action, corrupt_result, governor)
        assert verification.disposition is VerificationDisposition.FAILED
        assert rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
        assert rollback.state is corrupt_result.state


def test_corrupt_nonexecuted_record_fails_verification_instead_of_being_not_applicable(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("external_network_scan", "prohibited", "synthetic-target")
    result = SimulatedExecutionBroker(governor).execute(
        action, _authorize(governor, action, synthetic_state), synthetic_state
    )

    clean_verification = verify_execution(action, result, governor)
    corrupt_result = result.model_copy(
        update={"record": result.record.model_copy(update={"state_after_digest": "0" * 64})}
    )
    corrupt_verification = verify_execution(action, corrupt_result, governor)
    corrupt_rollback = rollback_execution(action, corrupt_result, governor)

    assert clean_verification.disposition is VerificationDisposition.NOT_APPLICABLE
    assert corrupt_verification.disposition is VerificationDisposition.FAILED
    assert corrupt_rollback.record.disposition is RollbackDisposition.NOT_ROLLED_BACK
    assert corrupt_rollback.state is corrupt_result.state


def test_forged_approve_cannot_override_governor_prohibition(
    synthetic_state: EnvironmentState,
) -> None:
    governor = SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=(),
            escalated_action_types=("require_human_review",),
            prohibited_action_types=("external_network_scan", "isolate_session"),
        )
    )
    action = _action("isolate_session", "automatic", "session-synthetic")
    genuine = _authorize(governor, action, synthetic_state)
    forged = genuine.model_copy(update={"disposition": PolicyDisposition.APPROVE})

    result = SimulatedExecutionBroker(governor).execute(action, forged, synthetic_state)

    assert genuine.disposition is PolicyDisposition.PROHIBIT
    assert not result.executed
    assert result.state is synthetic_state
    assert result.record.reason == "policy decision is not an exact fresh governor authorization"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "forged-decision"),
        ("tick", 99),
        ("schema_version", "forged-schema"),
        ("configuration_version", "forged-configuration"),
        ("policy_version", "forged-policy"),
        ("policy_digest", "0" * 64),
        ("state_digest", "1" * 64),
        ("governance_context_digest", "2" * 64),
    ],
)
def test_every_decision_field_mismatch_fails_closed_before_mutation(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
    field: str,
    value: object,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = _authorize(governor, action, synthetic_state)
    mutated = decision.model_copy(update={field: value})

    result = SimulatedExecutionBroker(governor).execute(action, mutated, synthetic_state)

    assert not result.executed
    assert result.state is synthetic_state
    assert result.record.reason == "policy decision is not an exact fresh governor authorization"


def test_authorization_cannot_be_replayed_against_changed_prestate(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    decision = _authorize(governor, action, synthetic_state)
    changed_state = synthetic_state.at_tick(1)

    result = SimulatedExecutionBroker(governor).execute(action, decision, changed_state)

    assert not result.executed
    assert result.state is changed_state
    assert result.record.reason == "policy decision is not an exact fresh governor authorization"


@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    [
        (
            "configuration_version",
            "different-configuration",
            "candidate action configuration does not match the environment state",
        ),
        (
            "schema_version",
            "different-schema",
            "candidate action schema does not match the environment state",
        ),
    ],
)
def test_action_state_version_mismatch_is_refused_before_transition(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
    field: str,
    value: str,
    expected_reason: str,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic").model_copy(
        update={field: value}
    )
    classification_only = governor.evaluate(action)

    result = SimulatedExecutionBroker(governor).execute(
        action,
        classification_only,
        synthetic_state,
    )

    assert not result.executed
    assert result.state is synthetic_state
    assert result.record.reason == expected_reason


def test_verification_rejects_self_consistent_collateral_state_change(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker(governor).execute(
        action,
        _authorize(governor, action, synthetic_state),
        synthetic_state,
    )
    identity = result.state.identities[0].model_copy(update={"enabled": False})
    collateral_state = result.state.model_copy(update={"identities": (identity,)})
    collateral_result = result.model_copy(
        update={
            "state": collateral_state,
            "record": result.record.model_copy(
                update={
                    "state_after": collateral_state,
                    "state_after_digest": canonical_sha256(collateral_state),
                }
            ),
        }
    )

    verification = verify_execution(action, collateral_result, governor)

    assert verification.state_hashes_valid
    assert not verification.expected_effect_observed
    assert verification.disposition is VerificationDisposition.FAILED


def test_verification_rejects_self_consistent_untrusted_policy_authorization(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker(governor).execute(
        action,
        _authorize(governor, action, synthetic_state),
        synthetic_state,
    )
    trusted_governor = SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=(),
            escalated_action_types=("require_human_review",),
            prohibited_action_types=("external_network_scan", "isolate_session"),
        )
    )

    verification = verify_execution(action, result, trusted_governor)

    assert verification.disposition is VerificationDisposition.FAILED
    assert "trusted-governor" in verification.reason


def test_verification_rejects_self_consistent_unbound_execution_tick(
    synthetic_state: EnvironmentState,
    governor: SafetyGovernor,
) -> None:
    action = _action("isolate_session", "automatic", "session-synthetic")
    result = SimulatedExecutionBroker(governor).execute(
        action,
        _authorize(governor, action, synthetic_state),
        synthetic_state,
    )
    forged_state = synthetic_state.at_tick(99).isolate_session(action.target_id)
    forged_result = result.model_copy(
        update={
            "state": forged_state,
            "record": result.record.model_copy(
                update={
                    "tick": 99,
                    "state_after": forged_state,
                    "state_after_digest": canonical_sha256(forged_state),
                }
            ),
        }
    )

    verification = verify_execution(action, forged_result, governor)

    assert verification.state_hashes_valid
    assert verification.disposition is VerificationDisposition.FAILED
    assert "execution tick" in verification.reason

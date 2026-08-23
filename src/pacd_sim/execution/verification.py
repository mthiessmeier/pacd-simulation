"""Independent verification and rollback for simulated execution records."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.execution.broker import ExecutionResult
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import (
    ConsequentialRecord,
    RollbackDisposition,
    StableId,
    StrictFrozenModel,
    VerificationDisposition,
)


class VerificationRecord(ConsequentialRecord):
    """Independent check of an observed simulated outcome."""

    execution_id: StableId
    action_id: StableId
    disposition: VerificationDisposition
    state_hashes_valid: bool
    expected_effect_observed: bool
    reason: str


class RollbackRecord(ConsequentialRecord):
    """Record of a rollback to the broker-retained prior immutable state."""

    execution_id: StableId
    action_id: StableId
    disposition: RollbackDisposition
    restored_state_digest: str
    reason: str


class RollbackResult(StrictFrozenModel):
    """Rollback record plus the resulting immutable state."""

    state: EnvironmentState
    record: RollbackRecord


def _binding_error(action: DefensiveAction, result: ExecutionResult) -> str | None:
    record = result.record
    if record.action_id != action.id:
        return "execution record action ID does not match the candidate action"
    if record.action_type != action.action_type:
        return "execution record action type does not match the candidate action"
    if record.target_id != action.target_id:
        return "execution record target does not match the candidate action"
    if record.authorized_action_digest != canonical_sha256(action):
        return "execution authorization digest does not match the candidate action"
    if record.action_configuration_version != action.configuration_version:
        return "execution record configuration does not match the candidate action"
    states = (record.state_before, record.state_after, result.state)
    if any(state.configuration_version != action.configuration_version for state in states):
        return "execution state configuration does not match the candidate action"
    if any(state.schema_version != action.schema_version for state in states):
        return "execution state schema does not match the candidate action"
    return None


def _hashes_valid(result: ExecutionResult) -> bool:
    record = result.record
    return (
        canonical_sha256(record.state_before) == record.state_before_digest
        and canonical_sha256(record.state_after) == record.state_after_digest
        and canonical_sha256(result.state) == record.state_after_digest
    )


def verify_execution(
    action: DefensiveAction,
    result: ExecutionResult,
) -> VerificationRecord:
    """Verify hashes and expected effects without trusting the proposing defender."""

    record = result.record
    hashes_valid = _hashes_valid(result)
    binding_error = _binding_error(action, result)
    if binding_error is not None:
        disposition = VerificationDisposition.FAILED
        effect_observed = False
        reason = binding_error
    elif not hashes_valid:
        disposition = VerificationDisposition.FAILED
        effect_observed = False
        reason = "execution before/after state hashes did not validate"
    elif not record.executed:
        unchanged = (
            record.state_before == record.state_after
            and result.state == record.state_after
            and record.state_before_digest == record.state_after_digest
        )
        if unchanged:
            disposition = VerificationDisposition.NOT_APPLICABLE
            effect_observed = False
            reason = "matching action was not executed and state remained unchanged"
        else:
            disposition = VerificationDisposition.FAILED
            effect_observed = False
            reason = "nonexecuted record contains an unauthorized state transition"
    elif action.action_type == "isolate_session":
        before_session = record.state_before.get_session(action.target_id)
        after_session = record.state_after.get_session(action.target_id)
        effect_observed = (
            before_session is not None
            and after_session is not None
            and before_session.active
            and not before_session.isolated
            and not after_session.active
            and after_session.isolated
        )
        disposition = (
            VerificationDisposition.VERIFIED
            if hashes_valid and effect_observed
            else VerificationDisposition.FAILED
        )
        reason = (
            "expected synthetic isolation transition observed"
            if disposition is VerificationDisposition.VERIFIED
            else "synthetic isolation transition or state hashes did not verify"
        )
    else:
        disposition = VerificationDisposition.FAILED
        effect_observed = False
        reason = "verification rule is unavailable for this action type"
    return VerificationRecord(
        id=f"verification-{record.id}",
        tick=record.tick,
        configuration_version=record.configuration_version,
        execution_id=record.id,
        action_id=action.id,
        disposition=disposition,
        state_hashes_valid=hashes_valid,
        expected_effect_observed=effect_observed,
        reason=reason,
    )


def rollback_execution(
    action: DefensiveAction,
    result: ExecutionResult,
) -> RollbackResult:
    """Restore the exact retained prior state only for an executed reversible action."""

    record = result.record
    verification = verify_execution(action, result)
    can_restore = (
        verification.disposition is VerificationDisposition.VERIFIED
        and record.executed
        and action.reversible
    )
    if can_restore:
        state = record.state_before
        disposition = RollbackDisposition.ROLLED_BACK
        reason = "restored exact prior immutable synthetic state"
    else:
        state = result.state
        disposition = RollbackDisposition.NOT_ROLLED_BACK
        reason = "rollback requires a matching executed reversible action"
    rollback = RollbackRecord(
        id=f"rollback-{record.id}",
        tick=record.tick,
        configuration_version=record.configuration_version,
        execution_id=record.id,
        action_id=action.id,
        disposition=disposition,
        restored_state_digest=canonical_sha256(state),
        reason=reason,
    )
    return RollbackResult(state=state, record=rollback)

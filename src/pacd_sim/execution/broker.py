"""The sole Release 1 execution adapter: pure in-memory simulated transitions."""

from typing import ClassVar, Literal

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.governance.governor import PolicyDecision
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import (
    ConsequentialRecord,
    ExecutionDisposition,
    PolicyDisposition,
    StableId,
    StrictFrozenModel,
)


class ExecutionRecord(ConsequentialRecord):
    """Accepted or refused simulated execution with complete before/after state."""

    action_id: StableId
    action_configuration_version: str
    authorized_action_digest: str
    policy_decision_id: StableId
    action_type: StableId
    target_id: StableId
    disposition: ExecutionDisposition
    reason: str
    state_before_digest: str
    state_after_digest: str
    state_before: EnvironmentState
    state_after: EnvironmentState

    @property
    def executed(self) -> bool:
        return self.disposition is ExecutionDisposition.EXECUTED


class ExecutionResult(StrictFrozenModel):
    """Convenience wrapper exposing the resulting immutable state and record."""

    state: EnvironmentState
    record: ExecutionRecord

    @property
    def executed(self) -> bool:
        return self.record.executed


class SimulatedExecutionBroker:
    """Allowlisted state transitions with no socket, process, shell, or API facility."""

    adapter_name: ClassVar[Literal["simulated_only"]] = "simulated_only"
    network_enabled: ClassVar[Literal[False]] = False
    supported_action_types: ClassVar[frozenset[str]] = frozenset({"isolate_session"})

    def execute(
        self,
        action: DefensiveAction,
        decision: PolicyDecision,
        state: EnvironmentState,
    ) -> ExecutionResult:
        """Execute only a matching, approved, reversible, automatic simulated action."""

        reason: str | None = None
        action_digest = canonical_sha256(action)
        if decision.action_id != action.id or decision.action_type != action.action_type:
            reason = "policy decision does not match the candidate action"
        elif decision.target_id != action.target_id:
            reason = "policy decision target does not match the candidate action"
        elif decision.action_digest != action_digest:
            reason = "candidate action digest does not match governor authorization"
        elif decision.disposition is not PolicyDisposition.APPROVE:
            reason = "non-approved governor disposition cannot execute"
        elif action.requested_authority != "automatic":
            reason = "only automatic-authority diagnostic actions may execute"
        elif not action.reversible:
            reason = "non-reversible actions cannot execute in the diagnostic broker"
        elif action.action_type not in self.supported_action_types:
            reason = "action type is not implemented by the simulated broker"

        before = state
        after = state
        if reason is None and action.action_type == "isolate_session":
            session = state.get_session(action.target_id)
            if session is None:
                reason = "target is not a known synthetic session"
            elif session.isolated or not session.active:
                reason = "target session is already inactive or isolated"
            else:
                after = state.at_tick(max(state.tick, action.tick, decision.tick)).isolate_session(
                    action.target_id
                )
                reason = "synthetic session isolated in immutable in-memory state"

        if reason is None:
            reason = "simulated transition completed"

        disposition = (
            ExecutionDisposition.EXECUTED
            if after is not before
            else ExecutionDisposition.NOT_EXECUTED
        )
        record = ExecutionRecord(
            id=f"execution-{action.id}",
            tick=max(state.tick, action.tick, decision.tick),
            configuration_version=decision.policy_version,
            action_id=action.id,
            action_configuration_version=action.configuration_version,
            authorized_action_digest=decision.action_digest,
            policy_decision_id=decision.id,
            action_type=action.action_type,
            target_id=action.target_id,
            disposition=disposition,
            reason=reason,
            state_before_digest=canonical_sha256(before),
            state_after_digest=canonical_sha256(after),
            state_before=before,
            state_after=after,
        )
        return ExecutionResult(state=after, record=record)

"""Deterministic simulated human oversight records."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.governance.governor import PolicyDecision
from pacd_sim.schema import (
    ApprovalDisposition,
    ConsequentialRecord,
    PolicyDisposition,
    StableId,
)


class ApprovalRecord(ConsequentialRecord):
    """Accountability record for a simulated review; it grants no real authority."""

    action_id: StableId
    policy_decision_id: StableId
    disposition: ApprovalDisposition
    requested_tick: int
    delay_ticks: int
    reason: str


class SimulatedApprovalAuthority:
    """Bounded reviewer with deterministic delay and fail-closed default behavior."""

    def __init__(self, delay_ticks: int = 1, approve_escalated: bool = False) -> None:
        if isinstance(delay_ticks, bool) or not isinstance(delay_ticks, int) or delay_ticks < 0:
            raise ValueError("delay_ticks must be a non-negative integer")
        self._delay_ticks = delay_ticks
        self._approve_escalated = approve_escalated

    def review(self, action: DefensiveAction, decision: PolicyDecision) -> ApprovalRecord:
        """Review a matching proposal without changing the governor's disposition."""

        if decision.action_id != action.id:
            raise ValueError("policy decision does not belong to the action")
        approved = (
            decision.disposition is PolicyDisposition.ESCALATE
            and self._approve_escalated
            and action.reversible
        )
        disposition = ApprovalDisposition.APPROVED if approved else ApprovalDisposition.DENIED
        if approved:
            reason = "simulated reviewer approved review package; governor decision is unchanged"
        elif decision.disposition is PolicyDisposition.PROHIBIT:
            reason = "prohibited actions cannot be approved"
        else:
            reason = "simulated review denied or was not required"
        return ApprovalRecord(
            id=f"approval-{action.id}",
            tick=max(action.tick, decision.tick) + self._delay_ticks,
            configuration_version=decision.policy_version,
            action_id=action.id,
            policy_decision_id=decision.id,
            disposition=disposition,
            requested_tick=max(action.tick, decision.tick),
            delay_ticks=self._delay_ticks,
            reason=reason,
        )

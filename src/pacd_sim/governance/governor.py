"""Independent fail-closed safety policy for simulated action proposals."""

from typing import Literal, Self

from pydantic import field_validator, model_validator

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.hypotheses.update import BeliefState
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import (
    ConsequentialRecord,
    PolicyDisposition,
    StableId,
    StrictFrozenModel,
)
from pacd_sim.state.snapshot import StateSnapshot


class Constraint(ConsequentialRecord):
    """Declarative action-type constraint owned by the governor."""

    action_type: StableId
    disposition: PolicyDisposition
    reason: str


class SafetyPolicy(StrictFrozenModel):
    """Versioned, disjoint action classification with network disabled."""

    policy_version: str = "diagnostic-safety-v1"
    allowed_action_types: tuple[StableId, ...]
    escalated_action_types: tuple[StableId, ...]
    prohibited_action_types: tuple[StableId, ...]
    execution_adapter: Literal["simulated_only"] = "simulated_only"
    network_enabled: Literal[False] = False

    @field_validator(
        "allowed_action_types",
        "escalated_action_types",
        "prohibited_action_types",
    )
    @classmethod
    def _stable_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("action classifications cannot contain duplicates")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _validate_disjoint(self) -> Self:
        allowed = set(self.allowed_action_types)
        escalated = set(self.escalated_action_types)
        prohibited = set(self.prohibited_action_types)
        if allowed & escalated or allowed & prohibited or escalated & prohibited:
            raise ValueError("action classifications must be pairwise disjoint")
        return self


class GovernanceContext(ConsequentialRecord):
    """Explicit context for a non-reportable, simulation-only decision."""

    id: StableId = "governance-context-diagnostic"
    evidence_label: Literal["NON_REPORTABLE_DIAGNOSTIC"] = EVIDENCE_LABEL
    operating_mode: Literal["diagnostic"] = "diagnostic"
    human_review_available: bool = True


class PolicyDecision(ConsequentialRecord):
    """Independent disposition for exactly one candidate action."""

    action_id: StableId
    action_type: StableId
    target_id: StableId
    action_digest: str
    disposition: PolicyDisposition
    policy_version: str
    reason: str

    @property
    def permits_execution(self) -> bool:
        return self.disposition is PolicyDisposition.APPROVE


class SafetyGovernor:
    """Classify proposals before utility ranking or simulated execution."""

    def __init__(self, policy: SafetyPolicy) -> None:
        self._policy = policy

    @property
    def policy(self) -> SafetyPolicy:
        return self._policy

    def evaluate(
        self,
        action: DefensiveAction,
        belief_state: BeliefState | None = None,
        mission_state: StateSnapshot | None = None,
        context: GovernanceContext | None = None,
    ) -> PolicyDecision:
        """Return APPROVE, ESCALATE, or PROHIBIT; unknown cases fail closed."""

        del belief_state, mission_state
        decision_tick = action.tick if context is None else max(action.tick, context.tick)
        if action.requested_authority == "prohibited":
            disposition = PolicyDisposition.PROHIBIT
            reason = "action explicitly requests prohibited authority"
        elif action.action_type in self._policy.prohibited_action_types:
            disposition = PolicyDisposition.PROHIBIT
            reason = "action type is prohibited by independent safety policy"
        elif action.action_type in self._policy.escalated_action_types:
            disposition = PolicyDisposition.ESCALATE
            reason = "action type requires simulated human review"
        elif action.action_type not in self._policy.allowed_action_types:
            disposition = PolicyDisposition.PROHIBIT
            reason = "unknown action type fails closed"
        elif action.requested_authority == "human":
            disposition = PolicyDisposition.ESCALATE
            reason = "candidate requests human authority"
        elif not action.reversible:
            disposition = PolicyDisposition.PROHIBIT
            reason = "automatic diagnostic actions must be reversible"
        else:
            disposition = PolicyDisposition.APPROVE
            reason = "reversible action is allowlisted for simulated execution"
        return PolicyDecision(
            id=f"policy-decision-{action.id}",
            tick=decision_tick,
            configuration_version=self._policy.policy_version,
            action_id=action.id,
            action_type=action.action_type,
            target_id=action.target_id,
            action_digest=canonical_sha256(action),
            disposition=disposition,
            policy_version=self._policy.policy_version,
            reason=reason,
        )

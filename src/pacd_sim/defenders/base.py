"""Common typed defender boundary, independent of the evaluation harness."""

from typing import Protocol, runtime_checkable

from pydantic import field_validator

from pacd_sim.actions.models import DefensiveAction, action_sort_key
from pacd_sim.defenders.observations import BaselineObservation as BaselineObservation
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.hypotheses.update import BeliefState
from pacd_sim.schema import (
    ConsequentialRecord,
    StableId,
)


class DefenderContext(ConsequentialRecord):
    """Immutable observations and state made available equally to defenders."""

    id: StableId = "defender-context-diagnostic"
    evidence: tuple[EvidenceItem, ...]
    belief_state: BeliefState
    environment: EnvironmentState

    @field_validator("evidence")
    @classmethod
    def _sort_evidence(cls, value: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        return tuple(sorted(value, key=lambda item: (item.tick, item.id)))


class DefenderDecision(ConsequentialRecord):
    """A defender's candidate actions; it is not an execution authorization."""

    defender_id: StableId
    proposed_actions: tuple[DefensiveAction, ...] = ()
    rationale: str

    @field_validator("proposed_actions")
    @classmethod
    def _sort_actions(cls, value: tuple[DefensiveAction, ...]) -> tuple[DefensiveAction, ...]:
        return tuple(sorted(value, key=action_sort_key))


@runtime_checkable
class Defender(Protocol):
    """Shared structural interface implemented by every defender condition."""

    @property
    def defender_id(self) -> str:
        """Return the stable defender identifier."""

    def decide(self, context: DefenderContext) -> DefenderDecision:
        """Return candidate actions from immutable synthetic context."""

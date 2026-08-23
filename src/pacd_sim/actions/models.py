"""Typed defensive action ontology for simulated state transitions."""

from typing import Literal

from pacd_sim.schema import ConsequentialRecord, NonNegativeFloat, StableId

type RequestedAuthority = Literal["automatic", "human", "prohibited"]


class DefensiveAction(ConsequentialRecord):
    """Candidate action carrying authority, cost, verification, and rollback intent."""

    action_type: StableId
    target_id: StableId
    reversible: bool
    requested_authority: RequestedAuthority
    expected_effect: str = "bounded simulated state transition"
    mission_cost: NonNegativeFloat = 0.0
    preconditions: tuple[str, ...] = ()
    verification: str = "compare immutable simulated state"
    rollback: str | None = None


def action_sort_key(action: DefensiveAction) -> tuple[int, str, str, str]:
    """Return the stable order used throughout orchestration and execution."""

    return (action.tick, action.action_type, action.target_id, action.id)

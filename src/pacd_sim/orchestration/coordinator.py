"""Stable reconciliation of defender proposals without safety-policy authority."""

from collections.abc import Iterable

from pacd_sim.actions.models import DefensiveAction, action_sort_key
from pacd_sim.defenders.base import DefenderDecision
from pacd_sim.schema import ConsequentialRecord, StableId


class CoordinationResult(ConsequentialRecord):
    """Ordered proposals plus IDs suppressed as exact duplicates."""

    action_sequence: tuple[DefensiveAction, ...]
    suppressed_action_ids: tuple[StableId, ...] = ()
    rationale: str


class ProposalCoordinator:
    """Reconcile candidates while leaving admissibility to the governor."""

    def coordinate(self, decisions: Iterable[DefenderDecision]) -> CoordinationResult:
        ordered_decisions = tuple(
            sorted(decisions, key=lambda item: (item.tick, item.defender_id, item.id))
        )
        candidates = sorted(
            (action for decision in ordered_decisions for action in decision.proposed_actions),
            key=lambda item: (item.mission_cost, *action_sort_key(item)),
        )
        selected: dict[tuple[str, str], DefensiveAction] = {}
        suppressed: list[str] = []
        for action in candidates:
            key = (action.action_type, action.target_id)
            if key in selected:
                suppressed.append(action.id)
            else:
                selected[key] = action
        sequence = tuple(sorted(selected.values(), key=action_sort_key))
        latest_tick = max((item.tick for item in ordered_decisions), default=0)
        return CoordinationResult(
            id=f"coordination-{latest_tick}",
            tick=latest_tick,
            action_sequence=sequence,
            suppressed_action_ids=tuple(sorted(suppressed)),
            rationale="exact duplicate targets were resolved by cost and stable ordering",
        )

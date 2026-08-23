"""Transparent scoring and deterministic selection of simulated variation operators."""

from collections.abc import Iterable
from typing import Literal

from pacd_sim.reproducibility.canonical import create_rng
from pacd_sim.schema import ConsequentialRecord, Probability, StableId

type OperatorCategory = Literal[
    "sensing",
    "deception",
    "infrastructure",
    "identity",
    "response",
    "coordination",
]


class PolymorphismOperator(ConsequentialRecord):
    """A simulation-only variation with explicit benefit, cost, and reversibility."""

    category: OperatorCategory
    variant: StableId
    expected_benefit: Probability
    mission_cost: Probability
    reversible: bool = True

    @property
    def score(self) -> float:
        return self.expected_benefit - self.mission_cost


def rank_operators(
    operators: Iterable[PolymorphismOperator],
) -> tuple[PolymorphismOperator, ...]:
    """Rank operators by transparent score and stable ID tie-breaking."""

    return tuple(sorted(operators, key=lambda item: (-item.score, item.id)))


def select_operator(
    operators: Iterable[PolymorphismOperator],
    run_seed: int,
    namespace: str = "polymorphism",
) -> PolymorphismOperator | None:
    """Choose reproducibly among equally best reversible operators."""

    ranked = tuple(item for item in rank_operators(operators) if item.reversible)
    if not ranked:
        return None
    best_score = ranked[0].score
    tied = tuple(item for item in ranked if abs(item.score - best_score) <= 1e-12)
    if len(tied) == 1:
        return tied[0]
    rng = create_rng(run_seed, namespace)
    return tied[int(rng.integers(0, len(tied)))]

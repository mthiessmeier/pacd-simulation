"""A fixed signal rule for human review of synthetic observations."""

from typing import Final

from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.defenders.observations import ReviewProposal as ReviewProposal

STATIC_REVIEW_VERSION: Final = "static_signal_review_v1"
MINIMUM_REVIEW_SIGNAL: Final = 0.75


def propose_review(observation: BaselineObservation) -> ReviewProposal | None:
    """Propose human review for an identified subject at or above the fixed threshold."""
    if observation.subject_id is None or observation.signal < MINIMUM_REVIEW_SIGNAL:
        return None
    return ReviewProposal(target_id=observation.subject_id)

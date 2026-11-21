"""Adapt a delivered sensor observation to the static rule and its governed candidate."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.defenders.base import BaselineObservation
from pacd_sim.defenders.baselines.static import propose_review
from pacd_sim.telemetry.generator import Observation


def static_review_candidate(
    observation: Observation, ordinal: int, protocol_version: str
) -> tuple[BaselineObservation, DefensiveAction | None]:
    subject = observation.identity_id or observation.target_id
    reading = BaselineObservation(
        tick=observation.tick,
        subject_id=None if subject == "synthetic-unknown" else subject,
        signal=observation.signal,
    )
    proposal = propose_review(reading)
    if proposal is None:
        return reading, None
    return reading, DefensiveAction(
        id=f"action-static-review-{ordinal}",
        tick=reading.tick,
        configuration_version=protocol_version,
        action_type=proposal.action_type,
        target_id=proposal.target_id,
        reversible=True,
        requested_authority=proposal.requested_authority,
    )

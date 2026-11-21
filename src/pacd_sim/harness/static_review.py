"""Adapt delivered sensor observations and human-review proposals to the governed harness."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.defenders.baselines.static import propose_review
from pacd_sim.defenders.observations import BaselineObservation, ReviewProposal
from pacd_sim.telemetry.generator import Observation


def sensor_reading(observation: Observation) -> BaselineObservation:
    subject = observation.identity_id or observation.target_id
    return BaselineObservation(
        tick=observation.tick,
        subject_id=None if subject == "synthetic-unknown" else subject,
        signal=observation.signal,
    )


def review_action(
    reading: BaselineObservation,
    proposal: ReviewProposal | None,
    action_id: str,
    protocol_version: str,
) -> DefensiveAction | None:
    if proposal is None:
        return None
    return DefensiveAction(
        id=action_id,
        tick=reading.tick,
        configuration_version=protocol_version,
        action_type=proposal.action_type,
        target_id=proposal.target_id,
        reversible=True,
        requested_authority=proposal.requested_authority,
    )


def static_review_candidate(
    observation: Observation, ordinal: int, protocol_version: str
) -> tuple[BaselineObservation, DefensiveAction | None]:
    reading = sensor_reading(observation)
    return reading, review_action(
        reading, propose_review(reading), f"action-static-review-{ordinal}", protocol_version
    )

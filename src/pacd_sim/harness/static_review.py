"""Adapt delivered sensor observations and human-review proposals to the governed harness."""

from typing import Final, TypedDict

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.configuration import GuardedReviewConfig
from pacd_sim.defenders.baselines.static import propose_review
from pacd_sim.defenders.observations import BaselineObservation, ReviewProposal
from pacd_sim.oversight.guarded import GuardedReviewQueue
from pacd_sim.telemetry.generator import Observation

# These evaluator settings define the same referral episode in every guarded condition.
_ELEVATED_SIGNAL: Final = 0.75
_MAX_REFERRAL_GAP_TICKS: Final = 3


class ReviewEpisodeGate:
    """Admit the first eligible referral per elevated episode for either condition."""

    def __init__(self) -> None:
        self._episodes: dict[str, tuple[int, bool]] = {}

    def suppress(self, reading: BaselineObservation, candidate: DefensiveAction | None) -> bool:
        subject = reading.subject_id
        if subject is None:
            return False
        if reading.signal < _ELEVATED_SIGNAL:
            self._episodes.pop(subject, None)
            return False
        prior = self._episodes.get(subject)
        referred = (
            prior is not None and reading.tick - prior[0] <= _MAX_REFERRAL_GAP_TICKS and prior[1]
        )
        self._episodes[subject] = (reading.tick, referred or candidate is not None)
        return referred and candidate is not None


class _DetectorOptions(TypedDict, total=False):
    benign_signal_mean: float
    adversary_signal_mean: float


def review_detector_options(config: GuardedReviewConfig | None) -> _DetectorOptions:
    """Bind the same sensor distribution to each truth condition in a matched fixture."""
    if config is None:
        return {}
    return {
        "benign_signal_mean": config.matched_signal_mean,
        "adversary_signal_mean": config.matched_signal_mean,
    }


def review_queue(config: GuardedReviewConfig) -> GuardedReviewQueue:
    return GuardedReviewQueue(
        capacity=config.capacity,
        delay_ticks=config.delay_ticks,
        ttl_ticks=config.validity_ticks,
        approve={"approve": True, "deny": False, "no_response": None}[config.response],
        rollback=config.rollback,
    )


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

"""Stateful, observation-only review planning for bounded synthetic episodes."""

from dataclasses import dataclass
from typing import Final, Literal

from pacd_sim.defenders.observations import BaselineObservation, ReviewProposal
from pacd_sim.schema import NonNegativeTick, StrictFrozenModel

POLICY: Final = "pacd_corroborated_review_v1"
MINIMUM_SIGNAL: Final = 0.75
MAX_GAP_TICKS: Final = 3

type Outcome = Literal[
    "no_subject", "below_threshold", "awaiting_corroboration", "already_referred", "proposed"
]


class ReviewStep(StrictFrozenModel):
    """The current input, its active same-subject predecessor and the planner's decision."""

    observation: BaselineObservation
    previous_elevated_tick: NonNegativeTick | None
    outcome: Outcome
    proposal: ReviewProposal | None


@dataclass(frozen=True)
class _ElevatedSubject:
    tick: int
    referred: bool


class CorroboratedReviewPlanner:
    """Issue one review request per sustained episode of elevated same-subject readings."""

    def __init__(self, *, suppress_repeats: bool = True) -> None:
        self._subjects: dict[str, _ElevatedSubject] = {}
        self._last_tick = -1
        self._suppress_repeats = suppress_repeats

    def observe(self, reading: BaselineObservation) -> ReviewStep:
        if reading.tick < self._last_tick:
            raise ValueError("Sensor readings must be delivered in nondecreasing tick order")
        if reading.tick > self._last_tick:
            self._subjects = {
                subject: entry
                for subject, entry in self._subjects.items()
                if reading.tick - entry.tick <= MAX_GAP_TICKS
            }
            self._last_tick = reading.tick

        subject = reading.subject_id
        prior = self._subjects.get(subject) if subject is not None else None
        outcome: Outcome
        proposal = None
        if subject is None or subject == "synthetic-unknown":
            outcome = "no_subject"
        elif reading.signal < MINIMUM_SIGNAL:
            self._subjects.pop(subject, None)
            outcome = "below_threshold"
        else:
            if prior is None or (not prior.referred and prior.tick == reading.tick):
                outcome = "awaiting_corroboration"
            elif prior.referred and self._suppress_repeats:
                outcome = "already_referred"
            else:
                outcome = "proposed"
                proposal = ReviewProposal(target_id=subject)
            self._subjects[subject] = _ElevatedSubject(
                tick=reading.tick, referred=outcome in ("proposed", "already_referred")
            )
        return ReviewStep(
            observation=reading,
            previous_elevated_tick=prior.tick if prior else None,
            outcome=outcome,
            proposal=proposal,
        )

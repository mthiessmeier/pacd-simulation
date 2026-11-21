"""Sensor-only inputs and human-review proposals shared by diagnostic policies."""

from typing import Literal

from pacd_sim.schema import NonNegativeTick, Probability, StableId, StrictFrozenModel


class BaselineObservation(StrictFrozenModel):
    """Sensor fields available to an observation-only defender at delivery."""

    tick: NonNegativeTick
    subject_id: StableId | None
    signal: Probability


class ReviewProposal(StrictFrozenModel):
    """A request for human review before any policy evaluation or execution."""

    target_id: StableId
    action_type: Literal["require_human_review"] = "require_human_review"
    requested_authority: Literal["human"] = "human"

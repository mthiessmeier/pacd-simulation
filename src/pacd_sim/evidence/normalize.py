"""Normalization of synthetic observations into provenance-preserving evidence."""

from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from pacd_sim.evidence.context import MAX_READINGS
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import ConsequentialRecord, Probability, Sha256Digest, StableId
from pacd_sim.telemetry.generator import Observation

EvidenceCategory = Literal["benign_context", "adversary_indicator", "unknown_signal"]


class EvidenceItem(ConsequentialRecord):
    """Normalized evidence that retains the source observation identifiers."""

    category: EvidenceCategory
    subject_id: StableId | None = None
    confidence: Probability
    integrity: Probability
    observation_ids: tuple[StableId, ...]
    provenance: tuple[StableId, ...]
    delivery_digest: Sha256Digest | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def normalize_observation(
    observation: Observation, *, delivery_ordinal: int | None = None
) -> EvidenceItem:
    """Normalize one synthetic observation without declaring compromise."""

    delivery_digest = None
    if delivery_ordinal is not None:
        if type(delivery_ordinal) is not int or not 1 <= delivery_ordinal <= MAX_READINGS:
            raise ValueError("delivery ordinal must identify a governed observation")
        delivery_digest = canonical_sha256(
            {
                "observation_key": delivery_ordinal,
                "observation": observation.model_dump(mode="json"),
            }
        )
    if observation.event_kind == "benign_administrative":
        category: EvidenceCategory = "benign_context"
        confidence = 1.0 - observation.signal
    elif observation.event_kind == "simulated_adversary":
        category = "adversary_indicator"
        confidence = observation.signal
    else:
        category = "unknown_signal"
        confidence = abs(observation.signal - 0.5) * 2.0
    subject_id = observation.identity_id or observation.target_id
    return EvidenceItem(
        id=f"evidence-{observation.id}",
        tick=observation.tick,
        configuration_version=observation.configuration_version,
        category=category,
        subject_id=subject_id,
        confidence=min(1.0, max(0.0, confidence)),
        integrity=observation.integrity,
        observation_ids=(observation.id,),
        provenance=tuple(sorted((observation.id, observation.sensor_id))),
        delivery_digest=delivery_digest,
    )


def normalize_observations(observations: Iterable[Observation]) -> tuple[EvidenceItem, ...]:
    """Normalize a collection in deterministic tick/ID order."""

    normalized = (normalize_observation(item) for item in observations)
    return tuple(sorted(normalized, key=lambda item: (item.tick, item.id)))

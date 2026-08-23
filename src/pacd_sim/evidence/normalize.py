"""Normalization of synthetic observations into provenance-preserving evidence."""

from collections.abc import Iterable
from typing import Literal

from pacd_sim.schema import ConsequentialRecord, Probability, StableId
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


def normalize_observation(observation: Observation) -> EvidenceItem:
    """Normalize one synthetic observation without declaring compromise."""

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
    )


def normalize_observations(observations: Iterable[Observation]) -> tuple[EvidenceItem, ...]:
    """Normalize a collection in deterministic tick/ID order."""

    normalized = (normalize_observation(item) for item in observations)
    return tuple(sorted(normalized, key=lambda item: (item.tick, item.id)))

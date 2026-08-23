"""Deterministic update of competing synthetic threat hypotheses."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Literal, Self

from pydantic import field_validator, model_validator

from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.schema import ConsequentialRecord, Probability, StableId

HypothesisLabel = Literal["benign", "compromise"]


class ThreatHypothesis(ConsequentialRecord):
    """One explicitly uncertain hypothesis about a synthetic subject."""

    subject_id: StableId
    label: HypothesisLabel
    probability: Probability
    evidence_ids: tuple[StableId, ...] = ()


class AdversaryState(ConsequentialRecord):
    """Bounded red-agent state with no operational capability."""

    id: StableId = "adversary-synthetic-diagnostic"
    active: bool = False
    objective: str = "synthetic diagnostic behavior only"
    stage: StableId = "inactive"


class BeliefState(ConsequentialRecord):
    """Stable collection of competing hypotheses and synthetic adversary state."""

    id: StableId = "belief-state-synthetic"
    hypotheses: tuple[ThreatHypothesis, ...] = ()
    adversary_state: AdversaryState = AdversaryState()

    @field_validator("hypotheses")
    @classmethod
    def _sort_hypotheses(cls, value: tuple[ThreatHypothesis, ...]) -> tuple[ThreatHypothesis, ...]:
        return tuple(sorted(value, key=lambda item: (item.subject_id, item.label, item.id)))

    @model_validator(mode="after")
    def _validate_competing_hypotheses(self) -> Self:
        keys = tuple((item.subject_id, item.label) for item in self.hypotheses)
        if len(keys) != len(set(keys)):
            raise ValueError("belief state contains duplicate subject/label hypotheses")
        by_subject: dict[str, list[ThreatHypothesis]] = defaultdict(list)
        for hypothesis in self.hypotheses:
            by_subject[hypothesis.subject_id].append(hypothesis)
        for hypotheses in by_subject.values():
            if {item.label for item in hypotheses} == {"benign", "compromise"}:
                total = sum(item.probability for item in hypotheses)
                if abs(total - 1.0) > 1e-12:
                    raise ValueError("competing hypothesis probabilities must sum to one")
        return self

    def compromise_probability(self, subject_id: str) -> float:
        """Return the explicit compromise probability, or a conservative prior."""

        for hypothesis in self.hypotheses:
            if hypothesis.subject_id == subject_id and hypothesis.label == "compromise":
                return hypothesis.probability
        return 0.1


def update_beliefs(
    evidence: Iterable[EvidenceItem],
    prior: BeliefState | None = None,
) -> BeliefState:
    """Apply a transparent bounded update; benign context never implies compromise."""

    ordered = tuple(sorted(evidence, key=lambda item: (item.tick, item.id)))
    grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in ordered:
        if item.subject_id is not None:
            grouped[item.subject_id].append(item)
    hypotheses: list[ThreatHypothesis] = []
    for subject_id in sorted(grouped):
        probability = prior.compromise_probability(subject_id) if prior is not None else 0.1
        subject_evidence = grouped[subject_id]
        for item in subject_evidence:
            strength = item.confidence * item.integrity
            if item.category == "adversary_indicator":
                probability = probability + (1.0 - probability) * strength
            elif item.category == "benign_context":
                probability = probability * (1.0 - 0.5 * strength)
        probability = min(1.0, max(0.0, probability))
        evidence_ids = tuple(item.id for item in subject_evidence)
        latest_tick = max(item.tick for item in subject_evidence)
        hypotheses.extend(
            (
                ThreatHypothesis(
                    id=f"hypothesis-{subject_id}-benign",
                    tick=latest_tick,
                    label="benign",
                    subject_id=subject_id,
                    probability=1.0 - probability,
                    evidence_ids=evidence_ids,
                ),
                ThreatHypothesis(
                    id=f"hypothesis-{subject_id}-compromise",
                    tick=latest_tick,
                    label="compromise",
                    subject_id=subject_id,
                    probability=probability,
                    evidence_ids=evidence_ids,
                ),
            )
        )
    latest_tick = max((item.tick for item in ordered), default=0)
    active = any(item.category == "adversary_indicator" for item in ordered)
    adversary_state = AdversaryState(
        tick=latest_tick,
        active=active,
        stage="synthetic_observed" if active else "inactive",
    )
    return BeliefState(
        tick=latest_tick,
        hypotheses=tuple(hypotheses),
        adversary_state=adversary_state,
    )

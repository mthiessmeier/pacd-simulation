"""Provenance and freshness of the sensor information available at delivery."""

from typing import Annotated, Final, Self

from pydantic import ConfigDict, Field, model_validator

from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import Probability, Signed64Count, StableId, StrictFrozenModel

MAX_AGE_TICKS: Final = 3
# The governed diagnostic scenario accepts at most 100 full-coverage events.
MAX_READINGS: Final = 100

type OpaqueKey = Annotated[Signed64Count, Field(gt=0)]


class EvidenceReading(StrictFrozenModel):
    """Episode-local observation with opaque source and record keys, in simulated ticks."""

    model_config = ConfigDict(revalidate_instances="always")

    observation_key: OpaqueKey
    source_key: OpaqueKey
    subject_id: StableId | None
    measured_tick: Signed64Count
    delivered_tick: Signed64Count
    signal: Probability

    @model_validator(mode="after")
    def _validate_clock(self) -> Self:
        if self.measured_tick > self.delivered_tick:
            raise ValueError("measurement cannot follow delivery")
        return self


def evidence_trace(readings: tuple[EvidenceReading, ...]) -> dict[str, object]:
    """Account for fresh source presence per subject in delivery order, without scoring belief."""
    _, trace = evidence_trace_with_readings(readings)
    return trace


def evidence_trace_with_readings(
    readings: tuple[EvidenceReading, ...],
) -> tuple[tuple[EvidenceReading, ...], dict[str, object]]:
    """Return the validated deliveries used to construct the trace and its digest."""
    if len(readings) > MAX_READINGS:
        raise ValueError(f"evidence trace is limited to {MAX_READINGS} readings")
    validated: list[EvidenceReading] = []
    seen: dict[int, EvidenceReading] = {}
    # Measurements delivered out of acquisition order must not shorten a source's lifetime.
    latest_measurement: dict[tuple[str, int], int] = {}
    decisions: list[dict[str, object]] = []
    clock = 0
    for item in readings:
        # model_copy can bypass validation. Consumers must use the values hashed in the trace.
        reading = EvidenceReading.model_validate(item)
        validated.append(reading)
        prior = seen.get(reading.observation_key)
        if prior is not None and prior != reading:
            raise ValueError("conflicting reuse of an observation key")
        if prior is None and reading.delivered_tick < clock:
            raise ValueError("new evidence must arrive in nondecreasing delivery order")
        # An exact duplicate carries the original delivery tick, even after expiry.
        clock = max(clock, reading.delivered_tick)
        age = clock - reading.measured_tick
        latest_measurement = {
            key: measured
            for key, measured in latest_measurement.items()
            if clock - measured <= MAX_AGE_TICKS
        }
        subject = reading.subject_id
        sources = {source for owner, source in latest_measurement if owner == subject}
        if prior is not None:
            relation = "duplicate"
        elif subject is None or subject == "synthetic-unknown":
            relation = "no_subject"
        elif age > MAX_AGE_TICKS:
            relation = "stale"
        else:
            if reading.source_key in sources:
                relation = "repeated_source"
            elif sources:
                relation = "distinct_source"
            else:
                relation = "first_source"
            sources.add(reading.source_key)
            key = (subject, reading.source_key)
            latest_measurement[key] = max(latest_measurement.get(key, 0), reading.measured_tick)
        seen[reading.observation_key] = reading
        decisions.append(
            {
                "reading": reading.model_dump(mode="json"),
                "as_of_tick": clock,
                "age_ticks": age,
                "freshness": "fresh" if age <= MAX_AGE_TICKS else "stale",
                "source_relation": relation,
                "eligible_distinct_source_count": len(sources),
            }
        )
    trace: dict[str, object] = {
        "version": "evidence_context_v1",
        "max_age_ticks": MAX_AGE_TICKS,
        "input_count": len(readings),
        "decisions": decisions,
    }
    trace["trace_sha256"] = canonical_sha256(trace)
    return tuple(validated), trace

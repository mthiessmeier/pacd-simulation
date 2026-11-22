"""Checks for subject-scoped, time-bounded sensor provenance and deterministic tracing."""

from typing import cast

import pytest
from pydantic import ValidationError

from pacd_sim.evidence.context import EvidenceReading, evidence_trace
from pacd_sim.reproducibility.canonical import canonical_sha256


def reading(
    key: int, source: int, measured: int, delivered: int, subject: str | None = "subject"
) -> EvidenceReading:
    return EvidenceReading(
        observation_key=key,
        source_key=source,
        subject_id=subject,
        measured_tick=measured,
        delivered_tick=delivered,
        signal=0.25,
    )


def steps(*readings: EvidenceReading) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], evidence_trace(readings)["decisions"])


def test_freshness_uses_measurement_clock_and_includes_boundary() -> None:
    decisions = steps(
        reading(1, 11, 1, 4),
        reading(2, 12, 0, 4),
        reading(3, 12, 3, 4),
        reading(4, 13, 1, 5),
        reading(5, 12, 4, 5),
        reading(6, 11, 5, 5),
    )
    assert [
        (d["age_ticks"], d["freshness"], d["source_relation"], d["eligible_distinct_source_count"])
        for d in decisions
    ] == [
        (3, "fresh", "first_source", 1),
        (4, "stale", "stale", 1),
        (1, "fresh", "distinct_source", 2),
        (4, "stale", "stale", 1),
        (1, "fresh", "repeated_source", 1),
        (0, "fresh", "distinct_source", 2),
    ]


def test_repeated_source_out_of_measurement_order_preserves_newest_tick() -> None:
    decisions = steps(reading(1, 1, 4, 4), reading(2, 1, 2, 5), reading(3, 2, 7, 7))
    assert [(d["source_relation"], d["eligible_distinct_source_count"]) for d in decisions] == [
        ("first_source", 1),
        ("repeated_source", 1),
        ("distinct_source", 2),
    ]


def test_source_count_does_not_measure_agreement_or_leak_across_subjects() -> None:
    a = reading(1, 1, 0, 0, "a")
    opposite = reading(2, 2, 0, 0, "a").model_copy(update={"signal": 1.0})
    b = reading(3, 1, 0, 0, "b")
    decisions = steps(a, opposite, b, reading(4, 2, 0, 0, None))
    assert [(d["source_relation"], d["eligible_distinct_source_count"]) for d in decisions] == [
        ("first_source", 1),
        ("distinct_source", 2),
        ("first_source", 1),
        ("no_subject", 0),
    ]
    assert steps(reading(1, 1, 0, 0, "synthetic-unknown"))[0]["source_relation"] == "no_subject"


def test_exact_duplicate_cannot_restore_expired_support_or_rewind_time() -> None:
    first = reading(1, 1, 1, 2)
    later = reading(2, 2, 5, 6)
    decisions = steps(first, first, later, first, reading(3, 3, 6, 6))
    assert [d["source_relation"] for d in decisions] == [
        "first_source",
        "duplicate",
        "first_source",
        "duplicate",
        "distinct_source",
    ]
    assert [d["eligible_distinct_source_count"] for d in decisions] == [1, 1, 1, 1, 2]
    assert (decisions[3]["as_of_tick"], decisions[3]["age_ticks"], decisions[3]["freshness"]) == (
        6,
        5,
        "stale",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signal", 0.1),
        ("source_key", 2),
        ("measured_tick", 2),
        ("delivered_tick", 4),
        ("subject_id", None),
    ],
)
def test_conflicting_reuse_is_rejected_even_after_expiry(field: str, value: object) -> None:
    first = reading(1, 1, 1, 3)
    with pytest.raises(ValueError, match="conflicting"):
        evidence_trace((first, reading(2, 2, 9, 9), first.model_copy(update={field: value})))


def test_new_key_cannot_rewind_delivery_clock() -> None:
    with pytest.raises(ValueError, match="delivery order"):
        steps(reading(1, 1, 4, 5), reading(2, 1, 1, 3))


def test_trace_has_no_episode_state_or_evaluator_only_fields() -> None:
    inputs = (reading(1, 1, 0, 0),)
    trace = evidence_trace(inputs)
    assert trace == evidence_trace(inputs)
    assert trace["version"] == "evidence_context_v1"
    assert trace["input_count"] == 1 and trace["max_age_ticks"] == 3
    assert trace.pop("trace_sha256") == canonical_sha256(trace)
    assert steps(*inputs)[0]["reading"] == {
        "observation_key": 1,
        "source_key": 1,
        "subject_id": "subject",
        "measured_tick": 0,
        "delivered_tick": 0,
        "signal": 0.25,
    }
    assert steps() == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signal", float("nan")),
        ("signal", 1.01),
        ("measured_tick", -1),
        ("measured_tick", 5),
        ("delivered_tick", "2"),
        ("observation_key", 0),
        ("source_key", True),
        ("subject_id", "x" * 257),
        ("event_kind", "evaluator_truth"),
    ],
)
def test_malformed_or_nonobservational_input_rejected(field: str, value: object) -> None:
    fields = reading(1, 1, 1, 2).model_dump()
    fields[field] = value
    with pytest.raises(ValidationError):
        EvidenceReading.model_validate(fields)


def test_input_and_duplicate_memory_are_bounded_by_governed_episode_size() -> None:
    first = reading(1, 1, 0, 0)
    assert evidence_trace((first,) * 100)["input_count"] == 100
    with pytest.raises(ValueError, match="limited to 100"):
        evidence_trace((first,) * 101)


def test_unvalidated_model_copy_cannot_publish_an_impossible_measurement() -> None:
    invalid = reading(1, 1, 0, 0).model_copy(update={"measured_tick": 3})
    with pytest.raises(ValidationError, match="measurement cannot follow delivery"):
        evidence_trace((invalid,))

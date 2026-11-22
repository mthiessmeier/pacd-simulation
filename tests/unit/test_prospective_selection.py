"""Development sensing selections at the third delivered observation."""

from fractions import Fraction
from math import copysign, nextafter
from typing import cast

import pytest

from pacd_sim.evidence.context import EvidenceReading, evidence_trace
from pacd_sim.polymorphism.selection import CONTEXTUAL, SCHEDULED, select_profile


def reading(
    key: int,
    measured: int,
    delivered: int,
    signal: float = 1.0,
    subject: str | None = "user",
    source: int = 1,
) -> EvidenceReading:
    return EvidenceReading(
        observation_key=key,
        source_key=source,
        subject_id=subject,
        measured_tick=measured,
        delivered_tick=delivered,
        signal=signal,
    )


def test_prefix_digest_persistence_discount_and_schedule() -> None:
    items = (reading(1, 1, 2, 0.9), reading(2, 1, 2, 0.5), reading(3, 2, 3, 0.75))
    outcome, detail = select_profile(CONTEXTUAL, items, 0.25, 1.0)
    assert outcome == "proposed"
    assert detail == {
        "selection_version": "sensing_selection_v1",
        "prefix_trace_sha256": evidence_trace(items)["trace_sha256"],
        "age_ticks": 1,
        "eligible_distinct_source_count": 1,
        "reference_measured_tick": 1,
        "reference_signal": 0.5,
        "benefit": 0.375,
        "utility": 0.125,
        "utility_exact": "1/8",
        "selected_profile": "alternate",
        "selection_reason": "proposed",
    }
    for prefix in (items[:1], items[:2], (*items, reading(4, 3, 4, 0.0))):
        outcome, detail = select_profile(CONTEXTUAL, prefix, 0.25, 1.0)
        assert outcome == "outside_opportunity" and detail["selected_profile"] is None
        assert detail["prefix_trace_sha256"] == evidence_trace(prefix)["trace_sha256"]
        assert detail["utility"] is None and detail["reference_signal"] is None
        assert detail["utility_exact"] is None


def test_reference_uses_newest_eligible_measurement_and_current_subject() -> None:
    current = reading(3, 3, 4, 0.75)
    previous = reading(1, 2, 3, 0.875)
    for other in (
        reading(2, 1, 4, 0.0),  # older acquisition delivered later
        reading(2, 3, 3, 0.0),  # simultaneous measurement
        reading(2, 4, 4, 0.0),  # newer measurement delivered first
        reading(2, 3, 3, 0.0, "other"),
    ):
        outcome, detail = select_profile(CONTEXTUAL, (previous, other, current), 0.5, 1.0)
        assert outcome == "proposed"
        assert detail["reference_measured_tick"] == 2 and detail["reference_signal"] == 0.875
        assert detail["benefit"] == 0.5625


@pytest.mark.parametrize(
    "history",
    [
        (reading(1, 0, 0), reading(2, 0, 1)),  # fresh on arrival, expired at decision
        (reading(1, 2, 3, subject=None), reading(2, 2, 3, subject="other")),
        (reading(1, 3, 3), reading(2, 4, 4)),  # same or later measurement
    ],
)
def test_only_contextual_requires_earlier_fresh_attributable_history(
    history: tuple[EvidenceReading, EvidenceReading],
) -> None:
    items = (*history, reading(3, 3, 4))
    outcome, detail = select_profile(CONTEXTUAL, items, 0.0, 0.0)
    assert outcome == "insufficient_history" and detail["selected_profile"] == "default"
    assert detail["benefit"] is None and detail["utility"] is None
    outcome, detail = select_profile(SCHEDULED, items, 0.0, 0.0)
    assert outcome == "proposed" and detail["selected_profile"] == "alternate"
    assert detail["reference_measured_tick"] is None and detail["utility"] is None
    assert detail["utility_exact"] is None


def test_equal_utility_falls_back_and_positive_margin_refers() -> None:
    items = (reading(1, 1, 1), reading(2, 2, 2), reading(3, 3, 5, 0.5))
    for cost in (0.25, 1.0):
        outcome, detail = select_profile(CONTEXTUAL, items, cost, 1.0)
        assert outcome == "no_positive_gain" and detail["selected_profile"] == "default"
        assert detail["benefit"] == 0.25 and detail["utility"] == 0.25 - cost
        assert select_profile(SCHEDULED, items, cost, 1.0)[0] == "proposed"
    assert select_profile(CONTEXTUAL, items, nextafter(0.25, 0.0), 1.0)[0] == "proposed"


@pytest.mark.parametrize(
    ("cost", "outcome", "margin"),
    [
        (nextafter(0.075, 0.0), "proposed", "1/50000000000000000"),
        (0.075, "no_positive_gain", "0"),
        (nextafter(0.075, 1.0), "no_positive_gain", "-1/100000000000000000"),
    ],
)
def test_decimal_tie_and_adjacent_costs(cost: float, outcome: str, margin: str) -> None:
    inputs = (reading(1, 1, 2, 0.1), reading(2, 1, 2, 0.9), reading(3, 2, 3, 0.4))
    actual, detail = select_profile(CONTEXTUAL, inputs, cost, 1.0)
    assert actual == outcome
    assert detail["benefit"] == 0.075
    assert detail["utility_exact"] == margin and detail["utility"] == float(Fraction(margin))


@pytest.mark.parametrize(
    ("signal", "cost", "outcome", "sign"),
    [(1.5e-323, 1e-323, "proposed", 1), (5e-324, 5e-324, "no_positive_gain", -1)],
)
def test_exact_audit_preserves_sign_when_numeric_display_underflows(
    signal: float, cost: float, outcome: str, sign: int
) -> None:
    inputs = (reading(1, 1, 2), reading(2, 1, 2), reading(3, 2, 3, signal))
    actual, detail = select_profile(CONTEXTUAL, inputs, cost, 1.0)
    assert actual == outcome
    assert detail["utility_exact"] == str(Fraction(sign, 8 * 10**323))
    display = cast(float, detail["utility"])
    assert display == 0.0 and copysign(1.0, display) == sign


@pytest.mark.parametrize("condition", [CONTEXTUAL, SCHEDULED])
def test_evaluator_precedence_and_freshness_boundary(condition: str) -> None:
    first = reading(1, 1, 1)
    second = reading(2, 2, 2)
    for current, cost, budget, reason in (
        (reading(3, 2, 5), 1.0, 0.0, "over_budget"),  # age 3 is fresh
        (reading(3, 2, 6), 1.0, 0.0, "stale_evidence"),
        (reading(3, 2, 6, subject=None), 1.0, 0.0, "no_subject"),
        (reading(3, 2, 6, subject="synthetic-unknown"), 0.0, 1.0, "no_subject"),
        (second, 0.0, 1.0, "duplicate_evidence"),
    ):
        outcome, detail = select_profile(condition, (first, second, current), cost, budget)
        assert outcome == reason and detail["selection_reason"] == reason
        assert detail["selected_profile"] == "default" and detail["benefit"] is None
    assert select_profile(condition, (first, second, reading(3, 1, 4)), 0.0, 0.0)[0] == (
        "proposed" if condition == SCHEDULED else "insufficient_history"
    )


def test_duplicate_history_does_not_multiply_signal_or_source_count() -> None:
    first = reading(1, 1, 1, 0.125)
    items = (first, first, reading(3, 2, 2, 0.5))
    outcome, detail = select_profile(CONTEXTUAL, items, 0.125, 1.0)
    assert outcome == "no_positive_gain"
    assert detail["benefit"] == 0.125 and detail["eligible_distinct_source_count"] == 1
    other_sensor = first.model_copy(update={"observation_key": 2, "source_key": 2})
    _, other_detail = select_profile(CONTEXTUAL, (first, other_sensor, items[-1]), 0.125, 1.0)
    assert other_detail["benefit"] == detail["benefit"]
    assert other_detail["eligible_distinct_source_count"] == 2


def test_duplicate_keeps_original_clock_and_cannot_renew_expired_budget_eligibility() -> None:
    first = reading(1, 1, 1)
    items = (first, reading(2, 9, 9, subject="other"), first)
    outcome, detail = select_profile(SCHEDULED, items, 0.0, 1.0)
    assert outcome == "stale_evidence" and detail["age_ticks"] == 8


@pytest.mark.parametrize("invalid", [True, -1.0, 1.001, float("nan"), float("inf"), "1"])
def test_cost_and_budget_validated_even_before_opportunity(invalid: object) -> None:
    prefix = (reading(1, 1, 1),)
    for cost, budget in ((cast(float, invalid), 1.0), (1.0, cast(float, invalid))):
        with pytest.raises(ValueError):
            select_profile(CONTEXTUAL, prefix, cost, budget)


def test_invalid_prefix_cannot_publish_a_decision() -> None:
    first = reading(1, 1, 1)
    for prefix in (
        (),
        (first,) * 101,
        (first, first.model_copy(update={"signal": 0.5})),
        (first, reading(2, 0, 0)),
        (first.model_copy(update={"delivered_tick": 0}),),
    ):
        with pytest.raises(ValueError):
            select_profile(CONTEXTUAL, prefix, 0.0, 1.0)
    with pytest.raises(ValueError, match="unexpected"):
        select_profile("unregistered", (first,), 0.25, 1.0)

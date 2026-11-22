"""Prospective selection between the default and alternate synthetic sensing profiles."""

from fractions import Fraction
from typing import Final, cast

from pydantic import TypeAdapter

from pacd_sim.evidence.context import (
    MAX_AGE_TICKS,
    MAX_READINGS,
    EvidenceReading,
    evidence_trace_with_readings,
)
from pacd_sim.schema import Probability

CONTEXTUAL: Final = "sensing_contextual_v1"
SCHEDULED: Final = "sensing_scheduled_v1"
_PROBABILITY: Final[TypeAdapter[float]] = TypeAdapter(Probability)


def select_profile(
    condition: str, prefix: tuple[EvidenceReading, ...], switch_cost: float, budget: float
) -> tuple[str, dict[str, object]]:
    """Consider a sensing referral using only the bounded prefix available at delivery."""
    if condition not in (CONTEXTUAL, SCHEDULED):
        raise ValueError("unexpected prospective sensing condition")
    if not isinstance(prefix, tuple) or not 1 <= len(prefix) <= MAX_READINGS:
        raise ValueError("selection requires a nonempty, bounded delivery prefix")
    if not all(isinstance(reading, EvidenceReading) for reading in prefix):
        raise ValueError("selection requires typed evidence readings")
    switch_cost = _PROBABILITY.validate_python(switch_cost, strict=True)
    budget = _PROBABILITY.validate_python(budget, strict=True)

    prefix, trace = evidence_trace_with_readings(prefix)
    current = prefix[-1]
    step = cast(list[dict[str, object]], trace["decisions"])[-1]
    age = cast(int, step["age_ticks"])
    clock = cast(int, step["as_of_tick"])
    reference_tick = None
    reference_signal = None
    benefit = None
    utility = None
    utility_exact = None

    if len(prefix) != 3:
        outcome = "outside_opportunity"
    elif current.subject_id in (None, "synthetic-unknown"):
        outcome = "no_subject"
    elif step["freshness"] == "stale":
        outcome = "stale_evidence"
    elif switch_cost > budget:
        outcome = "over_budget"
    elif step["source_relation"] == "duplicate":
        outcome = "duplicate_evidence"
    elif condition == SCHEDULED:
        outcome = "proposed"
    else:
        # Evaluate prior measurements at this delivery's clock. Same-tick readings
        # can supply a conservative reference signal but cannot establish persistence.
        history = [
            prior
            for prior in prefix[:-1]
            if prior.subject_id == current.subject_id
            and clock - MAX_AGE_TICKS <= prior.measured_tick < current.measured_tick
        ]
        if history:
            reference_tick = max(prior.measured_tick for prior in history)
            reference_signal = min(
                prior.signal for prior in history if prior.measured_tick == reference_tick
            )
            window = MAX_AGE_TICKS + 1
            # Score the canonical decimal inputs before converting the audit displays to floats.
            signal = Fraction(str(min(current.signal, reference_signal)))
            exact_benefit = signal * (window - age) / window
            exact_utility = exact_benefit - Fraction(str(switch_cost))
            outcome = "proposed" if exact_utility > 0 else "no_positive_gain"
            benefit = float(exact_benefit)
            utility = float(exact_utility)
            utility_exact = str(exact_utility)
        else:
            outcome = "insufficient_history"

    selected_profile = None
    if outcome != "outside_opportunity":
        selected_profile = "alternate" if outcome == "proposed" else "default"
    return outcome, {
        "selection_version": "sensing_selection_v1",
        "prefix_trace_sha256": trace["trace_sha256"],
        "age_ticks": age,
        "eligible_distinct_source_count": step["eligible_distinct_source_count"],
        "reference_measured_tick": reference_tick,
        "reference_signal": reference_signal,
        "benefit": benefit,
        "utility": utility,
        "utility_exact": utility_exact,
        "selected_profile": selected_profile,
        "selection_reason": outcome,
    }

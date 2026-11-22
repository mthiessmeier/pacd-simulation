"""Per-episode diagnostic measures derived from the verified raw-event counts."""

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import NotRequired, TypedDict, cast

from pacd_sim.metrics.summarize import EpisodeRecord


class Fraction(TypedDict):
    numerator: int
    denominator: int
    unit: str
    value: float | None


class EpisodeDispositions(TypedDict):
    format: str
    seed: int
    config_hash: str
    completion_status: str
    counts: dict[str, int]
    escalation_fraction: Fraction
    guarded_review: NotRequired[dict[str, object]]


def fraction(numerator: int, denominator: int, unit: str) -> Fraction:
    return Fraction(
        numerator=numerator,
        denominator=denominator,
        unit=unit,
        value=numerator / denominator if denominator else None,
    )


def guarded_review_metrics(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Account for adjudicated review events from a single fully verified episode."""
    counts: Counter[str] = Counter()
    open_requests: dict[str, int] = {}
    review_waits: list[int] = []
    horizon = 0
    mission_count: int | None = None
    initial_unavailable = unavailable = mission_ticks = previous_tick = 0
    for row in rows:
        event_type = row["event_type"]
        tick = int(cast(float, row["tick"]))
        if event_type == "manifest":
            horizon = tick
        if event_type == "run_started":
            initial = json.loads(str(row["payload_json"])).get("initial_availability")
            if initial is not None:
                mission_count = int(initial["mission_count"])
                initial_unavailable = unavailable = mission_count - int(
                    initial["operational_mission_count"]
                )
        if event_type != "guarded_review":
            continue
        outcome = str(row["outcome"])
        referral = str(row["action_id"])
        counts[outcome] += 1
        if outcome == "mission_effect" and mission_count is not None:
            after = json.loads(str(row["payload_json"]))["availability_after"]
            mission_ticks += unavailable * (tick - previous_tick)
            unavailable = mission_count - int(after["operational_mission_count"])
            previous_tick = tick
        if outcome == "pending":
            open_requests[referral] = tick
        elif outcome in {"approved", "denied", "expired"}:
            review_waits.append(tick - open_requests.pop(referral))

    mission: dict[str, object] | None = None
    if mission_count is not None:
        mission_ticks += unavailable * (horizon - previous_tick)
        possible = mission_count * horizon
        mission = {
            "initial_tick": 0,
            "horizon_tick": horizon,
            "mission_count": mission_count,
            "initially_unavailable_count": initial_unavailable,
            "unavailable_mission_ticks": mission_ticks,
            "possible_mission_ticks": possible,
            "unavailable_fraction": fraction(mission_ticks, possible, "fraction_of_mission_ticks"),
            "unit": "mission_ticks",
        }
    return {
        "clock_unit": "simulation_ticks",
        "horizon_tick": horizon,
        "outcome_event_counts": dict(sorted(counts.items())),
        "pending_at_horizon_count": len(open_requests),
        "mission_availability": mission,
        "resolved_wait_denominator": len(review_waits),
        "resolved_wait_sum_ticks": sum(review_waits),
        "mean_resolved_wait_ticks": sum(review_waits) / len(review_waits) if review_waits else None,
        "verified_execution_fraction": fraction(
            counts["verified"], counts["executed"], "fraction_of_executed_reviewed_actions"
        ),
        "rollback_success_fraction": fraction(
            counts["rolled_back"],
            counts["rolled_back"] + counts["rollback_failed"],
            "fraction_of_attempted_rollbacks",
        ),
    }


def episode_dispositions(
    episode: EpisodeRecord, guarded_review: dict[str, object] | None = None
) -> EpisodeDispositions:
    """Summarize one complete episode with one governor disposition per candidate."""
    if episode.completion_status != "EVENT_CHAIN_COMPLETED":
        raise ValueError("Disposition metrics require a completed episode")
    candidates = episode.candidate_action_count
    escalations = episode.escalated_action_count
    if episode.approved_action_count + escalations + episode.prohibited_action_count != candidates:
        raise ValueError("Governor disposition counts do not account for every candidate action")

    result: EpisodeDispositions = {
        "format": "pacd-episode-dispositions-v1",
        "seed": episode.seed,
        "config_hash": episode.config_hash,
        "completion_status": episode.completion_status,
        "counts": {
            "candidate_action_count": candidates,
            "approved_action_count": episode.approved_action_count,
            "escalated_action_count": escalations,
            "prohibited_action_count": episode.prohibited_action_count,
            "simulated_execution_count": episode.simulated_execution_count,
            "verified_execution_count": episode.verified_execution_count,
            "prohibited_execution_count": episode.prohibited_execution_count,
        },
        "escalation_fraction": fraction(escalations, candidates, "fraction_of_candidate_actions"),
    }
    if guarded_review is not None:
        result["format"] = "pacd-episode-dispositions-guarded-review-v1"
        result["guarded_review"] = guarded_review
    return result

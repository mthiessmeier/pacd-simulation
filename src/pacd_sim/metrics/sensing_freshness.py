"""Candidate and execution evidence ages for fully verified WP08 sensing episodes."""

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from pacd_sim.evidence.context import MAX_AGE_TICKS
from pacd_sim.metrics.dispositions import fraction
from pacd_sim.polymorphism.selection import CONTEXTUAL, SCHEDULED


@dataclass(frozen=True)
class _Support:
    decision_tick: int
    current: int | None
    reference: int | None
    prefix_digest: str | None


def _ages(support: _Support | None, stage_tick: int, contextual: bool) -> dict[str, object]:
    current = None if support is None else support.current
    reference = None if support is None else support.reference
    current_age = None if current is None else stage_tick - current
    reference_age = None if reference is None else stage_tick - reference
    if (
        support is None
        or support.prefix_digest is None
        or stage_tick < support.decision_tick
        or current_age is None
        or (contextual and reference_age is None)
    ):
        classification = "unknown"
    elif current_age > MAX_AGE_TICKS or (
        reference_age is not None and reference_age > MAX_AGE_TICKS
    ):
        classification = "stale"
    else:
        classification = "fresh"
    return {
        "stage_tick": stage_tick,
        "decision_tick": None if support is None else support.decision_tick,
        "prefix_trace_sha256": None if support is None else support.prefix_digest,
        "current_measured_tick": current,
        "current_age_ticks": current_age,
        "reference_measured_tick": reference,
        "reference_age_ticks": reference_age,
        "classification": classification,
    }


def _stage(actions: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(row["classification"] for row in actions)
    known = counts["fresh"] + counts["stale"]
    return {
        "total_count": len(actions),
        "fresh_count": counts["fresh"],
        "stale_count": counts["stale"],
        "unknown_count": counts["unknown"],
        "stale_fraction": fraction(counts["stale"], known, "fraction_of_known_stage_actions"),
        "actions": actions,
    }


def sensing_freshness_metrics(
    rows: Iterable[Mapping[str, object]], condition: str
) -> dict[str, object]:
    """Project replay-checked decision support onto actual referral and dispatch clocks."""
    if condition not in (CONTEXTUAL, SCHEDULED):
        raise ValueError("freshness attribution requires a WP08 sensing selection condition")
    contextual = condition == CONTEXTUAL
    decisions: dict[str, _Support] = {}
    candidates: dict[str, _Support | None] = {}
    request_support: dict[tuple[str, str, str], _Support | None] = {}
    candidate_actions: list[dict[str, object]] = []
    executions: list[dict[str, object]] = []
    for row in rows:
        kind = row["event_type"]
        tick = int(cast(float, row["tick"]))
        if kind == "baseline_decision" and row["outcome"] == "proposed":
            decision = json.loads(cast(str, row["payload_json"]))
            if decision["policy"] == condition and decision["candidate_action_id"] is not None:
                selection = decision["selection"]
                age = selection.get("age_ticks")
                reference = selection.get("reference_measured_tick")
                decisions[decision["candidate_action_id"]] = _Support(
                    decision_tick=tick,
                    current=tick - age if type(age) is int and 0 <= age <= tick else None,
                    reference=reference
                    if contextual and type(reference) is int and 0 <= reference <= tick
                    else None,
                    prefix_digest=selection.get("prefix_trace_sha256"),
                )
        elif kind == "candidate_action":
            referral = cast(str, row["action_id"])
            candidates[referral] = decisions.get(referral)
            candidate_actions.append(
                {
                    "referral_id": referral,
                    "action_id": referral,
                    **_ages(candidates[referral], tick, contextual),
                }
            )
        elif kind == "guarded_review" and row["outcome"] in ("pending", "executed"):
            referral = cast(str, row["action_id"])
            record = json.loads(cast(str, row["payload_json"]))
            digest = record["request_digest"]
            if row["outcome"] == "pending":
                action = record["binding"]["action"]["id"]
                request_support[referral, digest, action] = candidates.get(referral)
            else:
                action = record["policy_decision"]["action_id"]
                support = request_support.get((referral, digest, action))
                executions.append(
                    {
                        "referral_id": referral,
                        "action_id": action,
                        "request_digest": digest,
                        "execution_id": record["execution_id"],
                        **_ages(support, tick, contextual),
                    }
                )

    return {
        "format": "pacd-sensing-freshness-v1",
        "metric_id": "CAL-006",
        "condition": condition,
        "freshness_policy": "evidence_context_v1",
        "max_age_ticks": MAX_AGE_TICKS,
        "candidate": _stage(candidate_actions),
        "execution": _stage(executions),
    }

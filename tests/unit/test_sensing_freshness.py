"""Stage populations, causal bindings and inclusive freshness in the CAL-006 projection."""

import json
from typing import Any

import pytest

from pacd_sim.metrics.sensing_freshness import sensing_freshness_metrics
from pacd_sim.polymorphism.selection import CONTEXTUAL, SCHEDULED


def _row(kind: str, tick: int, referral: str, outcome: str, **payload: object) -> dict[str, object]:
    return {
        "event_type": kind,
        "tick": float(tick),
        "action_id": referral,
        "outcome": outcome,
        "payload_json": json.dumps(payload),
    }


def _decision(
    policy: str, referral: str, *, tick: int = 3, age: int | None = 1, reference: int | None = 1
) -> dict[str, object]:
    return _row(
        "baseline_decision",
        tick,
        "",
        "proposed",
        policy=policy,
        candidate_action_id=referral,
        selection={
            "age_ticks": age,
            "reference_measured_tick": reference,
            "prefix_trace_sha256": "a" * 64,
        },
    )


def _executed(
    tick: int, referral: str = "r", digest: str = "request", action: str = "switch"
) -> dict[str, object]:
    return _row(
        "guarded_review",
        tick,
        referral,
        "executed",
        request_digest=digest,
        policy_decision={"action_id": action},
        execution_id="execution-" + action,
    )


@pytest.mark.parametrize(("condition", "stale"), [(CONTEXTUAL, 1), (SCHEDULED, 0)])
def test_execution_ages_only_the_selected_support_at_its_own_tick(
    condition: str, stale: int
) -> None:
    candidate = _row("candidate_action", 3, "r", "candidate_only")
    pending = _row(
        "guarded_review",
        3,
        "r",
        "pending",
        request_digest="request",
        binding={"action": {"id": "switch"}},
    )
    rows = [_decision(condition, "r"), candidate, pending, _executed(5)]
    report: dict[str, Any] = sensing_freshness_metrics(rows, condition)
    before = report["candidate"]
    after = report["execution"]
    assert before["total_count"] == before["fresh_count"] == 1
    assert before["stale_fraction"]["value"] == 0
    assert after["total_count"] == 1 and after["stale_count"] == stale
    assert after["stale_fraction"]["value"] == stale
    assert [stage["actions"][0]["current_age_ticks"] for stage in (before, after)] == [1, 3]
    assert [stage["actions"][0]["reference_age_ticks"] for stage in (before, after)] == (
        [2, 4] if condition == CONTEXTUAL else [None, None]
    )
    assert after["actions"][0]["action_id"] == "switch"
    assert after["actions"][0]["referral_id"] == "r"
    assert after["actions"][0]["execution_id"] == "execution-switch"


@pytest.mark.parametrize(
    ("referral", "digest", "action"),
    [("other", "request", "switch"), ("r", "other", "switch"), ("r", "request", "other")],
)
def test_unbound_executions_stay_in_the_unknown_population(
    referral: str, digest: str, action: str
) -> None:
    pending = _row(
        "guarded_review",
        3,
        "r",
        "pending",
        request_digest="request",
        binding={"action": {"id": "switch"}},
    )
    rows = [
        _decision(CONTEXTUAL, "r"),
        _row("candidate_action", 3, "r", "candidate_only"),
        pending,
        _executed(5, referral, digest, action),
    ]
    report: dict[str, Any] = sensing_freshness_metrics(rows, CONTEXTUAL)
    after = report["execution"]
    assert after["total_count"] == after["unknown_count"] == 1
    assert after["stale_count"] == after["fresh_count"] == 0
    assert after["stale_fraction"]["denominator"] == 0 and after["stale_fraction"]["value"] is None
    assert after["actions"][0]["current_age_ticks"] is None


def test_missing_support_and_later_decisions_cannot_supply_a_denominator() -> None:
    rows = [
        _decision(CONTEXTUAL, "fresh", tick=4, reference=2),
        _decision(CONTEXTUAL, "missing", reference=None),
        _decision(CONTEXTUAL, "future", reference=5),
        _decision(CONTEXTUAL, "stale", tick=5, reference=1),
        *[
            _row("candidate_action", 5, r, "candidate_only")
            for r in ("fresh", "missing", "future", "stale", "later")
        ],
        _decision(CONTEXTUAL, "later", tick=6),
    ]
    report: dict[str, Any] = sensing_freshness_metrics(rows, CONTEXTUAL)
    candidates = report["candidate"]
    assert [row["classification"] for row in candidates["actions"]] == [
        "fresh",
        "unknown",
        "unknown",
        "stale",
        "unknown",
    ]
    assert candidates["total_count"] == 5 and candidates["unknown_count"] == 3
    assert candidates["stale_fraction"]["numerator"] == 1
    assert candidates["stale_fraction"]["denominator"] == 2
    assert report["execution"]["stale_fraction"]["value"] is None


@pytest.mark.parametrize(
    "outcome",
    [
        "pending",
        "approved",
        "denied",
        "expired",
        "execution_failed",
        "verified",
        "rolled_back",
        "mission_effect",
    ],
)
def test_only_occurring_actions_enter_stage_populations(outcome: str) -> None:
    rows = [
        _decision(SCHEDULED, "unemitted"),
        _row(
            "guarded_review",
            5,
            "r",
            outcome,
            request_digest="request",
            binding={"action": {"id": "switch"}},
        ),
    ]
    output: dict[str, Any] = sensing_freshness_metrics(rows, SCHEDULED)
    for label in ("candidate", "execution"):
        stage = output[label]
        assert stage["actions"] == []
        assert stage["total_count"] == stage["unknown_count"] == 0
        assert stage["stale_fraction"]["value"] is None


def test_other_conditions_require_separate_attribution_rules() -> None:
    with pytest.raises(ValueError, match="WP08"):
        sensing_freshness_metrics([], "sensing_adaptive")

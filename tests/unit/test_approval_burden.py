"""OPS-003 waiting intervals and admissions reconciled against verified event shapes."""

from typing import Any

import pytest

from pacd_sim.metrics.review_routing import guarded_review_projections, review_routing_metrics
from pacd_sim.reproducibility.canonical import canonical_sha256

from .test_review_routing import _binding, _decision, _pending, _review, _row


def _admit(
    referral: str, tick: int, *, subject: str = "identity-1", contract: str = "isolation-v1"
) -> tuple[list[dict[str, object]], str]:
    binding = _binding(referral)
    binding.update(subject_id=subject, submitted_tick=tick, contract=f"guarded-review-{contract}")
    if contract.endswith("-v2"):
        binding["operator_brief"] = {"format": "operator-preview-v1"}
    events = [_decision(referral), _pending(referral, binding)]
    for event in events:
        event.update(tick=tick, entity_id=subject)
    return events, canonical_sha256(binding)


def _metrics(rows: list[dict[str, object]], horizon: int) -> dict[str, Any]:
    rows = [*rows, {"event_type": "manifest", "tick": horizon}]
    projections = guarded_review_projections(
        iter(rows), include_review_routing=True, include_approval_burden=True
    )
    assert projections["review_routing"] == review_routing_metrics(rows)
    return projections["approval_burden"]


def test_overlapping_requests_have_separate_waits_and_censored_intervals() -> None:
    first, first_digest = _admit("first", 0)
    later, later_digest = _admit("later", 1, subject="identity-2", contract="sensing-v2")
    instant, instant_digest = _admit("instant", 3, subject="identity-3")
    rows = [
        *first,
        *later,
        # Crossed subject and crossed digest cannot close the first or second request.
        _review("first", "expired", first_digest, "identity-2"),
        _review("later", "denied", first_digest, "identity-2"),
        *instant,
        dict(_review("instant", "denied", instant_digest, "identity-3"), tick=3),
        dict(_review("first", "approved", first_digest), tick=4),
        dict(_review("first", "unauthorized", first_digest), tick=4),
        dict(_review("first", "approved", first_digest), tick=5),
    ]
    burden = _metrics(rows, 5)
    assert burden["request_count"] == burden["escalation_count"] == 3
    assert burden["wait_by_outcome"] == {
        "approved": {"count": 1, "observed_wait_sum_ticks": 4},
        "denied": {"count": 1, "observed_wait_sum_ticks": 0},
        "expired": {"count": 0, "observed_wait_sum_ticks": 0},
        "pending_at_horizon": {"count": 1, "observed_wait_sum_ticks": 4},
    }
    assert burden["observed_request_ticks"] == 8
    assert burden["resolved_wait_denominator"] == 2
    assert burden["resolved_wait_sum_ticks"] == 4
    assert burden["mean_resolved_wait_ticks"] == 2
    assert [
        (
            r["referral_id"],
            r["subject_id"],
            r["request_digest"],
            r["submitted_tick"],
            r["terminal_tick"],
            r["outcome"],
            r["observed_wait_ticks"],
        )
        for r in burden["requests"]
    ] == [
        ("first", "identity-1", first_digest, 0, 4, "approved", 4),
        ("later", "identity-2", later_digest, 1, None, "pending_at_horizon", 4),
        ("instant", "identity-3", instant_digest, 3, 3, "denied", 0),
    ]
    assert burden["override_count"] is None and burden["override_status"] == "unsupported"


def test_refused_full_and_unrouted_escalations_do_not_enter_wait_denominator() -> None:
    rows: list[dict[str, object]] = []
    for reason in ("capacity", "refused"):
        rows.extend(
            (
                _decision(reason),
                _row(
                    "guarded_review", reason, reason, {"referral_digest": canonical_sha256(reason)}
                ),
            )
        )
    rows.extend((_decision("orphan"), _decision("blocked", "PROHIBIT")))
    burden = _metrics(rows, 5)
    assert burden["admission_outcomes"] == {"capacity": 1, "refused": 1, "unrouted": 1}
    assert burden["escalation_count"] == 3
    assert burden["request_count"] == burden["observed_request_ticks"] == 0
    assert burden["requests"] == []
    assert burden["resolved_wait_denominator"] == 0 and burden["mean_resolved_wait_ticks"] is None


@pytest.mark.parametrize(("outcome", "terminal"), [("expired", 5), ("pending_at_horizon", None)])
def test_request_open_or_expired_at_horizon(outcome: str, terminal: int | None) -> None:
    rows, digest = _admit("r", 1)
    if terminal is not None:
        rows.append(dict(_review("r", outcome, digest), tick=terminal))
    burden = _metrics(rows, 5)
    assert burden["wait_by_outcome"][outcome] == {"count": 1, "observed_wait_sum_ticks": 4}
    assert burden["observed_request_ticks"] == 4
    assert burden["mean_resolved_wait_ticks"] == (None if terminal is None else 4)
    assert burden["requests"][0]["terminal_tick"] == terminal


def test_zero_horizon_can_measure_zero_elapsed_time() -> None:
    rows, _ = _admit("r", 0)
    burden = _metrics(rows, 0)
    assert burden["horizon_tick"] == burden["observed_request_ticks"] == 0
    assert burden["requests"][0]["observed_wait_ticks"] == 0
    assert burden["mean_resolved_wait_ticks"] is None


def test_missing_horizon_cannot_be_treated_as_zero() -> None:
    with pytest.raises(ValueError, match="verified episode horizon"):
        guarded_review_projections([], include_review_routing=False, include_approval_burden=True)

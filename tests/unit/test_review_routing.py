"""Attribution and denominators for the guarded GOV-002 projection."""

import json
from typing import Any

import pytest

from pacd_sim.metrics.review_routing import review_routing_metrics
from pacd_sim.reproducibility.canonical import canonical_sha256


def _row(
    kind: str,
    referral: str,
    outcome: str,
    payload: dict[str, object],
    *,
    subject: str = "identity-1",
    disposition: str = "",
) -> dict[str, object]:
    return {
        "event_type": kind,
        "action_id": referral,
        "outcome": outcome,
        "tick": 2.0,
        "entity_id": subject,
        "disposition": disposition,
        "payload_json": json.dumps(payload),
    }


def _decision(referral: str, disposition: str = "ESCALATE") -> dict[str, object]:
    return _row(
        "safety_decision",
        referral,
        "decided",
        {
            "action_digest": canonical_sha256(referral),
            "policy_digest": "a" * 64,
            "state_digest": "b" * 64,
        },
        disposition=disposition,
    )


def _binding(referral: str) -> dict[str, object]:
    action = {"id": "reviewed-" + referral, "target_id": "session-1"}
    return {
        "contract": "guarded-review-isolation-v1",
        "subject_id": "identity-1",
        "referral_digest": canonical_sha256(referral),
        "referral_decision_digest": "c" * 64,
        "evidence_id": "evidence-1",
        "evidence_digest": "d" * 64,
        "policy_digest": "a" * 64,
        "state_digest": "b" * 64,
        "action": action,
        "action_digest": canonical_sha256(action),
        "submitted_tick": 2,
        "due_tick": 4,
        "expires_tick": 6,
    }


def _pending(referral: str, binding: dict[str, object]) -> dict[str, object]:
    return _row(
        "guarded_review",
        referral,
        "pending",
        {"request_digest": canonical_sha256(binding), "binding": binding},
    )


def _review(
    referral: str, outcome: str, digest: str, subject: str = "identity-1"
) -> dict[str, object]:
    return _row("guarded_review", referral, outcome, {"request_digest": digest}, subject=subject)


def test_all_escalations_partitioned_and_terminal_approval_counted_once() -> None:
    rows = []
    for outcome in ("approved", "denied", "expired", "pending_at_horizon"):
        binding = _binding(outcome)
        rows.extend([_decision(outcome), _pending(outcome, binding)])
        if outcome != "pending_at_horizon":
            rows.append(_review(outcome, outcome, canonical_sha256(binding)))
    digest = canonical_sha256(_binding("approved"))
    rows.extend(
        _review("approved", outcome, digest) for outcome in ("approved", "executed", "rolled_back")
    )
    for outcome in ("capacity", "refused"):
        rows.extend(
            [
                _decision(outcome),
                _row(
                    "guarded_review",
                    outcome,
                    outcome,
                    {"referral_digest": canonical_sha256(outcome)},
                ),
            ]
        )
    rows.extend([_decision("no-admission"), _decision("other", "PROHIBIT")])
    report: dict[str, Any] = review_routing_metrics(rows)
    assert report["outcome_counts"] == dict.fromkeys(
        ("approved", "denied", "expired", "pending_at_horizon", "capacity", "refused", "unrouted"),
        1,
    )
    assert report["package_count"] == 4
    assert report["routing_completeness"] == {
        "numerator": 3,
        "denominator": 7,
        "value": 3 / 7,
        "unit": "fraction_of_escalations",
    }


@pytest.mark.parametrize(
    "wrong_field",
    [
        "contract",
        "subject_id",
        "referral_digest",
        "policy_digest",
        "state_digest",
        "submitted_tick",
        "missing_evidence",
    ],
)
def test_even_a_redigested_unbound_package_cannot_complete_a_referral(wrong_field: str) -> None:
    binding = _binding("r")
    if wrong_field == "missing_evidence":
        del binding["evidence_id"]
    else:
        binding[wrong_field] = "other"
    rows = [
        _decision("r"),
        _pending("r", binding),
        _review("r", "approved", canonical_sha256(binding)),
    ]
    report: dict[str, Any] = review_routing_metrics(rows)
    assert report["routing_completeness"]["value"] == 0
    assert report["outcome_counts"]["unrouted"] == 1
    assert report["package_count"] == 0


def test_adjudication_cannot_cross_request_subject_or_referral() -> None:
    binding = _binding("r")
    digest = canonical_sha256(binding)
    rows = [
        _decision("r"),
        _pending("r", binding),
        _review("r", "denied", "c" * 64),
        _review("other", "expired", digest),
        _review("r", "approved", digest, "other"),
    ]
    report: dict[str, Any] = review_routing_metrics(rows)
    assert report["routing_completeness"]["numerator"] == 0
    assert report["outcome_counts"]["pending_at_horizon"] == report["package_count"] == 1


@pytest.mark.parametrize("action", ["isolation", "sensing"])
@pytest.mark.parametrize(
    ("version", "brief_present", "expected"),
    [("v1", False, 1), ("v1", True, 0), ("v2", False, 0), ("v2", True, 1), ("v3", True, 0)],
)
def test_routing_uses_the_fields_of_the_declared_contract(
    action: str, version: str, brief_present: bool, expected: int
) -> None:
    binding = _binding("r")
    binding["contract"] = f"guarded-review-{action}-{version}"
    if brief_present:
        # Full brief content is checked upstream, when the verifier replays the admission.
        binding["operator_brief"] = {"format": "operator-preview-v1"}
    rows = [
        _decision("r"),
        _pending("r", binding),
        _review("r", "denied", canonical_sha256(binding)),
    ]
    report: dict[str, Any] = review_routing_metrics(rows)
    assert report["routing_completeness"]["denominator"] == 1
    assert report["package_count"] == report["routing_completeness"]["numerator"] == expected


def test_no_escalation_has_no_measured_fraction() -> None:
    binding = _binding("r")
    rows = [
        _decision("r", "APPROVE"),
        _pending("r", binding),
        _review("r", "approved", canonical_sha256(binding)),
    ]
    report: dict[str, Any] = review_routing_metrics(rows)
    assert report["routing_completeness"]["denominator"] == report["package_count"] == 0
    assert report["routing_completeness"]["value"] is None
    assert sum(report["outcome_counts"].values()) == 0

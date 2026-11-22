"""Routing and approval burden for the guarded requests of a fully replayed episode."""

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from pacd_sim.metrics.dispositions import fraction
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import PolicyDisposition

_TERMINAL = ("approved", "denied", "expired")
_ADMISSION_FAILURE = ("capacity", "refused")
_OUTCOMES = (*_TERMINAL, *_ADMISSION_FAILURE, "pending_at_horizon", "unrouted")
_PACKAGE_FIELDS = {
    "contract",
    "referral_digest",
    "referral_decision_digest",
    "subject_id",
    "evidence_id",
    "evidence_digest",
    "policy_digest",
    "state_digest",
    "action",
    "action_digest",
    "submitted_tick",
    "due_tick",
    "expires_tick",
}
_BRIEF_PACKAGE_FIELDS = _PACKAGE_FIELDS | {"operator_brief"}
_CONTRACT_FIELDS = {
    "guarded-review-isolation-v1": _PACKAGE_FIELDS,
    "guarded-review-sensing-v1": _PACKAGE_FIELDS,
    "guarded-review-isolation-v2": _BRIEF_PACKAGE_FIELDS,
    "guarded-review-sensing-v2": _BRIEF_PACKAGE_FIELDS,
}


@dataclass
class _Escalation:
    referral_id: str
    subject_id: str
    referral_digest: str
    policy_digest: str
    state_digest: str
    tick: int
    outcome: str = "unrouted"
    request_digest: str | None = None
    terminal_tick: int | None = None


def _bound_package(binding: object, digest: object, subject: str, escalation: _Escalation) -> bool:
    # Independent replay already verified each field against the scenario, evidence,
    # governor and concrete action. Link that package to this particular escalation.
    if not isinstance(binding, dict):
        return False
    contract = binding.get("contract")
    return (
        isinstance(contract, str)
        and binding.keys() == _CONTRACT_FIELDS.get(contract)
        and binding["subject_id"] == subject
        and binding["referral_digest"] == escalation.referral_digest
        and binding["policy_digest"] == escalation.policy_digest
        and binding["state_digest"] == escalation.state_digest
        and binding["submitted_tick"] == escalation.tick
        and canonical_sha256(binding) == digest
    )


def _match_reviews(
    raw_rows: Iterable[Mapping[str, object]],
) -> tuple[list[_Escalation], list[_Escalation], int | None]:
    """Match admissions and their first terminal outcome in retained event order."""
    escalations: list[_Escalation] = []
    admissions: list[_Escalation] = []
    horizon: int | None = None
    awaiting: dict[tuple[str, str], _Escalation] = {}
    pending: dict[tuple[str, str, str], _Escalation] = {}
    for row in raw_rows:
        kind = row["event_type"]
        if kind == "manifest":
            horizon = int(cast(float, row["tick"]))
        if kind not in ("safety_decision", "guarded_review"):
            continue
        referral, subject = cast(str, row["action_id"]), cast(str, row["entity_id"])
        key = (referral, subject)
        if kind == "safety_decision":
            awaiting.pop(key, None)
            if row["disposition"] == PolicyDisposition.ESCALATE:
                decision = json.loads(cast(str, row["payload_json"]))
                escalation = _Escalation(
                    referral,
                    subject,
                    decision["action_digest"],
                    decision["policy_digest"],
                    decision["state_digest"],
                    int(cast(float, row["tick"])),
                )
                escalations.append(escalation)
                awaiting[key] = escalation
            continue

        outcome = cast(str, row["outcome"])
        if outcome not in ("pending", *_TERMINAL, *_ADMISSION_FAILURE):
            continue
        payload = json.loads(cast(str, row["payload_json"]))
        if outcome in _TERMINAL:
            entry = pending.pop((referral, subject, payload["request_digest"]), None)
            if entry is not None:
                entry.outcome = outcome
                entry.terminal_tick = int(cast(float, row["tick"]))
        elif (entry := awaiting.get(key)) is not None:
            if (
                outcome in _ADMISSION_FAILURE
                and payload["referral_digest"] == entry.referral_digest
            ):
                entry.outcome = outcome
                del awaiting[key]
            elif outcome == "pending" and _bound_package(
                payload.get("binding"), payload.get("request_digest"), subject, entry
            ):
                entry.outcome = "pending_at_horizon"
                entry.request_digest = payload["request_digest"]
                admissions.append(entry)
                pending[referral, subject, payload["request_digest"]] = entry
                del awaiting[key]

    return escalations, admissions, horizon


def _routing(counts: Counter[str]) -> dict[str, object]:
    resolved = sum(counts[outcome] for outcome in _TERMINAL)
    return {
        "format": "pacd-review-routing-v1",
        "metric_id": "GOV-002",
        "routing_completeness": fraction(resolved, counts.total(), "fraction_of_escalations"),
        "package_count": resolved + counts["pending_at_horizon"],
        "outcome_counts": {outcome: counts[outcome] for outcome in _OUTCOMES},
    }


def _approval_burden(
    counts: Counter[str], admissions: list[_Escalation], horizon: int | None
) -> dict[str, object]:
    if horizon is None:
        raise ValueError("approval burden requires the verified episode horizon")
    waits: Counter[str] = Counter()
    requests: list[dict[str, object]] = []
    for request in admissions:
        stop = horizon if request.terminal_tick is None else request.terminal_tick
        if not request.tick <= stop <= horizon:
            raise ValueError("review wait falls outside the verified episode interval")
        wait = stop - request.tick
        waits[request.outcome] += wait
        requests.append(
            {
                "referral_id": request.referral_id,
                "subject_id": request.subject_id,
                "request_digest": request.request_digest,
                "submitted_tick": request.tick,
                "terminal_tick": request.terminal_tick,
                "outcome": request.outcome,
                "observed_wait_ticks": wait,
            }
        )

    resolved = sum(counts[outcome] for outcome in _TERMINAL)
    resolved_wait = sum(waits[outcome] for outcome in _TERMINAL)
    return {
        "format": "pacd-approval-burden-v1",
        "metric_id": "OPS-003",
        "clock_unit": "simulation_ticks",
        "horizon_tick": horizon,
        "escalation_count": counts.total(),
        "admission_outcomes": {
            outcome: counts[outcome] for outcome in (*_ADMISSION_FAILURE, "unrouted")
        },
        "request_count": len(requests),
        "wait_by_outcome": {
            outcome: {"count": counts[outcome], "observed_wait_sum_ticks": waits[outcome]}
            for outcome in (*_TERMINAL, "pending_at_horizon")
        },
        "resolved_wait_denominator": resolved,
        "resolved_wait_sum_ticks": resolved_wait,
        "mean_resolved_wait_ticks": resolved_wait / resolved if resolved else None,
        "observed_request_ticks": waits.total(),
        "override_count": None,
        "override_status": "unsupported",
        "requests": requests,
    }


def guarded_review_projections(
    raw_rows: Iterable[Mapping[str, object]],
    *,
    include_review_routing: bool,
    include_approval_burden: bool,
) -> dict[str, dict[str, object]]:
    """Compute the requested projections using the same matched review lifecycles."""
    escalations, admissions, horizon = _match_reviews(raw_rows)
    counts = Counter(entry.outcome for entry in escalations)
    projections = {}
    if include_review_routing:
        projections["review_routing"] = _routing(counts)
    if include_approval_burden:
        projections["approval_burden"] = _approval_burden(counts, admissions, horizon)
    return projections


def review_routing_metrics(raw_rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Reconcile every actual escalation to its own package and review resolution."""
    return guarded_review_projections(
        raw_rows, include_review_routing=True, include_approval_burden=False
    )["review_routing"]

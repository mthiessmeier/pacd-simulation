"""GOV-002 for the versioned guarded-review contracts in a fully replayed episode."""

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
    referral_digest: str
    policy_digest: str
    state_digest: str
    tick: int
    outcome: str = "unrouted"


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


def review_routing_metrics(raw_rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Reconcile every actual escalation to its own package and review resolution."""
    escalations: list[_Escalation] = []
    awaiting: dict[tuple[str, str], _Escalation] = {}
    pending: dict[tuple[str, str, str], _Escalation] = {}
    for row in raw_rows:
        kind = row["event_type"]
        if kind not in ("safety_decision", "guarded_review"):
            continue
        referral, subject = cast(str, row["action_id"]), cast(str, row["entity_id"])
        key = (referral, subject)
        if kind == "safety_decision":
            awaiting.pop(key, None)
            if row["disposition"] == PolicyDisposition.ESCALATE:
                decision = json.loads(cast(str, row["payload_json"]))
                escalation = _Escalation(
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
                pending[referral, subject, payload["request_digest"]] = entry
                del awaiting[key]

    counts = Counter(entry.outcome for entry in escalations)
    resolved = sum(counts[outcome] for outcome in _TERMINAL)
    return {
        "format": "pacd-review-routing-v1",
        "metric_id": "GOV-002",
        "routing_completeness": fraction(resolved, len(escalations), "fraction_of_escalations"),
        "package_count": resolved + counts["pending_at_horizon"],
        "outcome_counts": {outcome: counts[outcome] for outcome in _OUTCOMES},
    }

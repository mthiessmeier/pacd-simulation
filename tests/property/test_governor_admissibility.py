"""Bounded properties for independent action admissibility decisions."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.governance.governor import SafetyGovernor, SafetyPolicy
from pacd_sim.schema import PolicyDisposition

_ACTION_TYPES = st.sampled_from(
    ("isolate_session", "require_human_review", "external_network_scan", "unknown_action")
)
_AUTHORITIES = st.sampled_from(("automatic", "human", "prohibited"))


def _expected_disposition(
    action_type: str,
    authority: str,
    reversible: bool,
) -> PolicyDisposition:
    if authority == "prohibited" or action_type == "external_network_scan":
        return PolicyDisposition.PROHIBIT
    if action_type == "require_human_review":
        return PolicyDisposition.ESCALATE
    if action_type != "isolate_session":
        return PolicyDisposition.PROHIBIT
    if authority == "human":
        return PolicyDisposition.ESCALATE
    if not reversible:
        return PolicyDisposition.PROHIBIT
    return PolicyDisposition.APPROVE


@pytest.mark.property
@given(_ACTION_TYPES, _AUTHORITIES, st.booleans())
@settings(max_examples=60, deadline=None)
def test_governor_admissibility_matches_fail_closed_reference(
    action_type: str,
    authority: str,
    reversible: bool,
) -> None:
    governor = SafetyGovernor(
        SafetyPolicy(
            allowed_action_types=("isolate_session",),
            escalated_action_types=("require_human_review",),
            prohibited_action_types=("external_network_scan",),
        )
    )
    action = DefensiveAction.model_validate(
        {
            "id": f"property-{action_type}-{authority}-{int(reversible)}",
            "action_type": action_type,
            "target_id": "synthetic-target",
            "reversible": reversible,
            "requested_authority": authority,
        }
    )

    decision = governor.evaluate(action)
    expected = _expected_disposition(action_type, authority, reversible)

    assert decision.disposition is expected
    assert decision.permits_execution is (expected is PolicyDisposition.APPROVE)

"""Independent safety-governor disposition checks."""

from __future__ import annotations

import pytest

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.governance.governor import SafetyGovernor, SafetyPolicy
from pacd_sim.schema import PolicyDisposition


@pytest.fixture
def governor() -> SafetyGovernor:
    policy = SafetyPolicy(
        allowed_action_types=("isolate_session",),
        escalated_action_types=("require_human_review",),
        prohibited_action_types=("external_network_scan",),
    )
    return SafetyGovernor(policy)


def _action(
    action_type: str,
    *,
    authority: str,
    reversible: bool = True,
) -> DefensiveAction:
    return DefensiveAction.model_validate(
        {
            "id": f"candidate-{action_type}",
            "action_type": action_type,
            "target_id": "synthetic-target",
            "reversible": reversible,
            "requested_authority": authority,
        }
    )


@pytest.mark.parametrize(
    ("action_type", "authority", "expected"),
    [
        ("isolate_session", "automatic", PolicyDisposition.APPROVE),
        ("require_human_review", "human", PolicyDisposition.ESCALATE),
        ("external_network_scan", "prohibited", PolicyDisposition.PROHIBIT),
        ("unknown_action", "automatic", PolicyDisposition.PROHIBIT),
    ],
)
def test_governor_classifies_allowed_escalated_and_prohibited_actions(
    governor: SafetyGovernor,
    action_type: str,
    authority: str,
    expected: PolicyDisposition,
) -> None:
    decision = governor.evaluate(_action(action_type, authority=authority))

    assert decision.disposition is expected
    assert decision.permits_execution is (expected is PolicyDisposition.APPROVE)


def test_non_reversible_automatic_action_fails_closed(governor: SafetyGovernor) -> None:
    decision = governor.evaluate(
        _action("isolate_session", authority="automatic", reversible=False)
    )

    assert decision.disposition is PolicyDisposition.PROHIBIT
    assert not decision.permits_execution


def test_policy_requires_disjoint_action_classifications() -> None:
    with pytest.raises(ValueError, match="disjoint"):
        SafetyPolicy(
            allowed_action_types=("duplicate",),
            escalated_action_types=("duplicate",),
            prohibited_action_types=(),
        )

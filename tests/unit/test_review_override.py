"""Check evaluator-owned vetoes at the single-use simulated review boundary."""

from unittest.mock import patch

import pytest
from conftest import CONFIG_ROOT
from pydantic import ValidationError

from pacd_sim.configuration import GuardedReviewConfig, ScenarioConfig
from pacd_sim.constants import REVIEW_BRIEF_ISOLATION_FILE, REVIEW_OVERRIDE_FILES
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.normalize import normalize_observation
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.governance.governor import SafetyGovernor
from pacd_sim.harness.run import _build_environment, _build_policy, load_yaml_config
from pacd_sim.harness.static_review import review_queue, static_review_candidate
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewEvent
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.state.snapshot import create_snapshot
from pacd_sim.telemetry.generator import Observation


def _scenario(filename: str) -> ScenarioConfig:
    return ScenarioConfig.model_validate(load_yaml_config(CONFIG_ROOT / "scenarios" / filename))


def _admit(
    filename: str, **review_changes: object
) -> tuple[GuardedReviewQueue, SimulatedExecutionBroker, EnvironmentState, ReviewEvent]:
    scenario = _scenario(filename)
    assert scenario.guarded_review is not None
    config = GuardedReviewConfig.model_validate(
        {**scenario.guarded_review.model_dump(), **review_changes}
    )
    queue = review_queue(config, lambda _: None)
    broker = SimulatedExecutionBroker(
        SafetyGovernor(
            _build_policy(load_yaml_config(CONFIG_ROOT / "policies/diagnostic_safety.yaml"))
        )
    )
    state = _build_environment(scenario, scenario.protocol_version).at_tick(2)
    observation = Observation(
        id="observation-1",
        event_id=scenario.events[0].id,
        event_kind="benign_administrative",
        sensor_id="synthetic",
        identity_id=state.identities[0].id,
        event_tick=1,
        tick=state.tick,
        signal=0.9,
    )
    _, referral = static_review_candidate(observation, 1, scenario.protocol_version)
    assert referral is not None
    (admission,) = queue.submit(
        referral,
        broker.governor.evaluate(referral, mission_state=create_snapshot(state)),
        normalize_observation(observation, delivery_ordinal=1),
        state,
        broker,
        delivery=(1, observation),
    ).events
    return queue, broker, state, admission


def test_matched_policies_bind_the_same_request_before_resolution() -> None:
    retain, veto = REVIEW_OVERRIDE_FILES
    retained, exercised = _scenario(retain).model_dump(), _scenario(veto).model_dump()
    retained.pop("name")
    exercised.pop("name")
    assert retained["guarded_review"].pop("override_policy") == "retain_approval"
    assert exercised["guarded_review"].pop("override_policy") == "veto_approval"
    assert retained == exercised
    control, control_broker, state, planned = _admit(retain)
    treatment, treatment_broker, other_state, subject = _admit(veto)
    assert planned == subject and planned.outcome == "pending"
    assert planned.payload["request_digest"] == canonical_sha256(planned.payload["binding"])
    assert b"override_policy" not in canonical_json_bytes(planned.payload)

    # Any resolution-time governor or broker call on the veto would be a dispatch-path error.
    with (
        patch.object(treatment_broker.governor, "evaluate") as evaluate,
        patch.object(treatment_broker, "execute") as execute,
    ):
        vetoed = treatment.advance(6, other_state, treatment_broker)
        evaluate.assert_not_called()
        execute.assert_not_called()
        assert not treatment.advance(7, vetoed.state, treatment_broker).events
    assessment, denied = vetoed.events
    assert assessment.tick == denied.tick == 6
    assert assessment.action_id == denied.action_id == planned.action_id
    assert assessment.entity_id == denied.entity_id == planned.entity_id
    assert assessment.outcome == "override_assessment" and denied.outcome == "denied"
    assert denied.payload == {"request_digest": planned.payload["request_digest"]}
    assert assessment.payload == {
        **denied.payload,
        "original_response": "approve",
        "final_response": "deny",
        "override_policy": "veto_approval",
        "direction": "approve_to_deny",
        "rationale": "preserve_mission_continuity",
    }
    assert vetoed.state == state.at_tick(6)
    result = control.advance(6, state, control_broker)
    assert [e.outcome for e in result.events] == [
        "override_assessment",
        "approved",
        "executed",
        "verified",
        "mission_effect",
    ]
    assert result.events[0].payload == {
        **denied.payload,
        "original_response": "approve",
        "final_response": "approve",
        "override_policy": "retain_approval",
        "direction": "none",
        "rationale": "retain_planned_response",
    }
    assert result.state.sessions[0].isolated


@pytest.mark.parametrize(
    ("changes", "horizon", "expected"),
    [
        ({"response": "deny"}, 6, ["denied"]),
        ({"response": "no_response"}, 7, ["expired"]),
        ({"validity_ticks": 1}, 4, ["expired"]),
        ({}, 3, []),
        ({"capacity": 0}, 4, []),
    ],
)
def test_only_timely_planned_approvals_have_an_opportunity(
    changes: dict[str, object], horizon: int, expected: list[str]
) -> None:
    queue, broker, state, admission = _admit(REVIEW_OVERRIDE_FILES[1], **changes)
    assert admission.outcome == ("capacity" if changes.get("capacity") == 0 else "pending")
    result = queue.advance(horizon, state, broker)
    assert [event.outcome for event in result.events] == expected
    assert result.state == state.at_tick(horizon)


def test_retained_approval_still_requires_fresh_authority() -> None:
    queue, broker, state, _ = _admit(REVIEW_OVERRIDE_FILES[0])
    with (
        patch.object(broker.governor, "evaluate", side_effect=RuntimeError) as evaluate,
        patch.object(broker, "execute") as execute,
    ):
        result = queue.advance(6, state, broker)
        evaluate.assert_called_once()
        execute.assert_not_called()
    assert [e.outcome for e in result.events] == [
        "override_assessment",
        "approved",
        "authorization_failed",
    ]
    assert result.state == state.at_tick(6)


@pytest.mark.parametrize("invalid", [None, False, "approve_to_execute"])
def test_historical_omission_and_invalid_explicit_policy(invalid: object) -> None:
    wire = load_yaml_config(CONFIG_ROOT / "scenarios" / REVIEW_BRIEF_ISOLATION_FILE)
    legacy = ScenarioConfig.model_validate(wire)
    assert canonical_sha256(legacy) == canonical_sha256(wire)
    assert legacy.guarded_review is not None
    with pytest.raises(ValidationError, match="override_policy"):
        GuardedReviewConfig.model_validate(
            {**legacy.guarded_review.model_dump(), "override_policy": invalid}
        )

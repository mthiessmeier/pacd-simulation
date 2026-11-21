"""Guarded-review boundaries on synthetic immutable state, including failed recovery."""

import pytest

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.model import (
    Dependency,
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.execution.broker import ExecutionResult, SimulatedExecutionBroker
from pacd_sim.execution.verification import RollbackResult, rollback_execution
from pacd_sim.governance.governor import PolicyDecision, SafetyGovernor, SafetyPolicy
from pacd_sim.oversight import guarded
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewStep
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import ExecutionDisposition
from pacd_sim.state.snapshot import create_snapshot


@pytest.fixture
def state() -> EnvironmentState:
    return EnvironmentState(
        tick=1,
        identities=(Identity(id="user", role="synthetic_user"),),
        sessions=(Session(id="session", identity_id="user", service_id="service"),),
        mission_functions=(MissionFunction(id="mission", criticality=0.9),),
        services=(Service(id="service", mission_id="mission"),),
        dependencies=(Dependency(id="dependency", upstream_id="session", downstream_id="service"),),
    )


@pytest.fixture
def broker() -> SimulatedExecutionBroker:
    policy = SafetyPolicy(
        allowed_action_types=("isolate_session",),
        escalated_action_types=("require_human_review",),
        prohibited_action_types=(),
    )
    return SimulatedExecutionBroker(SafetyGovernor(policy))


def queue(
    *,
    delay: int = 1,
    ttl: int = 2,
    approve: bool | None = True,
    rollback: bool = False,
    capacity: int = 1,
) -> GuardedReviewQueue:
    return GuardedReviewQueue(
        capacity=capacity, delay_ticks=delay, ttl_ticks=ttl, approve=approve, rollback=rollback
    )


def inputs(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    suffix: str = "a",
) -> tuple[DefensiveAction, PolicyDecision, EvidenceItem]:
    referral = DefensiveAction(
        id=f"review-{suffix}",
        tick=state.tick,
        action_type="require_human_review",
        target_id="user",
        reversible=True,
        requested_authority="human",
    )
    evidence = EvidenceItem(
        id=f"evidence-{suffix}",
        tick=state.tick,
        category="unknown_signal",
        subject_id="user",
        confidence=0.65,
        integrity=1.0,
        observation_ids=(f"observation-{suffix}",),
        provenance=("sensor",),
    )
    return (
        referral,
        broker.governor.evaluate(referral, mission_state=create_snapshot(state)),
        evidence,
    )


def outcomes(step: ReviewStep) -> list[str]:
    return [event.outcome for event in step.events]


def test_action_policy_evidence_clock_and_exact_recovery(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
) -> None:
    review = queue(delay=2, ttl=2, rollback=True)
    referral, decision, evidence = inputs(state, broker)
    result = review.submit(referral, decision, evidence, state, broker)
    assert outcomes(result) == ["pending"]
    pending = result.events[0]
    binding = pending.payload["binding"]
    assert isinstance(binding, dict)
    assert binding["action"]["target_id"] == "session"
    assert binding["action_digest"] == canonical_sha256(binding["action"])
    assert binding["referral_decision_digest"] == canonical_sha256(decision)
    assert binding["evidence_digest"] == canonical_sha256(evidence)
    assert binding["policy_digest"] == canonical_sha256(broker.governor.policy)
    assert binding["state_digest"] == canonical_sha256(state)
    assert pending.payload["request_digest"] == canonical_sha256(binding)
    assert (binding["submitted_tick"], binding["due_tick"], binding["expires_tick"]) == (1, 3, 3)

    early = review.advance(2, state, broker)
    assert early.events == () and early.state == state.at_tick(2)
    resolved = review.advance(8, early.state, broker)
    assert outcomes(resolved) == [
        "approved",
        "executed",
        "verified",
        "mission_effect",
        "rolled_back",
        "mission_effect",
    ]
    assert all(event.tick == 3 for event in resolved.events)
    assert all(
        event.payload["request_digest"] == canonical_sha256(binding) for event in resolved.events
    )
    dispatch = resolved.events[1].payload
    assert dispatch["adapter"] == "simulated_only" and dispatch["network_enabled"] is False
    execution_decision = dispatch["policy_decision"]
    assert isinstance(execution_decision, dict)
    assert execution_decision["disposition"] == "APPROVE"
    assert execution_decision["state_digest"] == canonical_sha256(state.at_tick(3))
    assert execution_decision["action_digest"] == binding["action_digest"]
    start_effect = resolved.events[3].payload["mission_continuity"]
    recovery_effect = resolved.events[5].payload["mission_continuity"]
    assert isinstance(start_effect, dict) and start_effect["interrupted_mission_count"] == 1
    assert isinstance(recovery_effect, dict) and recovery_effect["restored_mission_count"] == 1
    assert resolved.state == state.at_tick(8)
    assert review.advance(8, resolved.state, broker).events == ()


@pytest.mark.parametrize(
    ("approve", "delay", "horizon", "expected"),
    [
        (False, 1, 3, ["denied"]),
        (True, 3, 9, ["expired"]),
        (None, 0, 9, ["expired"]),
        (None, 0, 3, []),
        (True, 2, 2, []),
    ],
)
def test_missing_denied_and_expired_have_no_transition(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    approve: bool | None,
    delay: int,
    horizon: int,
    expected: list[str],
) -> None:
    review = queue(approve=approve, delay=delay)
    assert outcomes(review.submit(*inputs(state, broker), state, broker)) == ["pending"]
    result = review.advance(horizon, state, broker)
    assert outcomes(result) == expected
    assert result.state == state.at_tick(horizon)
    if expected == ["expired"]:
        assert result.events[0].tick == 4


def test_capacity_then_replay_with_referral_or_evidence_alias(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
) -> None:
    review = queue(delay=0, rollback=True)
    original = inputs(state, broker)
    assert outcomes(review.submit(*original, state, broker)) == ["pending"]
    assert outcomes(review.submit(*inputs(state, broker, "b"), state, broker)) == ["capacity"]
    assert "rolled_back" in outcomes(review.advance(1, state, broker))
    assert outcomes(review.submit(*original, state, broker)) == ["refused"]
    other_referral, other_decision, _ = inputs(state, broker, "new")
    alias = review.submit(other_referral, other_decision, original[2], state, broker)
    assert "evidence ID already consumed" == alias.events[0].payload["reason"]
    new_referral, new_decision, new_evidence = inputs(state, broker, "relabel")
    new_evidence = new_evidence.model_copy(update={"observation_ids": original[2].observation_ids})
    replay = review.submit(new_referral, new_decision, new_evidence, state, broker)
    assert replay.events[0].payload["reason"] == "underlying observation already consumed"
    assert review.advance(1, state, broker).events == ()


@pytest.mark.parametrize(
    "change",
    [
        "evidence_subject",
        "evidence_config",
        "receipt",
        "target",
        "unnamed_source",
        "multiple_sessions",
        "no_session",
    ],
)
def test_mismatched_referrals_cannot_open_requests(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    change: str,
) -> None:
    if change == "multiple_sessions":
        state = state.model_copy(
            update={
                "sessions": (*state.sessions, state.sessions[0].model_copy(update={"id": "s2"}))
            }
        )
    if change == "no_session":
        state = state.isolate_session("session")
    referral, decision, evidence = inputs(state, broker)
    if change == "evidence_subject":
        evidence = evidence.model_copy(update={"subject_id": "wrong"})
    if change == "evidence_config":
        evidence = evidence.model_copy(update={"configuration_version": "other"})
    if change == "receipt":
        decision = decision.model_copy(update={"action_digest": "2" * 64})
    if change == "target":
        referral = referral.model_copy(update={"target_id": "other"})
    if change == "unnamed_source":
        evidence = evidence.model_copy(update={"observation_ids": ()})
    review = queue()
    assert outcomes(review.submit(referral, decision, evidence, state, broker)) == ["refused"]
    assert review.advance(8, state, broker).events == ()


@pytest.mark.parametrize("drift", ["state", "policy", "prohibited", "late"])
def test_simulated_approval_cannot_bypass_fresh_governor_or_state(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    drift: str,
) -> None:
    review = queue()
    review.submit(*inputs(state, broker), state, broker)
    if drift in ("policy", "prohibited"):
        policy = broker.governor.policy.model_copy(update={"policy_version": "new"})
        if drift == "prohibited":
            policy = policy.model_copy(
                update={"allowed_action_types": (), "prohibited_action_types": ("isolate_session",)}
            )
        broker = SimulatedExecutionBroker(SafetyGovernor(policy))
    if drift == "state":
        changed = state.mission_functions[0].model_copy(update={"operational": False})
        state = state.model_copy(update={"mission_functions": (changed,)})
    if drift == "late":
        state = state.at_tick(3)
    result = review.advance(8, state, broker)
    assert outcomes(result) == ["approved", "unauthorized"]
    assert result.state == state.at_tick(8)


def test_simultaneous_requests_get_separate_prestate_rechecks(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
) -> None:
    review = queue(capacity=2)
    for suffix in ("a", "b"):
        assert outcomes(review.submit(*inputs(state, broker, suffix), state, broker)) == ["pending"]
    result = review.advance(2, state, broker)
    assert outcomes(result) == [
        "approved",
        "executed",
        "verified",
        "mission_effect",
        "approved",
        "unauthorized",
    ]
    assert result.state == state.at_tick(2).isolate_session("session")


@pytest.mark.parametrize("failure", ["broker_refusal", "collateral", "rollback"])
def test_distinct_failures_and_suspended_dispatch(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    review = queue(rollback=True, capacity=2)
    for suffix in ("a", "b"):
        assert outcomes(review.submit(*inputs(state, broker, suffix), state, broker)) == ["pending"]
    execute = broker.execute

    def faulty_action(
        action: DefensiveAction, decision: PolicyDecision, before: EnvironmentState
    ) -> ExecutionResult:
        result = execute(action, decision, before)
        if failure == "broker_refusal":
            record = result.record.model_copy(
                update={
                    "disposition": ExecutionDisposition.NOT_EXECUTED,
                    "reason": "simulated refusal",
                    "state_after": before,
                    "state_after_digest": canonical_sha256(before),
                }
            )
            return ExecutionResult(state=before, record=record)
        collateral = result.state.model_copy(update={"id": "unintended"})
        record = result.record.model_copy(
            update={"state_after": collateral, "state_after_digest": canonical_sha256(collateral)}
        )
        return ExecutionResult(state=collateral, record=record)

    def faulty_recovery(
        action: DefensiveAction, result: ExecutionResult, governor: SafetyGovernor
    ) -> RollbackResult:
        rollback = rollback_execution(action, result, governor)
        # A positive rollback record alone cannot establish exact restoration.
        return RollbackResult(state=result.state, record=rollback.record)

    if failure == "rollback":
        monkeypatch.setattr(guarded, "rollback_execution", faulty_recovery)
    else:
        monkeypatch.setattr(broker, "execute", faulty_action)
    result = review.advance(8, state, broker)
    assert all(event.tick == 2 and event.action_id == "review-a" for event in result.events)
    assert result.state.tick == 2
    if failure == "broker_refusal":
        assert outcomes(result) == ["approved", "execution_failed"]
        assert result.state == state.at_tick(2)
    elif failure == "collateral":
        assert outcomes(result) == [
            "approved",
            "executed",
            "verification_failed",
            "rollback_failed",
        ]
        assert result.state.id == "unintended"
    else:
        assert outcomes(result) == [
            "approved",
            "executed",
            "verified",
            "mission_effect",
            "rollback_failed",
        ]
        assert result.state == state.at_tick(2).isolate_session("session")
    with pytest.raises(RuntimeError, match="suspended"):
        review.advance(8, result.state, broker)
    another = review.submit(*inputs(result.state, broker, "c"), result.state, broker)
    assert another.events[0].payload["reason"] == "episode guarded dispatch is suspended"


def test_regressing_queue_clock_refused(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
) -> None:
    review = queue()
    review.submit(*inputs(state, broker), state, broker)
    with pytest.raises(ValueError, match="advance"):
        later = state.at_tick(3)
        review.submit(*inputs(later, broker, "b"), later, broker)
    review.advance(2, state, broker)
    with pytest.raises(ValueError, match="clock"):
        review.advance(1, state, broker)
    with pytest.raises(ValueError, match="clock"):
        review.submit(*inputs(state, broker, "b"), state, broker)


@pytest.mark.parametrize("failure", ["execute", "verify_execution", "rollback_execution"])
def test_runtime_faults_retain_observed_stages(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    def fail(*args: object) -> None:
        raise RuntimeError("simulated diagnostic failure")

    review = queue(rollback=True, capacity=2)
    for suffix in ("a", "b"):
        assert outcomes(review.submit(*inputs(state, broker, suffix), state, broker)) == ["pending"]
    monkeypatch.setattr(broker if failure == "execute" else guarded, failure, fail)
    result = review.advance(8, state, broker)
    assert all(event.tick == 2 and event.action_id == "review-a" for event in result.events)
    with pytest.raises(RuntimeError, match="suspended"):
        review.advance(8, result.state, broker)
    failures = [event for event in result.events if event.outcome.endswith("_failed")]
    assert [event.payload["error_type"] for event in failures] == ["RuntimeError"]
    if failure == "execute":
        assert outcomes(result) == ["approved", "execution_failed"]
        assert failures[0].payload["state_after_digest"] is None
        assert result.state == state.at_tick(2)
    elif failure == "verify_execution":
        assert outcomes(result) == ["approved", "executed", "verification_failed", "rolled_back"]
        assert result.state == state.at_tick(2)
    else:
        assert outcomes(result) == [
            "approved",
            "executed",
            "verified",
            "mission_effect",
            "rollback_failed",
        ]
        assert result.state == state.at_tick(2).isolate_session("session")


@pytest.mark.parametrize("fail_stage", ["execution", "rollback"])
def test_measurement_failure_preserves_requested_recovery(
    state: EnvironmentState,
    broker: SimulatedExecutionBroker,
    monkeypatch: pytest.MonkeyPatch,
    fail_stage: str,
) -> None:
    review = queue(delay=0, rollback=True)
    review.submit(*inputs(state, broker), state, broker)
    measure = guarded.mission_effect

    def fail_one_measurement(
        before: EnvironmentState, after: EnvironmentState
    ) -> dict[str, object]:
        target = after.get_session("session")
        assert target is not None
        stage = "execution" if target.isolated else "rollback"
        if stage == fail_stage:
            raise TypeError("injected measurement failure")
        return measure(before, after)

    monkeypatch.setattr(guarded, "mission_effect", fail_one_measurement)
    resolved = review.advance(state.tick, state, broker)
    assert resolved.state == state
    assert "rolled_back" in outcomes(resolved)
    assert resolved.failed_outcomes == ("mission_measurement_failed",)
    failure = next(
        event for event in resolved.events if event.outcome == "mission_measurement_failed"
    )
    assert failure.payload["stage"] == fail_stage and failure.payload["error_type"] == "TypeError"

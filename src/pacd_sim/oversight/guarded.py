"""Episode-local simulated review of a single reversible session isolation contract."""

from collections.abc import Callable
from dataclasses import dataclass

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.availability import continuity_transition, evaluate_availability
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.execution.broker import ExecutionResult, SimulatedExecutionBroker
from pacd_sim.execution.verification import rollback_execution, verify_execution
from pacd_sim.governance.governor import PolicyDecision
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import PolicyDisposition, RollbackDisposition, VerificationDisposition
from pacd_sim.state.snapshot import create_snapshot


@dataclass(frozen=True)
class ReviewEvent:
    """Raw lifecycle observation. The outer action ID is the originating referral."""

    tick: int
    entity_id: str
    action_id: str
    outcome: str
    payload: dict[str, object]


@dataclass(frozen=True)
class ReviewStep:
    state: EnvironmentState
    events: tuple[ReviewEvent, ...]

    @property
    def failed_outcomes(self) -> tuple[str, ...]:
        """Terminal faults retained together with their attempted recovery rows."""
        return tuple(
            event.outcome
            for event in self.events
            if event.outcome
            in {
                "authorization_failed",
                "execution_failed",
                "verification_failed",
                "rollback_failed",
            }
        )


def reviewed_isolation(
    referral: DefensiveAction, session_id: str, due_tick: int
) -> DefensiveAction:
    """Construct the immutable concrete proposal whose dispatch the review may request."""
    return DefensiveAction(
        id=f"reviewed-isolation-{canonical_sha256(referral)}",
        tick=due_tick,
        schema_version=referral.schema_version,
        configuration_version=referral.configuration_version,
        action_type="isolate_session",
        target_id=session_id,
        reversible=True,
        requested_authority="automatic",
        preconditions=("unique active unisolated session for the observed subject",),
        expected_effect="make exactly the reviewed synthetic session inactive and isolated",
        verification="compare the complete state with the independently reconstructed transition",
        rollback="restore the exact immutable dispatch pre-state",
    )


def review_binding(
    referral: DefensiveAction,
    decision: PolicyDecision,
    evidence: EvidenceItem,
    state: EnvironmentState,
    action: DefensiveAction,
    expires_tick: int,
) -> dict[str, object]:
    """Material retained when enqueuing. The replay verifier can reconstruct every binding."""
    return {
        "contract": "guarded-review-isolation-v1",
        "referral_digest": canonical_sha256(referral),
        "referral_decision_digest": canonical_sha256(decision),
        "subject_id": referral.target_id,
        "evidence_id": evidence.id,
        "evidence_digest": canonical_sha256(evidence),
        "policy_digest": decision.policy_digest,
        "state_digest": canonical_sha256(state),
        "action": action.model_dump(mode="json"),
        "action_digest": canonical_sha256(action),
        "submitted_tick": referral.tick,
        "due_tick": action.tick,
        "expires_tick": expires_tick,
    }


@dataclass(frozen=True)
class _Pending:
    referral: DefensiveAction
    action: DefensiveAction
    state: EnvironmentState
    policy_digest: str
    digest: str
    expires_tick: int
    wake_tick: int
    record: Callable[[ReviewEvent], ReviewEvent]

    def event(self, tick: int, outcome: str, **payload: object) -> ReviewEvent:
        return self.record(
            ReviewEvent(
                tick,
                self.referral.target_id,
                self.referral.id,
                outcome,
                {"request_digest": self.digest, **payload},
            )
        )


def mission_effect(before: EnvironmentState, after: EnvironmentState) -> dict[str, object]:
    """Measure the complete availability projection across one observed transition."""
    previous = evaluate_availability(before)
    current = evaluate_availability(after)
    return {
        "state_before_digest": canonical_sha256(before),
        "state_after_digest": canonical_sha256(after),
        "availability_before": previous.audit_summary(),
        "availability_after": current.audit_summary(),
        "mission_continuity": continuity_transition(previous, current),
    }


class GuardedReviewQueue:
    """One-shot review reservations owned by one serial diagnostic episode."""

    def __init__(
        self,
        *,
        capacity: int,
        delay_ticks: int,
        ttl_ticks: int,
        approve: bool | None,
        rollback: bool,
        observe: Callable[[ReviewEvent], None] | None = None,
    ) -> None:
        for limit in (capacity, delay_ticks, ttl_ticks):
            if type(limit) is not int or limit < 0:
                raise ValueError("review limits must be nonnegative integers")
        if (approve is not None and type(approve) is not bool) or type(rollback) is not bool:
            raise ValueError("invalid simulated reviewer or recovery setting")
        self._capacity = capacity
        self._delay = delay_ticks
        self._ttl = ttl_ticks
        self._approve = approve
        self._observe = observe
        self._rollback = rollback
        self._now = 0
        self._seen_referrals: set[str] = set()
        self._seen_evidence: set[str] = set()
        self._seen_observations: set[str] = set()
        self._pending: dict[str, _Pending] = {}
        self._quarantined = False

    def _record(self, event: ReviewEvent) -> ReviewEvent:
        # Deliver each observed stage before calling the next fallible component.
        if self._observe is not None:
            self._observe(event)
        return event

    def submit(
        self,
        referral: DefensiveAction,
        decision: PolicyDecision,
        evidence: EvidenceItem,
        state: EnvironmentState,
        broker: SimulatedExecutionBroker,
    ) -> ReviewStep:
        """Reserve exactly one governed referral, delivered evidence and eligible session."""
        if state.tick < self._now:
            raise ValueError("review state cannot precede the episode clock")
        if any(req.wake_tick < state.tick for req in self._pending.values()):
            raise ValueError("advance the review queue before submitting at a later tick")
        self._now = state.tick

        def reject(outcome: str, reason: str) -> ReviewStep:
            event = ReviewEvent(
                state.tick,
                referral.target_id,
                referral.id,
                outcome,
                {
                    "reason": reason,
                    "referral_digest": canonical_sha256(referral),
                    "evidence_digest": canonical_sha256(evidence),
                    "state_digest": canonical_sha256(state),
                },
            )
            return ReviewStep(state, (self._record(event),))

        if referral.id in self._seen_referrals:
            return reject("refused", "referral ID already consumed")
        self._seen_referrals.add(referral.id)
        if evidence.id in self._seen_evidence:
            return reject("refused", "evidence ID already consumed")
        if self._seen_observations.intersection(evidence.observation_ids):
            return reject("refused", "underlying observation already consumed")
        self._seen_evidence.add(evidence.id)
        self._seen_observations.update(evidence.observation_ids)
        if self._quarantined:
            return reject("refused", "episode guarded dispatch is suspended")
        if (
            referral.action_type != "require_human_review"
            or referral.requested_authority != "human"
            or not referral.reversible
            or referral.tick != state.tick
            or evidence.tick != state.tick
            or evidence.subject_id != referral.target_id
            or not evidence.observation_ids
            or evidence.configuration_version != state.configuration_version
            or evidence.schema_version != state.schema_version
            or decision.disposition is not PolicyDisposition.ESCALATE
            or canonical_sha256(decision)
            != canonical_sha256(
                broker.governor.evaluate(referral, mission_state=create_snapshot(state))
            )
        ):
            return reject("refused", "referral, evidence, state or governing decision mismatch")
        eligible = [
            session
            for session in state.sessions
            if referral.target_id in (session.id, session.identity_id)
            and session.active
            and not session.isolated
        ]
        if len(eligible) != 1:
            return reject("refused", "observed subject lacks a unique eligible synthetic session")
        if len(self._pending) >= self._capacity:
            return reject("capacity", "simulated review queue is full")

        due_tick = state.tick + self._delay
        expiry = state.tick + self._ttl
        action = reviewed_isolation(referral, eligible[0].id, due_tick)
        binding = review_binding(referral, decision, evidence, state, action, expiry)
        wake = expiry + 1 if self._approve is None else min(due_tick, expiry + 1)
        request = _Pending(
            referral,
            action,
            state,
            decision.policy_digest,
            canonical_sha256(binding),
            expiry,
            wake,
            self._record,
        )
        self._pending[referral.id] = request
        return ReviewStep(state, (request.event(state.tick, "pending", binding=binding),))

    def advance(
        self,
        tick: int,
        state: EnvironmentState,
        broker: SimulatedExecutionBroker,
    ) -> ReviewStep:
        """Process due events in simulation time and submission order through the given horizon."""
        if type(tick) is not int or state.tick < self._now or tick < state.tick:
            raise ValueError("guarded review requires a nondecreasing integer clock")
        if self._quarantined:
            raise RuntimeError("episode guarded dispatch is suspended")
        events: list[ReviewEvent] = []
        due = sorted(
            (req for req in self._pending.values() if req.wake_tick <= tick),
            key=lambda req: req.wake_tick,
        )
        for req in due:
            # Consume before resolution, including every denial and failure.
            del self._pending[req.referral.id]
            state = state.at_tick(max(state.tick, req.wake_tick))
            resolution = self._resolve(req, state, broker)
            state = resolution.state
            events.extend(resolution.events)
            if resolution.failed_outcomes:
                # Hand off all recovery evidence at this event time. Other arrivals
                # remain pending when the harness records the failed attempt.
                self._quarantined = True
                self._now = resolution.events[-1].tick
                return ReviewStep(state, tuple(events))
        self._now = tick
        return ReviewStep(state.at_tick(tick), tuple(events))

    def _resolve(
        self, req: _Pending, state: EnvironmentState, broker: SimulatedExecutionBroker
    ) -> ReviewStep:
        tick = state.tick
        if tick > req.expires_tick:
            return ReviewStep(state, (req.event(tick, "expired"),))
        if not self._approve:
            return ReviewStep(state, (req.event(tick, "denied"),))

        events = [req.event(tick, "approved")]
        governor = broker.governor
        try:
            decision = governor.evaluate(req.action, mission_state=create_snapshot(state))
        except Exception as exc:
            events.append(req.event(tick, "authorization_failed", error_type=type(exc).__name__))
            return ReviewStep(state, tuple(events))
        timely = tick == req.action.tick
        unchanged = canonical_sha256(req.state.at_tick(tick)) == canonical_sha256(state)
        if (
            self._quarantined
            or not timely
            or not unchanged
            or decision.policy_digest != req.policy_digest
            or not decision.permits_execution
        ):
            events.append(
                req.event(
                    tick,
                    "unauthorized",
                    policy_decision=decision.model_dump(mode="json"),
                    timely=timely,
                    prestate_matches=unchanged,
                    dispatch_suspended=self._quarantined,
                )
            )
            return ReviewStep(state, tuple(events))

        try:
            result = broker.execute(req.action, decision, state)
        except Exception as exc:
            events.append(
                req.event(
                    tick,
                    "execution_failed",
                    policy_decision=decision.model_dump(mode="json"),
                    adapter=broker.adapter_name,
                    network_enabled=broker.network_enabled,
                    error_type=type(exc).__name__,
                    state_before_digest=canonical_sha256(state),
                    state_after_digest=None,
                )
            )
            return ReviewStep(state, tuple(events))
        record = result.record
        # The broker may report a refusal; retain it separately from a failed verification.
        events.append(
            req.event(
                tick,
                "executed" if result.executed else "execution_failed",
                execution_id=record.id,
                adapter=broker.adapter_name,
                network_enabled=broker.network_enabled,
                policy_decision=decision.model_dump(mode="json"),
                disposition=record.disposition.value,
                reason=record.reason,
                state_before_digest=record.state_before_digest,
                state_after_digest=record.state_after_digest,
            )
        )
        try:
            verification = verify_execution(req.action, result, governor)
        except Exception as exc:
            events.append(
                req.event(
                    tick,
                    "verification_failed",
                    execution_id=record.id,
                    error_type=type(exc).__name__,
                )
            )
            return self._recover(req, state, result, broker, events, verified=False)
        prestate_matches = canonical_sha256(record.state_before) == canonical_sha256(state)
        verified = (
            verification.disposition is VerificationDisposition.VERIFIED
            and prestate_matches
            and canonical_sha256(record.policy_decision) == canonical_sha256(decision)
        )
        if (
            not result.executed
            and verification.disposition is VerificationDisposition.NOT_APPLICABLE
        ):
            if canonical_sha256(result.state) == canonical_sha256(state) and prestate_matches:
                return ReviewStep(state, tuple(events))
        events.append(
            req.event(
                tick,
                "verified" if verified else "verification_failed",
                verification=verification.model_dump(mode="json"),
                dispatch_prestate_matches=prestate_matches,
            )
        )
        if verified:
            events.append(
                req.event(
                    tick, "mission_effect", stage="execution", **mission_effect(state, result.state)
                )
            )
        if verified and not self._rollback:
            return ReviewStep(result.state, tuple(events))

        return self._recover(req, state, result, broker, events, verified=verified)

    def _recover(
        self,
        req: _Pending,
        state: EnvironmentState,
        result: ExecutionResult,
        broker: SimulatedExecutionBroker,
        events: list[ReviewEvent],
        *,
        verified: bool,
    ) -> ReviewStep:
        tick = state.tick
        try:
            recovery = rollback_execution(req.action, result, broker.governor)
        except Exception as exc:
            events.append(
                req.event(
                    tick,
                    "rollback_failed",
                    execution_id=result.record.id,
                    error_type=type(exc).__name__,
                    exact_prestate_restored=False,
                )
            )
            return ReviewStep(result.state, tuple(events))
        restored = (
            recovery.record.disposition is RollbackDisposition.ROLLED_BACK
            and recovery.record.execution_id == result.record.id
            and recovery.record.action_id == req.action.id
            and recovery.record.tick == tick
            and canonical_sha256(recovery.state) == canonical_sha256(state)
            and recovery.record.restored_state_digest == canonical_sha256(state)
        )
        events.append(
            req.event(
                tick,
                "rolled_back" if restored else "rollback_failed",
                rollback=recovery.record.model_dump(mode="json"),
                exact_prestate_restored=restored,
            )
        )
        if restored and verified:
            events.append(
                req.event(
                    tick,
                    "mission_effect",
                    stage="rollback",
                    **mission_effect(result.state, recovery.state),
                )
            )
        return ReviewStep(recovery.state, tuple(events))

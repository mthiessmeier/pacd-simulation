"""Read-only projection of the governed review schedule and expected immutable transitions."""

from dataclasses import dataclass

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.configuration import GuardedReviewConfig
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.execution.verification import RollbackRecord, VerificationRecord, expected_isolation
from pacd_sim.governance.governor import PolicyDecision, SafetyGovernor
from pacd_sim.oversight.guarded import mission_effect, review_binding, reviewed_isolation
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import PolicyDisposition, RollbackDisposition, VerificationDisposition
from pacd_sim.state.snapshot import create_snapshot


@dataclass(frozen=True)
class _ExpectedRequest:
    referral: DefensiveAction
    action: DefensiveAction
    submitted_state: EnvironmentState
    digest: str
    expiry: int
    wake: int
    policy_digest: str


class ExpectedReviewQueue:
    """Derive expected audit rows from controlled inputs, without invoking the broker or queue."""

    def __init__(
        self, config: GuardedReviewConfig, governor: SafetyGovernor, rows: list[dict[str, object]]
    ) -> None:
        self.config = config
        self.governor = governor
        self.rows = rows
        self.pending: list[_ExpectedRequest] = []

    def _emit(self, referral: DefensiveAction, tick: int, outcome: str, **payload: object) -> None:
        self.rows.append(
            {
                "event_type": "guarded_review",
                "action_id": referral.id,
                "entity_id": referral.target_id,
                "tick": float(tick),
                "outcome": outcome,
                "disposition": "",
                "payload": payload,
            }
        )

    def submit(
        self,
        referral: DefensiveAction,
        decision: PolicyDecision,
        evidence: EvidenceItem,
        state: EnvironmentState,
    ) -> None:
        sessions = [
            s
            for s in state.sessions
            if s.active and not s.isolated and referral.target_id in (s.identity_id, s.id)
        ]
        reason = None
        outcome = "refused"
        if (
            referral.action_type != "require_human_review"
            or referral.requested_authority != "human"
            or not referral.reversible
            or evidence.subject_id != referral.target_id
            or evidence.tick != state.tick
            or referral.tick != state.tick
            or decision.disposition != PolicyDisposition.ESCALATE
            or decision != self.governor.evaluate(referral, mission_state=create_snapshot(state))
        ):
            reason = "referral, evidence, state or governing decision mismatch"
        elif len(sessions) != 1:
            reason = "observed subject lacks a unique eligible synthetic session"
        elif len(self.pending) >= self.config.capacity:
            reason = "simulated review queue is full"
            outcome = "capacity"
        if reason is not None:
            self._emit(
                referral,
                state.tick,
                outcome,
                reason=reason,
                referral_digest=canonical_sha256(referral),
                evidence_digest=canonical_sha256(evidence),
                state_digest=canonical_sha256(state),
            )
            return
        due = state.tick + self.config.delay_ticks
        expiry = state.tick + self.config.validity_ticks
        action = reviewed_isolation(referral, sessions[0].id, due)
        binding = review_binding(referral, decision, evidence, state, action, expiry)
        digest = canonical_sha256(binding)
        wake = expiry + 1 if self.config.response == "no_response" else min(due, expiry + 1)
        self.pending.append(
            _ExpectedRequest(referral, action, state, digest, expiry, wake, decision.policy_digest)
        )
        self._emit(referral, state.tick, "pending", request_digest=digest, binding=binding)

    def advance(self, horizon: int, state: EnvironmentState) -> EnvironmentState:
        # Sort stably so equal deadlines preserve the governed observation order.
        due = sorted((r for r in self.pending if r.wake <= horizon), key=lambda r: r.wake)
        self.pending = [r for r in self.pending if r.wake > horizon]
        for req in due:
            state = state.at_tick(req.wake)
            if req.wake > req.expiry:
                self._emit(req.referral, req.wake, "expired", request_digest=req.digest)
            elif self.config.response == "deny":
                self._emit(req.referral, req.wake, "denied", request_digest=req.digest)
            else:
                state = self._approved(req, state)
        return state.at_tick(horizon)

    def _approved(self, req: _ExpectedRequest, before: EnvironmentState) -> EnvironmentState:
        def record(outcome: str, **payload: object) -> None:
            self._emit(req.referral, before.tick, outcome, request_digest=req.digest, **payload)

        record("approved")
        action = req.action
        decision = self.governor.evaluate(action, mission_state=create_snapshot(before))
        policy = decision.model_dump(mode="json")
        unchanged = req.submitted_state.at_tick(before.tick) == before
        timely = action.tick == before.tick
        if not (
            unchanged
            and timely
            and decision.permits_execution
            and decision.policy_digest == req.policy_digest
        ):
            record(
                "unauthorized",
                policy_decision=policy,
                prestate_matches=unchanged,
                timely=timely,
                dispatch_suspended=False,
            )
            return before

        # The bound unique session is active in the submitted state. A valid dispatch changes
        # exactly that session, preserving all other field values and entity memberships.
        after = expected_isolation(before, action.target_id, decision.tick)
        execution_id = f"execution-{action.id}"
        record(
            "executed",
            adapter="simulated_only",
            network_enabled=False,
            execution_id=execution_id,
            policy_decision=policy,
            disposition="EXECUTED",
            reason="synthetic session isolated in immutable in-memory state",
            state_before_digest=canonical_sha256(before),
            state_after_digest=canonical_sha256(after),
        )
        common = {
            "tick": before.tick,
            "configuration_version": decision.policy_version,
            "execution_id": execution_id,
            "action_id": action.id,
        }
        verification = VerificationRecord.model_validate(
            {
                **common,
                "id": f"verification-{execution_id}",
                "disposition": VerificationDisposition.VERIFIED,
                "state_hashes_valid": True,
                "expected_effect_observed": True,
                "reason": "expected synthetic isolation transition observed",
            }
        )
        record(
            "verified",
            verification=verification.model_dump(mode="json"),
            dispatch_prestate_matches=True,
        )
        record("mission_effect", stage="execution", **mission_effect(before, after))
        if not self.config.rollback:
            return after
        rollback = RollbackRecord.model_validate(
            {
                **common,
                "id": f"rollback-{execution_id}",
                "disposition": RollbackDisposition.ROLLED_BACK,
                "restored_state_digest": canonical_sha256(before),
                "reason": "restored exact prior immutable synthetic state",
            }
        )
        record(
            "rolled_back", rollback=rollback.model_dump(mode="json"), exact_prestate_restored=True
        )
        record("mission_effect", stage="rollback", **mission_effect(after, before))
        return before

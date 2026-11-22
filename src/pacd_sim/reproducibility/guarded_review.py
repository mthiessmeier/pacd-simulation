"""Read-only projection of the governed review schedule and expected immutable transitions."""

from dataclasses import dataclass

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.configuration import GuardedReviewConfig
from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.environment.availability import (
    AvailabilityReport,
    evaluate_availability,
)
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.normalize import EvidenceItem
from pacd_sim.execution.verification import RollbackRecord, VerificationRecord, expected_isolation
from pacd_sim.governance.governor import PolicyDecision, SafetyGovernor
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import PolicyDisposition, RollbackDisposition, VerificationDisposition
from pacd_sim.state.snapshot import create_snapshot


def expected_availability(report: AvailabilityReport) -> dict[str, int | str]:
    """Check the wire counts against the canonical state-derived entity memberships."""
    return {
        "entity_count": len(report.available_entity_ids) + len(report.unavailable_entity_ids),
        "available_entity_count": len(report.available_entity_ids),
        "service_count": len(report.service_ids),
        "available_service_count": len(report.available_service_ids),
        "mission_count": len(report.mission_ids),
        "operational_mission_count": len(report.operational_mission_ids),
        "availability_digest": canonical_sha256(report),
    }


def _expected_mission_effect(
    before: EnvironmentState, after: EnvironmentState
) -> dict[str, object]:
    previous = evaluate_availability(before)
    current = evaluate_availability(after)
    was_up = set(previous.operational_mission_ids)
    now_up = set(current.operational_mission_ids)
    groups = {
        "continued": was_up & now_up,
        "interrupted": was_up - now_up,
        "restored": now_up - was_up,
        "unavailable_throughout": set(previous.mission_ids) - was_up - now_up,
    }
    continuity = {mission: label for label, missions in groups.items() for mission in missions}
    return {
        "state_before_digest": canonical_sha256(before),
        "state_after_digest": canonical_sha256(after),
        "availability_before": expected_availability(previous),
        "availability_after": expected_availability(current),
        "mission_continuity": {
            **{f"{label}_mission_count": len(missions) for label, missions in groups.items()},
            "continuity_digest": canonical_sha256(continuity),
        },
    }


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
        self.history: list[tuple[BaselineObservation, bool]] = []

    def suppresses(self, reading: BaselineObservation, proposed: bool) -> bool:
        """Look for an admitted proposal in this subject's contiguous elevated readings."""
        suppressed = False
        if proposed and reading.subject_id is not None and reading.signal >= 0.75:
            next_tick = reading.tick
            for earlier, admitted in reversed(self.history):
                if earlier.subject_id != reading.subject_id:
                    continue
                if earlier.signal < 0.75 or next_tick - earlier.tick > 3:
                    break
                if admitted:
                    suppressed = True
                    break
                next_tick = earlier.tick
        self.history.append((reading, proposed and not suppressed))
        return suppressed

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
            or canonical_sha256(decision)
            != canonical_sha256(
                self.governor.evaluate(referral, mission_state=create_snapshot(state))
            )
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
        referral_digest = canonical_sha256(referral)
        action = DefensiveAction(
            id=f"reviewed-isolation-{referral_digest}",
            tick=due,
            schema_version=state.schema_version,
            configuration_version=state.configuration_version,
            action_type="isolate_session",
            target_id=sessions[0].id,
            requested_authority="automatic",
            reversible=True,
            preconditions=("unique active unisolated session for the observed subject",),
            expected_effect="make exactly the reviewed synthetic session inactive and isolated",
            verification=(
                "compare the complete state with the independently reconstructed transition"
            ),
            rollback="restore the exact immutable dispatch pre-state",
        )
        binding = {
            "contract": "guarded-review-isolation-v1",
            "referral_digest": referral_digest,
            "referral_decision_digest": canonical_sha256(decision),
            "subject_id": evidence.subject_id,
            "evidence_id": evidence.id,
            "evidence_digest": canonical_sha256(evidence),
            "policy_digest": canonical_sha256(self.governor.policy),
            "state_digest": canonical_sha256(state),
            "action": action.model_dump(mode="json"),
            "action_digest": canonical_sha256(action),
            "submitted_tick": state.tick,
            "due_tick": due,
            "expires_tick": expiry,
        }
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
        unchanged = canonical_sha256(req.submitted_state.at_tick(before.tick)) == canonical_sha256(
            before
        )
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
        record("mission_effect", stage="execution", **_expected_mission_effect(before, after))
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
        record("mission_effect", stage="rollback", **_expected_mission_effect(after, before))
        return before

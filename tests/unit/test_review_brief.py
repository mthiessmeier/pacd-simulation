"""Review admissions must bind the original delivery and fit the guarded audit contract."""

from typing import Any

import pytest
from pydantic import ValidationError

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.configuration import GuardedReviewConfig
from pacd_sim.environment.model import EnvironmentState, Identity, MissionFunction, Service, Session
from pacd_sim.evidence.normalize import normalize_observation
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.governance.governor import SafetyGovernor, SafetyPolicy
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewEvent
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.schema import MAX_AUDIT_PAYLOAD_BYTES
from pacd_sim.state.snapshot import create_snapshot
from pacd_sim.telemetry.generator import Observation


def _queue() -> GuardedReviewQueue:
    return GuardedReviewQueue(
        capacity=2, delay_ticks=1, ttl_ticks=4, approve=None, rollback=False, include_brief=True
    )


@pytest.fixture
def state() -> EnvironmentState:
    return EnvironmentState(
        tick=4,
        identities=(Identity(id="u", role="synthetic"),),
        sessions=(Session(id="s", identity_id="u", service_id="svc"),),
        services=(Service(id="svc", mission_id="mission"),),
        mission_functions=(MissionFunction(id="mission", criticality=1.0),),
    )


def _observation(key: str) -> Observation:
    return Observation(
        id=key,
        event_id="truth-private",
        event_kind="benign_administrative",
        sensor_id="sensor-private",
        identity_id="u",
        event_tick=1,
        tick=4,
        signal=0.8,
    )


def _broker() -> SimulatedExecutionBroker:
    return SimulatedExecutionBroker(
        SafetyGovernor(
            SafetyPolicy(
                allowed_action_types=("isolate_session",),
                escalated_action_types=("require_human_review",),
                prohibited_action_types=(),
            )
        )
    )


def test_evidence_commitment_preserves_legacy_bytes_and_binds_the_original_delivery() -> None:
    observation = _observation("legacy").model_copy(update={"signal": 0.75})
    # Canonical bytes from the accepted GOV-002 revision, before evidence commitments.
    expected = (
        b'{"category":"benign_context","confidence":0.25,"configuration_version":"BOOTSTRAP_DRAFT_v1",'
        b'"id":"evidence-legacy","integrity":1.0,"observation_ids":["legacy"],'
        b'"provenance":["legacy","sensor-private"],"schema_version":"1.0",'
        b'"source":"synthetic","subject_id":"u","tick":4}'
    )
    assert canonical_json_bytes(normalize_observation(observation)) == expected
    issued = normalize_observation(observation, delivery_ordinal=1)
    assert issued.delivery_digest == canonical_sha256(
        {"observation_key": 1, "observation": observation}
    )
    assert canonical_json_bytes(issued) != expected


def _submit(
    queue: GuardedReviewQueue,
    state: EnvironmentState,
    observation: Observation,
    delivery: tuple[int, Observation] | None,
    *,
    original_ordinal: int | None = 1,
) -> ReviewEvent:
    broker = _broker()
    action = DefensiveAction(
        id="review-" + observation.id,
        tick=state.tick,
        action_type="require_human_review",
        target_id="u",
        requested_authority="human",
        reversible=True,
    )
    decision = broker.governor.evaluate(action, mission_state=create_snapshot(state))
    step = queue.submit(
        action,
        decision,
        normalize_observation(observation, delivery_ordinal=original_ordinal),
        state,
        broker,
        delivery=delivery,
    )
    assert step.state is state
    (row,) = step.events
    return row


@pytest.mark.parametrize("bad", ["missing", "other_record", "wrong_signal", "wrong_subject", "key"])
def test_missing_or_crossed_delivery_is_refused(state: EnvironmentState, bad: str) -> None:
    original = _observation("a")
    changes: dict[str, dict[str, object]] = {
        "other_record": {"id": "other"},
        "wrong_signal": {"signal": 0.3},
        "wrong_subject": {"identity_id": "other"},
    }
    supplied = original.model_copy(update=changes.get(bad, {}))
    delivery = None if bad == "missing" else (0 if bad == "key" else 1, supplied)
    row = _submit(_queue(), state, original, delivery)
    assert row.outcome == "refused"
    assert "request_digest" not in row.payload


def test_second_record_cannot_reuse_an_opaque_delivery_key(state: EnvironmentState) -> None:
    queue = _queue()
    first, second = _observation("a"), _observation("b")
    assert _submit(queue, state, first, (1, first)).outcome == "pending"
    assert _submit(queue, state, second, (1, second)).outcome == "refused"


@pytest.mark.parametrize("cross", ["clock", "ordinal", "mirrored_signal", "missing_commitment"])
def test_only_original_delivery_can_admit_or_dispatch(state: EnvironmentState, cross: str) -> None:
    original = _observation("committed").model_copy(
        update={"event_kind": "unknown", "signal": 0.25}
    )
    supplied = original
    ordinal = 1
    if cross == "clock":
        supplied = original.model_copy(update={"event_tick": 0})
    elif cross == "ordinal":
        ordinal = 2
    elif cross == "mirrored_signal":
        supplied = original.model_copy(update={"signal": 0.75})
    # In each case the previous normalized fields and eligibility are identical.
    assert normalize_observation(original) == normalize_observation(supplied)
    queue = GuardedReviewQueue(
        capacity=1, delay_ticks=1, ttl_ticks=4, approve=True, rollback=False, include_brief=True
    )
    rejected = _submit(
        queue,
        state,
        original,
        (ordinal, supplied),
        original_ordinal=None if cross == "missing_commitment" else 1,
    )
    assert rejected.outcome == "refused" and "request_digest" not in rejected.payload
    resolution = queue.advance(5, state, _broker())
    assert not resolution.events and resolution.state == state.at_tick(5)
    fresh = _observation("fresh").model_copy(update={"tick": 5, "event_tick": 4})
    # A rejected substitution cannot reserve the free slot or dispatch any action.
    admitted = _submit(queue, resolution.state, fresh, (2, fresh), original_ordinal=2)
    assert admitted.outcome == "pending"
    assert "executed" in [
        event.outcome for event in queue.advance(6, resolution.state, _broker()).events
    ]


def test_pending_payload_uses_the_inclusive_utf8_byte_limit(state: EnvironmentState) -> None:
    observation = _observation("one")

    def admission(extra: tuple[MissionFunction, ...]) -> ReviewEvent:
        hypothesis = state.model_copy(
            update={"mission_functions": (*state.mission_functions, *extra)}
        )
        return _submit(_queue(), hypothesis, observation, (1, observation))

    # Mission IDs with multibyte characters distinguish the byte and character limits.
    # A fixed-length request digest makes the final UTF-8 padding exact.
    minimal = MissionFunction(id="last", criticality=0.1)
    baseline = len(canonical_json_bytes(admission((minimal,)).payload))
    sample = MissionFunction(id="000" + "界" * 80, criticality=0.1)
    increment = len(canonical_json_bytes(admission((minimal, sample)).payload)) - baseline
    count, padding = divmod(MAX_AUDIT_PAYLOAD_BYTES - baseline, increment)
    extra = tuple(sample.model_copy(update={"id": f"{i:03}" + "界" * 80}) for i in range(count))
    name = "last" + "界" * (padding // 3) + "x" * (padding % 3)
    full = admission((*extra, MissionFunction(id=name, criticality=0.1)))
    assert full.outcome == "pending"
    assert len(canonical_json_bytes(full.payload)) == MAX_AUDIT_PAYLOAD_BYTES
    overflow = admission((*extra, MissionFunction(id=name + "x", criticality=0.1)))
    assert overflow.outcome == "refused"
    assert overflow.payload["reason"] == "review brief exceeds the audit payload limit"


def test_brief_version_preserves_omitted_field_and_rejects_explicit_null() -> None:
    config: dict[str, Any] = dict(
        capacity=1,
        delay_ticks=1,
        validity_ticks=2,
        end_tick=4,
        response="approve",
        rollback=False,
        matched_signal_mean=0.8,
    )
    assert GuardedReviewConfig.model_validate(config).model_dump(mode="json") == config
    assert GuardedReviewConfig.model_validate(
        dict(config, decision_brief="operator-preview-v1")
    ).decision_brief
    for value in (None, "operator-preview-v2", True):
        with pytest.raises(ValidationError):
            GuardedReviewConfig.model_validate(dict(config, decision_brief=value))

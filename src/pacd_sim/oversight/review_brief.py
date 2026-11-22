"""Prospective information for the simulated reviewer at queue admission."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.environment.availability import evaluate_availability
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.evidence.context import MAX_AGE_TICKS, EvidenceReading
from pacd_sim.execution.verification import expected_isolation, expected_sensing_profile
from pacd_sim.governance.governor import PolicyDecision

IMPACT_ASSUMPTION = (
    "Fresh authorization at the due tick with the submitted state otherwise unchanged."
)


def operator_brief(
    decision: PolicyDecision,
    reading: EvidenceReading,
    state: EnvironmentState,
    action: DefensiveAction,
) -> dict[str, object]:
    """Preview the proposed transition against its immutable submission state."""
    if action.action_type == "isolate_session":
        projected = expected_isolation(state, action.target_id, action.tick)
    elif action.action_type == "switch_sensing_profile":
        projected = expected_sensing_profile(state, action.target_id, action.tick)
    else:
        raise ValueError("unsupported review brief action")
    before = evaluate_availability(state)
    before_operational = set(before.operational_mission_ids)
    after_operational = set(evaluate_availability(projected).operational_mission_ids)
    age = reading.delivered_tick - reading.measured_tick
    return {
        "format": "operator-preview-v1",
        "rationale": decision.reason,
        "action_type": action.action_type,
        "target_id": action.target_id,
        "expected_effect": action.expected_effect,
        "triggering_reading": reading.model_dump(mode="json"),
        "uncertainty": {
            "age_ticks": age,
            "freshness": "fresh" if age <= MAX_AGE_TICKS else "stale",
            "compromise_probability": None,
        },
        "impact_preview": {
            "assumption": IMPACT_ASSUMPTION,
            "mission_cost": action.mission_cost,
            "missions": [
                {
                    "mission_id": mission_id,
                    "operational_before": mission_id in before_operational,
                    "operational_if_applied": mission_id in after_operational,
                }
                for mission_id in sorted(before.mission_ids)
            ],
        },
    }

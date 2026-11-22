"""One governed opportunity to change the precision of a local synthetic sensor."""

from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.environment.model import EnvironmentState
from pacd_sim.polymorphism.operators import PolymorphismOperator
from pacd_sim.telemetry.generator import Observation


def sensing_decision(
    policy: str, reading: BaselineObservation, ordinal: int, switch_cost: float, budget: float
) -> str:
    """Select a reversible sensing profile against the zero-cost default."""
    if ordinal != 1:
        return "outside_opportunity"
    if policy == "sensing_disabled_v1":
        return "disabled"
    if reading.subject_id is None:
        return "no_subject"
    if switch_cost > budget:
        return "over_budget"
    if policy == "sensing_fixed_v1":
        return "proposed"
    if policy != "sensing_adaptive_v1":
        raise ValueError("unexpected sensing policy")
    candidate = PolymorphismOperator(
        id="operator-sensing-alternate",
        tick=reading.tick,
        category="sensing",
        variant="alternate",
        expected_benefit=reading.signal,
        mission_cost=switch_cost,
    )
    return "proposed" if candidate.score > 0 else "no_positive_gain"


def project_sensing_observation(
    generated: Observation, state: EnvironmentState
) -> tuple[Observation, dict[str, object]]:
    """Quantize the already-generated signal using the current subject's session profile."""
    subject = generated.identity_id or generated.target_id
    sessions = [
        session
        for session in state.sessions
        if session.active and not session.isolated and subject in (session.id, session.identity_id)
    ]
    profile = sessions[0].sensing_profile if len(sessions) == 1 else "default"
    signal = round(generated.signal, 2 if profile == "alternate" else 1)
    return generated.model_copy(update={"signal": signal}), {
        "sensing_profile": profile,
        "latent_signal": generated.signal,
    }

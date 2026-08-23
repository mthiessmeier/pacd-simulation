"""Transparent PACD diagnostic candidate-action generator."""

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.defenders.base import DefenderContext, DefenderDecision


class DiagnosticPACDDefender:
    """Propose reversible isolation for high-confidence synthetic session risk."""

    def __init__(self, compromise_threshold: float = 0.5) -> None:
        if not isinstance(compromise_threshold, float) or not 0.0 <= compromise_threshold <= 1.0:
            raise ValueError("compromise_threshold must be a float between zero and one")
        self._compromise_threshold = compromise_threshold

    @property
    def defender_id(self) -> str:
        return "defender-pacd-diagnostic"

    def decide(self, context: DefenderContext) -> DefenderDecision:
        actions: list[DefensiveAction] = []
        for session in context.environment.sessions:
            probability = context.belief_state.compromise_probability(session.identity_id)
            if probability < self._compromise_threshold or session.isolated or not session.active:
                continue
            actions.append(
                DefensiveAction(
                    id=f"action-pacd-isolate-{session.id}-{context.tick}",
                    tick=context.tick,
                    configuration_version=context.configuration_version,
                    action_type="isolate_session",
                    target_id=session.id,
                    reversible=True,
                    requested_authority="automatic",
                    expected_effect="isolate one synthetic session in memory",
                    mission_cost=0.05,
                    preconditions=("target is an active synthetic session",),
                    verification="session becomes inactive and isolated",
                    rollback="restore exact prior synthetic session state",
                )
            )
        return DefenderDecision(
            id=f"decision-{self.defender_id}-{context.tick}",
            tick=context.tick,
            configuration_version=context.configuration_version,
            defender_id=self.defender_id,
            proposed_actions=tuple(actions),
            rationale=(
                "proposed reversible isolation for explicit high-confidence hypotheses"
                if actions
                else "no hypothesis crossed the diagnostic action threshold"
            ),
        )

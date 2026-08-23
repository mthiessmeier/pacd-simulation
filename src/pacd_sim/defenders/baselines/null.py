"""Fair null diagnostic baseline using the common defender interface."""

from pacd_sim.defenders.base import DefenderContext, DefenderDecision


class NullDefender:
    """Baseline that observes the same context and deliberately proposes nothing."""

    @property
    def defender_id(self) -> str:
        return "defender-null-diagnostic"

    def decide(self, context: DefenderContext) -> DefenderDecision:
        return DefenderDecision(
            id=f"decision-{self.defender_id}-{context.tick}",
            tick=context.tick,
            configuration_version=context.configuration_version,
            defender_id=self.defender_id,
            proposed_actions=(),
            rationale="null diagnostic baseline intentionally proposes no action",
        )

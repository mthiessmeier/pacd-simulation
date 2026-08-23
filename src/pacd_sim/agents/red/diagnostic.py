"""Bounded red-agent fixture that emits synthetic diagnostic events only."""

from pacd_sim.engine.scheduler import ScheduledEvent
from pacd_sim.schema import StableId


class DiagnosticRedAgent:
    """No-tool fixture for the authorized benign/adversary event pair."""

    def __init__(
        self,
        benign_identity_id: StableId = "identity-synthetic-admin",
        adversary_identity_id: StableId = "identity-synthetic-user",
    ) -> None:
        self._benign_identity_id = benign_identity_id
        self._adversary_identity_id = adversary_identity_id

    @property
    def agent_id(self) -> str:
        return "red-agent-synthetic-diagnostic"

    def events(self) -> tuple[ScheduledEvent, ...]:
        """Return a stable event sequence with no external target or capability."""

        return (
            ScheduledEvent(
                id="event-benign-admin",
                tick=1,
                kind="benign_administrative",
                identity_id=self._benign_identity_id,
            ),
            ScheduledEvent(
                id="event-simulated-adversary",
                tick=2,
                kind="simulated_adversary",
                identity_id=self._adversary_identity_id,
            ),
        )

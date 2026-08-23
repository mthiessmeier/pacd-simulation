"""Immutable environment snapshots bound to canonical SHA-256 digests."""

from pacd_sim.environment.model import EnvironmentState
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import ConsequentialRecord, StableId


class StateSnapshot(ConsequentialRecord):
    """A complete synthetic state plus its canonical integrity digest."""

    environment: EnvironmentState
    environment_digest: str


def create_snapshot(
    environment: EnvironmentState,
    snapshot_id: StableId | None = None,
) -> StateSnapshot:
    """Create a digest-bound snapshot without mutating the environment."""

    identifier = snapshot_id or f"snapshot-{environment.id}-{environment.tick}"
    return StateSnapshot(
        id=identifier,
        tick=environment.tick,
        configuration_version=environment.configuration_version,
        environment=environment,
        environment_digest=canonical_sha256(environment),
    )


def verify_snapshot(snapshot: StateSnapshot) -> bool:
    """Verify that a snapshot still matches its canonical digest."""

    return canonical_sha256(snapshot.environment) == snapshot.environment_digest

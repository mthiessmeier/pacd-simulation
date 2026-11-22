"""Time integral of criticality-weighted binary mission loss in a verified episode."""

from collections.abc import Mapping, Sequence
from fractions import Fraction
from itertools import chain, pairwise

type MissionSnapshot = tuple[int, tuple[str, ...]]


def mission_loss(
    weights: Mapping[str, float], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, object]:
    """Integrate the membership in force on each half-open interval from tick zero."""
    if not snapshots or snapshots[0][0] != 0:
        raise ValueError("mission loss requires initial availability at tick zero")
    unavailable = dict.fromkeys(weights, 0)
    # The end marker closes the last interval without supplying a new measurement.
    for (start, operational), (stop, _) in pairwise(chain(snapshots, [(horizon, ())])):
        up = set(operational)
        if stop < start or not up.issubset(weights):
            raise ValueError("invalid replayed mission clock or membership")
        for mission in weights.keys() - up:
            unavailable[mission] += stop - start

    per_mission = []
    total_loss = Fraction()
    possible = Fraction()
    for mission, criticality in sorted(weights.items()):
        weight = Fraction(str(criticality))
        loss = weight * unavailable[mission]
        total_loss += loss
        possible += weight * horizon
        per_mission.append(
            {
                "mission_id": mission,
                "criticality": criticality,
                "unavailable_ticks": unavailable[mission],
                "weighted_loss": float(loss),
            }
        )
    ratio = total_loss / possible if possible else None
    return {
        "format": "pacd-mission-loss-v1",
        "metric_id": "MIS-002",
        "horizon_ticks": horizon,
        "per_mission": per_mission,
        "weighted_loss": float(total_loss),
        "possible_weighted_ticks": float(possible),
        "loss_fraction": float(ratio) if ratio is not None else None,
        "loss_fraction_exact": str(ratio) if ratio is not None else None,
    }

"""Time integrals of binary mission loss and designated critical-function outages."""

from collections.abc import Collection, Iterator, Mapping, Sequence
from fractions import Fraction
from itertools import chain, pairwise

type MissionSnapshot = tuple[int, tuple[str, ...]]


def _mission_intervals(
    snapshots: Sequence[MissionSnapshot], horizon: int
) -> Iterator[tuple[int, tuple[str, ...]]]:
    if not snapshots or snapshots[0][0] != 0:
        raise ValueError("mission measure requires initial availability at tick zero")
    # The end marker closes the last interval without supplying a new measurement.
    for (start, operational), (stop, _) in pairwise(chain(snapshots, [(horizon, ())])):
        if stop < start:
            raise ValueError("invalid replayed mission clock")
        yield stop - start, operational


def mission_loss(
    weights: Mapping[str, float], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, object]:
    """Integrate the membership in force on each half-open interval from tick zero."""
    unavailable = dict.fromkeys(weights, 0)
    for duration, operational in _mission_intervals(snapshots, horizon):
        up = set(operational)
        if not up.issubset(weights):
            raise ValueError("invalid replayed mission membership")
        for mission in weights.keys() - up:
            unavailable[mission] += duration

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


def critical_outage(
    mission_ids: Collection[str],
    critical_ids: Collection[str],
    snapshots: Sequence[MissionSnapshot],
    horizon: int,
) -> dict[str, object]:
    """Measure time below operational state for the scenario's designated missions."""
    missions = set(mission_ids)
    critical = set(critical_ids)
    if len(missions) != len(mission_ids):
        raise ValueError("duplicate governed mission")
    if not critical or len(critical) != len(critical_ids) or not critical.issubset(missions):
        raise ValueError("critical missions must be a nonempty, unique set of governed missions")

    ticks = dict.fromkeys(critical, 0)
    any_outage = 0
    for duration, operational in _mission_intervals(snapshots, horizon):
        up = set(operational)
        if len(up) != len(operational) or not up.issubset(missions):
            raise ValueError("invalid replayed mission membership")
        down = critical - up
        if down:
            any_outage += duration
        for mission in down:
            ticks[mission] += duration

    final_up = set(snapshots[-1][1])
    return {
        "format": "pacd-critical-outage-v1",
        "metric_id": "MIS-003",
        "clock_unit": "simulation_ticks",
        "threshold_rule": "binary_unavailable",
        "horizon_ticks": horizon,
        "per_mission": [
            {
                "mission_id": mission,
                "outage_ticks": ticks[mission],
                "unavailable_at_horizon": mission not in final_up,
            }
            for mission in sorted(critical)
        ],
        "outage_function_ticks": sum(ticks.values()),
        "possible_function_ticks": len(critical) * horizon,
        "any_outage_ticks": any_outage,
        "any_outage_fraction": any_outage / horizon if horizon else None,
    }

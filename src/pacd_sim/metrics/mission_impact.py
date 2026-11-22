"""Time integrals of binary mission availability, loss and critical-function outages."""

from collections.abc import Collection, Iterator, Mapping, Sequence
from fractions import Fraction
from itertools import chain, pairwise

type MissionSnapshot = tuple[int, tuple[str, ...]]


def _mission_intervals(
    mission_ids: Collection[str], snapshots: Sequence[MissionSnapshot], horizon: int
) -> Iterator[tuple[int, set[str]]]:
    missions = set(mission_ids)
    if len(missions) != len(mission_ids):
        raise ValueError("duplicate governed mission")
    if not snapshots or snapshots[0][0] != 0:
        raise ValueError("mission measure requires initial availability at tick zero")
    # The end marker closes the last interval without supplying a new measurement.
    for (start, operational), (stop, _) in pairwise(chain(snapshots, [(horizon, ())])):
        if type(start) is not int or type(stop) is not int or stop < start:
            raise ValueError("invalid replayed mission clock")
        up = set(operational)
        if len(up) != len(operational) or not up.issubset(missions):
            raise ValueError("invalid replayed mission membership")
        yield stop - start, up


def _unavailable_ticks(
    mission_ids: Collection[str], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, int]:
    unavailable = dict.fromkeys(mission_ids, 0)
    for duration, up in _mission_intervals(mission_ids, snapshots, horizon):
        for mission in unavailable.keys() - up:
            unavailable[mission] += duration
    return unavailable


def function_availability(
    mission_ids: Collection[str], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, object]:
    """Measure the operational share of the observed clock for each governed mission."""
    if not mission_ids:
        raise ValueError("mission availability requires at least one governed mission")
    unavailable = _unavailable_ticks(mission_ids, snapshots, horizon)
    possible = horizon * len(unavailable)
    available = possible - sum(unavailable.values())
    return {
        "format": "pacd-function-availability-v1",
        "metric_id": "MIS-001",
        "clock_unit": "simulation_ticks",
        "dependency_model": "required_dependencies_v1",
        "horizon_ticks": horizon,
        "per_mission": [
            {
                "mission_id": mission,
                "available_ticks": horizon - down,
                "possible_ticks": horizon,
                "availability_fraction": (horizon - down) / horizon if horizon else None,
            }
            for mission, down in sorted(unavailable.items())
        ],
        "available_function_ticks": available,
        "possible_function_ticks": possible,
        "availability_fraction": available / possible if possible else None,
    }


def mission_loss(
    weights: Mapping[str, float], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, object]:
    """Integrate the membership in force on each half-open interval from tick zero."""
    unavailable = _unavailable_ticks(weights, snapshots, horizon)

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
    if not critical or len(critical) != len(critical_ids) or not critical.issubset(missions):
        raise ValueError("critical missions must be a nonempty, unique set of governed missions")

    ticks = dict.fromkeys(critical, 0)
    any_outage = 0
    for duration, up in _mission_intervals(mission_ids, snapshots, horizon):
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

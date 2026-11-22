"""Recovery from binary mission outages in independently replayed guarded episodes."""

from collections.abc import Collection, Sequence

from pacd_sim.metrics.mission_impact import MissionSnapshot


def _spell(onset: int | None, restored: int | None, horizon: int) -> dict[str, int | None]:
    observed_from = 0 if onset is None else onset
    observed_until = horizon if restored is None else restored
    return {
        "observed_from_tick": observed_from,
        "onset_tick": onset,
        "restored_tick": restored,
        "observed_ticks": observed_until - observed_from,
        "recovery_ticks": restored - onset if restored is not None and onset is not None else None,
    }


def mission_recovery(
    mission_ids: Collection[str], snapshots: Sequence[MissionSnapshot], horizon: int
) -> dict[str, object]:
    """Track every loss and restoration of operational membership in replay order."""
    if not snapshots or snapshots[0][0] != 0:
        raise ValueError("mission recovery requires initial availability at tick zero")
    missions = set(mission_ids)
    if len(missions) != len(mission_ids):
        raise ValueError("mission recovery requires unique governed missions")
    spells: dict[str, list[dict[str, int | None]]] = {mission: [] for mission in missions}
    onset: dict[str, int | None] = {}
    previous_up = missions
    previous_tick = 0
    completed_count = completed_ticks = 0
    for index, (tick, operational) in enumerate(snapshots):
        current_up = set(operational)
        if not previous_tick <= tick <= horizon or not current_up.issubset(missions):
            raise ValueError("invalid replayed mission clock or membership")
        if len(current_up) != len(operational):
            raise ValueError("duplicate replayed operational mission")
        for mission in previous_up - current_up:
            # An outage present in the initial state has an unknown onset.
            onset[mission] = None if index == 0 else tick
        for mission in current_up - previous_up:
            start = onset.pop(mission)
            spells[mission].append(_spell(start, tick, horizon))
            if start is not None:
                completed_count += 1
                completed_ticks += tick - start
        previous_up = current_up
        previous_tick = tick
    for mission, start in onset.items():
        spells[mission].append(_spell(start, None, horizon))
    return {
        "format": "pacd-mission-recovery-v1",
        "metric_id": "MIS-004",
        "clock_unit": "simulation_ticks",
        "horizon_ticks": horizon,
        "transition_model": "guarded_defensive_execution_and_rollback",
        "per_mission": [
            {"mission_id": mission, "spells": spells[mission]} for mission in sorted(missions)
        ],
        "completed_recovery_count": completed_count,
        "completed_recovery_sum_ticks": completed_ticks,
        "mean_completed_recovery_ticks": completed_ticks / completed_count
        if completed_count
        else None,
    }

"""Known and censored recovery times across ordered mission availability changes."""

import pytest

from pacd_sim.metrics.mission_impact import MissionSnapshot
from pacd_sim.metrics.mission_recovery import mission_recovery


def _expected_spell(
    observed_from: int, onset: int | None, restored: int | None, observed: int, recovery: int | None
) -> dict[str, int | None]:
    return {
        "observed_from_tick": observed_from,
        "onset_tick": onset,
        "restored_tick": restored,
        "observed_ticks": observed,
        "recovery_ticks": recovery,
    }


def test_multiple_missions_contribute_only_fully_observed_recoveries_to_mean() -> None:
    samples: list[MissionSnapshot] = [
        (0, ("a", "c")),
        (2, ("c",)),  # A goes down while B remains down from before observation.
        (3, ("b", "c")),
        (5, ("a", "c")),
        (6, ("a", "b", "c")),
        (7, ("b", "c")),
        (8, ("b", "c")),
    ]
    result = mission_recovery(("c", "b", "a"), samples, 10)
    assert result == {
        "format": "pacd-mission-recovery-v1",
        "metric_id": "MIS-004",
        "clock_unit": "simulation_ticks",
        "horizon_ticks": 10,
        "transition_model": "guarded_defensive_execution_and_rollback",
        "per_mission": [
            {
                "mission_id": "a",
                "spells": [_expected_spell(2, 2, 5, 3, 3), _expected_spell(7, 7, None, 3, None)],
            },
            {
                "mission_id": "b",
                "spells": [_expected_spell(0, None, 3, 3, None), _expected_spell(5, 5, 6, 1, 1)],
            },
            {"mission_id": "c", "spells": []},
        ],
        "completed_recovery_count": 2,
        "completed_recovery_sum_ticks": 4,
        "mean_completed_recovery_ticks": 2.0,
    }


def test_same_tick_recovery_and_horizon_outage_preserve_order() -> None:
    samples = [(0, ("a",)), (0, ()), (0, ("a",)), (5, ())]
    result = mission_recovery(["a"], samples, 5)
    assert result["per_mission"] == [
        {
            "mission_id": "a",
            "spells": [_expected_spell(0, 0, 0, 0, 0), _expected_spell(5, 5, None, 0, None)],
        }
    ]
    assert result["completed_recovery_count"] == 1
    assert result["completed_recovery_sum_ticks"] == result["mean_completed_recovery_ticks"] == 0


@pytest.mark.parametrize("horizon", [0, 4])
def test_outage_open_at_both_boundaries_and_always_available_mission(horizon: int) -> None:
    result = mission_recovery(["a", "b"], [(0, ("b",)), (horizon, ("b",))], horizon)
    assert result["per_mission"] == [
        {"mission_id": "a", "spells": [_expected_spell(0, None, None, horizon, None)]},
        {"mission_id": "b", "spells": []},
    ]
    assert result["completed_recovery_count"] == result["completed_recovery_sum_ticks"] == 0
    assert result["mean_completed_recovery_ticks"] is None


@pytest.mark.parametrize(
    ("missions", "samples"),
    [
        (["a"], []),
        (["a"], [(1, ("a",))]),
        (["a"], [(0, ("a",)), (3, ()), (2, ("a",))]),
        (["a"], [(0, ("a",)), (5, ())]),
        (["a"], [(0, ("a",)), (4, ("unknown",))]),
        (["a"], [(0, ("a", "a"))]),
        (["a", "a"], [(0, ("a",))]),
    ],
)
def test_invalid_clock_or_membership_fails_closed(
    missions: list[str], samples: list[MissionSnapshot]
) -> None:
    with pytest.raises(ValueError):
        mission_recovery(missions, samples, 4)

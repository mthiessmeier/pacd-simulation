"""Per-function availability on the governed binary mission clock."""

import pytest

from pacd_sim.metrics.mission_impact import (
    MissionSnapshot,
    critical_outage,
    function_availability,
    mission_loss,
)


def test_unequal_intervals_include_initial_loss_and_outage_open_at_horizon() -> None:
    samples = [(0, ("b", "c")), (2, ("a", "b", "c")), (4, ("a", "c"))]
    missions = ["c", "b", "a"]
    horizon = 10
    # A is initially down for two ticks, B loses its last six, and C stays up.
    result = function_availability(missions, samples, horizon)
    assert result == {
        "format": "pacd-function-availability-v1",
        "metric_id": "MIS-001",
        "clock_unit": "simulation_ticks",
        "dependency_model": "required_dependencies_v1",
        "horizon_ticks": 10,
        "per_mission": [
            {
                "mission_id": "a",
                "available_ticks": 8,
                "possible_ticks": 10,
                "availability_fraction": 0.8,
            },
            {
                "mission_id": "b",
                "available_ticks": 4,
                "possible_ticks": 10,
                "availability_fraction": 0.4,
            },
            {
                "mission_id": "c",
                "available_ticks": 10,
                "possible_ticks": 10,
                "availability_fraction": 1.0,
            },
        ],
        "available_function_ticks": 22,
        "possible_function_ticks": 30,
        "availability_fraction": 22 / 30,
    }
    # With unit weights, MIS-002 integrates the same eight missing function-ticks.
    assert mission_loss(dict.fromkeys(missions, 1.0), samples, horizon)["weighted_loss"] == 8
    for mission, down in (("a", 2), ("b", 6), ("c", 0)):
        assert (
            critical_outage(missions, [mission], samples, horizon)["outage_function_ticks"] == down
        )


def test_same_fleet_counts_preserve_distinct_function_histories() -> None:
    def availability(first_up: str, last_up: str) -> dict[str, object]:
        samples = [(0, (first_up,)), (1, ()), (1, (last_up,)), (5, (first_up,))]
        return function_availability(["a", "b"], samples, 5)

    a_first = availability("a", "b")
    b_first = availability("b", "a")
    assert a_first["availability_fraction"] == b_first["availability_fraction"] == 0.5
    for result, ticks in ((a_first, (1, 4)), (b_first, (4, 1))):
        assert result["per_mission"] == [
            {
                "mission_id": mission,
                "available_ticks": up,
                "possible_ticks": 5,
                "availability_fraction": up / 5,
            }
            for mission, up in zip(("a", "b"), ticks, strict=True)
        ]


@pytest.mark.parametrize(("horizon", "fraction"), [(0, None), (3, 0.0)])
def test_zero_exposure_and_measured_zero_remain_distinct(
    horizon: int, fraction: float | None
) -> None:
    result = function_availability(["a"], [(0, ("a",)), (0, ())], horizon)
    assert result["per_mission"] == [
        {
            "mission_id": "a",
            "available_ticks": 0,
            "possible_ticks": horizon,
            "availability_fraction": fraction,
        }
    ]
    assert result["available_function_ticks"] == 0
    assert result["possible_function_ticks"] == horizon
    assert result["availability_fraction"] == fraction


@pytest.mark.parametrize(
    ("missions", "samples", "horizon"),
    [
        ([], [(0, ())], 1),
        (["a", "a"], [(0, ())], 1),
        (["a"], [], 1),
        (["a"], [(1, ())], 1),
        (["a"], [(0, ())], -1),
        (["a"], [(0, ())], True),
        (["a"], [(0, ()), (0.5, ())], 1),
        (["a"], [(0, ()), (2, ())], 1),
        (["a"], [(0, ()), (2, ()), (1, ())], 3),
        (["a"], [(0, ()), (1, ("unknown",))], 1),
        (["a"], [(0, ("a", "a")), (0, ("a",))], 1),
    ],
)
def test_invalid_population_or_replayed_timeline_rejects_measurement(
    missions: list[str], samples: list[MissionSnapshot], horizon: int
) -> None:
    with pytest.raises(ValueError):
        function_availability(missions, samples, horizon)

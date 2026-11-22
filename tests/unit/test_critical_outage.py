"""Hand-calculated exposure and overlap for explicitly designated critical missions."""

import pytest

from pacd_sim.metrics.mission_impact import MissionSnapshot, critical_outage


def test_overlapping_outages_and_final_status_follow_the_designated_missions() -> None:
    samples = [
        (0, ("b", "d")),
        (2, ("d",)),
        (3, ("a", "d")),
        (5, ("a", "b", "d")),
        (6, ("a", "b")),
        (7, ("a",)),
    ]
    # A is down on [0, 3), B on [2, 5). C is down throughout and is undesignated.
    assert critical_outage(["d", "c", "b", "a"], ["b", "a"], samples, 7) == {
        "format": "pacd-critical-outage-v1",
        "metric_id": "MIS-003",
        "clock_unit": "simulation_ticks",
        "threshold_rule": "binary_unavailable",
        "horizon_ticks": 7,
        "per_mission": [
            {"mission_id": "a", "outage_ticks": 3, "unavailable_at_horizon": False},
            {"mission_id": "b", "outage_ticks": 3, "unavailable_at_horizon": True},
        ],
        "outage_function_ticks": 6,
        "possible_function_ticks": 14,
        "any_outage_ticks": 5,
        "any_outage_fraction": 5 / 7,
    }


def test_designation_changes_which_outage_contributes_on_the_same_timeline() -> None:
    samples = [(0, ("b",)), (2, ()), (2, ("b",))]
    for mission, expected_ticks in (("a", 5), ("b", 0)):
        measured = critical_outage(["a", "b"], [mission], samples, 5)
        assert measured["any_outage_ticks"] == measured["outage_function_ticks"] == expected_ticks
        assert measured["possible_function_ticks"] == 5
        assert measured["any_outage_fraction"] == expected_ticks / 5
        assert measured["per_mission"] == [
            {
                "mission_id": mission,
                "outage_ticks": expected_ticks,
                "unavailable_at_horizon": mission == "a",
            }
        ]


def test_zero_horizon_preserves_the_last_observed_state_without_exposure() -> None:
    measured = critical_outage(["a"], ["a"], [(0, ()), (0, ("a",)), (0, ())], 0)
    assert measured["per_mission"] == [
        {"mission_id": "a", "outage_ticks": 0, "unavailable_at_horizon": True}
    ]
    assert measured["any_outage_ticks"] == measured["outage_function_ticks"] == 0
    assert measured["possible_function_ticks"] == 0
    assert measured["any_outage_fraction"] is None


@pytest.mark.parametrize(
    ("missions", "critical", "samples", "horizon"),
    [
        (["a", "a"], ["a"], [(0, ())], 1),
        (["a"], [], [(0, ())], 1),
        (["a"], ["a", "a"], [(0, ())], 1),
        (["a"], ["unconfigured"], [(0, ())], 1),
        (["a"], ["a"], [], 1),
        (["a"], ["a"], [(1, ())], 1),
        (["a"], ["a"], [(0, ()), (2, ()), (1, ())], 3),
        (["a"], ["a"], [(0, ()), (2, ())], 1),
        (["a"], ["a"], [(0, ("unconfigured",))], 1),
        (["a"], ["a"], [(0, ("a", "a"))], 1),
    ],
)
def test_unknown_designations_and_invalid_membership_or_clock_fail_closed(
    missions: list[str], critical: list[str], samples: list[MissionSnapshot], horizon: int
) -> None:
    with pytest.raises(ValueError):
        critical_outage(missions, critical, samples, horizon)

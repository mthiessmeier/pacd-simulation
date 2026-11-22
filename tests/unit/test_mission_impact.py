"""Hand-integrated weighted mission exposures from deterministic availability snapshots."""

from fractions import Fraction

import pytest

from pacd_sim.metrics.mission_impact import MissionSnapshot, mission_loss


@pytest.mark.parametrize(
    ("weight_a", "weight_b", "expected_loss", "ratio"),
    [(0.2, 0.8, 5.2, "13/25"), (0.8, 0.2, 2.8, "7/25")],
)
def test_named_mission_weights_and_intervals(
    weight_a: float, weight_b: float, expected_loss: float, ratio: str
) -> None:
    # A starts unavailable for two ticks. B is unavailable from tick 4 through the horizon.
    samples = [(0, ("b",)), (2, ("a", "b")), (4, ("a",)), (9, ("a",))]
    measured = mission_loss({"b": weight_b, "a": weight_a}, samples, 10)
    assert measured["per_mission"] == [
        {
            "mission_id": "a",
            "criticality": weight_a,
            "unavailable_ticks": 2,
            "weighted_loss": float(Fraction(str(weight_a)) * 2),
        },
        {
            "mission_id": "b",
            "criticality": weight_b,
            "unavailable_ticks": 6,
            "weighted_loss": float(Fraction(str(weight_b)) * 6),
        },
    ]
    assert measured["weighted_loss"] == expected_loss
    assert measured["possible_weighted_ticks"] == 10
    assert measured["loss_fraction"] == float(Fraction(ratio))
    assert measured["loss_fraction_exact"] == ratio


def test_last_same_tick_state_carries_forward_and_horizon_change_has_no_duration() -> None:
    snapshots = [(0, ("a",)), (1, ()), (1, ("a",)), (4, ())]
    result = mission_loss({"a": 0.1}, snapshots, 4)
    assert result["weighted_loss"] == 0
    assert result["loss_fraction"] == 0
    assert result["loss_fraction_exact"] == "0"


@pytest.mark.parametrize(("horizon", "weight"), [(0, 0.7), (5, 0.0)])
def test_undefined_rate_preserves_measured_outage_ticks(horizon: int, weight: float) -> None:
    result = mission_loss({"a": weight}, [(0, ())], horizon)
    assert result["per_mission"] == [
        {"mission_id": "a", "criticality": weight, "unavailable_ticks": horizon, "weighted_loss": 0}
    ]
    assert result["possible_weighted_ticks"] == 0
    assert result["loss_fraction"] is result["loss_fraction_exact"] is None


def test_positive_exact_fraction_survives_display_underflow() -> None:
    result = mission_loss({"a": 5e-324, "b": 1.0}, [(0, ("b",)), (1, ("a", "b"))], 100)
    assert result["weighted_loss"] == 5e-324
    assert result["loss_fraction"] == 0.0
    assert result["loss_fraction_exact"] == str(Fraction(1, 100 * (2 * 10**323 + 1)))


@pytest.mark.parametrize(
    "snapshots", [[], [(1, ("a",))], [(0, ("unknown",))], [(0, ("a",)), (4, ())]]
)
def test_missing_coverage_or_out_of_order_clock_rejects_measurement(
    snapshots: list[MissionSnapshot],
) -> None:
    with pytest.raises(ValueError):
        mission_loss({"a": 0.5}, snapshots, 3)

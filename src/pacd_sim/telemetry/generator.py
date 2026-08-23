"""Deterministic generation of synthetic observations only."""

from collections.abc import Iterable
from typing import Self

from pydantic import model_validator

from pacd_sim.engine.scheduler import ScheduledEvent
from pacd_sim.reproducibility.canonical import create_rng
from pacd_sim.schema import ConsequentialRecord, NonNegativeFloat, Probability, StableId


class DetectorProfile(ConsequentialRecord):
    """Synthetic detector behavior used to generate bounded signals."""

    benign_signal_mean: Probability = 0.1
    adversary_signal_mean: Probability = 0.9
    unknown_signal_mean: Probability = 0.5
    noise_standard_deviation: NonNegativeFloat = 0.05


class Sensor(ConsequentialRecord):
    """Synthetic sensor metadata; it has no live ingestion capability."""

    detector_profile_id: StableId
    coverage: Probability = 1.0
    delay_ticks: int = 0
    enabled: bool = True

    @model_validator(mode="after")
    def _validate_delay(self) -> Self:
        if self.delay_ticks < 0:
            raise ValueError("delay_ticks must be non-negative")
        return self


class Observation(ConsequentialRecord):
    """One noisy observation derived from an authorized synthetic event."""

    event_id: StableId
    event_tick: int
    event_kind: StableId
    sensor_id: StableId
    identity_id: StableId | None = None
    target_id: StableId | None = None
    signal: Probability
    integrity: Probability = 1.0

    @model_validator(mode="after")
    def _validate_ticks(self) -> Self:
        if self.event_tick < 0:
            raise ValueError("event_tick must be non-negative")
        if self.tick < self.event_tick:
            raise ValueError("observation tick cannot precede its event")
        return self


class SyntheticTelemetryGenerator:
    """Order-independent telemetry generator backed by component-local NumPy RNGs."""

    def __init__(self, run_seed: int, sensor: Sensor, profile: DetectorProfile) -> None:
        if sensor.detector_profile_id != profile.id:
            raise ValueError("sensor and detector profile IDs do not match")
        self._run_seed = run_seed
        self._sensor = sensor
        self._profile = profile

    @property
    def sensor(self) -> Sensor:
        return self._sensor

    def generate(self, event: ScheduledEvent) -> Observation | None:
        """Generate at most one observation for an event, using no ambient RNG state."""

        if not self._sensor.enabled:
            return None
        rng = create_rng(
            self._run_seed,
            f"telemetry/{self._sensor.id}/{event.id}",
        )
        if float(rng.random()) > self._sensor.coverage:
            return None
        if event.kind == "benign_administrative":
            mean = self._profile.benign_signal_mean
        elif event.kind == "simulated_adversary":
            mean = self._profile.adversary_signal_mean
        else:
            mean = self._profile.unknown_signal_mean
        noisy_signal = float(rng.normal(mean, self._profile.noise_standard_deviation))
        signal = min(1.0, max(0.0, noisy_signal))
        observed_tick = event.tick + self._sensor.delay_ticks
        return Observation(
            id=f"observation-{self._sensor.id}-{event.id}",
            tick=observed_tick,
            configuration_version=event.configuration_version,
            event_id=event.id,
            event_tick=event.tick,
            event_kind=event.kind,
            sensor_id=self._sensor.id,
            identity_id=event.identity_id,
            target_id=event.target_id,
            signal=signal,
        )

    def generate_many(self, events: Iterable[ScheduledEvent]) -> tuple[Observation, ...]:
        """Generate observations in stable event order."""

        observations = (
            observation
            for event in sorted(events, key=lambda item: (item.tick, item.priority, item.id))
            if (observation := self.generate(event)) is not None
        )
        return tuple(sorted(observations, key=lambda item: (item.tick, item.id)))

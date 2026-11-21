"""Wire schemas for the five version 1.0 bootstrap diagnostic inputs."""

from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, model_validator

from pacd_sim.actions.models import RequestedAuthority
from pacd_sim.schema import (
    DiagnosticRecord,
    Probability,
    Signed64Count,
    StableId,
    StrictFrozenModel,
)


def _freeze_array(value: object) -> object:
    """JSON and YAML arrays become immutable tuples without coercing their elements."""
    return tuple(value) if isinstance(value, list) else value


def _require_bool(value: object) -> object:
    # Literal[True/False] alone accepts the equal integers 1/0 in Pydantic.
    if not isinstance(value, bool):
        raise ValueError("expected a boolean")
    return value


type Array[T] = Annotated[tuple[T, ...], BeforeValidator(_freeze_array)]
type NonemptyArray[T] = Annotated[
    tuple[T, ...], Field(min_length=1), BeforeValidator(_freeze_array)
]
type BoundedArray[T] = Annotated[
    tuple[T, ...], Field(min_length=1, max_length=100), BeforeValidator(_freeze_array)
]
type NonemptyText = Annotated[str, Field(min_length=1)]
type Enabled = Annotated[Literal[True], BeforeValidator(_require_bool)]
type Disabled = Annotated[Literal[False], BeforeValidator(_require_bool)]


class TelemetryConfig(StrictFrozenModel):
    noise_standard_deviation: Probability
    delay_ticks: Annotated[int, Field(ge=0, le=100)]


class IdentityConfig(StrictFrozenModel):
    id: StableId
    role: StableId


class SessionConfig(StrictFrozenModel):
    id: StableId
    identity_id: StableId
    service_id: StableId


class ServiceConfig(StrictFrozenModel):
    id: StableId
    mission_id: StableId


class MissionConfig(StrictFrozenModel):
    id: StableId
    criticality: Probability


class EventConfig(StrictFrozenModel):
    id: StableId
    tick: Annotated[int, Field(ge=0, le=10_000)]
    kind: StableId
    identity_id: StableId | None


class ActionConfig(StrictFrozenModel):
    id: StableId
    action_type: StableId
    target_id: StableId
    reversible: bool
    requested_authority: RequestedAuthority


class ScenarioConfig(DiagnosticRecord):
    protocol_version: NonemptyText
    name: NonemptyText
    synthetic: Enabled
    default_seed: Signed64Count
    telemetry: TelemetryConfig
    identities: NonemptyArray[IdentityConfig]
    sessions: NonemptyArray[SessionConfig]
    services: NonemptyArray[ServiceConfig]
    missions: NonemptyArray[MissionConfig]
    events: BoundedArray[EventConfig]
    actions: BoundedArray[ActionConfig]


class PolicyConfig(DiagnosticRecord):
    allowed_action_types: Array[StableId]
    escalated_action_types: Array[StableId]
    prohibited_action_types: Array[StableId]
    execution_adapter: Literal["simulated_only"]
    network_enabled: Disabled


class BaselineConfig(DiagnosticRecord):
    name: NonemptyText
    observations: Literal["synthetic_only"]
    actions: Literal["none"]


class MetricConfig(DiagnosticRecord):
    metrics: Array[Literal["event_count", "approved_action_count", "prohibited_action_count"]]
    comparative_claims: Disabled

    @model_validator(mode="after")
    def _complete_set(self) -> Self:
        if len(self.metrics) != 3 or len(set(self.metrics)) != 3:
            raise ValueError("diagnostic metrics must list each governed metric exactly once")
        return self


class SeedRegistryConfig(DiagnosticRecord):
    seeds: BoundedArray[Signed64Count]

    @model_validator(mode="after")
    def _unique_seeds(self) -> Self:
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("diagnostic seeds must be unique")
        return self


class DiagnosticInputs(StrictFrozenModel):
    """The loader validates wire types here before checking cross-component semantics."""

    scenario: ScenarioConfig
    policy: PolicyConfig
    seeds: SeedRegistryConfig
    baseline: BaselineConfig
    metrics: MetricConfig

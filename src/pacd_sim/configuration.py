"""Wire schemas for the five version 1.0 bootstrap diagnostic inputs."""

from sys import float_info
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from pacd_sim.actions.models import RequestedAuthority
from pacd_sim.schema import (
    STABLE_ID_MAX_LENGTH,
    DiagnosticRecord,
    NonemptyText,
    NonNegativeFloat,
    Probability,
    Signed64Count,
    StableId,
    StrictFrozenModel,
    validate_audit_text,
)

_MAX_INTEGER_WEIGHT = int(float_info.max)


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
type Enabled = Annotated[Literal[True], BeforeValidator(_require_bool)]
type Disabled = Annotated[Literal[False], BeforeValidator(_require_bool)]
type AuditId = Annotated[StableId, AfterValidator(validate_audit_text)]


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


class DependencyConfig(StrictFrozenModel):
    """One directed relationship among the scenario's synthetic entities."""

    id: StableId
    upstream_id: StableId
    downstream_id: StableId
    # Keep integer wire values intact for the configuration digest. State uses finite floats.
    weight: Annotated[int, Field(ge=0, le=_MAX_INTEGER_WEIGHT)] | NonNegativeFloat

    @field_validator("weight", mode="before")
    @classmethod
    def _require_exact_integer_weight(cls, value: object) -> object:
        # Test the source integer before the union can round it through its float branch.
        if isinstance(value, int) and not (
            0 <= value <= _MAX_INTEGER_WEIGHT and float(value) == value
        ):
            raise ValueError("integer weight must be exactly representable as a nonnegative float")
        return value


type DependencyRows = Annotated[
    tuple[DependencyConfig, ...], Field(max_length=100), BeforeValidator(_freeze_array)
]


class EventConfig(StrictFrozenModel):
    # The full-coverage v1 harness creates a context for every observation.
    id: Annotated[
        StableId,
        Field(
            max_length=STABLE_ID_MAX_LENGTH
            - len("defender-context-observation-sensor-synthetic-diagnostic-")
        ),
    ]
    tick: Annotated[int, Field(ge=0, le=10_000)]
    kind: StableId
    # Each observed subject gets both the benign and compromise hypotheses.
    identity_id: (
        Annotated[AuditId, Field(max_length=STABLE_ID_MAX_LENGTH - len("hypothesis--compromise"))]
        | None
    )


class ActionConfig(StrictFrozenModel):
    id: Annotated[AuditId, Field(max_length=STABLE_ID_MAX_LENGTH - len("policy-decision-"))]
    action_type: StableId
    target_id: AuditId
    reversible: bool
    requested_authority: RequestedAuthority


type ReviewOverridePolicy = Literal["retain_approval", "veto_approval"]


class GuardedReviewConfig(StrictFrozenModel):
    """Evaluator-owned timing, review response and matched sensor settings."""

    capacity: Annotated[int, Field(ge=0, le=100)]
    delay_ticks: Annotated[int, Field(ge=0, le=10_000)]
    validity_ticks: Annotated[int, Field(ge=0, le=10_000)]
    end_tick: Annotated[int, Field(ge=0, le=20_000)]
    response: Literal["approve", "deny", "no_response"]
    rollback: bool
    matched_signal_mean: Probability
    decision_brief: Literal["operator-preview-v1"] | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )
    override_policy: ReviewOverridePolicy | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )

    @field_validator("decision_brief", "override_policy", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            raise ValueError(f"explicit null is invalid for {info.field_name}")
        return value


class SensingOperatorConfig(StrictFrozenModel):
    """Governed costs and passive observer assumptions for one sensing opportunity."""

    switch_cost: Probability
    budget: Probability
    detectability: Probability


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
    critical_mission_ids: NonemptyArray[StableId] | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )
    # An omitted field has no wire representation. An explicit empty array is retained.
    dependencies: DependencyRows | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )
    availability_model: Literal["required_dependencies_v1"] | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )
    events: BoundedArray[EventConfig]
    actions: Annotated[
        tuple[ActionConfig, ...], Field(max_length=100), BeforeValidator(_freeze_array)
    ]
    guarded_review: GuardedReviewConfig | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )
    sensing_operator: SensingOperatorConfig | SkipJsonSchema[None] = Field(
        default_factory=lambda: None, validate_default=False, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _unique_event_ids(self) -> Self:
        if len({event.id for event in self.events}) != len(self.events):
            raise ValueError("diagnostic event IDs must be unique")
        return self

    @model_validator(mode="after")
    def _validate_review_scenario(self) -> Self:
        if self.guarded_review is None:
            if self.critical_mission_ids is not None:
                raise ValueError("critical mission designation requires guarded review")
            if self.sensing_operator is not None:
                raise ValueError("sensing operator requires guarded review")
            if not self.actions:
                raise ValueError("legacy diagnostics require configured actions")
            return self
        if self.actions:
            raise ValueError("guarded review requires an empty list of scripted actions")
        if self.availability_model is None:
            raise ValueError("guarded review requires a mission availability model")
        if self.critical_mission_ids is not None:
            selected = set(self.critical_mission_ids)
            if len(selected) != len(self.critical_mission_ids):
                raise ValueError("critical mission IDs must be unique")
            if not selected.issubset(mission.id for mission in self.missions):
                raise ValueError("critical mission IDs must name configured missions")
        if any(
            event.tick + self.telemetry.delay_ticks > self.guarded_review.end_tick
            for event in self.events
        ):
            raise ValueError("all guarded observations must arrive by end_tick")
        return self

    @field_validator(
        "dependencies",
        "availability_model",
        "guarded_review",
        "sensing_operator",
        "critical_mission_ids",
        mode="before",
    )
    @classmethod
    def _reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("explicit null is invalid for this optional scenario field")
        return value


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

    @field_validator("name")
    @classmethod
    def _reserve_review_policy_names(cls, value: str) -> str:
        if value in {
            "static_signal_review_v1",
            "pacd_corroborated_review_v1",
            "sensing_fixed_v1",
            "sensing_adaptive_v1",
            "sensing_disabled_v1",
            "sensing_contextual_v1",
            "sensing_scheduled_v1",
        }:
            raise ValueError(f"{value} requires the human-review action")
        return value


class StaticReviewBaselineConfig(DiagnosticRecord):
    name: Literal["static_signal_review_v1"]
    observations: Literal["synthetic_only"]
    actions: Literal["require_human_review"]


class CorroboratedReviewConfig(DiagnosticRecord):
    name: Literal["pacd_corroborated_review_v1"]
    observations: Literal["synthetic_only"]
    actions: Literal["require_human_review"]


class SensingReviewConfig(DiagnosticRecord):
    name: Literal[
        "sensing_fixed_v1",
        "sensing_adaptive_v1",
        "sensing_disabled_v1",
        "sensing_contextual_v1",
        "sensing_scheduled_v1",
    ]
    observations: Literal["synthetic_only"]
    actions: Literal["require_human_review"]


type ReviewConfig = Annotated[
    StaticReviewBaselineConfig | CorroboratedReviewConfig | SensingReviewConfig,
    Field(discriminator="name"),
]


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
    baseline: Annotated[BaselineConfig | ReviewConfig, Field(discriminator="actions")]
    metrics: MetricConfig

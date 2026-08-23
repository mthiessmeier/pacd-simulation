"""Shared strict schema primitives for the bounded PACD simulator."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pacd_sim.constants import DEFAULT_PROTOCOL_VERSION, SCHEMA_VERSION

type StableId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=256),
]
type NonNegativeTick = Annotated[int, Field(ge=0)]
type Probability = Annotated[float, Field(ge=0.0, le=1.0)]
type NonNegativeFloat = Annotated[float, Field(ge=0.0)]
type SyntheticSource = Literal["synthetic"]


class StrictFrozenModel(BaseModel):
    """Base for immutable records that reject unknown or coerced fields."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )


class SyntheticRecord(StrictFrozenModel):
    """Common provenance carried by simulation-only records."""

    schema_version: str = SCHEMA_VERSION
    configuration_version: str = DEFAULT_PROTOCOL_VERSION
    source: SyntheticSource = "synthetic"
    tick: NonNegativeTick = 0


class ConsequentialRecord(SyntheticRecord):
    """A simulation record with a stable identifier."""

    id: StableId


class AuthorityLevel(StrEnum):
    """Authority requested by a candidate action."""

    AUTOMATIC = "automatic"
    HUMAN = "human"
    PROHIBITED = "prohibited"


class PolicyDisposition(StrEnum):
    """Fail-closed decisions used by the bootstrap safety governor."""

    APPROVE = "APPROVE"
    ESCALATE = "ESCALATE"
    PROHIBIT = "PROHIBIT"


class ApprovalDisposition(StrEnum):
    """Outcome of simulated human review."""

    APPROVED = "APPROVED"
    DENIED = "DENIED"


class ExecutionDisposition(StrEnum):
    """Outcome of a simulated broker request."""

    EXECUTED = "EXECUTED"
    NOT_EXECUTED = "NOT_EXECUTED"


class VerificationDisposition(StrEnum):
    """Independent verification outcome."""

    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RollbackDisposition(StrEnum):
    """Outcome of a simulated rollback."""

    ROLLED_BACK = "ROLLED_BACK"
    NOT_ROLLED_BACK = "NOT_ROLLED_BACK"

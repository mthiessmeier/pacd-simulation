"""Shared strict schema primitives for the bounded PACD simulator."""

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pacd_sim.constants import DEFAULT_PROTOCOL_VERSION, SCHEMA_VERSION

STABLE_ID_MAX_LENGTH: Final = 256

type StableId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=STABLE_ID_MAX_LENGTH),
]
type NonNegativeTick = Annotated[int, Field(ge=0)]
type NonemptyText = Annotated[str, Field(min_length=1)]
type Probability = Annotated[float, Field(ge=0.0, le=1.0)]
type NonNegativeFloat = Annotated[float, Field(ge=0.0)]
type SyntheticSource = Literal["synthetic"]
type Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", max_length=64)]
type Signed64Count = Annotated[int, Field(ge=0, lt=2**63)]


def validate_audit_text(value: str) -> str:
    """Apply the raw audit row's UTF-8 bound to a scalar field."""
    if len(value.encode("utf-8")) > 500:
        raise ValueError("Audit identifiers and outcomes are limited to 500 UTF-8 bytes")
    return value


class StrictFrozenModel(BaseModel):
    """Base for immutable records that reject unknown or coerced fields."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        allow_inf_nan=False,
    )


class DiagnosticRecord(StrictFrozenModel):
    """Provenance shared by the existing v1 diagnostic wire records."""

    evidence_label: Literal["NON_REPORTABLE_DIAGNOSTIC"]
    schema_version: Literal["1.0"]


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

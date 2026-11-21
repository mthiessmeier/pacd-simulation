"""Evaluator-owned, ordered development comparison plans."""

from collections.abc import Mapping
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from pacd_sim.configuration import BoundedArray
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import Sha256Digest, Signed64Count, StrictFrozenModel

type PlanId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]


class RegisteredAttempt(StrictFrozenModel):
    attempt_id: PlanId
    invocation_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    seed: Signed64Count


class ComparisonInputs(StrictFrozenModel):
    scenario: PlanId
    condition: PlanId
    code_commit: Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
    config_sha256: Sha256Digest
    seed_registry_sha256: Sha256Digest
    events_sha256: Sha256Digest

    @classmethod
    def from_inputs(
        cls, config: Mapping[str, object], seed_registry: object, code_commit: str
    ) -> Self:
        """Identify actual governed input content, including the ordered exogenous script."""
        scenario = config["scenario"]
        baseline = config["baseline_definition"]
        if not isinstance(scenario, Mapping) or not isinstance(baseline, Mapping):
            raise ValueError("Missing governed scenario or condition")
        return cls(
            scenario=scenario["name"],
            condition=baseline["name"],
            code_commit=code_commit,
            config_sha256=canonical_sha256(config),
            seed_registry_sha256=canonical_sha256(seed_registry),
            events_sha256=canonical_sha256(scenario["events"]),
        )


class PlannedAttempt(RegisteredAttempt):
    cell_id: PlanId
    comparison_mode: Literal["controlled", "system_level"]
    expected: ComparisonInputs


def validate_attempt_ids(attempts: tuple[RegisteredAttempt, ...]) -> None:
    if len({a.attempt_id for a in attempts}) != len(attempts):
        raise ValueError("Duplicate attempt ID in register")
    if len({a.invocation_id for a in attempts}) != len(attempts):
        raise ValueError("Duplicate invocation ID in register")


class ComparisonPlan(StrictFrozenModel):
    format: Literal["pacd-development-comparison-plan-v1"]
    evidence_label: Literal["NON_REPORTABLE_DIAGNOSTIC"]
    attempts: BoundedArray[PlannedAttempt]

    @model_validator(mode="after")
    def _consistent_cells(self) -> Self:
        validate_attempt_ids(self.attempts)
        cells: dict[str, tuple[str, ComparisonInputs, int]] = {}
        for attempt in self.attempts:
            binding = (attempt.comparison_mode, attempt.expected, attempt.seed)
            if cells.setdefault(attempt.cell_id, binding) != binding:
                raise ValueError("Retries for a cell must preserve mode, inputs and seed")
        return self

    def select(self, invocation_id: str | None) -> PlannedAttempt:
        for attempt in self.attempts:
            if attempt.invocation_id == invocation_id:
                return attempt
        raise ValueError("Planned launch requires an invocation ID declared in the plan")

"""Read-only accounting for a declared set of local diagnostic invocations."""

from __future__ import annotations

import os
import re
import stat
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from pacd_sim.configuration import BoundedArray
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.metrics.dispositions import EpisodeDispositions, episode_dispositions, fraction
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.evidence_validation import strict_json_loads
from pacd_sim.reproducibility.manifest import RunManifest
from pacd_sim.reproducibility.paths import (
    assert_direct_workspace_path,
    assert_exact_control_path,
    path_has_symlink_or_reparse,
)
from pacd_sim.reproducibility.receipts import (
    read_ownership_marker,
    read_stable_bytes,
    receipt_path_for,
)
from pacd_sim.reproducibility.verify import verify_run_with_summary
from pacd_sim.schema import Signed64Count, StrictFrozenModel


class RegisteredAttempt(StrictFrozenModel):
    attempt_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
    invocation_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    seed: Signed64Count


class AttemptRegister(StrictFrozenModel):
    format: Literal["pacd-attempt-register-v1"]
    attempts: BoundedArray[RegisteredAttempt]

    @model_validator(mode="after")
    def _unique_attempts(self) -> Self:
        if len({a.attempt_id for a in self.attempts}) != len(self.attempts):
            raise ValueError("Duplicate attempt ID in register")
        if len({a.invocation_id for a in self.attempts}) != len(self.attempts):
            raise ValueError("Duplicate invocation ID in register")
        return self


@dataclass(frozen=True)
class Outcome:
    status: Literal["COMPLETED", "FAILED", "TIMED_OUT", "INCOMPLETE", "INVALID"]
    reason: str
    run_id: str | None = None
    metrics: EpisodeDispositions | None = None


def _direct_stat(path: Path) -> os.stat_result | None:
    if path_has_symlink_or_reparse(path):
        raise ValueError("Indirect evidence path")
    try:
        return path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None


@dataclass(frozen=True)
class OwnedRun:
    run_id: str
    final: Path
    staging: Path
    identity: tuple[int, int]


def _owned_run(attempt: RegisteredAttempt, workspace: Path, marker: dict[str, object]) -> OwnedRun:
    started = marker["created_at"]
    if not isinstance(started, str):
        raise ValueError("Invalid ownership timestamp")
    created = datetime.fromisoformat(started)
    if created.tzinfo != UTC or created.isoformat() != started:
        raise ValueError("Noncanonical ownership timestamp")
    stamp = created.strftime("%Y%m%dT%H%M%S.%fZ")
    run_id = f"diagnostic-{stamp}-seed-{attempt.seed}-{attempt.invocation_id}"
    final = workspace / "var/runs" / run_id
    staging = workspace / "var/tmp" / f"{run_id}.staging"
    expected = {
        "invocation_id": attempt.invocation_id,
        "seed": attempt.seed,
        "run_id": run_id,
        "final_run_path": str(final),
        "staging_path": str(staging),
        "schema_version": SCHEMA_VERSION,
        "ownership_version": "1.0",
        "evidence_label": EVIDENCE_LABEL,
    }
    if type(marker["seed"]) is not int or any(marker[k] != v for k, v in expected.items()):
        raise ValueError("Ownership marker does not bind the registered attempt")
    for key in ("capability_sha256", "receipt_capability_sha256"):
        value = marker[key]
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("Invalid ownership digest")
    device, inode = marker["staging_device"], marker["staging_inode"]
    if type(device) is not int or type(inode) is not int:
        raise ValueError("Invalid owned directory identity")
    return OwnedRun(run_id, final, staging, (device, inode))


def _directory_present(path: Path, identity: tuple[int, int]) -> bool:
    info = _direct_stat(path)
    if info is None:
        return False
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity:
        raise ValueError("Owned directory identity mismatch")
    return True


def _retained_object(path: Path, limit: int) -> dict[str, object]:
    data = read_stable_bytes(path, max_bytes=limit)
    value = strict_json_loads(data.decode("utf-8"), source=path.name)
    if not isinstance(value, dict) or canonical_json_bytes(value) != data:
        raise ValueError("Invalid retained JSON object")
    return value


def _final_outcome(
    run: OwnedRun, attempt: RegisteredAttempt, receipt: bool, workspace: Path, repo: Path
) -> Outcome:
    if receipt:
        verified, summary = verify_run_with_summary(run.final, workspace, repo_root=repo)
        if verified.valid and summary is not None and summary.episode.seed == attempt.seed:
            return Outcome(
                "COMPLETED",
                "verified_completion",
                run.run_id,
                episode_dispositions(summary.episode),
            )
        return Outcome("INVALID", "completion_verification_failed", run.run_id)

    status_path = run.final / "status.json"
    manifest_path = run.final / "manifest.json"
    if _direct_stat(status_path) is None:
        if _direct_stat(manifest_path) is not None:
            return Outcome("INVALID", "manifest_without_status", run.run_id)
        return Outcome("INCOMPLETE", "no_terminal_status", run.run_id)
    status = _retained_object(status_path, 65536)
    if status.get("completion_status") == "COMPLETED":
        return Outcome("INVALID", "completion_without_receipt", run.run_id)
    expected = {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "reportable": False,
        "seed": attempt.seed,
        "completion_status": "FAILED",
    }
    error = status.get("error_type")
    if (
        status.keys() != expected.keys() | {"error_type"}
        or status["reportable"] is not False
        or type(status["seed"]) is not int
        or any(status[k] != v for k, v in expected.items())
        or not isinstance(error, str)
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", error) is None
    ):
        return Outcome("INVALID", "invalid_failure_status", run.run_id)
    if _direct_stat(manifest_path) is not None:
        manifest = RunManifest.model_validate(_retained_object(manifest_path, 4 * 1024**2))
        if (
            manifest.run_id != run.run_id
            or manifest.seed != attempt.seed
            or manifest.completion_status != "FAILED"
            or manifest.failure_type != error
        ):
            return Outcome("INVALID", "conflicting_failure_manifest", run.run_id)
    kind: Literal["TIMED_OUT", "FAILED"] = (
        "TIMED_OUT" if error == "DiagnosticTimeoutError" else "FAILED"
    )
    return Outcome(kind, error, run.run_id)


def _observe(attempt: RegisteredAttempt, workspace: Path, repo: Path) -> Outcome:
    key = attempt.invocation_id
    marker_path = assert_exact_control_path(
        workspace / "var/invocations" / key / "ownership.json",
        workspace,
        "invocations",
        key,
        "ownership.json",
    )
    receipt_path = receipt_path_for(workspace, key)
    receipt = _direct_stat(receipt_path) is not None
    if _direct_stat(marker_path) is None:
        if receipt:
            return Outcome("INVALID", "receipt_without_ownership")
        if _direct_stat(marker_path.parent) is not None:
            return Outcome("INCOMPLETE", "allocation_without_marker")
        return Outcome("INCOMPLETE", "no_registered_invocation_observed")

    marker, digest = read_ownership_marker(workspace, key)
    run = _owned_run(attempt, workspace, marker)
    try:
        final = _directory_present(run.final, run.identity)
        staging = _directory_present(run.staging, run.identity)
        if final and not staging:
            outcome = _final_outcome(run, attempt, receipt, workspace, repo)
        elif receipt or final:
            outcome = Outcome("INVALID", "conflicting_run_locations", run.run_id)
        else:
            reason = "staging_only" if staging else "owned_directory_missing"
            outcome = Outcome("INCOMPLETE", reason, run.run_id)
        if (
            read_ownership_marker(workspace, key)[1] != digest
            or (_direct_stat(receipt_path) is not None) != receipt
            or _directory_present(run.final, run.identity) != final
            or _directory_present(run.staging, run.identity) != staging
        ):
            return Outcome("INVALID", "evidence_changed_during_read", run.run_id)
        return outcome
    except (OSError, ValueError, RecursionError):
        return Outcome("INVALID", "invalid_retained_evidence", run.run_id)


def registered_metrics(
    path: Path, workspace: Path, repo: Path, expected_digest: str | None
) -> dict[str, object]:
    """Account for each declared attempt once, releasing counts only for verified completions."""
    path = assert_direct_workspace_path(path, workspace)
    encoded = read_stable_bytes(path, max_bytes=65536)
    register = AttemptRegister.model_validate(
        strict_json_loads(encoded.decode("utf-8"), source="attempt register")
    )
    digest = canonical_sha256(register)
    if expected_digest is not None and expected_digest != digest:
        raise ValueError("Register does not match the pinned SHA-256")
    status_counts = dict.fromkeys(("COMPLETED", "FAILED", "TIMED_OUT", "INCOMPLETE", "INVALID"), 0)
    counts: Counter[str] = Counter()
    rows = []
    for attempt in register.attempts:
        try:
            outcome = _observe(attempt, workspace, repo)
        except (OSError, ValueError, RecursionError):
            outcome = Outcome("INVALID", "invalid_invocation_evidence")
        status_counts[outcome.status] += 1
        metric = outcome.metrics
        if metric is not None:
            counts.update(metric["counts"])
        rows.append(
            {
                **attempt.model_dump(),
                **asdict(outcome),
                "metrics_sha256": canonical_sha256(metric) if metric is not None else None,
            }
        )
    completed = status_counts["COMPLETED"]
    report = {
        "format": "pacd-registered-metrics-v1",
        "evidence_label": EVIDENCE_LABEL,
        "reportable": False,
        "register_sha256": digest,
        "attempts": rows,
        "status_counts": status_counts,
        "completion_fraction": fraction(completed, len(rows), "fraction_of_registered_attempts"),
        "observed_counts": dict(counts) if completed else None,
        "observed_escalation_fraction": fraction(
            counts["escalated_action_count"],
            counts["candidate_action_count"],
            "fraction_of_candidate_actions",
        ),
    }
    return {**report, "report_sha256": canonical_sha256(report)}

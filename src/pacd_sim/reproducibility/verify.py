"""Read-only verification of a retained PACD diagnostic run directory."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import cast

from pacd_sim.comparison import ComparisonInputs
from pacd_sim.configuration import EventConfig, ScenarioConfig
from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.defenders.base import BaselineObservation
from pacd_sim.defenders.pacd import corroboration
from pacd_sim.evidence.context import EvidenceReading
from pacd_sim.metrics.dispositions import guarded_review_metrics
from pacd_sim.metrics.review_routing import guarded_review_projections
from pacd_sim.metrics.sensing_freshness import sensing_freshness_metrics
from pacd_sim.metrics.summarize import EpisodeRecord, summary_from_raw_table
from pacd_sim.polymorphism.selection import CONTEXTUAL, SCHEDULED
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.evidence_validation import (
    strict_json_loads,
    validate_retained_evidence,
)
from pacd_sim.reproducibility.manifest import (
    semantic_events_hash,
    semantic_summary_hash,
)
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_existing_run_directory,
    is_symlink_or_reparse,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
)
from pacd_sim.reproducibility.receipts import (
    HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED,
    IDENTITY_ASSURANCE_SCOPE,
    verify_execution_receipt,
)

_REQUIRED_ARTIFACTS = (
    "NON_REPORTABLE_DIAGNOSTIC",
    "SHA256SUMS.txt",
    "canonical_config.json",
    "derived/episode_summary.csv",
    "derived/episode_summary.parquet",
    "logs/run.log",
    "manifest.json",
    "raw/events.jsonl",
    "raw/events.parquet",
    "seed_registry.json",
    "status.json",
)
_DIGEST_LINE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)$")
MAX_RUN_OUTPUT_BYTES = 2 * 1024**3


def _artifact_size(path: Path) -> int:
    """Return one artifact size; isolated for bounded hermetic budget tests."""
    return path.stat(follow_symlinks=False).st_size


def _aggregate_run_size(root: Path, errors: list[str]) -> tuple[int, set[str]]:
    total = 0
    regular_files: set[str] = set()
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_root)
        for directory_name in tuple(directory_names):
            directory = current / directory_name
            if is_symlink_or_reparse(directory):
                errors.append(f"Symlink or reparse-point directory is prohibited: {directory_name}")
                directory_names.remove(directory_name)
        for file_name in file_names:
            artifact = current / file_name
            if is_symlink_or_reparse(artifact):
                errors.append(f"Symlink or reparse-point artifact is prohibited: {file_name}")
                continue
            try:
                total += _artifact_size(artifact)
                regular_files.add(artifact.relative_to(root).as_posix())
            except OSError as error:
                errors.append(f"Could not establish artifact size for {file_name}: {error}")
    return total, regular_files


@dataclass(frozen=True)
class VerificationResult:
    """Structured result of complete run-artifact verification.

    Execution identity is a cooperative binding of current local content,
    lexical paths, run identity, and configuration. It does not assert
    historical control-file inode continuity or reportable provenance.
    """

    run_dir: Path
    valid: bool
    errors: tuple[str, ...]
    checked_files: tuple[str, ...]
    raw_semantic_hash: str | None
    summary_semantic_hash: str | None
    semantic_content_valid: bool = False
    execution_identity_assured: bool = False
    identity_assurance_scope: str = IDENTITY_ASSURANCE_SCOPE
    historical_control_file_inode_continuity_assured: bool = (
        HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED
    )
    reportable: bool = False
    receipt_path: Path | None = None
    evidence_label: str = EVIDENCE_LABEL
    event_sequence: tuple[EventConfig, ...] | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready result with a string path."""
        value = {
            field.name: getattr(self, field.name)
            for field in fields(self)
            if field.name != "event_sequence"
        }
        value["run_dir"] = str(self.run_dir)
        value["receipt_path"] = str(self.receipt_path) if self.receipt_path is not None else None
        if self.event_sequence is not None:
            events = [
                event.model_dump(mode="json", include={"id", "tick", "kind", "identity_id"})
                for event in self.event_sequence
            ]
            sequence = {"format": "pacd-scripted-events-v1", "events": events}
            value["event_sequence"] = {
                **sequence,
                "event_count": len(events),
                "sha256": canonical_sha256(sequence),
            }
        return value


@dataclass(frozen=True)
class VerifiedSummary:
    """Raw-derived summary and optional sensor observations from the same verified snapshot."""

    episode: EpisodeRecord
    csv_sha256: str
    parquet_sha256: str
    observations: tuple[BaselineObservation, ...] = ()
    comparison_inputs: ComparisonInputs | None = None
    guarded_review: dict[str, object] | None = None
    evidence_readings: tuple[EvidenceReading, ...] = ()


def _delivered_reading(row: dict[str, object], signal: float) -> BaselineObservation:
    # A literal subject with the v1 missing-subject spelling also abstains.
    subject = cast(str, row["entity_id"])
    return BaselineObservation(
        tick=int(cast(float, row["tick"])),
        subject_id=None if subject == "synthetic-unknown" else subject,
        signal=signal,
    )


def _verified_evidence_readings(
    raw_rows: tuple[dict[str, object], ...], scenario: ScenarioConfig
) -> tuple[EvidenceReading, ...]:
    """Project authenticated delivery rows and source ticks into an episode-local view."""
    measured_ticks = {event.id: event.tick for event in scenario.events}
    sources: dict[str, int] = {}
    observations: dict[tuple[str, str], int] = {}
    readings = []
    for row in raw_rows:
        if row["event_type"] != "observation":
            continue
        payload = json.loads(cast(str, row["payload_json"]))
        reading = _delivered_reading(row, payload["signal"])
        sensor_id, event_id = payload["sensor_id"], payload["event_id"]
        # A v1 sensor generates one observation per event. Their identifiers
        # can contain scenario labels, so only their equality is exposed.
        key = observations.setdefault((sensor_id, event_id), len(observations) + 1)
        source = sources.setdefault(sensor_id, len(sources) + 1)
        readings.append(
            EvidenceReading(
                observation_key=key,
                source_key=source,
                subject_id=reading.subject_id,
                measured_tick=measured_ticks[event_id],
                delivered_tick=reading.tick,
                signal=reading.signal,
            )
        )
    return tuple(readings)


@dataclass(frozen=True)
class _ArtifactSnapshot:
    path: Path
    device: int
    inode: int
    size: int
    mtime_ns: int
    link_count: int
    sha256: str

    def identity(self) -> tuple[int, int, int, int, int]:
        return (self.device, self.inode, self.size, self.mtime_ns, self.link_count)


def _stable_artifact_snapshot(path: Path) -> _ArtifactSnapshot:
    """Stream one artifact through a stable, singly linked regular-file handle."""

    if path_has_symlink_or_reparse(path):
        raise ValueError(f"Artifact path is indirect: {path.name}")
    before = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > MAX_RUN_OUTPUT_BYTES
    ):
        raise ValueError(f"Artifact is not a bounded singly linked file: {path.name}")
    expected_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if expected_identity != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        ):
            raise ValueError(f"Opened artifact identity differs from its path: {path.name}")
        while chunk := handle.read(1024 * 1024):
            total += len(chunk)
            if total > before.st_size:
                raise ValueError(f"Artifact grew during stable hashing: {path.name}")
            digest.update(chunk)
        opened_after = os.fstat(handle.fileno())
    after = path.stat(follow_symlinks=False)
    if (
        total != before.st_size
        or expected_identity
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
        or expected_identity
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
    ):
        raise ValueError(f"Artifact changed during stable hashing: {path.name}")
    return _ArtifactSnapshot(
        path=path,
        device=before.st_dev,
        inode=before.st_ino,
        size=before.st_size,
        mtime_ns=before.st_mtime_ns,
        link_count=before.st_nlink,
        sha256=digest.hexdigest(),
    )


def _cached_artifact_snapshot(
    path: Path,
    *,
    device: int,
    inode: int,
    size: int,
    mtime_ns: int,
    link_count: int,
    digest: str,
) -> _ArtifactSnapshot:
    """Convert one bounded-ingestion identity without reopening its path."""

    snapshot = _ArtifactSnapshot(
        path=path,
        device=device,
        inode=inode,
        size=size,
        mtime_ns=mtime_ns,
        link_count=link_count,
        sha256=digest,
    )
    current = path.stat(follow_symlinks=False)
    if path_has_symlink_or_reparse(path) or snapshot.identity() != (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
        current.st_nlink,
    ):
        raise ValueError(f"Artifact changed after bounded ingestion: {path.name}")
    return snapshot


def _revalidate_artifact_snapshots(
    snapshots: Mapping[str, _ArtifactSnapshot],
) -> tuple[str, ...]:
    """Perform the last complete-path identity check after all verifier consumers."""

    errors: list[str] = []
    for name, expected in snapshots.items():
        try:
            current = _stable_artifact_snapshot(expected.path)
            if current.identity() != expected.identity() or current.sha256 != expected.sha256:
                raise ValueError("identity or digest changed")
        except (OSError, RuntimeError, ValueError) as error:
            errors.append(f"Artifact changed during complete verification: {name}: {error}")
    return tuple(errors)


def _parse_sha256s(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != f"# evidence_label={EVIDENCE_LABEL}":
        raise ValueError("SHA256SUMS.txt is missing the diagnostic evidence-label header")
    hashes: dict[str, str] = {}
    for line in lines[1:]:
        match = _DIGEST_LINE.fullmatch(line)
        if match is None:
            raise ValueError("SHA256SUMS.txt contains a malformed line")
        digest, relative_name = match.groups()
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"SHA256SUMS.txt contains unsafe path: {relative_name}")
        normalized = relative.as_posix()
        if normalized in hashes:
            raise ValueError(f"SHA256SUMS.txt contains duplicate path: {normalized}")
        hashes[normalized] = digest
    return hashes


def _verify_labelled_rows(
    path: Path,
    errors: list[str],
    parquet_rows: tuple[dict[str, object], ...] | None = None,
) -> None:
    try:
        if path.suffix == ".parquet":
            if parquet_rows is None:
                errors.append(f"No bounded Parquet ingestion is available for {path.name}")
                return
            labels = [row.get("evidence_label") for row in parquet_rows]
        elif path.suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                labels = [row.get("evidence_label") for row in csv.DictReader(handle)]
        else:
            labels = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    value = strict_json_loads(line, source=path.name)
                    labels.append(value.get("evidence_label") if isinstance(value, dict) else None)
        if not labels or any(label != EVIDENCE_LABEL for label in labels):
            errors.append(f"Evidence label missing or invalid in {path.name}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"Could not inspect evidence labels in {path.name}: {error}")


def _is_ordered_subsequence(values: list[str], required: tuple[str, ...]) -> bool:
    position = 0
    for value in values:
        if position < len(required) and value == required[position]:
            position += 1
    return position == len(required)


def _verify_run_impl(
    run_dir: Path | str,
    workspace_root: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
    include_event_sequence: bool = False,
    include_observations: bool = False,
    include_comparison_inputs: bool = False,
    include_evidence_readings: bool = False,
    include_sensing_freshness: bool = False,
    include_function_availability: bool = False,
    include_mission_impact: bool = False,
    include_mission_recovery: bool = False,
    include_critical_outage: bool = False,
    include_review_routing: bool = False,
    include_approval_burden: bool = False,
) -> tuple[VerificationResult, VerifiedSummary | None]:
    """Implement complete verification behind the public defensive boundary."""
    errors: list[str] = []
    checked: list[str] = []
    raw_hash: str | None = None
    summary_hash: str | None = None
    workspace = resolve_workspace_root(workspace_root)
    requested_root = Path(os.path.abspath(Path(run_dir)))
    if path_has_symlink_or_reparse(requested_root):
        return VerificationResult(
            run_dir=requested_root,
            valid=False,
            errors=("Run path contains a symlink or reparse point",),
            checked_files=(),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None
    try:
        root = assert_existing_run_directory(run_dir, workspace)
    except PathBoundaryError as error:
        return VerificationResult(
            run_dir=Path(run_dir),
            valid=False,
            errors=(str(error),),
            checked_files=(),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None

    aggregate_size, inventory_files = _aggregate_run_size(root, errors)
    if aggregate_size > MAX_RUN_OUTPUT_BYTES:
        errors.append(
            f"Aggregate run output exceeds the 2 GiB diagnostic budget: {aggregate_size} bytes"
        )
        return VerificationResult(
            run_dir=root,
            valid=False,
            errors=tuple(errors),
            checked_files=(),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None
    expected_inventory = set(_REQUIRED_ARTIFACTS)
    for unexpected in sorted(inventory_files - expected_inventory):
        errors.append(f"Unexpected run artifact is prohibited: {unexpected}")
    for missing in sorted(expected_inventory - inventory_files):
        errors.append(f"Required artifact absent from run inventory: {missing}")

    artifacts: dict[str, Path] = {}
    for relative_name in _REQUIRED_ARTIFACTS:
        candidate = root / Path(relative_name)
        try:
            if path_has_symlink_or_reparse(candidate):
                raise ValueError("artifact path contains a symlink or reparse point")
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            errors.append(f"Required artifact missing or escapes run directory: {relative_name}")
            continue
        if not resolved.is_file():
            errors.append(f"Required artifact is not a regular file: {relative_name}")
            continue
        if _artifact_size(resolved) == 0:
            errors.append(f"Required artifact is empty: {relative_name}")
            continue
        if resolved.stat().st_size > 2 * 1024**3:
            errors.append(f"Artifact exceeds the diagnostic output cap: {relative_name}")
            continue
        artifacts[relative_name] = resolved
        checked.append(relative_name)

    strict_required = {
        "canonical_config.json",
        "seed_registry.json",
        "status.json",
        "manifest.json",
        "raw/events.jsonl",
        "raw/events.parquet",
        "derived/episode_summary.parquet",
    }
    missing_strict = tuple(sorted(strict_required - artifacts.keys()))
    if missing_strict:
        errors.append(
            "Strict retained-evidence artifact set is incomplete: " + ", ".join(missing_strict)
        )
        return VerificationResult(
            run_dir=root,
            valid=False,
            errors=tuple(errors),
            checked_files=tuple(sorted(checked)),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None
    if errors:
        return VerificationResult(
            run_dir=root,
            valid=False,
            errors=tuple(errors),
            checked_files=tuple(sorted(checked)),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None
    retained_validation = None
    retained_validation = validate_retained_evidence(
        root,
        artifacts,
        workspace,
        repo_root=repo_root,
        include_mission_impact=include_mission_impact,
        include_function_availability=include_function_availability,
        include_mission_recovery=include_mission_recovery,
        include_critical_outage=include_critical_outage,
    )
    errors.extend(retained_validation.errors)
    if retained_validation.errors:
        return VerificationResult(
            run_dir=root,
            valid=False,
            errors=tuple(errors),
            checked_files=tuple(sorted(checked)),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None

    artifact_snapshots: dict[str, _ArtifactSnapshot] = {}
    snapshot_errors: list[str] = []
    for relative_name, artifact in artifacts.items():
        try:
            cached_identity = None
            cached_digest = None
            if retained_validation is not None:
                if (
                    retained_validation.document_identities is not None
                    and retained_validation.document_sha256 is not None
                    and relative_name in retained_validation.document_identities
                    and relative_name in retained_validation.document_sha256
                ):
                    cached_identity = retained_validation.document_identities[relative_name]
                    cached_digest = retained_validation.document_sha256[relative_name]
                elif relative_name == "raw/events.parquet":
                    cached_identity = retained_validation.raw_file_identity
                    cached_digest = retained_validation.raw_encoded_sha256
                elif relative_name == "derived/episode_summary.parquet":
                    cached_identity = retained_validation.summary_file_identity
                    cached_digest = retained_validation.summary_encoded_sha256
            if cached_identity is not None and cached_digest is not None:
                artifact_snapshots[relative_name] = _cached_artifact_snapshot(
                    artifact,
                    device=cached_identity.device,
                    inode=cached_identity.inode,
                    size=cached_identity.size,
                    mtime_ns=cached_identity.mtime_ns,
                    link_count=cached_identity.link_count,
                    digest=cached_digest,
                )
            else:
                artifact_snapshots[relative_name] = _stable_artifact_snapshot(artifact)
        except (OSError, RuntimeError, ValueError) as error:
            snapshot_errors.append(
                f"Could not establish stable artifact snapshot: {relative_name}: {error}"
            )
    if snapshot_errors:
        errors.extend(snapshot_errors)
        return VerificationResult(
            run_dir=root,
            valid=False,
            errors=tuple(errors),
            checked_files=tuple(sorted(checked)),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
        ), None

    def artifact_sha256(relative_name: str, artifact: Path) -> str:
        snapshot = artifact_snapshots.get(relative_name)
        if snapshot is None or snapshot.path != artifact:
            raise ValueError(f"No stable artifact snapshot is available: {relative_name}")
        return snapshot.sha256

    marker = artifacts.get("NON_REPORTABLE_DIAGNOSTIC")
    if marker is not None:
        try:
            if marker.read_text(encoding="utf-8").strip() != EVIDENCE_LABEL:
                errors.append("Diagnostic marker content is invalid")
        except (OSError, UnicodeError):
            errors.append("Diagnostic marker is unreadable")

    json_objects = (
        dict(retained_validation.documents)
        if retained_validation is not None and retained_validation.documents is not None
        else {}
    )
    for name, value in json_objects.items():
        if value.get("evidence_label") != EVIDENCE_LABEL:
            errors.append(f"Evidence label missing or invalid in {name}")

    log_path = artifacts.get("logs/run.log")
    if log_path is not None:
        try:
            log_lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line]
            if not log_lines or any(EVIDENCE_LABEL not in line for line in log_lines):
                errors.append("Run log contains an unlabeled line")
        except (OSError, UnicodeError):
            errors.append("Run log is unreadable")

    for name in (
        "raw/events.jsonl",
        "raw/events.parquet",
        "derived/episode_summary.csv",
        "derived/episode_summary.parquet",
    ):
        path = artifacts.get(name)
        if path is not None:
            parquet_rows = None
            if retained_validation is not None:
                if name == "raw/events.parquet":
                    parquet_rows = retained_validation.raw_rows
                elif name == "derived/episode_summary.parquet":
                    parquet_rows = retained_validation.summary_rows
            _verify_labelled_rows(path, errors, parquet_rows)

    checksum_path = artifacts.get("SHA256SUMS.txt")
    checksum_values: dict[str, str] = {}
    if checksum_path is not None:
        try:
            checksum_values = _parse_sha256s(checksum_path)
            expected_names = set(_REQUIRED_ARTIFACTS) - {"SHA256SUMS.txt"}
            if set(checksum_values) != expected_names:
                errors.append("SHA256SUMS.txt does not list exactly all non-checksum artifacts")
            for relative_name, expected in checksum_values.items():
                checksum_artifact = artifacts.get(relative_name)
                if (
                    checksum_artifact is not None
                    and artifact_sha256(relative_name, checksum_artifact) != expected
                ):
                    errors.append(f"Checksum mismatch: {relative_name}")
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(str(error))

    manifest = json_objects.get("manifest.json", {})
    manifest_hashes = manifest.get("artifact_hashes")
    if isinstance(manifest_hashes, dict):
        expected_manifest_artifacts = set(_REQUIRED_ARTIFACTS) - {
            "manifest.json",
            "SHA256SUMS.txt",
        }
        if not manifest_hashes or set(manifest_hashes) != expected_manifest_artifacts:
            errors.append(
                "Manifest artifact_hashes does not list the exact complete artifact allowlist"
            )
        for relative_name, expected in manifest_hashes.items():
            if not isinstance(relative_name, str) or not isinstance(expected, str):
                errors.append("Manifest artifact_hashes contains a non-string entry")
                continue
            manifest_artifact = artifacts.get(relative_name)
            if (
                manifest_artifact is None
                or artifact_sha256(relative_name, manifest_artifact) != expected
            ):
                errors.append(f"Manifest artifact hash mismatch: {relative_name}")
    else:
        errors.append("Manifest artifact_hashes is missing or invalid")

    canonical_config = json_objects.get("canonical_config.json", {})
    scenario = canonical_config.get("scenario")
    safety_policy = canonical_config.get("safety_policy")
    baseline_definition = canonical_config.get("baseline_definition")
    metric_definition = canonical_config.get("metric_definition")
    configuration_hashes = manifest.get("configuration_hashes")
    components = {
        "scenario": scenario,
        "safety_policy": safety_policy,
        "baseline_definition": baseline_definition,
        "metric_definition": metric_definition,
    }
    if not all(isinstance(value, Mapping) for value in components.values()):
        errors.append("Canonical configuration is missing one or more component mappings")
    elif not isinstance(configuration_hashes, Mapping):
        errors.append("Manifest configuration_hashes is missing or invalid")
    else:
        expected_component_hashes = {
            name: canonical_sha256(value) for name, value in components.items()
        }
        expected_component_hashes["aggregate"] = artifact_sha256(
            "canonical_config.json",
            artifacts["canonical_config.json"],
        )
        for name, expected_digest in expected_component_hashes.items():
            if configuration_hashes.get(name) != expected_digest:
                errors.append(f"Manifest component hash mismatch: {name}")
        if (
            manifest.get("baseline_definition_hash")
            != expected_component_hashes["baseline_definition"]
        ):
            errors.append(
                "Manifest baseline_definition_hash does not match canonical configuration"
            )
        if manifest.get("metric_definition_hash") != expected_component_hashes["metric_definition"]:
            errors.append("Manifest metric_definition_hash does not match canonical configuration")
        for name, component_value in components.items():
            if (
                isinstance(component_value, Mapping)
                and component_value.get("evidence_label") != EVIDENCE_LABEL
            ):
                errors.append(f"Canonical {name} evidence label is invalid")

    if isinstance(safety_policy, Mapping):
        if safety_policy.get("execution_adapter") != "simulated_only":
            errors.append("Safety policy must require execution_adapter=simulated_only")
        if safety_policy.get("network_enabled") is not False:
            errors.append("Safety policy must require network_enabled=false")

    canonical_protocol = canonical_config.get("protocol_version")
    scenario_protocol = scenario.get("protocol_version") if isinstance(scenario, Mapping) else None
    if (
        not isinstance(canonical_protocol, str)
        or canonical_protocol != scenario_protocol
        or canonical_protocol != manifest.get("protocol_version")
    ):
        errors.append("Protocol version is inconsistent across canonical config and manifest")

    canonical_path = artifacts.get("canonical_config.json")
    if canonical_path is not None:
        config_digest = artifact_sha256("canonical_config.json", canonical_path)
        if manifest.get("config_hash_start") != config_digest:
            errors.append("Manifest start configuration hash does not match canonical_config.json")
        if manifest.get("config_hash_end") != config_digest:
            errors.append("Manifest end configuration hash does not match canonical_config.json")
        if manifest.get("config_hash_start") != manifest.get("config_hash_end"):
            errors.append("Canonical configuration changed during the run")

    seed_path = artifacts.get("seed_registry.json")
    if seed_path is not None and manifest.get("seed_registry_hash") != artifact_sha256(
        "seed_registry.json",
        seed_path,
    ):
        errors.append("Manifest seed-registry hash does not match seed_registry.json")
    seed_registry = json_objects.get("seed_registry.json", {})
    status = json_objects.get("status.json", {})
    registered_seeds = seed_registry.get("seeds")
    manifest_seed = manifest.get("seed")
    if (
        not isinstance(registered_seeds, list)
        or manifest_seed not in registered_seeds
        or status.get("seed") != manifest_seed
    ):
        errors.append("Seed is inconsistent across registry, status, and manifest")

    raw_parquet = artifacts.get("raw/events.parquet")
    raw_jsonl = artifacts.get("raw/events.jsonl")
    summary_parquet = artifacts.get("derived/episode_summary.parquet")
    summary_csv = artifacts.get("derived/episode_summary.csv")
    raw_table = retained_validation.raw_table if retained_validation is not None else None
    raw_rows = retained_validation.raw_rows if retained_validation is not None else ()
    summary_table = retained_validation.summary_table if retained_validation is not None else None
    summary_rows = retained_validation.summary_rows if retained_validation is not None else ()
    if raw_parquet is not None and raw_table is not None:
        try:
            raw_seeds = {row.get("seed") for row in raw_rows}
            raw_config_hashes = {row.get("config_hash") for row in raw_rows}
            if raw_seeds != {manifest_seed}:
                errors.append("Raw-event seed does not match the manifest seed")
            if raw_config_hashes != {manifest.get("config_hash_start")}:
                errors.append("Raw-event configuration hash does not match the manifest")
            raw_hash = semantic_events_hash(raw_rows)
            if manifest.get("raw_semantic_hash") != raw_hash:
                errors.append("Manifest raw semantic hash does not match raw events")
            if raw_jsonl is not None and semantic_events_hash(raw_jsonl) != raw_hash:
                errors.append("JSONL and Parquet raw-event semantics differ")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Raw semantic verification failed: {error}")

    expected_summary: dict[str, object] | None = None
    if summary_parquet is not None and summary_table is not None:
        try:
            if len(summary_rows) != 1:
                errors.append("Derived summary must contain exactly one row")
            else:
                summary_row = summary_rows[0]
                if summary_row.get("seed") != manifest_seed:
                    errors.append("Derived-summary seed does not match the manifest seed")
                if summary_row.get("config_hash") != manifest.get("config_hash_start"):
                    errors.append("Derived-summary configuration hash does not match the manifest")
            summary_hash = semantic_summary_hash(summary_rows)
            if manifest.get("summary_semantic_hash") != summary_hash:
                errors.append("Manifest summary semantic hash does not match derived summary")
            if summary_csv is not None and semantic_summary_hash(summary_csv) != summary_hash:
                errors.append("CSV and Parquet summary semantics differ")
            if raw_table is not None:
                expected_summary = summary_from_raw_table(raw_table)
                if canonical_sha256([expected_summary]) != summary_hash:
                    errors.append("Derived summary was not reproduced solely from raw events")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Summary semantic verification failed: {error}")

    if raw_parquet is not None and raw_table is not None:
        try:
            event_types = [str(row.get("event_type")) for row in raw_rows]
            review_only = (
                isinstance(baseline_definition, Mapping)
                and baseline_definition.get("actions") == "require_human_review"
            )
            decision_event = (
                "defender_decision"
                if isinstance(baseline_definition, Mapping)
                and baseline_definition.get("name") == corroboration.POLICY
                else "baseline_decision"
            )
            required_chain = (
                "observation",
                "evidence",
                "state_update",
                "hypothesis",
            ) + (
                (decision_event, "manifest")
                if review_only
                else (
                    "candidate_action",
                    "safety_decision",
                    "simulated_execution",
                    "verification",
                    "audit",
                    "manifest",
                )
            )
            if not _is_ordered_subsequence(event_types, required_chain):
                errors.append("Required ordered diagnostic event chain is incomplete")
            prohibited = {
                row.get("action_id")
                for row in raw_rows
                if row.get("event_type") == "safety_decision"
                and row.get("disposition") == "PROHIBIT"
            }
            if not review_only and not prohibited:
                errors.append("No prohibited safety decision is retained")
            retained_dispositions = {
                row.get("disposition")
                for row in raw_rows
                if row.get("event_type") == "safety_decision"
            }
            known_dispositions = {"APPROVE", "ESCALATE", "PROHIBIT"}
            if review_only and "APPROVE" in retained_dispositions:
                errors.append("Human-review proposal received APPROVE")
            if not review_only and not known_dispositions.issubset(retained_dispositions):
                errors.append("Raw audit does not retain APPROVE, ESCALATE, and PROHIBIT decisions")
            unknown_dispositions = retained_dispositions - known_dispositions
            if unknown_dispositions:
                errors.append("Raw audit contains an unknown safety disposition")
            decision_by_action: dict[object, object] = {}
            for row in raw_rows:
                if row.get("event_type") != "safety_decision":
                    continue
                action_id = row.get("action_id")
                disposition = row.get("disposition")
                prior_disposition = decision_by_action.get(action_id)
                if prior_disposition is not None and prior_disposition != disposition:
                    errors.append("Raw audit contains conflicting decisions for one action")
                decision_by_action[action_id] = disposition
            verified_action_ids = {
                row.get("action_id")
                for row in raw_rows
                if row.get("event_type") == "verification"
                and row.get("disposition") == "VERIFIED"
                and row.get("outcome") == "verified"
            }
            executed_approved_action_ids: set[object] = set()
            benign_negative_control = False
            for row in raw_rows:
                payload_text = row.get("payload_json")
                if not isinstance(payload_text, str):
                    continue
                payload = strict_json_loads(payload_text, source="raw payload_json")
                is_execution = row.get("event_type") == "simulated_execution"
                declares_executed = isinstance(payload, dict) and payload.get("executed") is True
                if is_execution or declares_executed:
                    if review_only:
                        errors.append("Human-review proposal reached execution")
                    action_id = row.get("action_id")
                    if decision_by_action.get(action_id) != "APPROVE":
                        errors.append(
                            "Only an APPROVE safety decision may have executed=true or an "
                            "execution event"
                        )
                    else:
                        executed_approved_action_ids.add(action_id)
                    if is_execution and row.get("disposition") != "APPROVE":
                        errors.append("Simulated execution row disposition must be exactly APPROVE")
                    if not isinstance(payload, dict) or payload.get("adapter") != "simulated_only":
                        errors.append("Execution payload must declare adapter=simulated_only")
                    if not isinstance(payload, dict) or payload.get("network_enabled") is not False:
                        errors.append("Execution payload must declare network_enabled=false")
                if (
                    isinstance(payload, dict)
                    and payload.get("classification") == "benign_negative_control"
                    and row.get("outcome") == "not_compromised"
                ):
                    benign_negative_control = True
            if executed_approved_action_ids - verified_action_ids:
                errors.append(
                    "Executed APPROVE action lacks a same-action VERIFIED verification event"
                )
            guarded_adverse = (
                isinstance(scenario, Mapping)
                and "guarded_review" in scenario
                and all(
                    event.kind == "simulated_adversary"
                    for event in ScenarioConfig.model_validate(scenario).events
                )
            )
            if not benign_negative_control and not guarded_adverse:
                errors.append("Benign negative control is absent from the retained raw audit")
            if any(
                row.get("event_type") == "simulated_execution"
                and row.get("action_id") in prohibited
                for row in raw_rows
            ):
                errors.append("A prohibited action reached simulated execution")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Raw safety-chain verification failed: {error}")

    if status.get("completion_status") != "COMPLETED":
        errors.append("Run status is not COMPLETED")
    if manifest.get("completion_status") != "COMPLETED":
        errors.append("Manifest completion status is not COMPLETED")
    if status.get("reportable") is not False:
        errors.append("Run status must declare reportable=false")
    if manifest.get("reportable") is not False:
        errors.append("Manifest must declare reportable=false")
    receipt = verify_execution_receipt(
        workspace_root=workspace,
        run_dir=root,
        manifest=manifest,
    )
    errors.extend(_revalidate_artifact_snapshots(artifact_snapshots))
    if expected_summary is None and not errors:
        errors.append("Verified raw-derived summary is unavailable")
    semantic_content_valid = not errors
    errors.extend(receipt.errors)
    result = VerificationResult(
        run_dir=root,
        valid=semantic_content_valid and receipt.identity_assured,
        errors=tuple(errors),
        checked_files=tuple(sorted(checked)),
        raw_semantic_hash=raw_hash,
        summary_semantic_hash=summary_hash,
        semantic_content_valid=semantic_content_valid,
        execution_identity_assured=receipt.identity_assured,
        identity_assurance_scope=receipt.identity_assurance_scope,
        historical_control_file_inode_continuity_assured=(
            receipt.historical_control_file_inode_continuity_assured
        ),
        reportable=receipt.reportable,
        receipt_path=receipt.receipt_path,
    )
    if result.valid and not result.errors and expected_summary is not None:
        if include_event_sequence:
            # The verifier has matched every full-coverage observation to the checked-out
            # scenario and authenticated the retained documents and rows in this pass.
            # Keep observed order, but take source tick and nullable subject from the script.
            by_id = {event.id: event for event in ScenarioConfig.model_validate(scenario).events}
            sequence = tuple(
                by_id[json.loads(cast(str, row["payload_json"]))["event_id"]]
                for row in raw_rows
                if row["event_type"] == "observation"
            )
            result = replace(result, event_sequence=sequence)
        observations: tuple[BaselineObservation, ...] = ()
        if include_observations:
            observations = tuple(
                _delivered_reading(row, json.loads(cast(str, row["payload_json"]))["signal"])
                for row in raw_rows
                if row["event_type"] == "observation"
            )
        guarded_review = None
        if isinstance(scenario, Mapping) and "guarded_review" in scenario:
            governed = ScenarioConfig.model_validate(scenario)
            guarded_review = guarded_review_metrics(raw_rows, governed.sensing_operator)
            if (
                include_function_availability
                and retained_validation.function_availability is not None
            ):
                guarded_review["function_availability"] = retained_validation.function_availability
            if include_mission_impact and retained_validation.mission_impact is not None:
                guarded_review["mission_impact"] = retained_validation.mission_impact
            if include_mission_recovery and retained_validation.mission_recovery is not None:
                guarded_review["mission_recovery"] = retained_validation.mission_recovery
            if include_critical_outage and retained_validation.critical_outage is not None:
                guarded_review["critical_outage"] = retained_validation.critical_outage
            if include_review_routing or include_approval_burden:
                guarded_review.update(
                    guarded_review_projections(
                        raw_rows,
                        include_review_routing=include_review_routing,
                        include_approval_burden=include_approval_burden,
                        override_policy=(
                            governed.guarded_review.override_policy
                            if governed.guarded_review is not None
                            else None
                        ),
                    )
                )
            if include_sensing_freshness and isinstance(baseline_definition, Mapping):
                condition = baseline_definition.get("name")
                if condition in (CONTEXTUAL, SCHEDULED):
                    guarded_review["sensing_freshness"] = sensing_freshness_metrics(
                        raw_rows, condition
                    )
        return result, VerifiedSummary(
            episode=EpisodeRecord.model_validate(expected_summary),
            csv_sha256=artifact_snapshots["derived/episode_summary.csv"].sha256,
            parquet_sha256=artifact_snapshots["derived/episode_summary.parquet"].sha256,
            observations=observations,
            evidence_readings=_verified_evidence_readings(
                raw_rows, ScenarioConfig.model_validate(scenario)
            )
            if include_evidence_readings
            else (),
            guarded_review=guarded_review,
            comparison_inputs=ComparisonInputs.from_inputs(
                canonical_config, seed_registry, cast(str, manifest["code_commit"])
            )
            if include_comparison_inputs
            else None,
        )
    return result, None


def verify_run_with_summary(
    run_dir: Path | str,
    workspace_root: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
    include_event_sequence: bool = False,
    include_observations: bool = False,
    include_comparison_inputs: bool = False,
    include_evidence_readings: bool = False,
    include_sensing_freshness: bool = False,
    include_function_availability: bool = False,
    include_mission_impact: bool = False,
    include_mission_recovery: bool = False,
    include_critical_outage: bool = False,
    include_review_routing: bool = False,
    include_approval_burden: bool = False,
) -> tuple[VerificationResult, VerifiedSummary | None]:
    """Release the summary and requested sensor fields only after full local verification."""

    try:
        return _verify_run_impl(
            run_dir,
            workspace_root=workspace_root,
            repo_root=repo_root,
            include_event_sequence=include_event_sequence,
            include_observations=include_observations,
            include_comparison_inputs=include_comparison_inputs,
            include_evidence_readings=include_evidence_readings,
            include_sensing_freshness=include_sensing_freshness,
            include_function_availability=include_function_availability,
            include_mission_impact=include_mission_impact,
            include_mission_recovery=include_mission_recovery,
            include_critical_outage=include_critical_outage,
            include_review_routing=include_review_routing,
            include_approval_burden=include_approval_burden,
        )
    except RecursionError as error:
        return VerificationResult(
            run_dir=Path(run_dir),
            valid=False,
            errors=(
                "Verification rejected excessively nested retained evidence: "
                f"RecursionError: {error}",
            ),
            checked_files=(),
            raw_semantic_hash=None,
            summary_semantic_hash=None,
            semantic_content_valid=False,
            execution_identity_assured=False,
            reportable=False,
        ), None


def verify_run(
    run_dir: Path | str,
    workspace_root: Path | str | None = None,
    *,
    repo_root: Path | str | None = None,
    include_event_sequence: bool = False,
) -> VerificationResult:
    """Return the public verification report without the optional regeneration material."""
    result, _ = verify_run_with_summary(
        run_dir,
        workspace_root=workspace_root,
        repo_root=repo_root,
        include_event_sequence=include_event_sequence,
    )
    return result

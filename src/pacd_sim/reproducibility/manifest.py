"""Canonical hashing and manifest construction for diagnostic run artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self, cast

import pyarrow.parquet as pq
from pydantic import ConfigDict, Field, field_validator, model_validator

from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.paths import assert_write_path
from pacd_sim.schema import (
    DiagnosticRecord,
    NonemptyText,
    Sha256Digest,
    Signed64Count,
    StableId,
    StrictFrozenModel,
)


class ConfigurationHashes(StrictFrozenModel):
    """Canonical digests for the five entries of the configuration hash object."""

    aggregate: Sha256Digest
    scenario: Sha256Digest
    safety_policy: Sha256Digest
    baseline_definition: Sha256Digest
    metric_definition: Sha256Digest


class ArtifactHashes(StrictFrozenModel):
    """The completed v1 run's fixed artifact allowlist, keyed by relative wire path."""

    model_config = ConfigDict(serialize_by_alias=True)

    label: Sha256Digest = Field(alias="NON_REPORTABLE_DIAGNOSTIC")
    configuration: Sha256Digest = Field(alias="canonical_config.json")
    summary_csv: Sha256Digest = Field(alias="derived/episode_summary.csv")
    summary_parquet: Sha256Digest = Field(alias="derived/episode_summary.parquet")
    run_log: Sha256Digest = Field(alias="logs/run.log")
    events_jsonl: Sha256Digest = Field(alias="raw/events.jsonl")
    events_parquet: Sha256Digest = Field(alias="raw/events.parquet")
    seeds: Sha256Digest = Field(alias="seed_registry.json")
    status: Sha256Digest = Field(alias="status.json")


class RunManifest(DiagnosticRecord):
    """Typed v1 manifest. A failure can amend an already-built manifest."""

    run_id: StableId
    seed: Signed64Count
    started_at: str
    ended_at: str
    completion_status: Literal["COMPLETED", "FAILED"]
    failure_type: StableId | None = Field(default=None, exclude_if=lambda value: value is None)
    reportable: Literal[False]
    code_commit: (
        Annotated[str, Field(pattern=r"^[a-f0-9]{40}$", max_length=40)] | Literal["UNAVAILABLE"]
    )
    dirty_state: bool
    python_version: StableId
    lockfile_hash: Sha256Digest | Literal["UNAVAILABLE"]
    os_class: StableId
    cpu_worker_count: Annotated[int, Field(ge=1)]
    protocol_version: NonemptyText
    config_hash_start: Sha256Digest
    config_hash_end: Sha256Digest
    configuration_hashes: ConfigurationHashes
    seed_registry_hash: Sha256Digest
    baseline_definition_hash: Sha256Digest
    metric_definition_hash: Sha256Digest
    raw_semantic_hash: Sha256Digest
    summary_semantic_hash: Sha256Digest
    test_status: Literal["NOT_RUN"]
    artifact_hashes: ArtifactHashes

    @field_validator("reportable", mode="before")
    @classmethod
    def _diagnostic_only(cls, value: object) -> Literal[False]:
        if value is not False:
            raise ValueError("Diagnostic manifests require reportable=false")
        return False

    @model_validator(mode="after")
    def _bind_manifest_fields(self) -> Self:
        if self.completion_status == "FAILED":
            if not self.failure_type:
                raise ValueError("A failed manifest must identify its failure type")
        elif "failure_type" in self.model_fields_set:
            raise ValueError("A completed manifest cannot declare a failure type")
        started = datetime.fromisoformat(self.started_at)
        ended = datetime.fromisoformat(self.ended_at)
        if started.utcoffset() is None or ended.utcoffset() is None or ended < started:
            raise ValueError("Manifest start and end times must be zoned and ordered")
        if (
            self.config_hash_start != self.configuration_hashes.aggregate
            or self.config_hash_end != self.config_hash_start
            or self.baseline_definition_hash != self.configuration_hashes.baseline_definition
            or self.metric_definition_hash != self.configuration_hashes.metric_definition
        ):
            raise ValueError("Manifest configuration hash bindings disagree")
        return self


_VOLATILE_KEYS = frozenset(
    {
        "artifact_path",
        "created_at",
        "duration_seconds",
        "ended_at",
        "host_path",
        "path",
        "run_dir",
        "run_directory",
        "run_id",
        "started_at",
        "timestamp",
        "wall_time",
    }
)
_INTEGER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(r"^-?(?:(?:0|[1-9][0-9]*)\.[0-9]+|(?:0|[1-9][0-9]*)[eE][+-]?[0-9]+)$")
_SUMMARY_INTEGER_FIELDS = frozenset(
    {
        "seed",
        "event_count",
        "observation_count",
        "evidence_count",
        "state_update_count",
        "hypothesis_count",
        "candidate_action_count",
        "approved_action_count",
        "escalated_action_count",
        "prohibited_action_count",
        "simulated_execution_count",
        "verified_execution_count",
        "benign_negative_control_count",
        "prohibited_execution_count",
    }
)

# Each independently decoded retained JSON document or embedded payload uses
# depth 1 at its own root. An enclosing event-record field is not charged again
# after its payload was independently decoded and checked against this limit.
MAX_RETAINED_PAYLOAD_DEPTH = 64


def validate_retained_json_text_depth(text: str, *, source: str) -> None:
    """Reject JSON syntax whose container nesting exceeds the retained-data limit.

    The scan is iterative and string-aware, so deeply nested hostile syntax is
    rejected before it reaches CPython's recursive JSON decoder. Full syntax
    validation remains the responsibility of the decoder that follows.
    """

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_RETAINED_PAYLOAD_DEPTH:
                raise ValueError(
                    f"Excessively nested JSON/payload in {source}: documented maximum depth "
                    f"{MAX_RETAINED_PAYLOAD_DEPTH} exceeded"
                )
        elif character in "]}" and depth:
            depth -= 1


def validate_retained_value_depth(value: object, *, source: str) -> None:
    """Iteratively enforce the retained-data depth limit on decoded values."""

    stack: list[tuple[object, int]] = [(value, 0)]
    while stack:
        item, parent_depth = stack.pop()
        if isinstance(item, Mapping):
            depth = parent_depth + 1
            if depth > MAX_RETAINED_PAYLOAD_DEPTH:
                raise ValueError(
                    f"Excessively nested JSON/payload in {source}: documented maximum depth "
                    f"{MAX_RETAINED_PAYLOAD_DEPTH} exceeded"
                )
            stack.extend((child, depth) for child in item.values())
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            depth = parent_depth + 1
            if depth > MAX_RETAINED_PAYLOAD_DEPTH:
                raise ValueError(
                    f"Excessively nested JSON/payload in {source}: documented maximum depth "
                    f"{MAX_RETAINED_PAYLOAD_DEPTH} exceeded"
                )
            stack.extend((child, depth) for child in item)


def sha256_file(path: Path | str) -> str:
    """Stream a file into SHA-256 without loading a potentially large artifact."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_canonical_json(
    path: Path | str,
    value: object,
    *,
    workspace_root: Path | str,
) -> Path:
    """Create (never overwrite) a confined canonical JSON file."""
    target = assert_write_path(path, workspace_root)
    with target.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
    return target


def _normalize_semantic(value: object, *, key: str | None = None) -> object:
    if key is not None and (key in _VOLATILE_KEYS or key.endswith("_path")):
        return None
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for raw_key, item in value.items():
            item_key = str(raw_key)
            if item_key in _VOLATILE_KEYS or item_key.endswith("_path"):
                continue
            normalized[item_key] = _normalize_semantic(item, key=item_key)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_semantic(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Semantic records may not contain NaN or infinity")
        return 0.0 if value == 0.0 else value
    return value


def _load_bounded_json(text: str, *, source: str) -> object:
    """Decode JSON only after iterative syntax-depth preflight."""

    validate_retained_json_text_depth(text, source=source)
    try:
        value = json.loads(text)
    except RecursionError as error:
        raise ValueError(f"Excessively nested JSON/payload in {source}") from error
    validate_retained_value_depth(value, source=source)
    return value


def _decode_payload(record: Mapping[str, object]) -> dict[str, object]:
    decoded = dict(record)
    payload = decoded.get("payload_json")
    if isinstance(payload, str):
        parsed = _load_bounded_json(payload, source="semantic payload_json")
        decoded["payload_json"] = parsed
    return decoded


def _records_from_path(path: Path) -> list[dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        parquet_rows = cast(list[dict[object, object]], pq.read_table(path).to_pylist())
        return [{str(key): value for key, value in row.items()} for row in parquet_rows]
    if suffix == ".jsonl":
        jsonl_rows: list[dict[str, object]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = _load_bounded_json(
                    line,
                    source=f"{path.name} row {line_number}",
                )
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL row {line_number} is not an object")
                jsonl_rows.append({str(key): item for key, item in value.items()})
        return jsonl_rows
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [
                {str(key): _coerce_csv_scalar(str(key), value) for key, value in row.items()}
                for row in csv.DictReader(handle)
            ]
    if suffix == ".json":
        value = _load_bounded_json(
            path.read_text(encoding="utf-8"),
            source=path.name,
        )
        if isinstance(value, dict):
            return [{str(key): item for key, item in value.items()}]
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return [{str(key): item_value for key, item_value in item.items()} for item in value]
        raise ValueError("JSON semantic source must be an object or list of objects")
    raise ValueError(f"Unsupported semantic-record format: {path.suffix}")


def _coerce_csv_scalar(field_name: str, value: str | None) -> object:
    if value is None or value == "":
        return ""
    if field_name in _SUMMARY_INTEGER_FIELDS and _INTEGER_RE.fullmatch(value):
        return int(value)
    if field_name in _SUMMARY_INTEGER_FIELDS and _FLOAT_RE.fullmatch(value):
        return float(value)
    return value


def semantic_records_hash(
    records: Path | str | Iterable[Mapping[str, object]],
    *,
    sort_fields: tuple[str, ...] = ("sequence",),
) -> str:
    """Hash records after excluding wall-clock, run-id, and path metadata."""
    try:
        if isinstance(records, (str, Path)):
            loaded = _records_from_path(Path(records))
        else:
            loaded = [dict(record) for record in records]
        decoded = [_decode_payload(record) for record in loaded]
        for index, record in enumerate(decoded, start=1):
            for field, value in record.items():
                validate_retained_value_depth(
                    value,
                    source=f"semantic record {index} field {field}",
                )
        if sort_fields and all(all(field in row for field in sort_fields) for row in decoded):
            decoded.sort(key=lambda row: tuple(row[field] for field in sort_fields))
        normalized = [_normalize_semantic(record) for record in decoded]
        return canonical_sha256(normalized)
    except RecursionError as error:
        raise ValueError("Excessively nested retained data reached semantic hashing") from error


def semantic_events_hash(events: Path | str | Iterable[Mapping[str, object]]) -> str:
    """Return the normalized raw-event hash used for same-seed replay."""
    return semantic_records_hash(events, sort_fields=("sequence",))


def semantic_summary_hash(summary: Path | str | Iterable[Mapping[str, object]]) -> str:
    """Return the normalized derived-summary hash used for replay."""
    return semantic_records_hash(summary, sort_fields=())


def collect_artifact_hashes(run_dir: Path | str, relative_paths: Iterable[str]) -> dict[str, str]:
    """Hash an explicit artifact allowlist in stable relative-path order."""
    root = Path(run_dir).resolve(strict=True)
    hashes: dict[str, str] = {}
    for relative_name in sorted(set(relative_paths)):
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Artifact path is not relative and confined: {relative_name}")
        artifact = (root / relative).resolve(strict=True)
        try:
            artifact.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Artifact escapes run directory: {relative_name}") from error
        if not artifact.is_file():
            raise ValueError(f"Artifact is not a regular file: {relative_name}")
        hashes[relative.as_posix()] = sha256_file(artifact)
    return hashes


def build_manifest(
    *,
    run_id: str,
    seed: int,
    started_at: str,
    ended_at: str,
    completion_status: str,
    code_commit: str,
    dirty_state: bool,
    python_version: str,
    lockfile_hash: str,
    os_class: str,
    cpu_worker_count: int,
    protocol_version: str,
    config_hash_start: str,
    config_hash_end: str,
    scenario_hash: str,
    safety_policy_hash: str,
    seed_registry_hash: str,
    baseline_definition_hash: str,
    metric_definition_hash: str,
    raw_semantic_hash: str,
    summary_semantic_hash: str,
    artifact_hashes: Mapping[str, str],
    test_status: str = "NOT_RUN",
) -> dict[str, object]:
    """Build the manifest data structure without performing any write."""
    return RunManifest.model_validate(
        {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "seed": seed,
            "started_at": started_at,
            "ended_at": ended_at,
            "completion_status": completion_status,
            "reportable": False,
            "code_commit": code_commit,
            "dirty_state": dirty_state,
            "python_version": python_version,
            "lockfile_hash": lockfile_hash,
            "os_class": os_class,
            "cpu_worker_count": cpu_worker_count,
            "protocol_version": protocol_version,
            "config_hash_start": config_hash_start,
            "config_hash_end": config_hash_end,
            "configuration_hashes": {
                "aggregate": config_hash_start,
                "scenario": scenario_hash,
                "safety_policy": safety_policy_hash,
                "baseline_definition": baseline_definition_hash,
                "metric_definition": metric_definition_hash,
            },
            "seed_registry_hash": seed_registry_hash,
            "baseline_definition_hash": baseline_definition_hash,
            "metric_definition_hash": metric_definition_hash,
            "raw_semantic_hash": raw_semantic_hash,
            "summary_semantic_hash": summary_semantic_hash,
            "test_status": test_status,
            "artifact_hashes": artifact_hashes,
        }
    ).model_dump(by_alias=True)


def write_manifest(
    run_dir: Path | str,
    manifest: Mapping[str, object],
    *,
    workspace_root: Path | str,
) -> Path:
    """Write a new manifest with mandatory diagnostic labeling."""
    record = RunManifest.model_validate(manifest)
    return write_canonical_json(
        Path(run_dir) / "manifest.json", record, workspace_root=workspace_root
    )


def write_sha256s(
    run_dir: Path | str,
    hashes: Mapping[str, str],
    *,
    workspace_root: Path | str,
) -> Path:
    """Create the conventional checksum list with a diagnostic-label header."""
    target = assert_write_path(Path(run_dir) / "SHA256SUMS.txt", workspace_root)
    lines = [f"# evidence_label={EVIDENCE_LABEL}"]
    for relative_name, digest in sorted(hashes.items()):
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid SHA-256 digest for {relative_name}")
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe checksum path: {relative_name}")
        lines.append(f"{digest}  {relative.as_posix()}")
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return target

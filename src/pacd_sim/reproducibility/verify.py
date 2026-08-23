"""Read-only verification of a retained PACD diagnostic run directory."""

from __future__ import annotations

import csv
import json
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow.parquet as pq

from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.metrics.summarize import summary_from_raw
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.reproducibility.manifest import (
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
)
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_existing_run_directory,
    is_symlink_or_reparse,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
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
    """Structured result of complete run-artifact verification."""

    run_dir: Path
    valid: bool
    errors: tuple[str, ...]
    checked_files: tuple[str, ...]
    raw_semantic_hash: str | None
    summary_semantic_hash: str | None
    evidence_label: str = EVIDENCE_LABEL

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready result with a string path."""
        value = asdict(self)
        value["run_dir"] = str(self.run_dir)
        return value


def _read_json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return {str(key): item for key, item in value.items()}


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


def _verify_labelled_rows(path: Path, errors: list[str]) -> None:
    try:
        if path.suffix == ".parquet":
            rows = pq.read_table(path, columns=["evidence_label"]).to_pylist()
            labels = [row.get("evidence_label") for row in rows]
        elif path.suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                labels = [row.get("evidence_label") for row in csv.DictReader(handle)]
        else:
            labels = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    value = json.loads(line)
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


def verify_run(
    run_dir: Path | str,
    workspace_root: Path | str | None = None,
) -> VerificationResult:
    """Validate checksums, labels, semantics, derivation, and safety invariants."""
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
        )
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
        )

    aggregate_size, inventory_files = _aggregate_run_size(root, errors)
    if aggregate_size > MAX_RUN_OUTPUT_BYTES:
        errors.append(
            f"Aggregate run output exceeds the 2 GiB diagnostic budget: {aggregate_size} bytes"
        )
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

    marker = artifacts.get("NON_REPORTABLE_DIAGNOSTIC")
    if marker is not None:
        try:
            if marker.read_text(encoding="utf-8").strip() != EVIDENCE_LABEL:
                errors.append("Diagnostic marker content is invalid")
        except (OSError, UnicodeError):
            errors.append("Diagnostic marker is unreadable")

    json_objects: dict[str, dict[str, object]] = {}
    for name in ("canonical_config.json", "seed_registry.json", "status.json", "manifest.json"):
        path = artifacts.get(name)
        if path is None:
            continue
        try:
            value = _read_json_object(path)
            json_objects[name] = value
            if value.get("evidence_label") != EVIDENCE_LABEL:
                errors.append(f"Evidence label missing or invalid in {name}")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"Could not parse {name}: {error}")

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
            _verify_labelled_rows(path, errors)

    checksum_path = artifacts.get("SHA256SUMS.txt")
    checksum_values: dict[str, str] = {}
    if checksum_path is not None:
        try:
            checksum_values = _parse_sha256s(checksum_path)
            expected_names = set(_REQUIRED_ARTIFACTS) - {"SHA256SUMS.txt"}
            if set(checksum_values) != expected_names:
                errors.append("SHA256SUMS.txt does not list exactly all non-checksum artifacts")
            for relative_name, expected in checksum_values.items():
                artifact = artifacts.get(relative_name)
                if artifact is not None and sha256_file(artifact) != expected:
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
            artifact = artifacts.get(relative_name)
            if artifact is None or sha256_file(artifact) != expected:
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
        expected_component_hashes["aggregate"] = sha256_file(artifacts["canonical_config.json"])
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
        config_digest = sha256_file(canonical_path)
        if manifest.get("config_hash_start") != config_digest:
            errors.append("Manifest start configuration hash does not match canonical_config.json")
        if manifest.get("config_hash_end") != config_digest:
            errors.append("Manifest end configuration hash does not match canonical_config.json")
        if manifest.get("config_hash_start") != manifest.get("config_hash_end"):
            errors.append("Canonical configuration changed during the run")

    seed_path = artifacts.get("seed_registry.json")
    if seed_path is not None and manifest.get("seed_registry_hash") != sha256_file(seed_path):
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
    if raw_parquet is not None:
        try:
            raw_table = pq.read_table(raw_parquet)
            raw_rows_for_identity = raw_table.to_pylist()
            raw_seeds = {row.get("seed") for row in raw_rows_for_identity}
            raw_config_hashes = {row.get("config_hash") for row in raw_rows_for_identity}
            if raw_seeds != {manifest_seed}:
                errors.append("Raw-event seed does not match the manifest seed")
            if raw_config_hashes != {manifest.get("config_hash_start")}:
                errors.append("Raw-event configuration hash does not match the manifest")
            raw_hash = semantic_events_hash(raw_parquet)
            if manifest.get("raw_semantic_hash") != raw_hash:
                errors.append("Manifest raw semantic hash does not match raw events")
            if raw_jsonl is not None and semantic_events_hash(raw_jsonl) != raw_hash:
                errors.append("JSONL and Parquet raw-event semantics differ")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Raw semantic verification failed: {error}")

    if summary_parquet is not None:
        try:
            summary_rows = pq.read_table(summary_parquet).to_pylist()
            if len(summary_rows) != 1:
                errors.append("Derived summary must contain exactly one row")
            else:
                summary_row = summary_rows[0]
                if summary_row.get("seed") != manifest_seed:
                    errors.append("Derived-summary seed does not match the manifest seed")
                if summary_row.get("config_hash") != manifest.get("config_hash_start"):
                    errors.append("Derived-summary configuration hash does not match the manifest")
            summary_hash = semantic_summary_hash(summary_parquet)
            if manifest.get("summary_semantic_hash") != summary_hash:
                errors.append("Manifest summary semantic hash does not match derived summary")
            if summary_csv is not None and semantic_summary_hash(summary_csv) != summary_hash:
                errors.append("CSV and Parquet summary semantics differ")
            if raw_parquet is not None:
                expected_summary = summary_from_raw(raw_parquet)
                if canonical_sha256([expected_summary]) != summary_hash:
                    errors.append("Derived summary was not reproduced solely from raw events")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Summary semantic verification failed: {error}")

    if raw_parquet is not None:
        try:
            raw_rows = pq.read_table(raw_parquet).to_pylist()
            event_types = [str(row.get("event_type")) for row in raw_rows]
            required_chain = (
                "observation",
                "evidence",
                "state_update",
                "hypothesis",
                "candidate_action",
                "safety_decision",
                "simulated_execution",
                "verification",
                "audit",
                "manifest",
            )
            if not _is_ordered_subsequence(event_types, required_chain):
                errors.append("Required ordered diagnostic event chain is incomplete")
            prohibited = {
                row.get("action_id")
                for row in raw_rows
                if row.get("event_type") == "safety_decision"
                and row.get("disposition") == "PROHIBIT"
            }
            if not prohibited:
                errors.append("No prohibited safety decision is retained")
            retained_dispositions = {
                row.get("disposition")
                for row in raw_rows
                if row.get("event_type") == "safety_decision"
            }
            required_dispositions = {"APPROVE", "ESCALATE", "PROHIBIT"}
            if not required_dispositions.issubset(retained_dispositions):
                errors.append("Raw audit does not retain APPROVE, ESCALATE, and PROHIBIT decisions")
            unknown_dispositions = retained_dispositions - required_dispositions
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
                payload = json.loads(payload_text)
                is_execution = row.get("event_type") == "simulated_execution"
                declares_executed = isinstance(payload, dict) and payload.get("executed") is True
                if is_execution or declares_executed:
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
            if not benign_negative_control:
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

    return VerificationResult(
        run_dir=root,
        valid=not errors,
        errors=tuple(errors),
        checked_files=tuple(sorted(checked)),
        raw_semantic_hash=raw_hash,
        summary_semantic_hash=summary_hash,
    )

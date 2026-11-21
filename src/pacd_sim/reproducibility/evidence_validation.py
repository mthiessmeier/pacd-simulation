"""Strict, checkout-anchored validation of retained diagnostic evidence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, cast

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from pacd_sim.audit.writer import EVENT_SCHEMA, EVENT_TYPES
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.defenders.base import DefenderContext
from pacd_sim.defenders.pacd.diagnostic import DiagnosticPACDDefender
from pacd_sim.engine.scheduler import DeterministicScheduler
from pacd_sim.evidence.normalize import EvidenceItem, normalize_observation
from pacd_sim.governance.governor import GovernanceContext, SafetyGovernor
from pacd_sim.harness.run import (
    ConfigurationError,
    _build_actions,
    _build_environment,
    _build_events,
    _build_policy,
    _load_json_config,
    _proposal_matches_candidate,
    _validate_loaded_configuration_bundle,
    load_yaml_config,
)
from pacd_sim.hypotheses.update import BeliefState, update_beliefs
from pacd_sim.metrics.summarize import SUMMARY_SCHEMA
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import (
    sha256_file,
    validate_retained_json_text_depth,
    validate_retained_value_depth,
)
from pacd_sim.reproducibility.paths import path_has_symlink_or_reparse
from pacd_sim.reproducibility.reportable import git_commit, git_is_dirty
from pacd_sim.schema import PolicyDisposition
from pacd_sim.state.snapshot import create_snapshot
from pacd_sim.telemetry.generator import DetectorProfile, Sensor, SyntheticTelemetryGenerator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID_RE = re.compile(r"^diagnostic-(\d{8}T\d{6}\.\d{6}Z)-seed-([0-9]+)(?:-[0-9a-f]{32})?$")
_MAX_RETAINED_JSON_BYTES = 4 * 1024 * 1024
_MAX_RAW_ARTIFACT_BYTES = 64 * 1024 * 1024
_MAX_SUMMARY_ARTIFACT_BYTES = 4 * 1024 * 1024
_MAX_PARQUET_AGGREGATE_ENCODED_BYTES = 64 * 1024 * 1024
_MAX_PARQUET_AGGREGATE_DECODED_BYTES = 64 * 1024 * 1024
_MAX_PARQUET_METADATA_BYTES = 2 * 1024 * 1024
_MAX_PARQUET_ROW_GROUPS = 128
_MAX_PARQUET_COLUMN_CHUNKS = 4096
_MAX_PARQUET_THRIFT_STRING_BYTES = 1024 * 1024
_MAX_PARQUET_THRIFT_CONTAINER_ITEMS = 8192
_MAX_RAW_LINE_BYTES = 128 * 1024
_MAX_RAW_PAYLOAD_BYTES = 64 * 1024
_MAX_RAW_IDENTIFIER_BYTES = 500
_MAX_SUMMARY_STRING_BYTES = 1024
_RAW_KEYS = frozenset(field.name for field in EVENT_SCHEMA)
_ACTION_EVENT_TYPES = frozenset(
    {"candidate_action", "safety_decision", "simulated_execution", "verification", "audit"}
)
_CANONICAL_CONFIG_KEYS = frozenset(
    {
        "evidence_label",
        "schema_version",
        "protocol_version",
        "scenario",
        "safety_policy",
        "baseline_definition",
        "metric_definition",
    }
)
_SEED_REGISTRY_KEYS = frozenset({"evidence_label", "schema_version", "seeds"})
_STATUS_KEYS = frozenset(
    {"evidence_label", "schema_version", "completion_status", "reportable", "seed"}
)
_CONFIGURATION_HASH_KEYS = frozenset(
    {"aggregate", "scenario", "safety_policy", "baseline_definition", "metric_definition"}
)
_MANIFEST_KEYS = frozenset(
    {
        "evidence_label",
        "schema_version",
        "run_id",
        "seed",
        "started_at",
        "ended_at",
        "completion_status",
        "reportable",
        "code_commit",
        "dirty_state",
        "python_version",
        "lockfile_hash",
        "os_class",
        "cpu_worker_count",
        "protocol_version",
        "config_hash_start",
        "config_hash_end",
        "configuration_hashes",
        "seed_registry_hash",
        "baseline_definition_hash",
        "metric_definition_hash",
        "raw_semantic_hash",
        "summary_semantic_hash",
        "test_status",
        "artifact_hashes",
    }
)
_MANIFEST_ARTIFACTS = frozenset(
    {
        "NON_REPORTABLE_DIAGNOSTIC",
        "canonical_config.json",
        "derived/episode_summary.csv",
        "derived/episode_summary.parquet",
        "logs/run.log",
        "raw/events.jsonl",
        "raw/events.parquet",
        "seed_registry.json",
        "status.json",
    }
)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key is prohibited: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"JSON NaN or infinity is prohibited: {value}")


def strict_json_loads(text: str, *, source: str) -> object:
    """Decode strict, depth-bounded JSON.

    ``MAX_RETAINED_PAYLOAD_DEPTH`` is the one documented container-depth limit
    for retained documents, JSONL records, and embedded payloads.
    """

    validate_retained_json_text_depth(text, source=source)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_json,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {source}: {error}") from error
    except RecursionError as error:
        raise ValueError(f"Excessively nested JSON in {source}") from error
    validate_retained_value_depth(value, source=source)
    return value


class _StrictDocumentError(ValueError):
    """Bounded parse failure that preserves the exact opened-file snapshot."""

    def __init__(
        self,
        message: str,
        *,
        digest: str,
        identity: _StableParquetIdentity,
    ) -> None:
        super().__init__(message)
        self.digest = digest
        self.identity = identity


def _read_strict_object(
    path: Path,
) -> tuple[dict[str, object], str, _StableParquetIdentity]:
    if path_has_symlink_or_reparse(path):
        raise ValueError(f"Retained JSON document path is indirect: {path.name}")
    before = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > _MAX_RETAINED_JSON_BYTES
    ):
        raise ValueError(f"Retained JSON document is not bounded and singly linked: {path.name}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        )
        if before_identity != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        ):
            raise ValueError(f"Opened retained JSON identity differs: {path.name}")
        encoded = handle.read(_MAX_RETAINED_JSON_BYTES + 1)
        opened_after = os.fstat(handle.fileno())
    after = path.stat(follow_symlinks=False)
    if (
        len(encoded) > _MAX_RETAINED_JSON_BYTES
        or before_identity
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
        or before_identity
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
    ):
        raise ValueError(f"Retained JSON document changed during bounded read: {path.name}")
    identity = _StableParquetIdentity(
        path=path,
        device=before.st_dev,
        inode=before.st_ino,
        size=before.st_size,
        mtime_ns=before.st_mtime_ns,
        link_count=before.st_nlink,
    )
    digest = hashlib.sha256(encoded).hexdigest()
    try:
        text = encoded.decode("utf-8")
        value = strict_json_loads(text, source=path.name)
        if not isinstance(value, dict):
            raise ValueError(f"Expected a JSON object: {path.name}")
        result = {str(key): item for key, item in value.items()}
        if text.encode("utf-8") != canonical_json_bytes(result):
            raise ValueError(f"JSON document is not canonical: {path.name}")
    except (RecursionError, UnicodeError, ValueError) as error:
        raise _StrictDocumentError(
            str(error),
            digest=digest,
            identity=identity,
        ) from error
    return result, digest, identity


def _exact_keys(
    value: Mapping[str, object], expected: frozenset[str], name: str, errors: list[str]
) -> bool:
    actual = frozenset(value)
    if actual == expected:
        return True
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    errors.append(f"{name} keys are not exact: missing={missing}; extra={extra}")
    return False


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _resolve_repository(workspace: Path, repo_root: Path | str | None) -> Path:
    repo_parent = (workspace / "repo").resolve(strict=True)
    if repo_root is None:
        candidates = tuple(
            path
            for path in repo_parent.iterdir()
            if path.is_dir() and (path / "pyproject.toml").is_file() and (path / "configs").is_dir()
        )
        if len(candidates) != 1:
            raise ValueError(
                "Verifier could not identify exactly one controlled repository; pass repo_root"
            )
        repository = candidates[0]
    else:
        repository = Path(repo_root)
    if path_has_symlink_or_reparse(repository):
        raise ValueError("Verifier repository path contains a symlink or reparse point")
    repository = repository.resolve(strict=True)
    if repository.parent != repo_parent:
        raise ValueError(
            "Verifier repository must be a direct child of the designated workspace repo directory"
        )
    controlled_paths = (
        repository / ".git",
        repository / "uv.lock",
        repository / "configs" / "scenarios" / "diagnostic_identity_smoke.yaml",
        repository / "configs" / "policies" / "diagnostic_safety.yaml",
        repository / "configs" / "seeds" / "diagnostic_seeds.json",
        repository / "configs" / "defenders" / "diagnostic_baseline.yaml",
        repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
    )
    for path in controlled_paths:
        if not path.exists() or path_has_symlink_or_reparse(path):
            raise ValueError(f"Controlled verifier input is absent or indirect: {path.name}")
    return repository


def _load_controlled_bundle(
    repository: Path,
) -> tuple[dict[str, object], dict[str, object], str, tuple[int, ...]]:
    scenario = load_yaml_config(
        repository / "configs" / "scenarios" / "diagnostic_identity_smoke.yaml"
    )
    policy = load_yaml_config(repository / "configs" / "policies" / "diagnostic_safety.yaml")
    seed_registry = _load_json_config(repository / "configs" / "seeds" / "diagnostic_seeds.json")
    baseline = load_yaml_config(repository / "configs" / "defenders" / "diagnostic_baseline.yaml")
    metrics = load_yaml_config(repository / "configs" / "metrics" / "diagnostic_metrics.yaml")
    protocol_version, seeds = _validate_loaded_configuration_bundle(
        scenario,
        policy,
        seed_registry,
        baseline,
        metrics,
    )
    canonical_config: dict[str, object] = {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "protocol_version": protocol_version,
        "scenario": scenario,
        "safety_policy": policy,
        "baseline_definition": baseline,
        "metric_definition": metrics,
    }
    return canonical_config, seed_registry, protocol_version, seeds


def _validate_document_shapes(
    root: Path,
    documents: Mapping[str, dict[str, object]],
    expected_config: dict[str, object],
    expected_seeds: dict[str, object],
    protocol_version: str,
    registered_seeds: tuple[int, ...],
    repository: Path,
    errors: list[str],
) -> None:
    canonical_config = documents["canonical_config.json"]
    seed_registry = documents["seed_registry.json"]
    status = documents["status.json"]
    manifest = documents["manifest.json"]
    _exact_keys(canonical_config, _CANONICAL_CONFIG_KEYS, "canonical_config.json", errors)
    _exact_keys(seed_registry, _SEED_REGISTRY_KEYS, "seed_registry.json", errors)
    _exact_keys(status, _STATUS_KEYS, "status.json", errors)
    _exact_keys(manifest, _MANIFEST_KEYS, "manifest.json", errors)

    if canonical_config != expected_config:
        errors.append("Retained canonical configuration does not match the controlled repository")
    if seed_registry != expected_seeds:
        errors.append("Retained seed registry does not match the controlled repository")

    manifest_seed = manifest.get("seed")
    if not _is_integer(manifest_seed) or manifest_seed not in registered_seeds:
        errors.append("Manifest seed is not a controlled registered seed")
    if status != {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "completion_status": "COMPLETED",
        "reportable": False,
        "seed": manifest_seed,
    }:
        errors.append("status.json does not match the exact completed diagnostic contract")

    configuration_hashes = manifest.get("configuration_hashes")
    if not isinstance(configuration_hashes, dict):
        errors.append("Manifest configuration_hashes is missing or invalid")
        configuration_hashes = {}
    else:
        _exact_keys(
            configuration_hashes,
            _CONFIGURATION_HASH_KEYS,
            "manifest.configuration_hashes",
            errors,
        )
    artifact_hashes = manifest.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict):
        errors.append("Manifest artifact_hashes is missing or invalid")
    else:
        if frozenset(str(key) for key in artifact_hashes) != _MANIFEST_ARTIFACTS:
            errors.append("Manifest artifact_hashes keys are not the exact artifact allowlist")
        if any(not _is_sha256(value) for value in artifact_hashes.values()):
            errors.append("Manifest artifact_hashes contains an invalid digest")

    scenario = cast(dict[str, object], expected_config["scenario"])
    policy = cast(dict[str, object], expected_config["safety_policy"])
    baseline = cast(dict[str, object], expected_config["baseline_definition"])
    metrics = cast(dict[str, object], expected_config["metric_definition"])
    config_hash = canonical_sha256(expected_config)
    expected_hashes = {
        "aggregate": config_hash,
        "scenario": canonical_sha256(scenario),
        "safety_policy": canonical_sha256(policy),
        "baseline_definition": canonical_sha256(baseline),
        "metric_definition": canonical_sha256(metrics),
    }
    if configuration_hashes != expected_hashes:
        errors.append("Manifest configuration hashes do not match controlled repository inputs")
    expected_manifest_values: dict[str, object] = {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "run_id": root.name,
        "completion_status": "COMPLETED",
        "reportable": False,
        "protocol_version": protocol_version,
        "config_hash_start": config_hash,
        "config_hash_end": config_hash,
        "seed_registry_hash": canonical_sha256(expected_seeds),
        "baseline_definition_hash": expected_hashes["baseline_definition"],
        "metric_definition_hash": expected_hashes["metric_definition"],
        "python_version": platform.python_version(),
        "lockfile_hash": sha256_file(repository / "uv.lock"),
        "os_class": platform.system(),
        "cpu_worker_count": 1,
        "test_status": "NOT_RUN",
    }
    for key, expected in expected_manifest_values.items():
        if manifest.get(key) != expected:
            errors.append(f"Manifest provenance or identity mismatch: {key}")
    for digest_name in ("raw_semantic_hash", "summary_semantic_hash"):
        if not _is_sha256(manifest.get(digest_name)):
            errors.append(f"Manifest contains an invalid digest: {digest_name}")
    commit_value = manifest.get("code_commit")
    if not isinstance(commit_value, str) or _COMMIT_RE.fullmatch(commit_value) is None:
        errors.append("Manifest code_commit is not a canonical Git commit")
    else:
        try:
            if commit_value != git_commit(repository):
                errors.append("Manifest code_commit does not match the controlled checkout")
        except (OSError, PermissionError, RuntimeError, ValueError) as error:
            errors.append(f"Could not establish controlled Git commit: {error}")
    dirty_value = manifest.get("dirty_state")
    if not isinstance(dirty_value, bool):
        errors.append("Manifest dirty_state must be a boolean")
    else:
        try:
            actual_dirty = git_is_dirty(repository)
            if dirty_value is not actual_dirty:
                errors.append("Manifest dirty_state does not match the controlled checkout")
            if dirty_value or actual_dirty:
                errors.append("Independent verification requires a clean controlled checkout")
        except (OSError, PermissionError, RuntimeError, ValueError) as error:
            errors.append(f"Could not establish controlled Git dirty state: {error}")
    timestamps: dict[str, datetime] = {}
    for timestamp_name in ("started_at", "ended_at"):
        timestamp = manifest.get(timestamp_name)
        if not isinstance(timestamp, str):
            errors.append(f"Manifest {timestamp_name} must be an ISO-8601 string")
            continue
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"Manifest {timestamp_name} is not valid ISO-8601")
        else:
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                errors.append(f"Manifest {timestamp_name} must include a timezone")
            else:
                timestamps[timestamp_name] = parsed
    if set(timestamps) == {"started_at", "ended_at"}:
        elapsed = timestamps["ended_at"] - timestamps["started_at"]
        if elapsed.total_seconds() < 0 or elapsed.total_seconds() >= 300:
            errors.append("Manifest timestamps violate the bounded diagnostic runtime")
        run_id_match = _RUN_ID_RE.fullmatch(root.name)
        if run_id_match is None:
            errors.append("Run directory name does not match the canonical diagnostic run ID")
        else:
            run_timestamp_text, run_seed_text = run_id_match.groups()
            run_timestamp = datetime.strptime(run_timestamp_text, "%Y%m%dT%H%M%S.%fZ").replace(
                tzinfo=UTC
            )
            start_offset = (timestamps["started_at"] - run_timestamp).total_seconds()
            if not 0 <= start_offset <= 60:
                errors.append("Manifest start time is inconsistent with the diagnostic run ID")
            if str(manifest_seed) != run_seed_text:
                errors.append("Manifest seed is inconsistent with the diagnostic run ID")


def _expected_event_rows(
    canonical_config: Mapping[str, object], seed: int
) -> list[dict[str, object]]:
    scenario = cast(dict[str, object], canonical_config["scenario"])
    policy_config = cast(dict[str, object], canonical_config["safety_policy"])
    protocol_version = cast(str, canonical_config["protocol_version"])
    environment = _build_environment(scenario, protocol_version)
    scheduled_events = _build_events(scenario, protocol_version)
    observations = SyntheticTelemetryGenerator(
        seed,
        Sensor(
            id="sensor-synthetic-diagnostic",
            configuration_version=protocol_version,
            detector_profile_id="detector-profile-diagnostic",
            delay_ticks=cast(
                int,
                cast(dict[str, object], scenario["telemetry"])["delay_ticks"],
            ),
        ),
        DetectorProfile(
            id="detector-profile-diagnostic",
            configuration_version=protocol_version,
            noise_standard_deviation=cast(
                float,
                cast(dict[str, object], scenario["telemetry"])["noise_standard_deviation"],
            ),
        ),
    ).generate_many(DeterministicScheduler(scheduled_events).run())

    rows: list[dict[str, object]] = []

    def emit(
        event_type: str,
        *,
        tick: int | float,
        entity_id: str = "",
        action_id: str = "",
        disposition: str = "",
        outcome: str = "",
        payload: Mapping[str, object] | None = None,
    ) -> None:
        rows.append(
            {
                "event_type": event_type,
                "tick": float(tick),
                "entity_id": entity_id,
                "action_id": action_id,
                "disposition": disposition,
                "outcome": outcome,
                "payload": dict(payload or {}),
            }
        )

    emit(
        "run_started",
        tick=0,
        outcome="started",
        payload={
            "scheduler": "simpy",
            "state_graph": "networkx_detached_view",
            "synthetic_only": True,
        },
    )
    evidence_items: list[EvidenceItem] = []
    belief_state = BeliefState(configuration_version=protocol_version)
    state = environment
    actions_processed = False
    governor = SafetyGovernor(_build_policy(policy_config))
    defender = DiagnosticPACDDefender(compromise_threshold=0.5)
    for observation in observations:
        emit(
            "observation",
            tick=observation.tick,
            entity_id=observation.identity_id or observation.target_id or "synthetic-unknown",
            outcome="observed",
            payload={
                "event_id": observation.event_id,
                "event_kind": observation.event_kind,
                "signal": observation.signal,
                "sensor_id": observation.sensor_id,
                "synthetic": True,
            },
        )
        evidence = normalize_observation(observation)
        evidence_items.append(evidence)
        benign = evidence.category == "benign_context"
        classification = "benign_negative_control" if benign else "synthetic_adversary_indicator"
        emit(
            "evidence",
            tick=evidence.tick,
            entity_id=evidence.subject_id or "synthetic-unknown",
            outcome="not_compromised" if benign else "indicator_retained",
            payload={
                "classification": classification,
                "confidence": evidence.confidence,
                "evidence_id": evidence.id,
                "integrity": evidence.integrity,
            },
        )
        state = state.at_tick(observation.tick)
        graph = state.to_graph(multigraph=True)
        snapshot = create_snapshot(state)
        emit(
            "state_update",
            tick=state.tick,
            entity_id=state.id,
            outcome="immutable_snapshot",
            payload={
                "graph_edge_count": graph.number_of_edges(),
                "graph_node_count": graph.number_of_nodes(),
                "snapshot_digest": snapshot.environment_digest,
            },
        )
        belief_state = update_beliefs(evidence_items)
        compromise_probability = (
            belief_state.compromise_probability(evidence.subject_id)
            if evidence.subject_id is not None
            else 0.1
        )
        emit(
            "hypothesis",
            tick=belief_state.tick,
            entity_id=evidence.subject_id or belief_state.id,
            outcome="not_compromised" if benign else "uncertainty_updated",
            payload={
                "classification": classification,
                "compromise_probability": compromise_probability,
                "hypothesis_ids": [item.id for item in belief_state.hypotheses],
            },
        )
        context = DefenderContext(
            id=f"defender-context-{observation.id}",
            tick=observation.tick,
            configuration_version=protocol_version,
            evidence=tuple(evidence_items),
            belief_state=belief_state,
            environment=state,
        )
        defender_decision = defender.decide(context)
        if observation.event_kind != "simulated_adversary" or actions_processed:
            continue
        actions = _build_actions(scenario, protocol_version, observation.tick)
        for action in actions:
            matching_proposal = next(
                (
                    proposal
                    for proposal in defender_decision.proposed_actions
                    if _proposal_matches_candidate(proposal, action)
                ),
                None,
            )
            proposer = (
                defender.defender_id if matching_proposal is not None else "diagnostic-safety-probe"
            )
            emit(
                "candidate_action",
                tick=action.tick,
                entity_id=action.target_id,
                action_id=action.id,
                outcome="candidate_only",
                payload={
                    "action_digest": canonical_sha256(action),
                    "action_type": action.action_type,
                    "configuration_version": action.configuration_version,
                    "proposer": proposer,
                    "requested_authority": action.requested_authority,
                    "reversible": action.reversible,
                },
            )
            governance_context = GovernanceContext(
                tick=action.tick,
                configuration_version=protocol_version,
            )
            decision = governor.evaluate(
                action,
                belief_state=belief_state,
                mission_state=create_snapshot(state),
                context=governance_context,
            )
            emit(
                "safety_decision",
                tick=decision.tick,
                entity_id=action.target_id,
                action_id=action.id,
                disposition=decision.disposition.value,
                outcome="decided",
                payload={
                    "action_digest": decision.action_digest,
                    "action_type": decision.action_type,
                    "configuration_version": decision.configuration_version,
                    "governance_context_digest": decision.governance_context_digest,
                    "policy_decision_id": decision.id,
                    "policy_digest": decision.policy_digest,
                    "policy_version": decision.policy_version,
                    "reason": decision.reason,
                    "state_digest": decision.state_digest,
                    "target_id": decision.target_id,
                },
            )
            if decision.disposition is PolicyDisposition.APPROVE:
                if matching_proposal is None or action.action_type != "isolate_session":
                    raise ConfigurationError(
                        "Only a defender-proposed supported isolation action may be reconstructed "
                        "as executed"
                    )
                before_digest = canonical_sha256(state)
                state = state.at_tick(max(state.tick, action.tick, decision.tick)).isolate_session(
                    action.target_id
                )
                after_digest = canonical_sha256(state)
                execution_id = f"execution-{action.id}"
                emit(
                    "simulated_execution",
                    tick=decision.tick,
                    entity_id=action.target_id,
                    action_id=action.id,
                    disposition=decision.disposition.value,
                    outcome="executed",
                    payload={
                        "action_configuration_version": action.configuration_version,
                        "action_type": action.action_type,
                        "adapter": "simulated_only",
                        "authorized_action_digest": decision.action_digest,
                        "authorized_state_digest": decision.state_digest,
                        "execution_id": execution_id,
                        "network_enabled": False,
                        "policy_decision_id": decision.id,
                        "policy_decision_digest": canonical_sha256(decision),
                        "policy_digest": decision.policy_digest,
                        "state_after_digest": after_digest,
                        "state_before_digest": before_digest,
                        "target_id": action.target_id,
                    },
                )
                emit(
                    "verification",
                    tick=decision.tick,
                    entity_id=action.target_id,
                    action_id=action.id,
                    disposition="VERIFIED",
                    outcome="verified",
                    payload={
                        "execution_id": execution_id,
                        "expected_effect_observed": True,
                        "state_hashes_valid": True,
                        "verification_id": f"verification-{execution_id}",
                    },
                )
            else:
                emit(
                    "verification",
                    tick=decision.tick,
                    entity_id=action.target_id,
                    action_id=action.id,
                    disposition=decision.disposition.value,
                    outcome="not_executed",
                    payload={"reason": "governor disposition did not permit execution"},
                )
            emit(
                "audit",
                tick=decision.tick,
                entity_id=action.target_id,
                action_id=action.id,
                disposition=decision.disposition.value,
                outcome="recorded",
                payload={"candidate_and_decision_retained": True},
            )
        actions_processed = True
    final_tick = float(max((observation.tick for observation in observations), default=0))
    emit(
        "manifest",
        tick=final_tick,
        outcome="artifact_generation_started",
        payload={"event_chain_status": "COMPLETED", "manifest_format": "canonical_json"},
    )
    return rows


@dataclass(frozen=True)
class RetainedEvidenceValidation:
    """Strict evidence result carrying the only materialized Parquet tables."""

    errors: tuple[str, ...]
    raw_table: pa.Table | None = None
    summary_table: pa.Table | None = None
    raw_rows: tuple[dict[str, object], ...] = ()
    summary_rows: tuple[dict[str, object], ...] = ()
    raw_encoded_sha256: str | None = None
    summary_encoded_sha256: str | None = None
    raw_file_identity: _StableParquetIdentity | None = None
    summary_file_identity: _StableParquetIdentity | None = None
    documents: Mapping[str, dict[str, object]] | None = None
    document_sha256: Mapping[str, str] | None = None
    document_identities: Mapping[str, _StableParquetIdentity] | None = None
    document_ingestion_failed: bool = False
    parquet_ingestion_failed: bool = False


@dataclass(frozen=True)
class _StableParquetIdentity:
    """Opened-file identity binding one table and digest to one path."""

    path: Path
    device: int
    inode: int
    size: int
    mtime_ns: int
    link_count: int

    def stat_tuple(self) -> tuple[int, int, int, int, int]:
        return (self.device, self.inode, self.size, self.mtime_ns, self.link_count)


@dataclass(frozen=True)
class _BoundedParquetIngestion:
    errors: tuple[str, ...]
    raw_table: pa.Table | None = None
    raw_rows: tuple[dict[str, object], ...] = ()
    raw_encoded_sha256: str | None = None
    raw_file_identity: _StableParquetIdentity | None = None
    summary_table: pa.Table | None = None
    summary_rows: tuple[dict[str, object], ...] = ()
    summary_encoded_sha256: str | None = None
    summary_file_identity: _StableParquetIdentity | None = None


def _opened_parquet_identity(path: Path, handle: BinaryIO) -> _StableParquetIdentity:
    before = path.stat(follow_symlinks=False)
    opened = os.fstat(handle.fileno())
    before_tuple = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    opened_tuple = (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_nlink,
    )
    if (
        path_has_symlink_or_reparse(path)
        or not stat.S_ISREG(before.st_mode)
        or not stat.S_ISREG(opened.st_mode)
        or before.st_nlink != 1
        or before_tuple != opened_tuple
    ):
        raise ValueError("Parquet path is not a stable, singly linked regular file")
    return _StableParquetIdentity(
        path=path,
        device=opened.st_dev,
        inode=opened.st_ino,
        size=opened.st_size,
        mtime_ns=opened.st_mtime_ns,
        link_count=opened.st_nlink,
    )


def _parquet_identity_is_stable(
    identity: _StableParquetIdentity,
    handle: BinaryIO | None = None,
) -> bool:
    try:
        path_stat = identity.path.stat(follow_symlinks=False)
        if path_has_symlink_or_reparse(identity.path) or identity.stat_tuple() != (
            path_stat.st_dev,
            path_stat.st_ino,
            path_stat.st_size,
            path_stat.st_mtime_ns,
            path_stat.st_nlink,
        ):
            return False
        if handle is not None:
            opened = os.fstat(handle.fileno())
            if identity.stat_tuple() != (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_nlink,
            ):
                return False
    except OSError:
        return False
    return True


def _sha256_open_parquet(handle: BinaryIO, identity: _StableParquetIdentity) -> str:
    digest = hashlib.sha256()
    total = 0
    handle.seek(0)
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        total += len(chunk)
        if total > identity.size:
            raise ValueError("Parquet file grew during bounded hashing")
        digest.update(chunk)
    handle.seek(0)
    if total != identity.size or not _parquet_identity_is_stable(identity, handle):
        raise ValueError("Parquet file changed during bounded hashing")
    return digest.hexdigest()


def _preflight_parquet_file(
    source: BinaryIO,
    *,
    artifact_name: str,
    expected_schema: pa.Schema,
    expected_row_count: int,
    decoded_size_limit: int,
    errors: list[str],
) -> tuple[Any | None, int]:
    """Open only Parquet metadata and reject unbounded or inexact structures."""
    try:
        starting_error_count = len(errors)
        parquet_file = pq.ParquetFile(
            source,
            thrift_string_size_limit=_MAX_PARQUET_THRIFT_STRING_BYTES,
            thrift_container_size_limit=_MAX_PARQUET_THRIFT_CONTAINER_ITEMS,
        )
        metadata = parquet_file.metadata
        if not parquet_file.schema_arrow.equals(expected_schema, check_metadata=True):
            errors.append(f"{artifact_name} schema is not exact")
        if metadata.num_rows != expected_row_count:
            if artifact_name == "Raw Parquet":
                errors.append(
                    "Raw event count does not match the independently reconstructed "
                    "diagnostic chain"
                )
            else:
                errors.append(
                    f"{artifact_name} row count is not exactly {expected_row_count}: "
                    f"{metadata.num_rows}"
                )
        if metadata.num_columns != len(expected_schema):
            errors.append(f"{artifact_name} column metadata count is not exact")
        if not 1 <= metadata.num_row_groups <= min(_MAX_PARQUET_ROW_GROUPS, expected_row_count):
            errors.append(f"{artifact_name} row-group metadata exceeds the bounded limit")
        serialized_size = metadata.serialized_size
        if serialized_size < 0 or serialized_size > _MAX_PARQUET_METADATA_BYTES:
            errors.append(f"{artifact_name} footer metadata exceeds the bounded limit")
        if len(errors) != starting_error_count:
            return parquet_file, 0

        decoded_column_bytes = 0
        column_chunks = 0
        row_group_rows = 0
        for row_group_index in range(metadata.num_row_groups):
            row_group = metadata.row_group(row_group_index)
            row_group_rows += row_group.num_rows
            if row_group.num_rows <= 0 or row_group.num_rows > expected_row_count:
                errors.append(f"{artifact_name} row-group row count is invalid")
            if row_group.num_columns != len(expected_schema):
                errors.append(f"{artifact_name} row-group column count is not exact")
                continue
            if row_group.total_byte_size < 0 or row_group.total_byte_size > decoded_size_limit:
                errors.append(f"{artifact_name} row-group decoded size exceeds the bounded limit")
            for column_index in range(row_group.num_columns):
                column_chunks += 1
                if column_chunks > _MAX_PARQUET_COLUMN_CHUNKS:
                    errors.append(f"{artifact_name} column metadata exceeds the bounded limit")
                    break
                column = row_group.column(column_index)
                decoded_size = column.total_uncompressed_size
                encoded_size = column.total_compressed_size
                if decoded_size < 0 or encoded_size < 0:
                    errors.append(f"{artifact_name} column metadata contains an invalid size")
                    continue
                if column.num_values != row_group.num_rows:
                    errors.append(f"{artifact_name} column value count is not exact")
                decoded_column_bytes += decoded_size
                if decoded_column_bytes > decoded_size_limit:
                    errors.append(f"{artifact_name} decoded column data exceeds the bounded cap")
                    break
        if row_group_rows != metadata.num_rows:
            errors.append(f"{artifact_name} row-group totals do not match its row count")
        return parquet_file, decoded_column_bytes
    except (
        IndexError,
        MemoryError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        errors.append(f"Could not preflight {artifact_name}: {error}")
        return None, 0


def _validate_materialized_table(
    table: pa.Table,
    *,
    artifact_name: str,
    expected_schema: pa.Schema,
    expected_row_count: int,
    decoded_size_limit: int,
    errors: list[str],
) -> None:
    """Validate the bounded table before exposing it to any verifier consumer."""
    if not table.schema.equals(expected_schema, check_metadata=True):
        errors.append(f"Materialized {artifact_name} schema is not exact")
    if table.num_rows != expected_row_count:
        errors.append(f"Materialized {artifact_name} row count is not exact")
    if table.nbytes > decoded_size_limit:
        errors.append(f"Materialized {artifact_name} exceeds the decoded-size cap")


def _validate_string_bounds(
    table: pa.Table,
    *,
    artifact_name: str,
    field_limits: Mapping[str, int],
    errors: list[str],
) -> None:
    """Enforce Arrow-buffer UTF-8 bounds before rows reach Python consumers."""
    try:
        for field_name, byte_limit in field_limits.items():
            column = table[field_name]
            if column.null_count:
                errors.append(f"{artifact_name} field {field_name} contains a null value")
                continue
            maximum = pc.max(pc.binary_length(column)).as_py()
            if not isinstance(maximum, int) or maximum > byte_limit:
                errors.append(f"{artifact_name} field {field_name} exceeds its bounded UTF-8 limit")
    except (
        IndexError,
        KeyError,
        MemoryError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        errors.append(f"Could not validate {artifact_name} string bounds: {error}")


def _ingest_bounded_parquet(
    artifacts: Mapping[str, Path],
    *,
    expected_raw_row_count: int,
) -> _BoundedParquetIngestion:
    """Preflight both retained Parquet files, then materialize each at most once."""
    errors: list[str] = []
    raw_path = artifacts["raw/events.parquet"]
    summary_path = artifacts["derived/episode_summary.parquet"]

    def failed() -> _BoundedParquetIngestion:
        return _BoundedParquetIngestion(errors=tuple(errors))

    try:
        with raw_path.open("rb") as raw_handle, summary_path.open("rb") as summary_handle:
            raw_identity = _opened_parquet_identity(raw_path, raw_handle)
            summary_identity = _opened_parquet_identity(summary_path, summary_handle)
            if raw_identity.size > _MAX_RAW_ARTIFACT_BYTES:
                errors.append("Raw Parquet encoded file exceeds the 64 MiB cap")
            if summary_identity.size > _MAX_SUMMARY_ARTIFACT_BYTES:
                errors.append("Derived summary Parquet encoded file exceeds the 4 MiB cap")
            if raw_identity.size + summary_identity.size > _MAX_PARQUET_AGGREGATE_ENCODED_BYTES:
                errors.append("Aggregate encoded Parquet size exceeds the bounded cap")
            if errors:
                return failed()

            raw_encoded_sha256 = _sha256_open_parquet(raw_handle, raw_identity)
            summary_encoded_sha256 = _sha256_open_parquet(
                summary_handle,
                summary_identity,
            )
            raw_file, raw_decoded_size = _preflight_parquet_file(
                raw_handle,
                artifact_name="Raw Parquet",
                expected_schema=EVENT_SCHEMA,
                expected_row_count=expected_raw_row_count,
                decoded_size_limit=_MAX_RAW_ARTIFACT_BYTES,
                errors=errors,
            )
            summary_file, summary_decoded_size = _preflight_parquet_file(
                summary_handle,
                artifact_name="Derived summary Parquet",
                expected_schema=SUMMARY_SCHEMA,
                expected_row_count=1,
                decoded_size_limit=_MAX_SUMMARY_ARTIFACT_BYTES,
                errors=errors,
            )
            if raw_decoded_size + summary_decoded_size > _MAX_PARQUET_AGGREGATE_DECODED_BYTES:
                errors.append("Aggregate decoded Parquet size exceeds the bounded cap")
            if errors or raw_file is None or summary_file is None:
                return failed()

            try:
                raw_table = raw_file.read()
            except (
                MemoryError,
                OSError,
                OverflowError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as error:
                errors.append(f"Could not materialize bounded Raw Parquet: {error}")
                return failed()
            if not _parquet_identity_is_stable(raw_identity, raw_handle):
                errors.append("Raw Parquet path identity changed during materialization")
                return failed()

            _validate_materialized_table(
                raw_table,
                artifact_name="Raw Parquet",
                expected_schema=EVENT_SCHEMA,
                expected_row_count=expected_raw_row_count,
                decoded_size_limit=_MAX_RAW_ARTIFACT_BYTES,
                errors=errors,
            )
            if errors:
                return failed()
            _validate_string_bounds(
                raw_table,
                artifact_name="Raw Parquet",
                field_limits={
                    "evidence_label": _MAX_RAW_IDENTIFIER_BYTES,
                    "schema_version": _MAX_RAW_IDENTIFIER_BYTES,
                    "run_id": _MAX_RAW_IDENTIFIER_BYTES,
                    "event_type": _MAX_RAW_IDENTIFIER_BYTES,
                    "entity_id": _MAX_RAW_IDENTIFIER_BYTES,
                    "action_id": _MAX_RAW_IDENTIFIER_BYTES,
                    "disposition": _MAX_RAW_IDENTIFIER_BYTES,
                    "outcome": _MAX_RAW_IDENTIFIER_BYTES,
                    "config_hash": _MAX_RAW_IDENTIFIER_BYTES,
                    "payload_json": _MAX_RAW_PAYLOAD_BYTES,
                },
                errors=errors,
            )
            if errors:
                return failed()
            try:
                raw_rows = tuple(
                    {str(key): item for key, item in row.items()} for row in raw_table.to_pylist()
                )
            except (MemoryError, OverflowError, RuntimeError, TypeError, ValueError) as error:
                errors.append(f"Could not decode bounded Raw Parquet rows: {error}")
                return failed()

            try:
                summary_table = summary_file.read()
            except (
                MemoryError,
                OSError,
                OverflowError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as error:
                errors.append(f"Could not materialize bounded Derived summary Parquet: {error}")
                return failed()
            if not _parquet_identity_is_stable(summary_identity, summary_handle):
                errors.append(
                    "Derived summary Parquet path identity changed during materialization"
                )
                return failed()

            _validate_materialized_table(
                summary_table,
                artifact_name="Derived summary Parquet",
                expected_schema=SUMMARY_SCHEMA,
                expected_row_count=1,
                decoded_size_limit=_MAX_SUMMARY_ARTIFACT_BYTES,
                errors=errors,
            )
            if errors:
                return failed()
            _validate_string_bounds(
                summary_table,
                artifact_name="Derived summary Parquet",
                field_limits={
                    "evidence_label": _MAX_SUMMARY_STRING_BYTES,
                    "schema_version": _MAX_SUMMARY_STRING_BYTES,
                    "config_hash": _MAX_SUMMARY_STRING_BYTES,
                    "completion_status": _MAX_SUMMARY_STRING_BYTES,
                },
                errors=errors,
            )
            if errors:
                return failed()
            try:
                summary_rows = tuple(
                    {str(key): item for key, item in row.items()}
                    for row in summary_table.to_pylist()
                )
            except (MemoryError, OverflowError, RuntimeError, TypeError, ValueError) as error:
                errors.append(f"Could not decode bounded Derived summary Parquet rows: {error}")
                return failed()
            if not _parquet_identity_is_stable(
                raw_identity,
                raw_handle,
            ) or not _parquet_identity_is_stable(summary_identity, summary_handle):
                errors.append("Parquet path identity changed during bounded ingestion")
                return failed()
            return _BoundedParquetIngestion(
                errors=(),
                raw_table=raw_table,
                raw_rows=raw_rows,
                raw_encoded_sha256=raw_encoded_sha256,
                raw_file_identity=raw_identity,
                summary_table=summary_table,
                summary_rows=summary_rows,
                summary_encoded_sha256=summary_encoded_sha256,
                summary_file_identity=summary_identity,
            )
    except (
        MemoryError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        errors.append(f"Could not establish stable bounded Parquet ingestion: {error}")
        return failed()


def _validate_raw_events(
    artifacts: Mapping[str, Path],
    manifest: Mapping[str, object],
    canonical_config: Mapping[str, object],
    parquet_rows: tuple[dict[str, object], ...],
    expected_rows: list[dict[str, object]],
    errors: list[str],
) -> None:
    jsonl_path = artifacts["raw/events.jsonl"]
    seed = manifest.get("seed")
    if not _is_integer(seed):
        errors.append("Cannot reconstruct raw events because manifest seed is invalid")
        return
    if jsonl_path.stat().st_size > _MAX_RAW_ARTIFACT_BYTES:
        errors.append("Raw evidence exceeds the 64 MiB bounded-read cap")
        return
    jsonl_rows: list[dict[str, object]] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if len(line.encode("utf-8")) > _MAX_RAW_LINE_BYTES:
                errors.append(f"Raw JSONL line {line_number} exceeds the 128 KiB cap")
                return
            if not line.strip():
                errors.append(f"Raw JSONL contains a blank line at {line_number}")
                continue
            value = strict_json_loads(line, source=f"raw/events.jsonl:{line_number}")
            if not isinstance(value, dict):
                errors.append(f"Raw JSONL row {line_number} is not an object")
                continue
            row = {str(key): item for key, item in value.items()}
            if line.rstrip("\r\n").encode("utf-8") != canonical_json_bytes(row):
                errors.append(f"Raw JSONL row {line_number} is not canonical JSON")
            payload_text = row.get("payload_json")
            if not isinstance(payload_text, str):
                errors.append(f"Raw JSONL row {line_number} payload_json is not a string")
            elif len(payload_text.encode("utf-8")) > _MAX_RAW_PAYLOAD_BYTES:
                errors.append(f"Raw JSONL row {line_number} payload_json exceeds its bounded cap")
            else:
                payload = strict_json_loads(
                    payload_text,
                    source=f"raw/events.jsonl payload_json row {line_number}",
                )
                if not isinstance(payload, dict):
                    errors.append(f"Raw JSONL row {line_number} payload is not an object")
                elif payload_text.encode("utf-8") != canonical_json_bytes(payload):
                    errors.append(f"Raw JSONL row {line_number} payload_json is not canonical JSON")
            jsonl_rows.append(row)
    if errors:
        return
    if tuple(jsonl_rows) != parquet_rows:
        errors.append("JSONL and Parquet raw-event rows are not exactly identical")
        return

    run_id = manifest.get("run_id")
    config_hash = canonical_sha256(canonical_config)
    previous_tick = -1.0
    for index, row in enumerate(parquet_rows, start=1):
        if frozenset(row) != _RAW_KEYS:
            errors.append(f"Raw row {index} keys are not exact")
        if row.get("sequence") != index:
            errors.append("Raw event sequences must be unique and exactly contiguous from 1")
        tick = row.get("tick")
        if (
            isinstance(tick, bool)
            or not isinstance(tick, (int, float))
            or not math.isfinite(float(tick))
            or float(tick) < previous_tick
            or float(tick) < 0
        ):
            errors.append(f"Raw row {index} has an invalid or decreasing tick")
        else:
            previous_tick = float(tick)
        expected_base = {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "sequence": index,
            "seed": seed,
            "config_hash": config_hash,
        }
        for key, expected in expected_base.items():
            if row.get(key) != expected:
                errors.append(f"Raw row {index} identity mismatch: {key}")
        event_type = row.get("event_type")
        if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
            errors.append(f"Raw row {index} has an unknown event type")
        action_id = row.get("action_id")
        if isinstance(event_type, str) and event_type in _ACTION_EVENT_TYPES:
            if not isinstance(action_id, str) or not action_id:
                errors.append(f"Raw action event {index} has no action ID")
        elif action_id != "":
            errors.append(f"Raw non-action event {index} carries an action ID")
        payload_text = row.get("payload_json")
        if not isinstance(payload_text, str):
            errors.append(f"Raw row {index} payload_json is not a string")
            continue
        payload = strict_json_loads(payload_text, source=f"payload_json row {index}")
        if not isinstance(payload, dict):
            errors.append(f"Raw row {index} payload is not an object")
            continue
        if payload_text.encode("utf-8") != canonical_json_bytes(payload):
            errors.append(f"Raw row {index} payload_json is not canonical JSON")
        if index <= len(expected_rows):
            expected = expected_rows[index - 1]
            for key in (
                "event_type",
                "tick",
                "entity_id",
                "action_id",
                "disposition",
                "outcome",
            ):
                if row.get(key) != expected[key]:
                    errors.append(
                        f"Raw row {index} does not match reconstructed {key}: {event_type}"
                    )
            if payload != expected["payload"]:
                errors.append(
                    f"Raw row {index} payload does not match reconstructed event semantics"
                )


def validate_retained_evidence(
    root: Path,
    artifacts: Mapping[str, Path],
    workspace: Path,
    *,
    repo_root: Path | str | None,
) -> RetainedEvidenceValidation:
    """Validate retained evidence and return the sole bounded Parquet materialization."""
    errors: list[str] = []
    raw_table: pa.Table | None = None
    summary_table: pa.Table | None = None
    raw_rows: tuple[dict[str, object], ...] = ()
    summary_rows: tuple[dict[str, object], ...] = ()
    raw_encoded_sha256: str | None = None
    summary_encoded_sha256: str | None = None
    raw_file_identity: _StableParquetIdentity | None = None
    summary_file_identity: _StableParquetIdentity | None = None
    documents: dict[str, dict[str, object]] = {}
    document_sha256: dict[str, str] = {}
    document_identities: dict[str, _StableParquetIdentity] = {}
    document_ingestion_failed = False
    parquet_ingestion_failed = False
    try:
        repository = _resolve_repository(workspace, repo_root)
        expected_config, expected_seeds, protocol_version, registered_seeds = (
            _load_controlled_bundle(repository)
        )
        document_names = (
            "canonical_config.json",
            "seed_registry.json",
            "status.json",
            "manifest.json",
        )
        for name in document_names:
            try:
                document, digest, identity = _read_strict_object(artifacts[name])
                documents[name] = document
                document_sha256[name] = digest
                document_identities[name] = identity
            except _StrictDocumentError as error:
                document_ingestion_failed = True
                document_sha256[name] = error.digest
                document_identities[name] = error.identity
                errors.append(f"Strict retained-evidence verification failed for {name}: {error}")
                return RetainedEvidenceValidation(
                    errors=tuple(errors),
                    documents=documents,
                    document_sha256=document_sha256,
                    document_identities=document_identities,
                    document_ingestion_failed=True,
                )
            except (OSError, RecursionError, TypeError, UnicodeError, ValueError) as error:
                document_ingestion_failed = True
                errors.append(f"Strict retained-evidence verification failed for {name}: {error}")
                return RetainedEvidenceValidation(
                    errors=tuple(errors),
                    documents=documents,
                    document_sha256=document_sha256,
                    document_identities=document_identities,
                    document_ingestion_failed=True,
                )
        if len(documents) == len(document_names):
            _validate_document_shapes(
                root,
                documents,
                expected_config,
                expected_seeds,
                protocol_version,
                registered_seeds,
                repository,
                errors,
            )
        if errors:
            return RetainedEvidenceValidation(
                errors=tuple(errors),
                documents=documents,
                document_sha256=document_sha256,
                document_identities=document_identities,
            )
        manifest = documents.get("manifest.json")
        if manifest is None:
            return RetainedEvidenceValidation(
                errors=tuple(errors),
                documents=documents,
                document_sha256=document_sha256,
                document_identities=document_identities,
            )
        seed = manifest.get("seed")
        if not _is_integer(seed):
            errors.append("Cannot preflight Parquet row counts because manifest seed is invalid")
            return RetainedEvidenceValidation(
                errors=tuple(errors),
                documents=documents,
                document_sha256=document_sha256,
                document_identities=document_identities,
            )
        expected_rows = _expected_event_rows(expected_config, cast(int, seed))
        ingestion = _ingest_bounded_parquet(
            artifacts,
            expected_raw_row_count=len(expected_rows),
        )
        errors.extend(ingestion.errors)
        if ingestion.errors:
            parquet_ingestion_failed = True
            return RetainedEvidenceValidation(
                errors=tuple(errors),
                documents=documents,
                document_sha256=document_sha256,
                document_identities=document_identities,
                parquet_ingestion_failed=True,
            )
        raw_table = ingestion.raw_table
        raw_rows = ingestion.raw_rows
        raw_encoded_sha256 = ingestion.raw_encoded_sha256
        raw_file_identity = ingestion.raw_file_identity
        summary_table = ingestion.summary_table
        summary_rows = ingestion.summary_rows
        summary_encoded_sha256 = ingestion.summary_encoded_sha256
        summary_file_identity = ingestion.summary_file_identity
        if len(documents) == len(document_names):
            _validate_raw_events(
                artifacts,
                manifest,
                expected_config,
                raw_rows,
                expected_rows,
                errors,
            )
        if errors:
            return RetainedEvidenceValidation(
                errors=tuple(errors),
                documents=documents,
                document_sha256=document_sha256,
                document_identities=document_identities,
                raw_encoded_sha256=raw_encoded_sha256,
                summary_encoded_sha256=summary_encoded_sha256,
                raw_file_identity=raw_file_identity,
                summary_file_identity=summary_file_identity,
            )
    except (
        ConfigurationError,
        OSError,
        PermissionError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as error:
        errors.append(f"Strict retained-evidence verification failed: {error}")
        raw_table = None
        summary_table = None
        raw_rows = ()
        summary_rows = ()
        parquet_ingestion_failed = False
    return RetainedEvidenceValidation(
        errors=tuple(errors),
        raw_table=raw_table,
        summary_table=summary_table,
        raw_rows=raw_rows,
        summary_rows=summary_rows,
        raw_encoded_sha256=raw_encoded_sha256,
        summary_encoded_sha256=summary_encoded_sha256,
        raw_file_identity=raw_file_identity,
        summary_file_identity=summary_file_identity,
        documents=documents,
        document_sha256=document_sha256,
        document_identities=document_identities,
        document_ingestion_failed=document_ingestion_failed,
        parquet_ingestion_failed=parquet_ingestion_failed,
    )

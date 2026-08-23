"""Strict, checkout-anchored validation of retained diagnostic evidence."""

from __future__ import annotations

import json
import math
import platform
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

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
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import sha256_file
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
_MAX_RAW_LINE_BYTES = 128 * 1024
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
    """Decode strict JSON while rejecting duplicate keys and non-finite constants."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_json,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {source}: {error}") from error


def _read_strict_object(path: Path) -> dict[str, object]:
    if path.stat().st_size > _MAX_RETAINED_JSON_BYTES:
        raise ValueError(f"Retained JSON document exceeds the 4 MiB cap: {path.name}")
    text = path.read_text(encoding="utf-8")
    value = strict_json_loads(text, source=path.name)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    result = {str(key): item for key, item in value.items()}
    if text.encode("utf-8") != canonical_json_bytes(result):
        raise ValueError(f"JSON document is not canonical: {path.name}")
    return result


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
        graph = state.to_graph()
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


def _validate_raw_events(
    artifacts: Mapping[str, Path],
    manifest: Mapping[str, object],
    canonical_config: Mapping[str, object],
    errors: list[str],
) -> None:
    parquet_path = artifacts["raw/events.parquet"]
    jsonl_path = artifacts["raw/events.jsonl"]
    seed = manifest.get("seed")
    if not _is_integer(seed):
        errors.append("Cannot reconstruct raw events because manifest seed is invalid")
        return
    expected_rows = _expected_event_rows(canonical_config, cast(int, seed))
    if (
        parquet_path.stat().st_size > _MAX_RAW_ARTIFACT_BYTES
        or jsonl_path.stat().st_size > _MAX_RAW_ARTIFACT_BYTES
    ):
        errors.append("Raw evidence exceeds the 64 MiB bounded-read cap")
        return
    parquet_file = pq.ParquetFile(parquet_path)
    if not parquet_file.schema_arrow.equals(EVENT_SCHEMA, check_metadata=True):
        errors.append("Raw Parquet schema is not exactly EVENT_SCHEMA")
        return
    if parquet_file.metadata.num_rows != len(expected_rows):
        errors.append(
            "Raw event count does not match the independently reconstructed diagnostic chain"
        )
        return
    table = parquet_file.read()
    parquet_rows = [{str(key): item for key, item in row.items()} for row in table.to_pylist()]
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
            jsonl_rows.append(row)
    if jsonl_rows != parquet_rows:
        errors.append("JSONL and Parquet raw-event rows are not exactly identical")

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
) -> tuple[str, ...]:
    """Validate exact schemas, controlled provenance, and reconstructed raw semantics."""
    errors: list[str] = []
    try:
        repository = _resolve_repository(workspace, repo_root)
        expected_config, expected_seeds, protocol_version, registered_seeds = (
            _load_controlled_bundle(repository)
        )
        documents = {
            name: _read_strict_object(artifacts[name])
            for name in (
                "canonical_config.json",
                "seed_registry.json",
                "status.json",
                "manifest.json",
            )
        }
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
        _validate_raw_events(
            artifacts,
            documents["manifest.json"],
            expected_config,
            errors,
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
    return tuple(errors)

"""Independent, deterministic NON_REPORTABLE_DIAGNOSTIC evaluation harness."""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import platform
import re
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, TextIO, cast
from uuid import uuid4

import yaml
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, TagToken

from pacd_sim.actions.models import DefensiveAction, RequestedAuthority
from pacd_sim.audit.writer import AuditWriter
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.defenders.base import DefenderContext
from pacd_sim.defenders.pacd.diagnostic import DiagnosticPACDDefender
from pacd_sim.engine.scheduler import DeterministicScheduler, ScheduledEvent
from pacd_sim.environment.model import (
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.evidence.normalize import EvidenceItem, normalize_observation
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.execution.verification import verify_execution
from pacd_sim.governance.governor import GovernanceContext, SafetyGovernor, SafetyPolicy
from pacd_sim.hypotheses.update import BeliefState, update_beliefs
from pacd_sim.metrics.summarize import summarize_raw_events
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import (
    build_manifest,
    collect_artifact_hashes,
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
    write_canonical_json,
    write_manifest,
    write_sha256s,
)
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_write_path,
    default_workspace_root,
    infer_workspace_root,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
)
from pacd_sim.reproducibility.reportable import (
    ReportableModeDenied,
    git_commit,
    git_is_dirty,
    validate_reportable_approval,
)
from pacd_sim.schema import PolicyDisposition, VerificationDisposition
from pacd_sim.state.snapshot import create_snapshot
from pacd_sim.telemetry.generator import DetectorProfile, Sensor, SyntheticTelemetryGenerator

_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_CONFIG_DEPTH = 40
_MAX_CONFIG_NODES = 10_000
_MAX_DIAGNOSTIC_EVENTS = 100
_MAX_DIAGNOSTIC_ACTIONS = 100
_MAX_DIAGNOSTIC_SECONDS = 300.0


class ConfigurationError(ValueError):
    """Raised when a diagnostic input is unsafe, ambiguous, or out of bounds."""


class DiagnosticTimeoutError(RuntimeError):
    """Raised after the bounded worker is terminated at the runtime limit."""


class _StrictSafeLoader(yaml.SafeLoader):  # type: ignore[misc]
    """SafeLoader variant that additionally rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _StrictSafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[str, object]:
    loader.flatten_mapping(node)
    mapping: dict[str, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConfigurationError("Configuration mapping keys must be strings")
        if key in mapping:
            raise ConfigurationError(f"Duplicate configuration key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _validate_configuration_tree(value: object) -> None:
    node_count = 0
    active_containers: set[int] = set()

    def visit(item: object, depth: int) -> None:
        nonlocal node_count
        node_count += 1
        if node_count > _MAX_CONFIG_NODES:
            raise ConfigurationError("Configuration exceeds the expanded-node limit")
        if depth > _MAX_CONFIG_DEPTH:
            raise ConfigurationError("Configuration exceeds the nesting-depth limit")
        if isinstance(item, float) and not math.isfinite(item):
            raise ConfigurationError("Configuration may not contain NaN or infinity")
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in active_containers:
                raise ConfigurationError("Recursive YAML aliases are not permitted")
            active_containers.add(identity)
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ConfigurationError("Configuration mapping keys must be strings")
                visit(child, depth + 1)
            active_containers.remove(identity)
            return
        if isinstance(item, list):
            identity = id(item)
            if identity in active_containers:
                raise ConfigurationError("Recursive YAML aliases are not permitted")
            active_containers.add(identity)
            for child in item:
                visit(child, depth + 1)
            active_containers.remove(identity)
            return
        if item is not None and not isinstance(item, (str, int, float, bool)):
            raise ConfigurationError(f"Unsupported configuration value type: {type(item).__name__}")

    visit(value, 0)


def load_yaml_config(path: Path | str, *, max_aliases: int = 20) -> dict[str, object]:
    """Load bounded YAML through SafeLoader with no custom tags or duplicate keys."""
    if isinstance(max_aliases, bool) or not isinstance(max_aliases, int) or max_aliases < 0:
        raise ValueError("max_aliases must be a nonnegative integer")
    source = Path(path)
    if source.suffix.lower() not in {".yaml", ".yml"}:
        raise ConfigurationError("Configuration input must use .yaml or .yml")
    if not source.is_file() or source.is_symlink():
        raise ConfigurationError("Configuration input must be a regular, non-symlink file")
    if source.stat().st_size > _MAX_CONFIG_BYTES:
        raise ConfigurationError("Configuration exceeds the 1 MiB input limit")
    text = source.read_text(encoding="utf-8")
    try:
        tokens = tuple(yaml.scan(text))
    except yaml.YAMLError as error:
        raise ConfigurationError("Configuration is not valid YAML") from error
    alias_count = sum(isinstance(token, AliasToken) for token in tokens)
    if alias_count > max_aliases:
        raise ConfigurationError(
            f"Configuration contains {alias_count} aliases; maximum is {max_aliases}"
        )
    if any(isinstance(token, TagToken) for token in tokens):
        raise ConfigurationError("Explicit YAML tags are not permitted")
    loader = _StrictSafeLoader(text)
    try:
        value = loader.get_single_data()
    except (yaml.YAMLError, ConfigurationError) as error:
        raise ConfigurationError("Configuration failed strict safe loading") from error
    finally:
        loader.dispose()
    if not isinstance(value, dict):
        raise ConfigurationError("Configuration root must be a mapping")
    _validate_configuration_tree(value)
    return {str(key): item for key, item in value.items()}


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"Duplicate JSON configuration key: {key}")
        result[key] = value
    return result


def _load_json_config(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ConfigurationError("JSON configuration must be a regular, non-symlink file")
    if path.stat().st_size > _MAX_CONFIG_BYTES:
        raise ConfigurationError("JSON configuration exceeds the 1 MiB input limit")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ConfigurationError("JSON configuration is invalid") from error
    if not isinstance(value, dict):
        raise ConfigurationError("JSON configuration root must be an object")
    _validate_configuration_tree(value)
    return {str(key): item for key, item in value.items()}


def _discover_repo_root(source: Path) -> Path:
    for candidate in (source.parent, *source.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "configs").is_dir():
            return candidate.resolve(strict=True)
    raise ConfigurationError("Could not establish repository root from diagnostic configuration")


def _assert_controlled_config(path: Path | str, repo_root: Path) -> Path:
    candidate = Path(path)
    if path_has_symlink_or_reparse(candidate):
        raise ConfigurationError(
            "Configuration symlinks, junctions, and reparse points are not permitted"
        )
    resolved = candidate.resolve(strict=True)
    controlled_root = (repo_root / "configs").resolve(strict=True)
    try:
        resolved.relative_to(controlled_root)
    except ValueError as error:
        raise ConfigurationError(
            "Configuration input is outside the controlled configs tree"
        ) from error
    return resolved


def _expect_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _expect_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{name} must be a list")
    return value


def _expect_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{name} must be a nonempty string")
    return value


def _expect_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer")
    return value


def _expect_probability(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ConfigurationError(f"{name} must be finite and in [0,1]")
    return result


def _validate_label(config: Mapping[str, object], name: str) -> None:
    if config.get("evidence_label") != EVIDENCE_LABEL:
        raise ConfigurationError(f"{name} must be labeled {EVIDENCE_LABEL}")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ConfigurationError(f"{name} schema_version must be {SCHEMA_VERSION}")


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    name: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected={','.join(unexpected)}")
        raise ConfigurationError(f"{name} keys are not exact: {'; '.join(details)}")


def _validate_exact_configuration_shapes(
    scenario: Mapping[str, object],
    policy: Mapping[str, object],
    baseline: Mapping[str, object],
    metrics: Mapping[str, object],
    seed_registry: Mapping[str, object],
) -> None:
    _require_exact_keys(
        scenario,
        {
            "evidence_label",
            "schema_version",
            "protocol_version",
            "name",
            "synthetic",
            "default_seed",
            "telemetry",
            "identities",
            "sessions",
            "services",
            "missions",
            "events",
            "actions",
        },
        "scenario",
    )
    telemetry = _expect_mapping(scenario.get("telemetry"), "telemetry")
    _require_exact_keys(
        telemetry,
        {"noise_standard_deviation", "delay_ticks"},
        "telemetry",
    )
    nested_shapes = (
        ("identities", {"id", "role"}, "identity"),
        ("sessions", {"id", "identity_id", "service_id"}, "session"),
        ("services", {"id", "mission_id"}, "service"),
        ("missions", {"id", "criticality"}, "mission"),
        ("events", {"id", "tick", "kind", "identity_id"}, "event"),
        (
            "actions",
            {"id", "action_type", "target_id", "reversible", "requested_authority"},
            "action",
        ),
    )
    for collection_name, expected_keys, item_name in nested_shapes:
        for raw_item in _expect_list(scenario.get(collection_name), collection_name):
            item = _expect_mapping(raw_item, item_name)
            _require_exact_keys(item, expected_keys, item_name)

    _require_exact_keys(
        policy,
        {
            "evidence_label",
            "schema_version",
            "allowed_action_types",
            "escalated_action_types",
            "prohibited_action_types",
            "execution_adapter",
            "network_enabled",
        },
        "policy",
    )
    _require_exact_keys(
        baseline,
        {"evidence_label", "schema_version", "name", "observations", "actions"},
        "baseline",
    )
    _require_exact_keys(
        metrics,
        {"evidence_label", "schema_version", "metrics", "comparative_claims"},
        "metrics",
    )
    _require_exact_keys(
        seed_registry,
        {"evidence_label", "schema_version", "seeds"},
        "seed registry",
    )


def _build_environment(scenario: Mapping[str, object], protocol_version: str) -> EnvironmentState:
    identities = tuple(
        Identity(
            id=_expect_string(item["id"], "identity.id"),
            role=_expect_string(item["role"], "identity.role"),
            configuration_version=protocol_version,
        )
        for item in (
            _expect_mapping(value, "identity")
            for value in _expect_list(scenario.get("identities"), "identities")
        )
    )
    missions = tuple(
        MissionFunction(
            id=_expect_string(item["id"], "mission.id"),
            criticality=_expect_probability(item.get("criticality"), "mission.criticality"),
            configuration_version=protocol_version,
        )
        for item in (
            _expect_mapping(value, "mission")
            for value in _expect_list(scenario.get("missions"), "missions")
        )
    )
    services = tuple(
        Service(
            id=_expect_string(item["id"], "service.id"),
            mission_id=_expect_string(item["mission_id"], "service.mission_id"),
            configuration_version=protocol_version,
        )
        for item in (
            _expect_mapping(value, "service")
            for value in _expect_list(scenario.get("services"), "services")
        )
    )
    sessions = tuple(
        Session(
            id=_expect_string(item["id"], "session.id"),
            identity_id=_expect_string(item["identity_id"], "session.identity_id"),
            service_id=_expect_string(item["service_id"], "session.service_id"),
            configuration_version=protocol_version,
        )
        for item in (
            _expect_mapping(value, "session")
            for value in _expect_list(scenario.get("sessions"), "sessions")
        )
    )
    if not identities or not missions or not services or not sessions:
        raise ConfigurationError(
            "Diagnostic scenario must include identity, mission, service, and session"
        )
    return EnvironmentState(
        configuration_version=protocol_version,
        identities=identities,
        sessions=sessions,
        services=services,
        mission_functions=missions,
    )


def _build_events(
    scenario: Mapping[str, object], protocol_version: str
) -> tuple[ScheduledEvent, ...]:
    values = _expect_list(scenario.get("events"), "events")
    if not 0 < len(values) <= _MAX_DIAGNOSTIC_EVENTS:
        raise ConfigurationError("Diagnostic event count is outside the bounded range")
    events: list[ScheduledEvent] = []
    for raw_value in values:
        item = _expect_mapping(raw_value, "event")
        tick = _expect_int(item.get("tick"), "event.tick")
        if not 0 <= tick <= 10_000:
            raise ConfigurationError("Diagnostic event tick is outside the bounded range")
        identity_value = item.get("identity_id")
        events.append(
            ScheduledEvent(
                id=_expect_string(item.get("id"), "event.id"),
                tick=tick,
                configuration_version=protocol_version,
                kind=_expect_string(item.get("kind"), "event.kind"),
                identity_id=(
                    _expect_string(identity_value, "event.identity_id")
                    if identity_value is not None
                    else None
                ),
            )
        )
    kinds = {event.kind for event in events}
    if not {"benign_administrative", "simulated_adversary"}.issubset(kinds):
        raise ConfigurationError("Diagnostic requires benign and simulated-adversary events")
    return tuple(events)


def _build_actions(
    scenario: Mapping[str, object], protocol_version: str, tick: int
) -> tuple[DefensiveAction, ...]:
    values = _expect_list(scenario.get("actions"), "actions")
    if not 0 < len(values) <= _MAX_DIAGNOSTIC_ACTIONS:
        raise ConfigurationError("Diagnostic action count is outside the bounded range")
    actions: list[DefensiveAction] = []
    action_ids: set[str] = set()
    for raw_value in values:
        item = _expect_mapping(raw_value, "action")
        action_id = _expect_string(item.get("id"), "action.id")
        if action_id in action_ids:
            raise ConfigurationError(f"Duplicate diagnostic action ID: {action_id}")
        action_ids.add(action_id)
        requested_authority = _expect_string(
            item.get("requested_authority"), "action.requested_authority"
        )
        if requested_authority not in {"automatic", "human", "prohibited"}:
            raise ConfigurationError("action.requested_authority is invalid")
        reversible = item.get("reversible")
        if not isinstance(reversible, bool):
            raise ConfigurationError("action.reversible must be a boolean")
        actions.append(
            DefensiveAction(
                id=action_id,
                tick=tick,
                configuration_version=protocol_version,
                action_type=_expect_string(item.get("action_type"), "action.action_type"),
                target_id=_expect_string(item.get("target_id"), "action.target_id"),
                reversible=reversible,
                requested_authority=cast(RequestedAuthority, requested_authority),
                rollback=("restore exact prior immutable synthetic state" if reversible else None),
            )
        )
    return tuple(actions)


def _proposal_matches_candidate(
    proposal: DefensiveAction,
    candidate: DefensiveAction,
) -> bool:
    """Bind an executable configured candidate to a defender-proposed transition."""
    return (
        proposal.tick == candidate.tick
        and proposal.schema_version == candidate.schema_version
        and proposal.configuration_version == candidate.configuration_version
        and proposal.action_type == candidate.action_type
        and proposal.target_id == candidate.target_id
        and proposal.reversible == candidate.reversible
        and proposal.requested_authority == candidate.requested_authority
    )


def _build_policy(config: Mapping[str, object]) -> SafetyPolicy:
    def action_types(name: str) -> tuple[str, ...]:
        return tuple(_expect_string(value, name) for value in _expect_list(config.get(name), name))

    if (
        config.get("execution_adapter") != "simulated_only"
        or config.get("network_enabled") is not False
    ):
        raise ConfigurationError("Safety policy must select simulated_only with network disabled")
    return SafetyPolicy(
        allowed_action_types=action_types("allowed_action_types"),
        escalated_action_types=action_types("escalated_action_types"),
        prohibited_action_types=action_types("prohibited_action_types"),
        execution_adapter="simulated_only",
        network_enabled=False,
    )


def _validate_seed_registry(registry: Mapping[str, object]) -> tuple[int, ...]:
    _validate_label(registry, "seed registry")
    seeds = tuple(
        _expect_int(value, "seed") for value in _expect_list(registry.get("seeds"), "seeds")
    )
    if not seeds or len(seeds) > 100 or len(seeds) != len(set(seeds)):
        raise ConfigurationError("Seed registry must contain 1-100 unique seeds")
    if any(seed < 0 or seed >= 2**63 for seed in seeds):
        raise ConfigurationError("Seeds must be nonnegative signed 64-bit integers")
    return seeds


def _validate_loaded_configuration_bundle(
    scenario: Mapping[str, object],
    policy_config: Mapping[str, object],
    seed_registry: Mapping[str, object],
    baseline_definition: Mapping[str, object],
    metric_definition: Mapping[str, object],
) -> tuple[str, tuple[int, ...]]:
    for name, config in (
        ("scenario", scenario),
        ("policy", policy_config),
        ("baseline", baseline_definition),
        ("metrics", metric_definition),
    ):
        _validate_label(config, name)
    _validate_exact_configuration_shapes(
        scenario,
        policy_config,
        baseline_definition,
        metric_definition,
        seed_registry,
    )
    _expect_string(scenario.get("name"), "scenario.name")
    _expect_string(baseline_definition.get("name"), "baseline.name")
    if scenario.get("synthetic") is not True:
        raise ConfigurationError("Diagnostic scenario must explicitly declare synthetic=true")
    if baseline_definition.get("observations") != "synthetic_only":
        raise ConfigurationError("Diagnostic baseline must use synthetic_only observations")
    if baseline_definition.get("actions") != "none":
        raise ConfigurationError("Diagnostic baseline must declare actions=none")
    if metric_definition.get("comparative_claims") is not False:
        raise ConfigurationError("Diagnostic metrics must prohibit comparative claims")
    configured_metrics = tuple(
        _expect_string(value, "metrics.metrics")
        for value in _expect_list(metric_definition.get("metrics"), "metrics.metrics")
    )
    expected_metrics = {
        "event_count",
        "approved_action_count",
        "prohibited_action_count",
    }
    if set(configured_metrics) != expected_metrics or len(configured_metrics) != len(
        expected_metrics
    ):
        raise ConfigurationError("Diagnostic metric definitions do not match the governed set")

    protocol_version = _expect_string(scenario.get("protocol_version"), "protocol_version")
    registered_seeds = _validate_seed_registry(seed_registry)
    default_seed = _expect_int(scenario.get("default_seed"), "default_seed")
    if default_seed not in registered_seeds:
        raise ConfigurationError("Scenario default_seed is absent from the seed registry")

    environment = _build_environment(scenario, protocol_version)
    events = _build_events(scenario, protocol_version)
    policy = _build_policy(policy_config)
    action_tick = max(event.tick for event in events)
    actions = _build_actions(scenario, protocol_version, action_tick)
    governor = SafetyGovernor(policy)
    dispositions = {governor.evaluate(action).disposition for action in actions}
    required_dispositions = {
        PolicyDisposition.APPROVE,
        PolicyDisposition.ESCALATE,
        PolicyDisposition.PROHIBIT,
    }
    if not required_dispositions.issubset(dispositions):
        raise ConfigurationError("Governed actions must exercise APPROVE, ESCALATE, and PROHIBIT")
    approved_actions = [
        action
        for action in actions
        if governor.evaluate(action).disposition is PolicyDisposition.APPROVE
    ]
    if any(environment.get_session(action.target_id) is None for action in approved_actions):
        raise ConfigurationError("Approved diagnostic action targets an unknown session")
    return protocol_version, registered_seeds


def validate_diagnostic_configuration_files(
    repo_root: Path | str,
) -> dict[str, str]:
    """Fully validate all governed diagnostic inputs without creating output."""
    repository = Path(repo_root).resolve(strict=True)
    scenario = load_yaml_config(
        _assert_controlled_config(
            repository / "configs" / "scenarios" / "diagnostic_identity_smoke.yaml",
            repository,
        )
    )
    policy_config = load_yaml_config(
        _assert_controlled_config(
            repository / "configs" / "policies" / "diagnostic_safety.yaml",
            repository,
        )
    )
    seed_registry = _load_json_config(
        _assert_controlled_config(
            repository / "configs" / "seeds" / "diagnostic_seeds.json",
            repository,
        )
    )
    baseline_definition = load_yaml_config(
        _assert_controlled_config(
            repository / "configs" / "defenders" / "diagnostic_baseline.yaml",
            repository,
        )
    )
    metric_definition = load_yaml_config(
        _assert_controlled_config(
            repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
            repository,
        )
    )
    protocol_version, _registered_seeds = _validate_loaded_configuration_bundle(
        scenario,
        policy_config,
        seed_registry,
        baseline_definition,
        metric_definition,
    )
    canonical_config: dict[str, object] = {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "protocol_version": protocol_version,
        "scenario": scenario,
        "safety_policy": policy_config,
        "baseline_definition": baseline_definition,
        "metric_definition": metric_definition,
    }
    return {
        "protocol_version": protocol_version,
        "config_hash": canonical_sha256(canonical_config),
        "scenario_hash": canonical_sha256(scenario),
        "safety_policy_hash": canonical_sha256(policy_config),
        "seed_registry_hash": canonical_sha256(seed_registry),
        "baseline_definition_hash": canonical_sha256(baseline_definition),
        "metric_definition_hash": canonical_sha256(metric_definition),
    }


def _write_labelled_text(path: Path, text: str, workspace_root: Path) -> Path:
    target = assert_write_path(path, workspace_root)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return target


def _replace_task_created_json(
    path: Path,
    value: Mapping[str, object],
    workspace_root: Path,
) -> Path:
    """Atomically replace task-created run metadata during fail-closed finalization."""
    target = assert_write_path(path, workspace_root)
    temporary = assert_write_path(target.with_name(target.name + ".replacement"), workspace_root)
    if temporary.exists():
        raise RuntimeError("Task-created metadata replacement file already exists")
    with temporary.open("xb") as handle:
        handle.write(canonical_json_bytes(dict(value)))
    temporary.replace(target)
    return target


def _log(handle: TextIO, message: str) -> None:
    handle.write(f"[{EVIDENCE_LABEL}] {message}\n")
    handle.flush()


def _new_run_directory(
    output_root: Path,
    workspace_root: Path,
    seed: int,
    *,
    invocation_token: str | None = None,
) -> tuple[str, Path, Path]:
    if invocation_token is not None and re.fullmatch(r"[0-9a-f]{32}", invocation_token) is None:
        raise ValueError("Diagnostic invocation token is invalid")
    if path_has_symlink_or_reparse(output_root):
        raise PathBoundaryError("Diagnostic output path contains a symlink or reparse point")
    authorized_output_input = workspace_root / "var" / "runs"
    staging_root_input = workspace_root / "var" / "tmp"
    if path_has_symlink_or_reparse(authorized_output_input) or path_has_symlink_or_reparse(
        staging_root_input
    ):
        raise PathBoundaryError("Diagnostic run roots contain a symlink or reparse point")
    authorized_output = assert_write_path(authorized_output_input, workspace_root)
    output = assert_write_path(output_root, workspace_root)
    if output != authorized_output:
        raise PathBoundaryError("Diagnostic output_root must be exactly workspace/var/runs")
    output.mkdir(parents=True, exist_ok=True)
    staging_root = assert_write_path(staging_root_input, workspace_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    run_id = f"diagnostic-{timestamp}-seed-{seed}"
    if invocation_token is not None:
        run_id = f"{run_id}-{invocation_token}"
    final_dir = assert_write_path(output / run_id, workspace_root)
    staging_dir = assert_write_path(staging_root / f"{run_id}.staging", workspace_root)
    if final_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing run directory: {final_dir}")
    staging_created_by_task = False
    try:
        staging_dir.mkdir(parents=False, exist_ok=False)
        staging_created_by_task = True
    except FileExistsError as error:
        # An existing path may belong to another process or predate this task.  Its
        # presence is not evidence that this invocation created it, so leave it
        # byte-for-byte untouched and fail closed.
        raise FileExistsError(
            f"Refusing to modify existing staging directory: {staging_dir}"
        ) from error
    except OSError:
        # Path.mkdir only establishes ownership by returning successfully.  If it
        # raises for any other reason, do not inspect, label, move, or replace the
        # target based merely on its existence.
        raise
    if not staging_created_by_task:
        raise RuntimeError("Staging directory ownership was not established")
    return run_id, staging_dir, final_dir


def _retain_failed_run(
    run_dir: Path,
    final_run_dir: Path,
    workspace_root: Path,
    seed: int,
    error: Exception,
    *,
    log_path: Path | None = None,
) -> None:
    """Mark and retain a task-created staging run without deleting raw evidence."""
    if log_path is not None and log_path.is_file():
        try:
            with log_path.open("a", encoding="utf-8", newline="\n") as failure_log:
                _log(failure_log, f"diagnostic failed; error_type={type(error).__name__}")
        except OSError:
            pass
    _replace_task_created_json(
        run_dir / "status.json",
        {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "completion_status": "FAILED",
            "reportable": False,
            "seed": seed,
            "error_type": type(error).__name__,
        },
        workspace_root,
    )
    failed_manifest_path = run_dir / "manifest.json"
    if failed_manifest_path.is_file():
        try:
            failed_manifest_value = json.loads(failed_manifest_path.read_text(encoding="utf-8"))
            if isinstance(failed_manifest_value, dict):
                failed_manifest = {str(key): value for key, value in failed_manifest_value.items()}
                failed_manifest["completion_status"] = "FAILED"
                failed_manifest["failure_type"] = type(error).__name__
                _replace_task_created_json(
                    failed_manifest_path,
                    failed_manifest,
                    workspace_root,
                )
        except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError):
            pass
    if run_dir.exists() and not final_run_dir.exists():
        run_dir.replace(final_run_dir)


@dataclass(frozen=True)
class RunResult:
    """Paths and normalized digests returned by one completed diagnostic."""

    run_dir: Path
    run_id: str
    seed: int
    config_hash: str
    raw_semantic_hash: str
    summary_semantic_hash: str
    manifest_path: Path
    elapsed_seconds: float
    evidence_label: str = EVIDENCE_LABEL

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["run_dir"] = str(self.run_dir)
        value["manifest_path"] = str(self.manifest_path)
        return value


def _run_diagnostic_worker(
    scenario_path: Path | str,
    policy_path: Path | str,
    seed_registry_path: Path | str,
    output_root: Path | str,
    *,
    seed: int | None = None,
    workspace_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    baseline_path: Path | str | None = None,
    metric_path: Path | str | None = None,
    reportable: bool = False,
    _invocation_token: str | None = None,
) -> RunResult:
    """Run the tiny synthetic diagnostic and retain a fully verified artifact set."""
    start_counter = time.perf_counter()
    initial_scenario = Path(scenario_path)
    repository = (
        Path(repo_root).resolve(strict=True)
        if repo_root is not None
        else _discover_repo_root(initial_scenario.resolve(strict=True))
    )
    workspace = (
        resolve_workspace_root(workspace_root)
        if workspace_root is not None
        else infer_workspace_root(repository)
    )
    if workspace != default_workspace_root():
        raise PathBoundaryError(
            "Diagnostic worker authority must equal the author-designated PACD workspace"
        )
    repository_parent = (workspace / "repo").resolve(strict=False)
    if repository.parent != repository_parent:
        raise ConfigurationError(
            "Repository must be a direct child of the designated PACD workspace repo directory"
        )

    scenario_file = _assert_controlled_config(scenario_path, repository)
    policy_file = _assert_controlled_config(policy_path, repository)
    seed_file = _assert_controlled_config(seed_registry_path, repository)
    baseline_file = _assert_controlled_config(
        baseline_path or repository / "configs" / "defenders" / "diagnostic_baseline.yaml",
        repository,
    )
    metric_file = _assert_controlled_config(
        metric_path or repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
        repository,
    )

    scenario = load_yaml_config(scenario_file)
    policy_config = load_yaml_config(policy_file)
    seed_registry = _load_json_config(seed_file)
    baseline_definition = load_yaml_config(baseline_file)
    metric_definition = load_yaml_config(metric_file)
    protocol_version, registered_seeds = _validate_loaded_configuration_bundle(
        scenario,
        policy_config,
        seed_registry,
        baseline_definition,
        metric_definition,
    )
    selected_seed = (
        _expect_int(scenario.get("default_seed"), "default_seed") if seed is None else seed
    )
    if isinstance(selected_seed, bool) or not isinstance(selected_seed, int):
        raise ConfigurationError("Selected seed must be an integer")
    if selected_seed not in registered_seeds:
        raise ConfigurationError("Selected seed is not present in the controlled seed registry")

    canonical_config: dict[str, object] = {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "protocol_version": protocol_version,
        "scenario": scenario,
        "safety_policy": policy_config,
        "baseline_definition": baseline_definition,
        "metric_definition": metric_definition,
    }
    config_hash = canonical_sha256(canonical_config)
    scenario_hash = canonical_sha256(scenario)
    safety_policy_hash = canonical_sha256(policy_config)
    seed_registry_hash = canonical_sha256(seed_registry)
    baseline_definition_hash = canonical_sha256(baseline_definition)
    metric_definition_hash = canonical_sha256(metric_definition)

    if reportable:
        validate_reportable_approval(
            repository,
            config_hash=config_hash,
            seed_registry_hash=seed_registry_hash,
            baseline_definition_hash=baseline_definition_hash,
            metric_definition_hash=metric_definition_hash,
            protocol_version=protocol_version,
        )
        raise ReportableModeDenied(
            "The bootstrap implements diagnostics only; reportable execution remains unavailable"
        )

    environment = _build_environment(scenario, protocol_version)
    scheduled_events = _build_events(scenario, protocol_version)
    safety_policy = _build_policy(policy_config)
    scheduler = DeterministicScheduler(scheduled_events)
    delivered_events = scheduler.run()
    telemetry_config = _expect_mapping(scenario.get("telemetry"), "telemetry")
    noise = telemetry_config.get("noise_standard_deviation")
    delay = _expect_int(telemetry_config.get("delay_ticks"), "telemetry.delay_ticks")
    noise_value = _expect_probability(noise, "telemetry.noise_standard_deviation")
    if not 0 <= delay <= 100:
        raise ConfigurationError("telemetry.delay_ticks is outside the bounded range")
    profile = DetectorProfile(
        id="detector-profile-diagnostic",
        configuration_version=protocol_version,
        noise_standard_deviation=noise_value,
    )
    sensor = Sensor(
        id="sensor-synthetic-diagnostic",
        configuration_version=protocol_version,
        detector_profile_id=profile.id,
        delay_ticks=delay,
    )
    observations = SyntheticTelemetryGenerator(selected_seed, sensor, profile).generate_many(
        delivered_events
    )
    if len(observations) != len(delivered_events):
        raise RuntimeError("Full-coverage diagnostic telemetry unexpectedly omitted an event")

    run_id, run_dir, final_run_dir = _new_run_directory(
        Path(output_root),
        workspace,
        selected_seed,
        invocation_token=_invocation_token,
    )
    log_path = run_dir / "logs" / "run.log"
    try:
        started_at = datetime.now(UTC).isoformat()
        marker_path = _write_labelled_text(
            run_dir / EVIDENCE_LABEL,
            EVIDENCE_LABEL + "\n",
            workspace,
        )
        del marker_path
        canonical_path = write_canonical_json(
            run_dir / "canonical_config.json", canonical_config, workspace_root=workspace
        )
        seed_registry_path_copy = write_canonical_json(
            run_dir / "seed_registry.json", seed_registry, workspace_root=workspace
        )
        config_hash_start = sha256_file(canonical_path)
        if config_hash_start != config_hash:
            raise RuntimeError("Canonical configuration hash differs before simulation")
        if sha256_file(seed_registry_path_copy) != seed_registry_hash:
            raise RuntimeError("Canonical seed registry hash differs before simulation")

        logs_dir = assert_write_path(run_dir / "logs", workspace)
        logs_dir.mkdir(parents=False, exist_ok=False)
        log_path = assert_write_path(logs_dir / "run.log", workspace)
        log_handle = log_path.open("x", encoding="utf-8", newline="\n")
    except Exception as error:
        _retain_failed_run(
            run_dir,
            final_run_dir,
            workspace,
            selected_seed,
            error,
            log_path=log_path,
        )
        raise
    audit: AuditWriter | None = None
    try:
        _log(log_handle, "bounded synthetic diagnostic started")
        _log(log_handle, "SimPy scheduler and detached NetworkX state enabled")
        audit = AuditWriter(
            run_dir,
            run_id,
            config_hash,
            selected_seed,
            workspace_root=workspace,
        )
        audit.emit(
            "run_started",
            tick=0,
            outcome="started",
            payload={
                "scheduler": "simpy",
                "state_graph": "networkx_detached_view",
                "synthetic_only": True,
            },
        )

        governor = SafetyGovernor(safety_policy)
        broker = SimulatedExecutionBroker(governor)
        defender = DiagnosticPACDDefender(compromise_threshold=0.5)
        evidence_items: list[EvidenceItem] = []
        belief_state = BeliefState(configuration_version=protocol_version)
        state = environment
        actions_processed = False

        for observation in observations:
            audit.emit(
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
            classification = (
                "benign_negative_control" if benign else "synthetic_adversary_indicator"
            )
            audit.emit(
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
            audit.emit(
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
            if benign and compromise_probability >= 0.5:
                raise RuntimeError("Benign negative control was treated as compromise")
            audit.emit(
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
            if not defender_decision.proposed_actions:
                raise RuntimeError(
                    "Diagnostic defender did not propose the expected bounded action"
                )

            actions = _build_actions(scenario, protocol_version, observation.tick)
            observed_dispositions: set[PolicyDisposition] = set()
            for action in actions:
                matching_proposal = next(
                    (
                        proposed
                        for proposed in defender_decision.proposed_actions
                        if _proposal_matches_candidate(proposed, action)
                    ),
                    None,
                )
                proposer = (
                    defender.defender_id
                    if matching_proposal is not None
                    else "diagnostic-safety-probe"
                )
                audit.emit(
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
                observed_dispositions.add(decision.disposition)
                audit.emit(
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
                if decision.permits_execution:
                    if matching_proposal is None:
                        raise RuntimeError(
                            "Governor-approved diagnostic candidate was not proposed "
                            "by the defender"
                        )
                    execution = broker.execute(action, decision, state)
                    if not execution.executed:
                        raise RuntimeError(
                            "Approved diagnostic action did not execute in simulation"
                        )
                    state = execution.state
                    audit.emit(
                        "simulated_execution",
                        tick=execution.record.tick,
                        entity_id=action.target_id,
                        action_id=action.id,
                        disposition=decision.disposition.value,
                        outcome="executed",
                        payload={
                            "action_configuration_version": (
                                execution.record.action_configuration_version
                            ),
                            "action_type": execution.record.action_type,
                            "adapter": broker.adapter_name,
                            "authorized_action_digest": (execution.record.authorized_action_digest),
                            "authorized_state_digest": execution.record.authorized_state_digest,
                            "execution_id": execution.record.id,
                            "network_enabled": broker.network_enabled,
                            "policy_decision_id": execution.record.policy_decision_id,
                            "policy_decision_digest": execution.record.policy_decision_digest,
                            "policy_digest": execution.record.policy_digest,
                            "state_after_digest": execution.record.state_after_digest,
                            "state_before_digest": execution.record.state_before_digest,
                            "target_id": execution.record.target_id,
                        },
                    )
                    verification = verify_execution(action, execution, governor)
                    if verification.disposition is not VerificationDisposition.VERIFIED:
                        raise RuntimeError("Simulated execution failed independent verification")
                    audit.emit(
                        "verification",
                        tick=verification.tick,
                        entity_id=action.target_id,
                        action_id=action.id,
                        disposition=verification.disposition.value,
                        outcome="verified",
                        payload={
                            "execution_id": verification.execution_id,
                            "expected_effect_observed": verification.expected_effect_observed,
                            "state_hashes_valid": verification.state_hashes_valid,
                            "verification_id": verification.id,
                        },
                    )
                else:
                    audit.emit(
                        "verification",
                        tick=decision.tick,
                        entity_id=action.target_id,
                        action_id=action.id,
                        disposition=decision.disposition.value,
                        outcome="not_executed",
                        payload={"reason": "governor disposition did not permit execution"},
                    )
                audit.emit(
                    "audit",
                    tick=decision.tick,
                    entity_id=action.target_id,
                    action_id=action.id,
                    disposition=decision.disposition.value,
                    outcome="recorded",
                    payload={"candidate_and_decision_retained": True},
                )
            required_dispositions = {
                PolicyDisposition.APPROVE,
                PolicyDisposition.ESCALATE,
                PolicyDisposition.PROHIBIT,
            }
            if not required_dispositions.issubset(observed_dispositions):
                raise RuntimeError(
                    "Diagnostic did not exercise allowed, escalated, and prohibited decisions"
                )
            actions_processed = True

        if not actions_processed:
            raise RuntimeError("Diagnostic adversary event did not exercise candidate actions")
        final_tick = float(max((observation.tick for observation in observations), default=0))
        audit.emit(
            "manifest",
            tick=final_tick,
            outcome="artifact_generation_started",
            payload={
                "event_chain_status": "COMPLETED",
                "manifest_format": "canonical_json",
            },
        )
        audit.close()
        _log(log_handle, "raw JSONL and fixed-schema Parquet retained")

        summarize_raw_events(
            audit.parquet_path,
            run_dir / "derived",
            workspace_root=workspace,
        )
        _log(log_handle, "summary derived exclusively from raw/events.parquet")
        raw_semantic_hash = semantic_events_hash(audit.parquet_path)
        summary_semantic_hash = semantic_summary_hash(
            run_dir / "derived" / "episode_summary.parquet"
        )

        config_hash_end = sha256_file(canonical_path)
        if config_hash_end != config_hash_start:
            raise RuntimeError("Canonical configuration changed during diagnostic execution")
        elapsed = time.perf_counter() - start_counter
        if elapsed >= _MAX_DIAGNOSTIC_SECONDS:
            raise RuntimeError("Diagnostic exceeded the five-minute runtime boundary")
        _log(log_handle, "canonical configuration end hash matches start hash")
        _log(log_handle, "bounded synthetic diagnostic completed")
        log_handle.close()

        ended_at = datetime.now(UTC).isoformat()
        status = {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "completion_status": "COMPLETED",
            "reportable": False,
            "seed": selected_seed,
        }
        artifact_names_without_status = (
            EVIDENCE_LABEL,
            "canonical_config.json",
            "seed_registry.json",
            "raw/events.jsonl",
            "raw/events.parquet",
            "derived/episode_summary.csv",
            "derived/episode_summary.parquet",
            "logs/run.log",
        )
        artifact_hashes = collect_artifact_hashes(run_dir, artifact_names_without_status)
        status_bytes = canonical_json_bytes(status)
        artifact_hashes["status.json"] = hashlib.sha256(status_bytes).hexdigest()
        try:
            commit_value = git_commit(repository)
            dirty_value = git_is_dirty(repository)
        except (OSError, PermissionError, RuntimeError, ValueError):
            commit_value = "UNAVAILABLE"
            dirty_value = True
        lock_path = repository / "uv.lock"
        lock_hash = sha256_file(lock_path) if lock_path.is_file() else "UNAVAILABLE"
        manifest = build_manifest(
            run_id=run_id,
            seed=selected_seed,
            started_at=started_at,
            ended_at=ended_at,
            completion_status="COMPLETED",
            code_commit=commit_value,
            dirty_state=dirty_value,
            python_version=platform.python_version(),
            lockfile_hash=lock_hash,
            os_class=platform.system(),
            cpu_worker_count=1,
            protocol_version=protocol_version,
            config_hash_start=config_hash_start,
            config_hash_end=config_hash_end,
            scenario_hash=scenario_hash,
            safety_policy_hash=safety_policy_hash,
            seed_registry_hash=seed_registry_hash,
            baseline_definition_hash=baseline_definition_hash,
            metric_definition_hash=metric_definition_hash,
            raw_semantic_hash=raw_semantic_hash,
            summary_semantic_hash=summary_semantic_hash,
            artifact_hashes=artifact_hashes,
        )
        manifest_digest = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
        checksums = dict(artifact_hashes)
        checksums["manifest.json"] = manifest_digest
        write_sha256s(run_dir, checksums, workspace_root=workspace)
        write_manifest(run_dir, manifest, workspace_root=workspace)
        write_canonical_json(run_dir / "status.json", status, workspace_root=workspace)
        run_dir.replace(final_run_dir)
        manifest_path = final_run_dir / "manifest.json"
        return RunResult(
            run_dir=final_run_dir,
            run_id=run_id,
            seed=selected_seed,
            config_hash=config_hash,
            raw_semantic_hash=raw_semantic_hash,
            summary_semantic_hash=summary_semantic_hash,
            manifest_path=manifest_path,
            elapsed_seconds=elapsed,
        )
    except Exception as error:
        if audit is not None:
            try:
                audit.close()
            except (OSError, ValueError):
                pass
        if not log_handle.closed:
            log_handle.close()
        _retain_failed_run(
            run_dir,
            final_run_dir,
            workspace,
            selected_seed,
            error,
            log_path=log_path,
        )
        raise


@dataclass(frozen=True)
class _DiagnosticRequest:
    scenario_path: str
    policy_path: str
    seed_registry_path: str
    output_root: str
    seed: int | None
    workspace_root: str
    repo_root: str
    baseline_path: str | None
    metric_path: str | None
    reportable: bool
    invocation_token: str


def _diagnostic_process_entry(sender: Connection, request: _DiagnosticRequest) -> None:
    """Execute one diagnostic in an isolated process and return a small typed envelope."""
    try:
        result = _run_diagnostic_worker(
            request.scenario_path,
            request.policy_path,
            request.seed_registry_path,
            request.output_root,
            seed=request.seed,
            workspace_root=request.workspace_root,
            repo_root=request.repo_root,
            baseline_path=request.baseline_path,
            metric_path=request.metric_path,
            reportable=request.reportable,
            _invocation_token=request.invocation_token,
        )
        sender.send({"ok": True, "result": result.to_dict()})
    except Exception as error:
        sender.send(
            {
                "ok": False,
                "error_type": type(error).__name__,
                "message": str(error),
            }
        )
    finally:
        sender.close()


def _raise_worker_error(error_type: str, message: str) -> None:
    exception_types: dict[str, type[Exception]] = {
        "ConfigurationError": ConfigurationError,
        "DiagnosticTimeoutError": DiagnosticTimeoutError,
        "FileExistsError": FileExistsError,
        "FileNotFoundError": FileNotFoundError,
        "OSError": OSError,
        "PathBoundaryError": PathBoundaryError,
        "PermissionError": PermissionError,
        "ReportableModeDenied": ReportableModeDenied,
        "RuntimeError": RuntimeError,
        "ValueError": ValueError,
    }
    exception_type = exception_types.get(error_type, RuntimeError)
    raise exception_type(message)


def _retain_interrupted_evidence(
    workspace: Path,
    invocation_token: str,
    error: Exception,
) -> None:
    """Fail only this invocation and retain staging or atomically finalized evidence."""
    staging_root = assert_write_path(workspace / "var" / "tmp", workspace)
    final_root = assert_write_path(workspace / "var" / "runs", workspace)
    if path_has_symlink_or_reparse(staging_root) or path_has_symlink_or_reparse(final_root):
        raise RuntimeError("Diagnostic evidence root contains a symlink or reparse point")
    candidates: list[tuple[Path, bool]] = []
    if staging_root.is_dir():
        candidates.extend(
            (path, True)
            for path in staging_root.iterdir()
            if path.is_dir() and path.name.endswith(f"-{invocation_token}.staging")
        )
    if final_root.is_dir():
        candidates.extend(
            (path, False)
            for path in final_root.iterdir()
            if path.is_dir() and path.name.endswith(f"-{invocation_token}")
        )
    if not candidates:
        return
    if len(candidates) != 1:
        raise RuntimeError("Interrupted invocation has an ambiguous evidence directory")
    candidate, is_staging = candidates[0]
    if path_has_symlink_or_reparse(candidate):
        raise RuntimeError("Interrupted invocation evidence path is indirect")
    run_dir = assert_write_path(candidate, workspace)
    run_id = run_dir.name.removesuffix(".staging") if is_staging else run_dir.name
    match = re.fullmatch(
        rf"diagnostic-.+-seed-(\d+)-{re.escape(invocation_token)}",
        run_id,
    )
    if match is None:
        raise RuntimeError("Interrupted invocation evidence name is invalid")
    seed = int(match.group(1))
    final_dir = assert_write_path(final_root / run_id, workspace)
    _retain_failed_run(
        run_dir,
        final_dir,
        workspace,
        seed,
        error,
        log_path=run_dir / "logs" / "run.log",
    )


def _retain_timeout_evidence(workspace: Path, invocation_token: str) -> None:
    """Retain raw evidence after terminating one timed-out diagnostic worker."""
    _retain_interrupted_evidence(
        workspace,
        invocation_token,
        DiagnosticTimeoutError("Diagnostic worker exceeded the five-minute runtime boundary"),
    )


def _retain_parent_failure(
    workspace: Path,
    invocation_token: str,
    error: RuntimeError,
) -> None:
    try:
        _retain_interrupted_evidence(workspace, invocation_token, error)
    except (OSError, RuntimeError, ValueError) as retention_error:
        raise RuntimeError(
            "Diagnostic worker failed and evidence retention also failed: "
            f"{type(retention_error).__name__}"
        ) from retention_error


def _validate_public_workspace(
    scenario_path: Path | str,
    workspace_root: Path | str | None,
    repo_root: Path | str | None,
) -> tuple[Path, Path]:
    initial_scenario = Path(scenario_path)
    if repo_root is not None and path_has_symlink_or_reparse(repo_root):
        raise PathBoundaryError("Repository path contains a symlink or reparse point")
    if workspace_root is not None and path_has_symlink_or_reparse(workspace_root):
        raise PathBoundaryError("Workspace path contains a symlink or reparse point")
    if path_has_symlink_or_reparse(initial_scenario):
        raise PathBoundaryError("Scenario path contains a symlink or reparse point")
    repository = (
        Path(repo_root).resolve(strict=True)
        if repo_root is not None
        else _discover_repo_root(initial_scenario.resolve(strict=True))
    )
    workspace = (
        resolve_workspace_root(workspace_root)
        if workspace_root is not None
        else infer_workspace_root(repository)
    )
    mandated = default_workspace_root()
    if workspace != mandated:
        raise PathBoundaryError(
            "Diagnostic workspace authority must equal the author-designated PACD workspace"
        )
    repository_parent = (workspace / "repo").resolve(strict=False)
    if repository.parent != repository_parent:
        raise ConfigurationError(
            "Repository must be a direct child of the designated PACD workspace repo directory"
        )
    return repository, workspace


def run_diagnostic(
    scenario_path: Path | str,
    policy_path: Path | str,
    seed_registry_path: Path | str,
    output_root: Path | str,
    *,
    seed: int | None = None,
    workspace_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    baseline_path: Path | str | None = None,
    metric_path: Path | str | None = None,
    reportable: bool = False,
) -> RunResult:
    """Run one diagnostic in a killable process bounded to five wall-clock minutes."""
    repository, workspace = _validate_public_workspace(
        scenario_path,
        workspace_root,
        repo_root,
    )
    invocation_token = uuid4().hex
    request = _DiagnosticRequest(
        scenario_path=str(Path(scenario_path)),
        policy_path=str(Path(policy_path)),
        seed_registry_path=str(Path(seed_registry_path)),
        output_root=str(Path(output_root)),
        seed=seed,
        workspace_root=str(workspace),
        repo_root=str(repository),
        baseline_path=str(Path(baseline_path)) if baseline_path is not None else None,
        metric_path=str(Path(metric_path)) if metric_path is not None else None,
        reportable=reportable,
        invocation_token=invocation_token,
    )
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_diagnostic_process_entry,
        args=(sender, request),
        name=f"pacd-diagnostic-{invocation_token}",
    )
    process.start()
    sender.close()
    process.join(_MAX_DIAGNOSTIC_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        if process.is_alive():
            process.kill()
            process.join(5.0)
        receiver.close()
        if process.is_alive():
            raise DiagnosticTimeoutError(
                "Diagnostic worker exceeded five minutes and could not be terminated"
            )
        process.close()
        try:
            _retain_timeout_evidence(workspace, invocation_token)
        except (OSError, RuntimeError, ValueError) as retention_error:
            raise DiagnosticTimeoutError(
                "Diagnostic worker was terminated at five minutes, but timeout evidence "
                f"retention failed: {type(retention_error).__name__}"
            ) from retention_error
        raise DiagnosticTimeoutError(
            "Diagnostic worker was terminated at the five-minute runtime boundary"
        )
    if not receiver.poll():
        exit_code = process.exitcode
        receiver.close()
        process.close()
        error = RuntimeError(f"Diagnostic worker exited without a result (exit_code={exit_code})")
        _retain_parent_failure(workspace, invocation_token, error)
        raise error
    try:
        envelope = receiver.recv()
    except (EOFError, OSError) as receive_error:
        receiver.close()
        process.close()
        error = RuntimeError(
            f"Diagnostic worker result channel failed: {type(receive_error).__name__}"
        )
        _retain_parent_failure(workspace, invocation_token, error)
        raise error from receive_error
    receiver.close()
    process.close()
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        error = RuntimeError("Diagnostic worker returned an invalid result envelope")
        _retain_parent_failure(workspace, invocation_token, error)
        raise error
    if envelope["ok"] is not True:
        _raise_worker_error(str(envelope.get("error_type")), str(envelope.get("message")))
    value = envelope.get("result")
    if not isinstance(value, dict):
        error = RuntimeError("Diagnostic worker result is missing")
        _retain_parent_failure(workspace, invocation_token, error)
        raise error
    return RunResult(
        run_dir=Path(str(value["run_dir"])),
        run_id=str(value["run_id"]),
        seed=int(value["seed"]),
        config_hash=str(value["config_hash"]),
        raw_semantic_hash=str(value["raw_semantic_hash"]),
        summary_semantic_hash=str(value["summary_semantic_hash"]),
        manifest_path=Path(str(value["manifest_path"])),
        elapsed_seconds=float(value["elapsed_seconds"]),
        evidence_label=str(value["evidence_label"]),
    )

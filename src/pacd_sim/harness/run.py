"""Independent, deterministic NON_REPORTABLE_DIAGNOSTIC evaluation harness."""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import os
import platform
import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from functools import partial
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, TextIO, cast
from uuid import uuid4

import yaml
from pydantic import ValidationError
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from pacd_sim.actions.models import DefensiveAction, RequestedAuthority
from pacd_sim.audit.writer import AuditWriter, EventType
from pacd_sim.comparison import ComparisonInputs, ComparisonPlan, PlannedAttempt
from pacd_sim.configuration import DiagnosticInputs, ScenarioConfig, SensingReviewConfig
from pacd_sim.constants import (
    DEFAULT_BASELINE_FILE,
    DEFAULT_SCENARIO_FILE,
    DIAGNOSTIC_BASELINE_FILES,
    DIAGNOSTIC_SCENARIO_FILES,
    EVIDENCE_LABEL,
    SCHEMA_VERSION,
    SENSING_BASELINE_FILES,
    SENSING_POLICY_FILE,
    SENSING_SCENARIO_FILES,
    diagnostic_pair_supported,
    policy_file_for_scenario,
)
from pacd_sim.defenders.base import DefenderContext
from pacd_sim.defenders.baselines.static import STATIC_REVIEW_VERSION
from pacd_sim.defenders.observations import ReviewProposal
from pacd_sim.defenders.pacd import corroboration
from pacd_sim.defenders.pacd.diagnostic import DiagnosticPACDDefender
from pacd_sim.engine.scheduler import DeterministicScheduler, ScheduledEvent
from pacd_sim.environment.availability import continuity_transition, evaluate_availability
from pacd_sim.environment.model import (
    Dependency,
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)
from pacd_sim.evidence.context import EvidenceReading
from pacd_sim.evidence.normalize import EvidenceItem, normalize_observation
from pacd_sim.execution.broker import SimulatedExecutionBroker
from pacd_sim.execution.verification import verify_execution
from pacd_sim.governance.governor import GovernanceContext, SafetyGovernor, SafetyPolicy
from pacd_sim.harness.static_review import (
    SELECTION_OPPORTUNITY,
    ReviewEpisodeGate,
    review_action,
    review_detector_options,
    review_queue,
    sensing_opportunity_ordinal,
    sensing_referral_rejection,
    sensor_reading,
    static_review_candidate,
)
from pacd_sim.hypotheses.update import BeliefState, update_beliefs
from pacd_sim.metrics.summarize import summarize_raw_events
from pacd_sim.oversight.guarded import ReviewEvent, ReviewStep
from pacd_sim.polymorphism.selection import select_profile
from pacd_sim.polymorphism.sensing import project_sensing_observation, sensing_decision
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import (
    build_manifest,
    collect_artifact_hashes,
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
    validate_retained_json_text_depth,
    write_canonical_json,
    write_manifest,
    write_sha256s,
)
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_exact_control_path,
    assert_write_path,
    default_workspace_root,
    infer_workspace_root,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
)
from pacd_sim.reproducibility.receipts import (
    create_execution_receipt,
    receipt_path_for,
    valid_ownership_shape,
)
from pacd_sim.reproducibility.reportable import (
    ReportableModeDenied,
    git_commit,
    git_is_dirty,
    validate_reportable_approval,
)
from pacd_sim.schema import STABLE_ID_MAX_LENGTH, PolicyDisposition, VerificationDisposition
from pacd_sim.state.snapshot import create_snapshot
from pacd_sim.telemetry.generator import DetectorProfile, Sensor, SyntheticTelemetryGenerator

_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_CONFIG_DEPTH = 40
_MAX_CONFIG_NODES = 10_000
_MAX_DIAGNOSTIC_EVENTS = 100
_MAX_DIAGNOSTIC_ACTIONS = 100
_MAX_DIAGNOSTIC_SECONDS = 300.0
_MAX_PARENT_MANIFEST_BYTES = 1024 * 1024


class ConfigurationError(ValueError):
    """Raised when a diagnostic input is unsafe, ambiguous, or out of bounds."""


class DiagnosticTimeoutError(RuntimeError):
    """Raised after the bounded worker is terminated at the runtime limit."""


class _StrictSafeLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Check the YAML syntax tree before construction or merge-key flattening."""

    def __init__(self, text: str, max_aliases: int) -> None:
        super().__init__(text)
        self.aliases_left = max_aliases
        self.depth = 0
        self.nodes = 0

    def compose_node(self, parent: Node | None, index: object) -> Node:
        event = self.peek_event()
        if isinstance(event, AliasEvent):
            self.aliases_left -= 1
            if self.aliases_left < 0:
                raise ConfigurationError("Configuration exceeds the alias limit")
        elif getattr(event, "tag", None) is not None:
            raise ConfigurationError("Explicit YAML tags are not permitted")
        self.nodes += 1
        # Source syntax counts mapping keys as nodes as well as mapping values.
        if self.nodes > 2 * _MAX_CONFIG_NODES:
            raise ConfigurationError("Configuration exceeds the syntax-node limit")
        if self.depth > _MAX_CONFIG_DEPTH:
            raise ConfigurationError("Configuration exceeds the nesting-depth limit")
        self.depth += 1
        try:
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1


def _check_yaml_expansion(root: Node) -> None:
    """Charge each alias use, including keys hidden by YAML map merging."""
    count = 0
    scalar_bytes = 0

    def visit(node: Node, depth: int) -> None:
        nonlocal count, scalar_bytes
        count += 1
        if count > 2 * _MAX_CONFIG_NODES:
            raise ConfigurationError("Configuration exceeds the expanded syntax-node limit")
        if depth > _MAX_CONFIG_DEPTH:
            raise ConfigurationError("Recursive or excessively nested YAML alias")
        if isinstance(node, MappingNode):
            if sum(key.tag == "tag:yaml.org,2002:merge" for key, _ in node.value) > 1:
                raise ConfigurationError("Duplicate configuration merge key")
            for key, value in node.value:
                visit(key, depth + 1)
                visit(value, depth + 1)
        elif isinstance(node, SequenceNode):
            for child in node.value:
                visit(child, depth + 1)
        elif isinstance(node, ScalarNode):
            scalar_bytes += len(node.value.encode("utf-8"))
            if scalar_bytes > _MAX_CONFIG_BYTES:
                raise ConfigurationError("Configuration exceeds the expanded scalar-byte limit")

    visit(root, 0)


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
        if isinstance(item, str):
            item.encode("utf-8")  # Escaped surrogates cannot be canonicalized as UTF-8.
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in active_containers:
                raise ConfigurationError("Recursive YAML aliases are not permitted")
            active_containers.add(identity)
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ConfigurationError("Configuration mapping keys must be strings")
                key.encode("utf-8")
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


def _read_configuration_text(path: Path) -> str:
    if not path.is_file() or path_has_symlink_or_reparse(path):
        raise ConfigurationError("Configuration input must be a regular, non-symlink file")
    with path.open("rb") as handle:
        encoded = handle.read(_MAX_CONFIG_BYTES + 1)
    if len(encoded) > _MAX_CONFIG_BYTES:
        raise ConfigurationError("Configuration exceeds the 1 MiB input limit")
    try:
        return encoded.decode("utf-8")
    except UnicodeError as error:
        raise ConfigurationError("Configuration must be UTF-8") from error


def load_yaml_config(path: Path | str, *, max_aliases: int = 20) -> dict[str, object]:
    """Load bounded YAML through SafeLoader with no custom tags or duplicate keys."""
    if isinstance(max_aliases, bool) or not isinstance(max_aliases, int) or max_aliases < 0:
        raise ValueError("max_aliases must be a nonnegative integer")
    source = Path(path)
    if source.suffix.lower() not in {".yaml", ".yml"}:
        raise ConfigurationError("Configuration input must use .yaml or .yml")
    text = _read_configuration_text(source)
    try:
        loader = _StrictSafeLoader(text, max_aliases)
        try:
            root = loader.get_single_node()
            if not isinstance(root, MappingNode):
                raise ConfigurationError("Configuration root must be a mapping")
            _check_yaml_expansion(root)
            value = loader.construct_document(root)
        finally:
            loader.dispose()
        _validate_configuration_tree(value)
    except ConfigurationError:
        raise
    except (yaml.YAMLError, ValueError, OverflowError) as error:
        raise ConfigurationError("Configuration failed strict safe loading") from error
    if not isinstance(value, dict):
        raise ConfigurationError("Configuration root must be a mapping")
    return {str(key): item for key, item in value.items()}


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError(f"Duplicate JSON configuration key: {key}")
        result[key] = value
    return result


def _load_json_config(path: Path) -> dict[str, object]:
    text = _read_configuration_text(path)
    try:
        # The shared lexical guard bounds the decoder stack. The configuration
        # tree below has a tighter limit than retained evidence.
        validate_retained_json_text_depth(text, source="configuration")
        value = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
        )
        _validate_configuration_tree(value)
    except ConfigurationError:
        raise
    except ValueError as error:
        raise ConfigurationError("JSON configuration is invalid") from error
    if not isinstance(value, dict):
        raise ConfigurationError("JSON configuration root must be an object")
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


def _validate_sensing_sources(
    repository: Path,
    scenario_file: Path,
    policy_file: Path,
    baseline_file: Path,
    scenario: Mapping[str, object],
    baseline: Mapping[str, object],
) -> None:
    """Bind opted-in roles to their complete checkout path and declared condition identity."""
    if (
        "sensing_operator" not in scenario
        and scenario_file.name not in SENSING_SCENARIO_FILES
        and not any(scenario.get("name") == Path(name).stem for name in SENSING_SCENARIO_FILES)
        and baseline_file.name not in SENSING_BASELINE_FILES
        and policy_file.name != SENSING_POLICY_FILE
        and not any(
            baseline.get("name") == f"{Path(name).stem}_v1" for name in SENSING_BASELINE_FILES
        )
    ):
        return
    configs = repository / "configs"
    if (
        scenario_file.name not in SENSING_SCENARIO_FILES
        or scenario_file != configs / "scenarios" / scenario_file.name
        or scenario.get("name") != scenario_file.stem
        or "sensing_operator" not in scenario
        or baseline_file.name not in SENSING_BASELINE_FILES
        or baseline_file != configs / "defenders" / baseline_file.name
        or baseline.get("name") != f"{baseline_file.stem}_v1"
        or policy_file != configs / "policies" / SENSING_POLICY_FILE
        or not diagnostic_pair_supported(scenario_file.name, baseline_file.name)
    ):
        raise ConfigurationError(
            "Sensing inputs must match their governed filenames, roles and identities"
        )


def _load_condition_inputs(
    repository: Path,
    scenario_path: Path | str,
    policy_path: Path | str,
    baseline_path: Path | str | None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    scenario_file = _assert_controlled_config(scenario_path, repository)
    policy_file = _assert_controlled_config(policy_path, repository)
    baseline_file = _assert_controlled_config(
        baseline_path or repository / "configs" / "defenders" / DEFAULT_BASELINE_FILE, repository
    )
    scenario = load_yaml_config(scenario_file)
    baseline = load_yaml_config(baseline_file)
    _validate_sensing_sources(
        repository, scenario_file, policy_file, baseline_file, scenario, baseline
    )
    return scenario, load_yaml_config(policy_file), baseline


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


def _build_environment(
    scenario: Mapping[str, object] | ScenarioConfig, protocol_version: str
) -> EnvironmentState:
    try:
        config = ScenarioConfig.model_validate(scenario)
        return EnvironmentState(
            configuration_version=protocol_version,
            identities=tuple(
                Identity(configuration_version=protocol_version, **item.model_dump())
                for item in config.identities
            ),
            sessions=tuple(
                Session(configuration_version=protocol_version, **item.model_dump())
                for item in config.sessions
            ),
            services=tuple(
                Service(configuration_version=protocol_version, **item.model_dump())
                for item in config.services
            ),
            mission_functions=tuple(
                MissionFunction(configuration_version=protocol_version, **item.model_dump())
                for item in config.missions
            ),
            dependencies=tuple(
                Dependency(configuration_version=protocol_version, **item.model_dump())
                for item in config.dependencies or ()
            ),
        )
    except ValidationError as error:
        issue = error.errors(include_url=False, include_input=False)[0]
        raise ConfigurationError(f"Invalid diagnostic environment: {issue['msg']}") from error


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
    if "guarded_review" in scenario:
        if kinds not in ({"benign_administrative"}, {"simulated_adversary"}):
            raise ConfigurationError("A matched guarded fixture must use a single scripted truth")
    elif not {"benign_administrative", "simulated_adversary"}.issubset(kinds):
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


def _validate_loaded_configuration_bundle(
    scenario: Mapping[str, object],
    policy_config: Mapping[str, object],
    seed_registry: Mapping[str, object],
    baseline_definition: Mapping[str, object],
    metric_definition: Mapping[str, object],
) -> tuple[str, tuple[int, ...]]:
    try:
        inputs = DiagnosticInputs.model_validate(
            {
                "scenario": scenario,
                "policy": policy_config,
                "seeds": seed_registry,
                "baseline": baseline_definition,
                "metrics": metric_definition,
            }
        )
    except ValidationError as error:
        issue = error.errors(include_url=False, include_input=False)[0]
        field = ".".join(str(segment) for segment in issue["loc"])
        raise ConfigurationError(f"Invalid configuration field {field}: {issue['msg']}") from error

    protocol_version = inputs.scenario.protocol_version
    registered_seeds = inputs.seeds.seeds
    default_seed = inputs.scenario.default_seed
    if default_seed not in registered_seeds:
        raise ConfigurationError("Scenario default_seed is absent from the seed registry")

    environment = _build_environment(inputs.scenario, protocol_version)
    events = _build_events(scenario, protocol_version)
    policy = _build_policy(policy_config)
    if (inputs.scenario.sensing_operator is not None) != isinstance(
        inputs.baseline, SensingReviewConfig
    ):
        raise ConfigurationError(
            "The sensing scenario and sensing defender must be selected together"
        )
    if inputs.scenario.guarded_review is not None:
        if inputs.baseline.actions != "require_human_review":
            raise ConfigurationError("Guarded review requires a review-proposing baseline")
        return protocol_version, registered_seeds
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
    # The diagnostic processes configured actions once, at the first adversary
    # observation. Every approved candidate needs a matching proposal and a
    # verification record there for the episode to complete.
    response_tick = min(event.tick for event in events if event.kind == "simulated_adversary")
    response_tick += inputs.scenario.telemetry.delay_ticks
    for action in approved_actions:
        if len(f"verification-execution-{action.id}") > STABLE_ID_MAX_LENGTH:
            raise ConfigurationError("Approved action ID is too long for its verification record")
        if len(f"action-pacd-isolate-{action.target_id}-{response_tick}") > STABLE_ID_MAX_LENGTH:
            raise ConfigurationError("Approved session target ID is too long for its proposal")
    return protocol_version, registered_seeds


def validate_diagnostic_configuration_files(
    repo_root: Path | str,
    *,
    scenario_file: str = DEFAULT_SCENARIO_FILE,
    defender_file: str = DEFAULT_BASELINE_FILE,
) -> dict[str, str]:
    """Validate the shipped pairs and return canonical hashes for the selected pair."""
    repository = Path(repo_root).resolve(strict=True)
    if (
        scenario_file not in DIAGNOSTIC_SCENARIO_FILES
        or defender_file not in DIAGNOSTIC_BASELINE_FILES
    ):
        raise ConfigurationError("Select a governed diagnostic scenario and defender filename")
    configs = repository / "configs"
    scenario, policy_config, baseline_definition = _load_condition_inputs(
        repository,
        configs / "scenarios" / scenario_file,
        configs / "policies" / policy_file_for_scenario(scenario_file),
        configs / "defenders" / defender_file,
    )
    seed_registry = _load_json_config(
        _assert_controlled_config(
            repository / "configs" / "seeds" / "diagnostic_seeds.json",
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
    policies = {policy_file_for_scenario(scenario_file): policy_config}
    scenarios = {scenario_file: scenario}
    for other_defender in DIAGNOSTIC_BASELINE_FILES:
        defender_path = repository / "configs" / "defenders" / other_defender
        definition = load_yaml_config(_assert_controlled_config(defender_path, repository))
        for other_scenario in DIAGNOSTIC_SCENARIO_FILES:
            if (other_scenario, other_defender) == (scenario_file, defender_file):
                continue  # Already validated above for the returned hashes.
            if not diagnostic_pair_supported(other_scenario, other_defender):
                continue
            policy_file = policy_file_for_scenario(other_scenario)
            if policy_file not in policies:
                policies[policy_file] = load_yaml_config(
                    _assert_controlled_config(
                        repository / "configs" / "policies" / policy_file, repository
                    )
                )
            scenario_path = repository / "configs" / "scenarios" / other_scenario
            if other_scenario not in scenarios:
                scenarios[other_scenario] = load_yaml_config(
                    _assert_controlled_config(scenario_path, repository)
                )
            _validate_sensing_sources(
                repository,
                scenario_path,
                configs / "policies" / policy_file,
                defender_path,
                scenarios[other_scenario],
                definition,
            )
            _validate_loaded_configuration_bundle(
                scenarios[other_scenario],
                policies[policy_file],
                seed_registry,
                definition,
                metric_definition,
            )
    canonical_config = _canonical_bundle(
        protocol_version, scenario, policy_config, baseline_definition, metric_definition
    )
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
    lexical_target = Path(os.path.abspath(path))
    if path_has_symlink_or_reparse(lexical_target):
        raise RuntimeError("Task-created metadata path is indirect")
    target = assert_write_path(lexical_target, workspace_root)
    temporary = assert_write_path(target.with_name(target.name + ".replacement"), workspace_root)
    if path_has_symlink_or_reparse(temporary) or temporary.exists() or temporary.is_symlink():
        raise RuntimeError("Task-created metadata replacement file already exists")
    with temporary.open("xb") as handle:
        handle.write(canonical_json_bytes(dict(value)))
    temporary.replace(target)
    return target


def _log(handle: TextIO, message: str) -> None:
    handle.write(f"[{EVIDENCE_LABEL}] {message}\n")
    handle.flush()


@dataclass(frozen=True)
class _ProducerRevision:
    """Checkout observed before allocation and checked again by worker and receipt owner."""

    repository: Path
    commit: str
    dirty: bool
    sensing: bool

    @classmethod
    def capture(cls, repository: Path, *, sensing: bool) -> _ProducerRevision:
        executing = Path(__file__).resolve().parents[3]
        if executing != repository:
            raise ConfigurationError(
                "Diagnostic execution requires the checkout running this harness"
            )
        try:
            commit = git_commit(executing)
            dirty = git_is_dirty(executing)
        except ReportableModeDenied as error:
            raise ConfigurationError(
                "Diagnostic producer Git state could not be established"
            ) from error
        return cls(executing, commit, dirty, sensing)

    def recheck(self, repository: Path) -> None:
        if self != self.capture(repository, sensing=self.sensing):
            raise RuntimeError("Diagnostic producer checkout, revision or dirty state changed")


@dataclass(frozen=True)
class _InvocationOwnership:
    """Parent-created authority for exactly one diagnostic staging directory."""

    workspace_root: Path
    invocation_id: str
    capability: str
    receipt_capability: str | None
    run_id: str
    seed: int
    staging_dir: Path
    final_run_dir: Path
    marker_path: Path
    started_at: str
    staging_device: int
    staging_inode: int
    marker_device: int
    marker_inode: int
    marker_size: int
    marker_mtime_ns: int
    plan_sha256: str | None = None
    planned_attempt: PlannedAttempt | None = None


def _validate_invocation_id(invocation_id: str) -> None:
    if re.fullmatch(r"[0-9a-f]{32}", invocation_id) is None:
        raise ValueError("Diagnostic invocation ID is invalid")


def _invocation_control_path(
    workspace: Path,
    invocation_id: str | None = None,
    *,
    marker: bool = False,
) -> Path:
    """Return an exact lexical invocation control-store path."""

    root = assert_exact_control_path(
        workspace / "var" / "invocations",
        workspace,
        "invocations",
    )
    if invocation_id is None:
        if marker:
            raise ValueError("An ownership marker requires an invocation ID")
        return root
    invocation_dir = assert_exact_control_path(
        root / invocation_id,
        workspace,
        "invocations",
        invocation_id,
    )
    if not marker:
        return invocation_dir
    return assert_exact_control_path(
        invocation_dir / "ownership.json",
        workspace,
        "invocations",
        invocation_id,
        "ownership.json",
    )


def _ownership_marker_value(
    *,
    invocation_id: str,
    capability: str,
    receipt_capability: str,
    run_id: str,
    seed: int,
    staging_dir: Path,
    final_run_dir: Path,
    started_at: str,
    staging_device: int,
    staging_inode: int,
) -> dict[str, object]:
    return {
        "capability_sha256": hashlib.sha256(bytes.fromhex(capability)).hexdigest(),
        "created_at": started_at,
        "evidence_label": EVIDENCE_LABEL,
        "final_run_path": str(final_run_dir),
        "invocation_id": invocation_id,
        "ownership_version": "1.0",
        "receipt_capability_sha256": hashlib.sha256(bytes.fromhex(receipt_capability)).hexdigest(),
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "staging_device": staging_device,
        "staging_inode": staging_inode,
        "staging_path": str(staging_dir),
    }


def _create_invocation_ownership(
    output_root: Path,
    workspace_root: Path,
    seed: int,
    *,
    invocation_id: str | None = None,
    plan: ComparisonPlan | None = None,
) -> _InvocationOwnership:
    """Exclusively establish exact staging ownership before a worker starts."""

    selected_invocation_id = uuid4().hex if invocation_id is None else invocation_id
    _validate_invocation_id(selected_invocation_id)
    attempt = plan.select(invocation_id) if plan is not None else None
    plan_digest = canonical_sha256(plan) if plan is not None else None
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("Diagnostic invocation seed is invalid")
    workspace = resolve_workspace_root(workspace_root)
    if invocation_id is not None:
        receipt = receipt_path_for(workspace, selected_invocation_id)
        try:
            receipt.stat(follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError("A retained receipt already occupies the registered invocation")
    if path_has_symlink_or_reparse(output_root):
        raise PathBoundaryError("Diagnostic output path contains a symlink or reparse point")
    output_input = workspace / "var" / "runs"
    staging_root_input = workspace / "var" / "tmp"
    if any(path_has_symlink_or_reparse(path) for path in (output_input, staging_root_input)):
        raise PathBoundaryError("Diagnostic ownership roots contain an indirect path")
    _invocation_control_path(workspace)
    output = assert_write_path(output_root, workspace)
    authorized_output = assert_write_path(output_input, workspace)
    if output != authorized_output:
        raise PathBoundaryError("Diagnostic output_root must be exactly workspace/var/runs")
    staging_root = assert_write_path(staging_root_input, workspace)
    ownership_root = _invocation_control_path(workspace)
    for root in (output, staging_root):
        root.mkdir(parents=True, exist_ok=True)
    if _invocation_control_path(workspace) != ownership_root:
        raise PathBoundaryError("Invocation control-store root changed before creation")
    ownership_root.mkdir(parents=True, exist_ok=True)
    if _invocation_control_path(workspace) != ownership_root:
        raise PathBoundaryError("Invocation control-store root changed during creation")

    started_at = datetime.now(UTC).isoformat()
    timestamp = datetime.fromisoformat(started_at).strftime("%Y%m%dT%H%M%S.%fZ")
    run_id = f"diagnostic-{timestamp}-seed-{seed}-{selected_invocation_id}"
    staging_dir = assert_write_path(staging_root / f"{run_id}.staging", workspace)
    final_run_dir = assert_write_path(output / run_id, workspace)
    ownership_dir = _invocation_control_path(workspace, selected_invocation_id)
    marker_path = _invocation_control_path(workspace, selected_invocation_id, marker=True)
    for target, name in (
        (final_run_dir, "final run"),
        (staging_dir, "staging directory"),
        (ownership_dir, "invocation ownership"),
    ):
        if path_has_symlink_or_reparse(target):
            raise PathBoundaryError(f"Diagnostic {name} path is indirect")
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Refusing to modify existing {name} path: {target}")

    # The ownership directory and staging directory are both claimed only by
    # successful exclusive creation.  Existing collisions are never inspected,
    # labelled, moved, or reused.
    if _invocation_control_path(workspace, selected_invocation_id) != ownership_dir:
        raise PathBoundaryError("Invocation ownership lexical path changed before creation")
    ownership_dir.mkdir(parents=False, exist_ok=False)
    if _invocation_control_path(workspace, selected_invocation_id) != ownership_dir:
        raise PathBoundaryError("Invocation ownership lexical path changed during creation")
    try:
        staging_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError as error:
        raise FileExistsError(
            f"Refusing to modify existing staging directory: {staging_dir}"
        ) from error
    staging_stat = staging_dir.stat(follow_symlinks=False)
    capability = secrets.token_hex(32)
    receipt_capability = secrets.token_hex(32)
    marker = _ownership_marker_value(
        invocation_id=selected_invocation_id,
        capability=capability,
        receipt_capability=receipt_capability,
        run_id=run_id,
        seed=seed,
        staging_dir=staging_dir,
        final_run_dir=final_run_dir,
        started_at=started_at,
        staging_device=staging_stat.st_dev,
        staging_inode=staging_stat.st_ino,
    )
    if plan_digest is not None:
        marker.update(ownership_version="1.1", plan_sha256=plan_digest)
    if _invocation_control_path(workspace, selected_invocation_id, marker=True) != marker_path:
        raise PathBoundaryError("Invocation marker lexical path changed before creation")
    with marker_path.open("xb") as handle:
        handle.write(canonical_json_bytes(marker))
        handle.flush()
        os.fsync(handle.fileno())
    if _invocation_control_path(workspace, selected_invocation_id, marker=True) != marker_path:
        raise RuntimeError("Invocation marker lexical path changed during creation")
    marker_stat = marker_path.stat(follow_symlinks=False)
    if marker_stat.st_nlink != 1:
        raise RuntimeError("Invocation ownership marker has an unexpected link count")
    if _invocation_control_path(workspace, selected_invocation_id, marker=True) != marker_path:
        raise RuntimeError("Invocation marker lexical path changed after creation")
    return _InvocationOwnership(
        workspace_root=workspace,
        invocation_id=selected_invocation_id,
        capability=capability,
        receipt_capability=receipt_capability,
        run_id=run_id,
        seed=seed,
        staging_dir=staging_dir,
        final_run_dir=final_run_dir,
        marker_path=marker_path,
        started_at=started_at,
        staging_device=staging_stat.st_dev,
        staging_inode=staging_stat.st_ino,
        marker_device=marker_stat.st_dev,
        marker_inode=marker_stat.st_ino,
        marker_size=marker_stat.st_size,
        marker_mtime_ns=marker_stat.st_mtime_ns,
        plan_sha256=plan_digest,
        planned_attempt=attempt,
    )


def _validate_invocation_ownership(
    ownership: _InvocationOwnership,
    workspace_root: Path,
    *,
    allow_finalized: bool = False,
    require_receipt_authority: bool = False,
) -> Path:
    """Revalidate marker, capability, exact paths, and directory identity."""

    workspace = resolve_workspace_root(workspace_root)
    if ownership.workspace_root != workspace:
        raise RuntimeError("Invocation ownership workspace does not match")
    _validate_invocation_id(ownership.invocation_id)
    if re.fullmatch(r"[0-9a-f]{64}", ownership.capability) is None:
        raise RuntimeError("Invocation ownership capability is invalid")
    if require_receipt_authority:
        if (
            ownership.receipt_capability is None
            or re.fullmatch(r"[0-9a-f]{64}", ownership.receipt_capability) is None
        ):
            raise RuntimeError("Parent receipt capability is absent or invalid")
    expected_marker = _invocation_control_path(
        workspace,
        ownership.invocation_id,
        marker=True,
    )
    expected_staging = assert_write_path(
        workspace / "var" / "tmp" / f"{ownership.run_id}.staging",
        workspace,
    )
    expected_final = assert_write_path(
        workspace / "var" / "runs" / ownership.run_id,
        workspace,
    )
    if (
        ownership.staging_dir != expected_staging
        or ownership.final_run_dir != expected_final
        or ownership.marker_path != expected_marker
    ):
        raise RuntimeError("Invocation ownership paths do not match their exact authority")
    match = re.fullmatch(
        rf"diagnostic-\d{{8}}T\d{{6}}\.\d{{6}}Z-seed-(\d+)-{ownership.invocation_id}",
        ownership.run_id,
    )
    if match is None or int(match.group(1)) != ownership.seed:
        raise RuntimeError("Invocation ownership run identity is invalid")
    if any(
        path_has_symlink_or_reparse(path)
        for path in (ownership.marker_path, ownership.staging_dir, ownership.final_run_dir)
    ):
        raise RuntimeError("Invocation ownership path is indirect")

    if (
        _invocation_control_path(workspace, ownership.invocation_id, marker=True)
        != ownership.marker_path
    ):
        raise RuntimeError("Invocation ownership lexical path changed before verification")
    before = ownership.marker_path.stat(follow_symlinks=False)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    ) != (
        ownership.marker_device,
        ownership.marker_inode,
        ownership.marker_size,
        ownership.marker_mtime_ns,
        1,
    ):
        raise RuntimeError("Invocation ownership marker identity changed")
    with ownership.marker_path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        ):
            raise RuntimeError("Opened ownership marker identity differs from its path")
        if before.st_size > _MAX_PARENT_MANIFEST_BYTES:
            raise RuntimeError("Invocation ownership marker exceeds its bounded limit")
        marker_bytes = handle.read(_MAX_PARENT_MANIFEST_BYTES + 1)
        opened_after = os.fstat(handle.fileno())
    after = ownership.marker_path.stat(follow_symlinks=False)
    if (
        _invocation_control_path(workspace, ownership.invocation_id, marker=True)
        != ownership.marker_path
    ):
        raise RuntimeError("Invocation ownership lexical path changed during verification")
    if (
        (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        )
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        or (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        )
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
        or len(marker_bytes) > _MAX_PARENT_MANIFEST_BYTES
    ):
        raise RuntimeError("Invocation ownership marker changed during stable read")
    marker = json.loads(marker_bytes, object_pairs_hook=_unique_json_object)
    if not isinstance(marker, dict) or not valid_ownership_shape(marker):
        raise RuntimeError("Invocation ownership marker shape is invalid")
    expected_marker_values: dict[str, object] = {
        "created_at": ownership.started_at,
        "evidence_label": EVIDENCE_LABEL,
        "final_run_path": str(ownership.final_run_dir),
        "invocation_id": ownership.invocation_id,
        "ownership_version": "1.1" if ownership.plan_sha256 is not None else "1.0",
        "run_id": ownership.run_id,
        "schema_version": SCHEMA_VERSION,
        "seed": ownership.seed,
        "staging_device": ownership.staging_device,
        "staging_inode": ownership.staging_inode,
        "staging_path": str(ownership.staging_dir),
    }
    if ownership.plan_sha256 is not None:
        expected_marker_values["plan_sha256"] = ownership.plan_sha256
    if canonical_json_bytes(marker) != marker_bytes or any(
        marker.get(key) != expected for key, expected in expected_marker_values.items()
    ):
        raise RuntimeError("Invocation ownership marker binding is invalid")
    capability_sha256 = marker.get("capability_sha256")
    if not isinstance(capability_sha256, str) or not secrets.compare_digest(
        capability_sha256,
        hashlib.sha256(bytes.fromhex(ownership.capability)).hexdigest(),
    ):
        raise RuntimeError("Invocation ownership capability does not match")
    if require_receipt_authority:
        if ownership.receipt_capability is None:
            raise RuntimeError("Parent receipt capability is absent")
        receipt_capability_sha256 = marker.get("receipt_capability_sha256")
        if not isinstance(receipt_capability_sha256, str) or not secrets.compare_digest(
            receipt_capability_sha256,
            hashlib.sha256(bytes.fromhex(ownership.receipt_capability)).hexdigest(),
        ):
            raise RuntimeError("Parent receipt capability does not match")

    existing_locations = [
        path for path in (ownership.staging_dir, ownership.final_run_dir) if path.exists()
    ]
    if len(existing_locations) != 1:
        raise RuntimeError("Invocation evidence has an ambiguous or missing exact path")
    location = existing_locations[0]
    if location == ownership.final_run_dir and not allow_finalized:
        raise RuntimeError("Invocation evidence was finalized before parent authorization")
    location_stat = location.stat(follow_symlinks=False)
    if (location_stat.st_dev, location_stat.st_ino) != (
        ownership.staging_device,
        ownership.staging_inode,
    ):
        raise RuntimeError("Invocation evidence directory identity changed")
    if (
        _invocation_control_path(workspace, ownership.invocation_id, marker=True)
        != ownership.marker_path
    ):
        raise RuntimeError("Invocation ownership lexical path changed before authorization")
    return location


def _retain_failed_run(
    workspace_root: Path,
    ownership: _InvocationOwnership,
    error: Exception,
) -> None:
    """Mark and retain only the exact parent-owned invocation directory."""

    run_dir = _validate_invocation_ownership(
        ownership,
        workspace_root,
        allow_finalized=True,
        require_receipt_authority=True,
    )
    lexical_run_dir = Path(os.path.abspath(run_dir))
    if path_has_symlink_or_reparse(lexical_run_dir):
        raise RuntimeError("Task-created run directory is indirect")
    _replace_task_created_json(
        run_dir / "status.json",
        {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "completion_status": "FAILED",
            "reportable": False,
            "seed": ownership.seed,
            "error_type": type(error).__name__,
        },
        workspace_root,
    )
    failed_manifest_path = run_dir / "manifest.json"
    if path_has_symlink_or_reparse(failed_manifest_path):
        raise RuntimeError("Task-created manifest path is indirect")
    if failed_manifest_path.is_file():
        try:
            failed_manifest = _read_parent_manifest(run_dir)
            failed_manifest["completion_status"] = "FAILED"
            failed_manifest["failure_type"] = type(error).__name__
            _replace_task_created_json(
                failed_manifest_path,
                failed_manifest,
                workspace_root,
            )
        except (
            OSError,
            RecursionError,
            UnicodeError,
            json.JSONDecodeError,
            RuntimeError,
            ValueError,
        ):
            pass
    if path_has_symlink_or_reparse(ownership.final_run_dir):
        raise RuntimeError("Task-created final run path is indirect")
    if run_dir == ownership.staging_dir:
        if ownership.final_run_dir.exists() or ownership.final_run_dir.is_symlink():
            raise RuntimeError("Exact final run path was occupied during failed retention")
        retained = _validate_invocation_ownership(
            ownership,
            workspace_root,
            allow_finalized=True,
            require_receipt_authority=True,
        )
        if retained != ownership.staging_dir:
            raise RuntimeError("Failed evidence moved before exact retention")
        run_dir.rename(ownership.final_run_dir)
    finalized = _validate_invocation_ownership(
        ownership,
        workspace_root,
        allow_finalized=True,
    )
    if finalized != ownership.final_run_dir:
        raise RuntimeError("Failed evidence was not retained at its exact final path")


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
    invocation_id: str
    receipt_path: Path | None = None
    evidence_label: str = EVIDENCE_LABEL

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["run_dir"] = str(self.run_dir)
        value["manifest_path"] = str(self.manifest_path)
        value["receipt_path"] = str(self.receipt_path) if self.receipt_path is not None else None
        return value


def _emit_guarded_event(audit: AuditWriter, row: ReviewEvent) -> None:
    audit.emit(
        "guarded_review",
        tick=row.tick,
        entity_id=row.entity_id,
        action_id=row.action_id,
        outcome=row.outcome,
        payload=row.payload,
    )


def _checked_review_state(step: ReviewStep) -> EnvironmentState:
    if failed := step.failed_outcomes:
        # The existing parent failure path retains the raw evidence, including recovery,
        # and withholds a successful execution receipt and completed outcome measures.
        raise RuntimeError(f"Guarded review failed: {', '.join(failed)}")
    return step.state


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
    _ownership: _InvocationOwnership,
    _producer: _ProducerRevision,
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
    _validate_invocation_ownership(_ownership, workspace)
    _producer.recheck(repository)

    scenario, policy_config, baseline_definition = _load_condition_inputs(
        repository, scenario_path, policy_path, baseline_path
    )
    seed_file = _assert_controlled_config(seed_registry_path, repository)
    metric_file = _assert_controlled_config(
        metric_path or repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
        repository,
    )

    evaluate_missions = "availability_model" in scenario
    seed_registry = _load_json_config(seed_file)
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
    if selected_seed != _ownership.seed:
        raise ConfigurationError("Selected seed differs from parent invocation authority")
    if _producer.sensing != ("sensing_operator" in scenario):
        raise ConfigurationError("Sensing configuration differs from the parent producer binding")

    canonical_config = _canonical_bundle(
        protocol_version, scenario, policy_config, baseline_definition, metric_definition
    )
    if _ownership.planned_attempt is not None:
        _check_planned_inputs(
            _ownership.planned_attempt,
            _producer.commit,
            selected_seed,
            canonical_config,
            seed_registry,
        )
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
    scenario_settings = ScenarioConfig.model_validate(scenario)
    guarded = scenario_settings.guarded_review
    sensing = scenario_settings.sensing_operator
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
        **review_detector_options(guarded),
    )
    sensor = Sensor(
        id="sensor-synthetic-diagnostic",
        configuration_version=protocol_version,
        detector_profile_id=profile.id,
        delay_ticks=delay,
    )
    telemetry = SyntheticTelemetryGenerator(selected_seed, sensor, profile)

    authorized_output = assert_write_path(Path(output_root), workspace)
    if authorized_output != _ownership.final_run_dir.parent:
        raise PathBoundaryError("Worker output root differs from parent invocation authority")
    _validate_invocation_ownership(_ownership, workspace)
    run_id = _ownership.run_id
    run_dir = _ownership.staging_dir
    log_path = run_dir / "logs" / "run.log"
    try:
        started_at = _ownership.started_at
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
    except Exception:
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
        start_payload: dict[str, object] = {
            "scheduler": "simpy",
            "state_graph": "networkx_detached_view",
            "synthetic_only": True,
        }
        if guarded is not None:
            start_payload["initial_availability"] = evaluate_availability(
                environment
            ).audit_summary()
        audit.emit(
            "run_started",
            tick=0,
            outcome="started",
            payload=start_payload,
        )

        governor = SafetyGovernor(safety_policy)
        broker = SimulatedExecutionBroker(governor)
        prospective = baseline_definition["actions"] == "require_human_review"
        planner = (
            corroboration.CorroboratedReviewPlanner(suppress_repeats=guarded is None)
            if baseline_definition["name"] == corroboration.POLICY
            else None
        )
        queue = (
            review_queue(guarded, partial(_emit_guarded_event, audit))
            if guarded is not None
            else None
        )
        episode_gate = ReviewEpisodeGate() if queue is not None and sensing is None else None
        defender = DiagnosticPACDDefender(compromise_threshold=0.5)
        evidence_items: list[EvidenceItem] = []
        selection_readings: list[EvidenceReading] = []
        belief_state = BeliefState(configuration_version=protocol_version)
        state = environment
        actions_processed = False

        # The single fixed-delay sensor preserves the scheduler's tick/ID order.
        # Finish each decision before generating the next reading.
        for ordinal, event in enumerate(delivered_events, start=1):
            observation = telemetry.generate(event)
            if observation is None:
                raise RuntimeError(
                    "Full-coverage diagnostic telemetry unexpectedly omitted an event"
                )
            if queue is not None:
                state = _checked_review_state(queue.advance(observation.tick, state, broker))
            sensing_fields: dict[str, object] = {}
            if sensing is not None:
                observation, sensing_fields = project_sensing_observation(observation, state)
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
                    **sensing_fields,
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
            graph = state.to_graph(multigraph=True)
            snapshot = create_snapshot(state)
            state_payload: dict[str, object] = {
                "graph_edge_count": graph.number_of_edges(),
                "graph_node_count": graph.number_of_nodes(),
                "snapshot_digest": snapshot.environment_digest,
            }
            if evaluate_missions:
                state_payload["availability"] = evaluate_availability(state).audit_summary()
            audit.emit(
                "state_update",
                tick=state.tick,
                entity_id=state.id,
                outcome="immutable_snapshot",
                payload=state_payload,
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

            actions: tuple[DefensiveAction, ...]
            proposed_actions: tuple[DefensiveAction, ...]
            if prospective:
                decision_type: EventType
                detail: dict[str, object] = {}
                if sensing is not None:
                    reading = sensor_reading(observation)
                    defender_id = _expect_string(baseline_definition["name"], "defender name")
                    decision_type = "baseline_decision"
                    opportunity = sensing_opportunity_ordinal(defender_id)
                    detail = {
                        "operator_class": "sensing",
                        "variant": "alternate",
                        "switch_cost": sensing.switch_cost,
                        "budget": sensing.budget,
                        "detectability": sensing.detectability,
                        "signal": reading.signal,
                        "opportunity": ordinal == opportunity,
                    }
                    if opportunity == SELECTION_OPPORTUNITY:
                        # Each unique event in the v1 script yields exactly one delivery
                        # from a single sensor. Opaque keys match the verified WP03 view.
                        selection_readings.append(
                            EvidenceReading(
                                observation_key=ordinal,
                                source_key=1,
                                subject_id=reading.subject_id,
                                measured_tick=observation.event_tick,
                                delivered_tick=reading.tick,
                                signal=reading.signal,
                            )
                        )
                        outcome, selection_detail = select_profile(
                            defender_id,
                            tuple(selection_readings),
                            sensing.switch_cost,
                            sensing.budget,
                        )
                        detail["selection"] = selection_detail
                    else:
                        outcome = sensing_decision(
                            defender_id, reading, ordinal, sensing.switch_cost, sensing.budget
                        )
                    rejection = (
                        sensing_referral_rejection(
                            sensing, defender_id, ordinal, reading, observation.event_tick
                        )
                        if outcome == "proposed"
                        else None
                    )
                    if (
                        opportunity == SELECTION_OPPORTUNITY
                        and outcome == "proposed"
                        and rejection is None
                        and (
                            selection_detail.get("selected_profile") != "alternate"
                            or selection_detail.get("selection_reason") != outcome
                        )
                    ):
                        rejection = "selection does not identify the proposed profile"
                    if rejection is not None:
                        outcome = "inadmissible_proposal"
                    proposal = (
                        ReviewProposal(target_id=reading.subject_id)
                        if outcome == "proposed" and reading.subject_id is not None
                        else None
                    )
                    candidate = review_action(
                        reading, proposal, f"action-sensing-review-{ordinal}", protocol_version
                    )
                    if rejection is not None:
                        detail["reason"] = rejection
                elif planner is None:
                    reading, candidate = static_review_candidate(
                        observation, ordinal, protocol_version
                    )
                    defender_id = STATIC_REVIEW_VERSION
                    decision_type = "baseline_decision"
                    outcome = "abstained" if candidate is None else "proposed"
                else:
                    reading = sensor_reading(observation)
                    step = planner.observe(reading)
                    candidate = review_action(
                        reading, step.proposal, f"action-pacd-review-{ordinal}", protocol_version
                    )
                    defender_id = corroboration.POLICY
                    decision_type = "defender_decision"
                    outcome = step.outcome
                    detail["previous_elevated_tick"] = step.previous_elevated_tick
                if episode_gate is not None:
                    suppressed = episode_gate.suppress(reading, candidate)
                    detail["raw_candidate_action_id"] = candidate.id if candidate else None
                    detail["duplicate_suppressed"] = suppressed
                    if suppressed:
                        candidate = None
                        outcome = "duplicate_suppressed"
                audit.emit(
                    decision_type,
                    tick=reading.tick,
                    entity_id=reading.subject_id or "synthetic-unknown",
                    outcome=outcome,
                    payload={
                        **detail,
                        "observation_id": observation.id,
                        "observation_sha256": canonical_sha256(reading),
                        "policy": defender_id,
                        "candidate_action_id": candidate.id if candidate else None,
                    },
                )
                if outcome == "inadmissible_proposal":
                    raise RuntimeError(
                        f"Sensing proposal exceeded evaluator authority: {detail['reason']}"
                    )
                if candidate is None:
                    continue
                actions = proposed_actions = (candidate,)
            else:
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
                proposed_actions = defender_decision.proposed_actions
                actions = _build_actions(scenario, protocol_version, observation.tick)
                defender_id = defender.defender_id
            observed_dispositions: set[PolicyDisposition] = set()
            for action in actions:
                matching_proposal = next(
                    (
                        proposed
                        for proposed in proposed_actions
                        if _proposal_matches_candidate(proposed, action)
                    ),
                    None,
                )
                proposer = (
                    defender_id if matching_proposal is not None else "diagnostic-safety-probe"
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
                    if prospective:
                        raise RuntimeError("Human review requires a withheld execution")
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
                    if evaluate_missions:
                        before = evaluate_availability(execution.record.state_before)
                        after = evaluate_availability(execution.record.state_after)
                        audit.emit(
                            "mission_effect",
                            tick=verification.tick,
                            entity_id=action.target_id,
                            action_id=action.id,
                            outcome="evaluated",
                            payload={
                                "execution_id": execution.record.id,
                                "verification_id": verification.id,
                                "state_before_digest": execution.record.state_before_digest,
                                "state_after_digest": execution.record.state_after_digest,
                                "availability_before": before.audit_summary(),
                                "availability_after": after.audit_summary(),
                                "mission_continuity": continuity_transition(before, after),
                            },
                        )
                else:
                    withheld = {"reason": "governor disposition did not permit execution"}
                    if prospective:
                        after_digest = canonical_sha256(state)
                        if decision.state_digest != snapshot.environment_digest or (
                            snapshot.environment_digest != after_digest
                        ):
                            raise RuntimeError("Withheld human review changed the governed state")
                        withheld.update(
                            state_before_digest=snapshot.environment_digest,
                            state_after_digest=after_digest,
                        )
                    audit.emit(
                        "verification",
                        tick=decision.tick,
                        entity_id=action.target_id,
                        action_id=action.id,
                        disposition=decision.disposition.value,
                        outcome="not_executed",
                        payload=withheld,
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
                if queue is not None:
                    state = _checked_review_state(
                        queue.submit(
                            action,
                            decision,
                            evidence,
                            state,
                            broker,
                            sensing_cost=sensing.switch_cost if sensing is not None else None,
                            delivery=(ordinal, observation)
                            if guarded is not None and guarded.decision_brief is not None
                            else None,
                        )
                    )
                    state = _checked_review_state(queue.advance(action.tick, state, broker))
            required_dispositions = {
                PolicyDisposition.APPROVE,
                PolicyDisposition.ESCALATE,
                PolicyDisposition.PROHIBIT,
            }
            if not prospective and not required_dispositions.issubset(observed_dispositions):
                raise RuntimeError(
                    "Diagnostic did not exercise allowed, escalated, and prohibited decisions"
                )
            actions_processed = True

        if not prospective and not actions_processed:
            raise RuntimeError("Diagnostic adversary event did not exercise candidate actions")
        if queue is not None and guarded is not None:
            state = _checked_review_state(queue.advance(guarded.end_tick, state, broker))
        final_tick = float(state.tick)
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
        _producer.recheck(repository)
        lock_path = repository / "uv.lock"
        lock_hash = sha256_file(lock_path) if lock_path.is_file() else "UNAVAILABLE"
        manifest = build_manifest(
            run_id=run_id,
            seed=selected_seed,
            started_at=started_at,
            ended_at=ended_at,
            completion_status="COMPLETED",
            code_commit=_producer.commit,
            dirty_state=_producer.dirty,
            producer_commit=_producer.commit if _producer.sensing else None,
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
        manifest_path = run_dir / "manifest.json"
        return RunResult(
            run_dir=run_dir,
            run_id=run_id,
            seed=selected_seed,
            config_hash=config_hash,
            raw_semantic_hash=raw_semantic_hash,
            summary_semantic_hash=summary_semantic_hash,
            manifest_path=manifest_path,
            elapsed_seconds=elapsed,
            invocation_id=_ownership.invocation_id,
        )
    except Exception:
        if audit is not None:
            try:
                audit.close()
            except (OSError, ValueError):
                pass
        if not log_handle.closed:
            log_handle.close()
        raise


def _read_parent_manifest(run_dir: Path) -> dict[str, object]:
    """Reread the finalized manifest rather than trusting worker envelope fields."""

    manifest_path = run_dir / "manifest.json"
    if path_has_symlink_or_reparse(manifest_path):
        raise RuntimeError("Final manifest path is indirect")
    before = manifest_path.stat(follow_symlinks=False)
    if before.st_nlink != 1 or before.st_size > _MAX_PARENT_MANIFEST_BYTES:
        raise RuntimeError("Final manifest is not a bounded singly linked file")
    with manifest_path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_nlink) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_nlink,
        ):
            raise RuntimeError("Opened final manifest identity differs from its path")
        manifest_bytes = handle.read(_MAX_PARENT_MANIFEST_BYTES + 1)
        opened_after = os.fstat(handle.fileno())
    after = manifest_path.stat(follow_symlinks=False)
    if (
        len(manifest_bytes) > _MAX_PARENT_MANIFEST_BYTES
        or (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        )
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        or (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        )
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
    ):
        raise RuntimeError("Final manifest changed during bounded stable read")
    manifest = json.loads(manifest_bytes, object_pairs_hook=_unique_json_object)
    if not isinstance(manifest, dict):
        raise RuntimeError("Final manifest is not a JSON object")
    if canonical_json_bytes(manifest) != manifest_bytes:
        raise RuntimeError("Final manifest is not canonical JSON")
    return {str(key): value for key, value in manifest.items()}


def _finalize_owned_result(
    ownership: _InvocationOwnership,
    result: RunResult,
    workspace_root: Path,
    producer: _ProducerRevision,
) -> RunResult:
    """Parent-finalize one exact owned directory and create its receipt."""

    location = _validate_invocation_ownership(
        ownership,
        workspace_root,
        require_receipt_authority=True,
    )
    if location != ownership.staging_dir:
        raise RuntimeError("Completed worker evidence is not in its authorized staging path")
    if (
        result.invocation_id != ownership.invocation_id
        or result.run_id != ownership.run_id
        or result.seed != ownership.seed
        or result.run_dir != ownership.staging_dir
        or result.manifest_path != ownership.staging_dir / "manifest.json"
    ):
        raise RuntimeError("Diagnostic worker result does not match invocation ownership")
    if ownership.final_run_dir.exists() or ownership.final_run_dir.is_symlink():
        raise FileExistsError(
            f"Refusing to overwrite existing run directory: {ownership.final_run_dir}"
        )
    location = _validate_invocation_ownership(
        ownership,
        workspace_root,
        require_receipt_authority=True,
    )
    if location != ownership.staging_dir:
        raise RuntimeError("Completed evidence moved before exact finalization")
    ownership.staging_dir.rename(ownership.final_run_dir)
    finalized = _validate_invocation_ownership(
        ownership,
        workspace_root,
        allow_finalized=True,
        require_receipt_authority=True,
    )
    if finalized != ownership.final_run_dir:
        raise RuntimeError("Parent finalization did not preserve exact directory identity")
    manifest = _read_parent_manifest(finalized)
    parent_bindings = {
        "run_id": ownership.run_id,
        "seed": ownership.seed,
        "started_at": ownership.started_at,
        "config_hash_start": result.config_hash,
        "raw_semantic_hash": result.raw_semantic_hash,
        "summary_semantic_hash": result.summary_semantic_hash,
    }
    for key, expected in parent_bindings.items():
        if manifest.get(key) != expected:
            raise RuntimeError(f"Final manifest {key} differs from parent invocation result")
    if (
        manifest.get("code_commit") != producer.commit
        or manifest.get("dirty_state") is not producer.dirty
    ):
        raise RuntimeError("Final manifest differs from the pinned producer revision")
    if producer.sensing and manifest.get("producer_commit") != producer.commit:
        raise RuntimeError("Final sensing manifest lacks the pinned producer revision")
    if not producer.sensing and "producer_commit" in manifest:
        raise RuntimeError("Unexpected sensing producer binding on a legacy episode")
    producer.recheck(producer.repository)
    receipt_path = create_execution_receipt(
        workspace_root=workspace_root,
        invocation_id=ownership.invocation_id,
        receipt_capability=_required_receipt_capability(ownership),
        run_dir=finalized,
        manifest=manifest,
        completed_at=datetime.now(UTC).isoformat(),
    )
    receipt_finalized = _validate_invocation_ownership(
        ownership,
        workspace_root,
        allow_finalized=True,
        require_receipt_authority=True,
    )
    if receipt_finalized != ownership.final_run_dir:
        raise RuntimeError("Receipt creation changed invocation ownership")
    return replace(
        result,
        run_dir=finalized,
        manifest_path=finalized / "manifest.json",
        receipt_path=receipt_path,
    )


def _required_receipt_capability(ownership: _InvocationOwnership) -> str:
    """Return the parent-only receipt authority after explicit validation."""

    capability = ownership.receipt_capability
    if capability is None or re.fullmatch(r"[0-9a-f]{64}", capability) is None:
        raise RuntimeError("Parent receipt capability is absent or invalid")
    return capability


def _canonical_bundle(
    protocol_version: str,
    scenario: Mapping[str, object],
    policy: Mapping[str, object],
    baseline: Mapping[str, object],
    metrics: Mapping[str, object],
) -> dict[str, object]:
    return {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "protocol_version": protocol_version,
        "scenario": scenario,
        "safety_policy": policy,
        "baseline_definition": baseline,
        "metric_definition": metrics,
    }


def _check_planned_inputs(
    attempt: PlannedAttempt,
    commit: str,
    seed: int,
    canonical_config: Mapping[str, object],
    seed_registry: Mapping[str, object],
) -> None:
    observed = ComparisonInputs.from_inputs(canonical_config, seed_registry, commit)
    if attempt.seed != seed or attempt.expected != observed:
        raise ValueError("Governed inputs, code revision or seed differ from planned attempt")


def _prepare_invocation(
    scenario_path: Path | str,
    policy_path: Path | str,
    seed_registry_path: Path | str,
    repository: Path,
    requested_seed: int | None,
    *,
    baseline_path: Path | str | None,
    metric_path: Path | str | None,
    planned_attempt: PlannedAttempt | None = None,
) -> tuple[int, _ProducerRevision]:
    """Fully validate controlled inputs in the parent before allocating ownership."""

    scenario, policy, baseline = _load_condition_inputs(
        repository, scenario_path, policy_path, baseline_path
    )
    seed_registry = _load_json_config(_assert_controlled_config(seed_registry_path, repository))
    metrics = load_yaml_config(
        _assert_controlled_config(
            metric_path or repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
            repository,
        )
    )
    protocol_version, registered = _validate_loaded_configuration_bundle(
        scenario,
        policy,
        seed_registry,
        baseline,
        metrics,
    )
    selected = (
        _expect_int(scenario.get("default_seed"), "default_seed")
        if requested_seed is None
        else requested_seed
    )
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise ConfigurationError("Selected seed must be an integer")
    if selected not in registered:
        raise ConfigurationError("Selected seed is not present in the controlled seed registry")
    producer = _ProducerRevision.capture(repository, sensing="sensing_operator" in scenario)
    if producer.dirty and (producer.sensing or planned_attempt is not None):
        raise ConfigurationError(
            "Planned and sensing diagnostics require a clean producer checkout"
        )
    if planned_attempt is not None:
        config = _canonical_bundle(protocol_version, scenario, policy, baseline, metrics)
        _check_planned_inputs(planned_attempt, producer.commit, selected, config, seed_registry)
    return selected, producer


def _deny_reportable_without_invocation(
    *,
    repository: Path,
    scenario_path: Path | str,
    policy_path: Path | str,
    seed_registry_path: Path | str,
    baseline_path: Path | str | None,
    metric_path: Path | str | None,
) -> None:
    """Run the approval interlock before creating any invocation-owned path."""

    scenario, policy_config, baseline_definition = _load_condition_inputs(
        repository, scenario_path, policy_path, baseline_path
    )
    seed_registry = _load_json_config(_assert_controlled_config(seed_registry_path, repository))
    metric_definition = load_yaml_config(
        _assert_controlled_config(
            metric_path or repository / "configs" / "metrics" / "diagnostic_metrics.yaml",
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
    validate_reportable_approval(
        repository,
        config_hash=canonical_sha256(canonical_config),
        seed_registry_hash=canonical_sha256(seed_registry),
        baseline_definition_hash=canonical_sha256(baseline_definition),
        metric_definition_hash=canonical_sha256(metric_definition),
        protocol_version=protocol_version,
    )
    raise ReportableModeDenied(
        "The bootstrap implements diagnostics only; reportable execution remains unavailable"
    )


def _run_diagnostic_in_process(
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
    invocation_id: str | None = None,
    plan: ComparisonPlan | None = None,
) -> RunResult:
    """Parent-style in-process helper for hermetic tests; no worker self-provisioning."""

    repository, workspace = _validate_public_workspace(
        scenario_path,
        workspace_root,
        repo_root,
    )
    if reportable:
        _deny_reportable_without_invocation(
            repository=repository,
            scenario_path=scenario_path,
            policy_path=policy_path,
            seed_registry_path=seed_registry_path,
            baseline_path=baseline_path,
            metric_path=metric_path,
        )
    selected_seed, producer = _prepare_invocation(
        scenario_path,
        policy_path,
        seed_registry_path,
        repository,
        seed,
        baseline_path=baseline_path,
        metric_path=metric_path,
        planned_attempt=plan.select(invocation_id) if plan is not None else None,
    )
    ownership = _create_invocation_ownership(
        Path(output_root),
        workspace,
        selected_seed,
        invocation_id=invocation_id,
        plan=plan,
    )
    try:
        staged_result = _run_diagnostic_worker(
            scenario_path,
            policy_path,
            seed_registry_path,
            output_root,
            seed=selected_seed,
            workspace_root=workspace,
            repo_root=repository,
            baseline_path=baseline_path,
            metric_path=metric_path,
            reportable=reportable,
            _ownership=_worker_ownership(ownership),
            _producer=producer,
        )
        return _finalize_owned_result(ownership, staged_result, workspace, producer)
    except Exception as error:
        _retain_parent_failure(workspace, ownership, error)
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
    ownership: _InvocationOwnership
    producer: _ProducerRevision


def _worker_ownership(ownership: _InvocationOwnership) -> _InvocationOwnership:
    """Remove the parent-only receipt capability before crossing into a worker."""

    if ownership.receipt_capability is None:
        raise RuntimeError("Parent receipt capability is absent")
    return replace(ownership, receipt_capability=None)


def _diagnostic_process_entry(sender: Connection, request: _DiagnosticRequest) -> None:
    """Execute one diagnostic in an isolated process and return a small typed envelope."""
    try:
        if request.ownership.receipt_capability is not None:
            raise RuntimeError("Diagnostic worker received parent-only receipt authority")
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
            _ownership=request.ownership,
            _producer=request.producer,
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
    ownership: _InvocationOwnership,
    error: Exception,
) -> None:
    """Retain only the exact directory established by the parent capability."""

    _retain_failed_run(
        workspace,
        ownership,
        error,
    )
    finalized = _validate_invocation_ownership(
        ownership,
        workspace,
        allow_finalized=True,
    )
    if finalized != ownership.final_run_dir:
        raise RuntimeError("Interrupted evidence did not retain at its exact final path")


def _retain_timeout_evidence(workspace: Path, ownership: _InvocationOwnership) -> None:
    """Retain raw evidence after terminating one timed-out diagnostic worker."""
    _retain_interrupted_evidence(
        workspace,
        ownership,
        DiagnosticTimeoutError("Diagnostic worker exceeded the five-minute runtime boundary"),
    )


def _retain_parent_failure(
    workspace: Path,
    ownership: _InvocationOwnership,
    error: Exception,
) -> None:
    try:
        _retain_interrupted_evidence(workspace, ownership, error)
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
    invocation_id: str | None = None,
    plan: ComparisonPlan | None = None,
) -> RunResult:
    """Run one diagnostic in a killable process bounded to five wall-clock minutes."""
    repository, workspace = _validate_public_workspace(
        scenario_path,
        workspace_root,
        repo_root,
    )
    if reportable:
        _deny_reportable_without_invocation(
            repository=repository,
            scenario_path=scenario_path,
            policy_path=policy_path,
            seed_registry_path=seed_registry_path,
            baseline_path=baseline_path,
            metric_path=metric_path,
        )
    selected_seed, producer = _prepare_invocation(
        scenario_path,
        policy_path,
        seed_registry_path,
        repository,
        seed,
        baseline_path=baseline_path,
        metric_path=metric_path,
        planned_attempt=plan.select(invocation_id) if plan is not None else None,
    )
    ownership = _create_invocation_ownership(
        Path(output_root),
        workspace,
        selected_seed,
        invocation_id=invocation_id,
        plan=plan,
    )
    request = _DiagnosticRequest(
        scenario_path=str(Path(scenario_path)),
        policy_path=str(Path(policy_path)),
        seed_registry_path=str(Path(seed_registry_path)),
        output_root=str(Path(output_root)),
        seed=selected_seed,
        workspace_root=str(workspace),
        repo_root=str(repository),
        baseline_path=str(Path(baseline_path)) if baseline_path is not None else None,
        metric_path=str(Path(metric_path)) if metric_path is not None else None,
        reportable=reportable,
        ownership=_worker_ownership(ownership),
        producer=producer,
    )
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_diagnostic_process_entry,
        args=(sender, request),
        name=f"pacd-diagnostic-{ownership.invocation_id}",
    )
    try:
        process.start()
    except Exception as start_error:
        sender.close()
        receiver.close()
        try:
            process.close()
        except ValueError:
            pass
        _retain_parent_failure(workspace, ownership, start_error)
        raise
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
            _retain_timeout_evidence(workspace, ownership)
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
        _retain_parent_failure(workspace, ownership, error)
        raise error
    try:
        envelope = receiver.recv()
    except (EOFError, OSError) as receive_error:
        receiver.close()
        process.close()
        error = RuntimeError(
            f"Diagnostic worker result channel failed: {type(receive_error).__name__}"
        )
        _retain_parent_failure(workspace, ownership, error)
        raise error from receive_error
    receiver.close()
    process.close()
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        error = RuntimeError("Diagnostic worker returned an invalid result envelope")
        _retain_parent_failure(workspace, ownership, error)
        raise error
    if envelope["ok"] is not True:
        try:
            _raise_worker_error(str(envelope.get("error_type")), str(envelope.get("message")))
        except Exception as worker_error:
            _retain_parent_failure(workspace, ownership, worker_error)
            raise
    value = envelope.get("result")
    if not isinstance(value, dict):
        error = RuntimeError("Diagnostic worker result is missing")
        _retain_parent_failure(workspace, ownership, error)
        raise error
    try:
        staged_result = RunResult(
            run_dir=Path(str(value["run_dir"])),
            run_id=str(value["run_id"]),
            seed=int(value["seed"]),
            config_hash=str(value["config_hash"]),
            raw_semantic_hash=str(value["raw_semantic_hash"]),
            summary_semantic_hash=str(value["summary_semantic_hash"]),
            manifest_path=Path(str(value["manifest_path"])),
            elapsed_seconds=float(value["elapsed_seconds"]),
            invocation_id=str(value["invocation_id"]),
            receipt_path=None,
            evidence_label=str(value["evidence_label"]),
        )
        if value.get("receipt_path") is not None:
            raise ValueError("Worker may not create or return an execution receipt")
    except (KeyError, TypeError, ValueError, OverflowError) as conversion_error:
        error = RuntimeError(
            f"Diagnostic worker result fields are invalid: {type(conversion_error).__name__}"
        )
        _retain_parent_failure(workspace, ownership, error)
        raise error from conversion_error
    try:
        return _finalize_owned_result(ownership, staged_result, workspace, producer)
    except Exception as finalization_error:
        _retain_parent_failure(workspace, ownership, finalization_error)
        raise

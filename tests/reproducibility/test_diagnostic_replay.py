"""Semantic replay and retained SHA-256 verification checks."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from conftest import (
    DiagnosticRuns,
    IsolatedWorkspace,
    controlled_config_files,
    run_committed_scenario,
)

from pacd_sim.audit.writer import EVENT_SCHEMA
from pacd_sim.harness.run import RunResult, load_yaml_config
from pacd_sim.reproducibility import evidence_validation
from pacd_sim.reproducibility import verify as verify_module
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import (
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
)
from pacd_sim.reproducibility.paths import is_symlink_or_reparse
from pacd_sim.reproducibility.verify import verify_run


def _run_mission_fixture(workspace: IsolatedWorkspace, redundant: bool = False) -> RunResult:
    source = controlled_config_files(workspace.config_root)[0]
    scenario = load_yaml_config(source)
    scenario["availability_model"] = "required_dependencies_v1"
    scenario["dependencies"] = [
        {
            "id": "dependency-session-service",
            "upstream_id": "session-synthetic-001",
            "downstream_id": "service-synthetic-saas",
            "weight": 1,
        },
    ]
    if redundant:
        services = scenario["services"]
        assert isinstance(services, list)
        services.append({"id": "service-synthetic-backup", "mission_id": "mission-synthetic-core"})
    source.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    return run_committed_scenario(workspace)


@pytest.mark.reproducibility
@pytest.mark.parametrize("redundant", [False, True], ids=["single-support", "redundant-support"])
def test_verified_mission_effect_tracks_actual_session_isolation(
    isolated_workspace: IsolatedWorkspace, redundant: bool
) -> None:
    result = _run_mission_fixture(isolated_workspace, redundant)
    verified = verify_run(
        result.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    )
    assert verified.valid and verified.execution_identity_assured, verified.errors
    rows = pq.read_table(result.run_dir / "raw" / "events.parquet").to_pylist()
    (effect_index,) = [i for i, row in enumerate(rows) if row["event_type"] == "mission_effect"]
    execution, verification, effect = rows[effect_index - 2 : effect_index + 1]
    assert [execution["event_type"], verification["event_type"]] == [
        "simulated_execution",
        "verification",
    ]
    assert (
        execution["action_id"]
        == verification["action_id"]
        == effect["action_id"]
        == "action-allowed"
    )
    assert effect["entity_id"] == "session-synthetic-001"
    assert effect["tick"] == verification["tick"] == execution["tick"]
    executed = json.loads(execution["payload_json"])
    checked = json.loads(verification["payload_json"])
    payload = json.loads(effect["payload_json"])
    assert payload["execution_id"] == executed["execution_id"]
    assert payload["verification_id"] == checked["verification_id"]
    for field in ("state_before_digest", "state_after_digest"):
        assert payload[field] == executed[field]
    before, after = payload["availability_before"], payload["availability_after"]
    assert before["entity_count"] == after["entity_count"] == 5 + int(redundant)
    assert before["service_count"] == after["service_count"] == 1 + int(redundant)
    assert before["mission_count"] == after["mission_count"] == 1
    assert before["available_entity_count"] == before["entity_count"]
    assert before["available_service_count"] == before["service_count"]
    assert before["operational_mission_count"] == 1
    assert after["available_entity_count"] == (4 if redundant else 2)
    assert after["available_service_count"] == after["operational_mission_count"] == int(redundant)
    assert before["availability_digest"] != after["availability_digest"]
    checkpoints = [
        json.loads(row["payload_json"]) for row in rows if row["event_type"] == "state_update"
    ]
    assert len(checkpoints) == 2 and all(entry["availability"] == before for entry in checkpoints)
    disposition = "continued" if redundant else "interrupted"
    assert payload["mission_continuity"] == {
        "continued_mission_count": int(redundant),
        "interrupted_mission_count": int(not redundant),
        "restored_mission_count": 0,
        "unavailable_throughout_mission_count": 0,
        "continuity_digest": canonical_sha256({"mission-synthetic-core": disposition}),
    }


@pytest.mark.reproducibility
@pytest.mark.parametrize("incorrect", [False, 0.0, 1], ids=["boolean", "float", "wrong-count"])
def test_verifier_rejects_incorrect_post_execution_availability(
    isolated_workspace: IsolatedWorkspace, incorrect: bool | float | int
) -> None:
    result = _run_mission_fixture(isolated_workspace)
    copy = isolated_workspace.root / "var" / "tmp" / "altered" / result.run_dir.name
    shutil.copytree(result.run_dir, copy)
    rows = pq.read_table(copy / "raw" / "events.parquet").to_pylist()
    (effect,) = [row for row in rows if row["event_type"] == "mission_effect"]
    payload = json.loads(effect["payload_json"])
    assert payload["availability_after"]["operational_mission_count"] == 0
    payload["availability_after"]["operational_mission_count"] = incorrect
    effect["payload_json"] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _rewrite_raw_events_with_refreshed_closure(copy, rows)
    verified = verify_run(
        copy,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    )
    assert not verified.valid and not verified.semantic_content_valid
    assert any("payload does not match reconstructed event semantics" in e for e in verified.errors)
    assert not any("checksum mismatch" in e.lower() for e in verified.errors)


@pytest.mark.reproducibility
def test_mission_effect_wire_types_match_across_raw_formats(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    result = _run_mission_fixture(isolated_workspace)
    mirror = isolated_workspace.root / "var" / "tmp" / "mirror" / result.run_dir.name
    shutil.copytree(result.run_dir, mirror)
    jsonl = mirror / "raw" / "events.jsonl"
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    (effect,) = [row for row in rows if row["event_type"] == "mission_effect"]
    assert type(effect["tick"]) is float and effect["tick"].is_integer()
    effect["tick"] = int(effect["tick"])
    jsonl.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))
    _refresh_integrity_closure(mirror, ("raw/events.jsonl",))

    verification = verify_run(
        mirror, workspace_root=isolated_workspace.root, repo_root=isolated_workspace.repo_root
    )
    assert not verification.semantic_content_valid
    assert any("JSONL and Parquet raw-event rows" in error for error in verification.errors)


def _manifest(run_dir: Path) -> dict[str, object]:
    value = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


@pytest.mark.reproducibility
def test_v1_schema_migration_preserves_accepted_diagnostic(diagnostic_runs: DiagnosticRuns) -> None:
    """Golden semantic digests from the tagged bootstrap's registered 424242 scenario."""
    run = diagnostic_runs.same_seed_a
    assert run.config_hash == "54e7a429b27bf94deeefe22f79ba22fff7ce36ae35dc6647b02784008ef10364"
    assert run.raw_semantic_hash == (
        "6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf"
    )
    assert run.summary_semantic_hash == (
        "9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76"
    )


def _copy_run(diagnostic_runs: DiagnosticRuns, case_name: str) -> Path:
    """Copy a run beneath a unique parent while preserving its bound run ID."""

    source = diagnostic_runs.same_seed_a.run_dir
    case_id = hashlib.sha256(case_name.encode("utf-8")).hexdigest()[:8]
    parent = diagnostic_runs.workspace.root / "var" / "tmp" / case_id
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / source.name
    shutil.copytree(source, destination)
    return destination


def _write_canonical_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _refresh_integrity_closure(run_dir: Path, changed_artifacts: tuple[str, ...]) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest = _manifest(run_dir)
    manifest_hashes_raw = manifest.get("artifact_hashes")
    assert isinstance(manifest_hashes_raw, dict)
    manifest_hashes = {str(key): str(value) for key, value in manifest_hashes_raw.items()}
    for relative_name in changed_artifacts:
        manifest_hashes[relative_name] = sha256_file(run_dir / relative_name)
    manifest["artifact_hashes"] = manifest_hashes
    _write_canonical_json(manifest_path, manifest)

    checksum_path = run_dir / "SHA256SUMS.txt"
    checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
    checksums: dict[str, str] = {}
    for line in checksum_lines[1:]:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        assert match is not None
        digest, relative_name = match.groups()
        checksums[relative_name] = digest
    for relative_name in changed_artifacts:
        checksums[relative_name] = sha256_file(run_dir / relative_name)
    checksums["manifest.json"] = sha256_file(manifest_path)
    checksum_text = "# evidence_label=NON_REPORTABLE_DIAGNOSTIC\n" + "".join(
        f"{digest}  {relative_name}\n" for relative_name, digest in sorted(checksums.items())
    )
    checksum_path.write_text(checksum_text, encoding="utf-8")


def _rewrite_raw_events_with_refreshed_closure(
    run_dir: Path,
    rows: list[dict[str, object]],
) -> None:
    parquet_path = run_dir / "raw" / "events.parquet"
    jsonl_path = run_dir / "raw" / "events.jsonl"
    jsonl_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(rows, schema=EVENT_SCHEMA),
        parquet_path,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    manifest = _manifest(run_dir)
    manifest["raw_semantic_hash"] = semantic_events_hash(parquet_path)
    _write_canonical_json(run_dir / "manifest.json", manifest)
    _refresh_integrity_closure(
        run_dir,
        ("raw/events.jsonl", "raw/events.parquet"),
    )


def _refresh_manifest_checksum_only(run_dir: Path) -> None:
    checksum_path = run_dir / "SHA256SUMS.txt"
    values: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines()[1:]:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        assert match is not None
        digest, relative_name = match.groups()
        values[relative_name] = digest
    values["manifest.json"] = sha256_file(run_dir / "manifest.json")
    checksum_path.write_text(
        "# evidence_label=NON_REPORTABLE_DIAGNOSTIC\n"
        + "".join(
            f"{digest}  {relative_name}\n" for relative_name, digest in sorted(values.items())
        ),
        encoding="utf-8",
    )


def _refresh_complete_integrity_closure(run_dir: Path) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest = _manifest(run_dir)
    artifact_names = tuple(
        sorted(
            path.relative_to(run_dir).as_posix()
            for path in run_dir.rglob("*")
            if path.is_file() and path.name not in {"SHA256SUMS.txt", "manifest.json"}
        )
    )
    manifest["artifact_hashes"] = {
        relative_name: sha256_file(run_dir / relative_name) for relative_name in artifact_names
    }
    _write_canonical_json(manifest_path, manifest)
    checksums = {
        relative_name: sha256_file(run_dir / relative_name)
        for relative_name in (*artifact_names, "manifest.json")
    }
    (run_dir / "SHA256SUMS.txt").write_text(
        "# evidence_label=NON_REPORTABLE_DIAGNOSTIC\n"
        + "".join(
            f"{digest}  {relative_name}\n" for relative_name, digest in sorted(checksums.items())
        ),
        encoding="utf-8",
    )


@pytest.mark.reproducibility
def test_same_seed_semantic_hashes_match_and_different_seed_is_distinguishable(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    first = diagnostic_runs.same_seed_a
    replay = diagnostic_runs.same_seed_b
    different = diagnostic_runs.different_seed

    assert first.run_id != replay.run_id
    assert first.seed == replay.seed == 424242
    assert first.config_hash == replay.config_hash == different.config_hash
    assert first.raw_semantic_hash == replay.raw_semantic_hash
    assert first.summary_semantic_hash == replay.summary_semantic_hash

    assert different.seed == 424243
    assert different.raw_semantic_hash != first.raw_semantic_hash
    assert different.summary_semantic_hash != first.summary_semantic_hash
    assert _manifest(first.run_dir)["seed"] == 424242
    assert _manifest(different.run_dir)["seed"] == 424243


@pytest.mark.reproducibility
@pytest.mark.parametrize("run_name", ["same_seed_a", "same_seed_b", "different_seed"])
def test_jsonl_parquet_and_manifest_semantic_hashes_agree(
    diagnostic_runs: DiagnosticRuns,
    run_name: str,
) -> None:
    run = getattr(diagnostic_runs, run_name)
    raw_jsonl = run.run_dir / "raw" / "events.jsonl"
    raw_parquet = run.run_dir / "raw" / "events.parquet"
    summary_csv = run.run_dir / "derived" / "episode_summary.csv"
    summary_parquet = run.run_dir / "derived" / "episode_summary.parquet"
    manifest = _manifest(run.run_dir)

    assert semantic_events_hash(raw_jsonl) == semantic_events_hash(raw_parquet)
    assert semantic_events_hash(raw_parquet) == run.raw_semantic_hash
    assert semantic_summary_hash(summary_csv) == semantic_summary_hash(summary_parquet)
    assert semantic_summary_hash(summary_parquet) == run.summary_semantic_hash
    assert manifest["raw_semantic_hash"] == run.raw_semantic_hash
    assert manifest["summary_semantic_hash"] == run.summary_semantic_hash


@pytest.mark.reproducibility
def test_sha256_manifest_lists_and_verifies_every_non_checksum_artifact(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    lines = (run_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()

    assert lines[0] == "# evidence_label=NON_REPORTABLE_DIAGNOSTIC"
    listed: dict[str, str] = {}
    for line in lines[1:]:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        assert match is not None
        digest, relative_name = match.groups()
        assert relative_name not in listed
        assert ".." not in Path(relative_name).parts
        listed[relative_name] = digest
        assert sha256_file(run_dir / relative_name) == digest

    actual_non_checksum = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    assert set(listed) == actual_non_checksum

    result = verify_run(run_dir, workspace_root=diagnostic_runs.workspace.root)
    assert result.valid, result.errors
    assert result.errors == ()
    assert set(result.checked_files) == actual_non_checksum | {"SHA256SUMS.txt"}


@pytest.mark.reproducibility
def test_verifier_detects_post_run_artifact_tampering(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "tampered-run")
    status_path = destination / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert isinstance(status, dict)
    status["post_run_tampering_probe"] = True
    status_path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert not result.semantic_content_valid
    assert any(
        "status.json" in error and "not canonical" in error.lower() for error in result.errors
    )
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error_fragment"),
    [
        ("component", "controlled repository"),
        ("protocol", "controlled repository"),
        ("seed", "seed"),
        ("label", "exact completed diagnostic contract"),
    ],
)
def test_verifier_rejects_cross_artifact_semantic_tampering_even_with_fresh_checksums(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error_fragment: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"semantic-tamper-{tamper_kind}")

    if tamper_kind in {"component", "protocol"}:
        relative_name = "canonical_config.json"
        canonical_path = destination / relative_name
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        assert isinstance(canonical, dict)
        if tamper_kind == "component":
            baseline = canonical.get("baseline_definition")
            assert isinstance(baseline, dict)
            baseline["name"] = "tampered-baseline-definition"
        else:
            canonical["protocol_version"] = "TAMPERED_PROTOCOL"
        _write_canonical_json(canonical_path, canonical)
    elif tamper_kind == "seed":
        relative_name = "seed_registry.json"
        seed_path = destination / relative_name
        registry = json.loads(seed_path.read_text(encoding="utf-8"))
        assert isinstance(registry, dict)
        registry["seeds"] = [424242, 999999]
        _write_canonical_json(seed_path, registry)
    else:
        relative_name = "status.json"
        status_path = destination / relative_name
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert isinstance(status, dict)
        status["evidence_label"] = "TAMPERED_LABEL"
        _write_canonical_json(status_path, status)

    _refresh_integrity_closure(destination, (relative_name,))
    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any(expected_error_fragment in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_enforces_aggregate_output_budget_without_creating_large_files(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_size = verify_module._artifact_size

    def logical_size(path: Path) -> int:
        if path.name == "manifest.json":
            return verify_module.MAX_RUN_OUTPUT_BYTES + 1
        return original_size(path)

    monkeypatch.setattr(verify_module, "_artifact_size", logical_size)

    result = verify_run(
        diagnostic_runs.same_seed_a.run_dir,
        workspace_root=diagnostic_runs.workspace.root,
    )

    assert not result.valid
    assert any("aggregate run output" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_compressed_parquet_that_expands_past_the_read_cap(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "parquet-expansion-cap")

    parquet_path = destination / "raw" / "events.parquet"
    rows = pq.read_table(parquet_path).to_pylist()
    rows[0]["payload_json"] = json.dumps(
        {"padding": "x" * (512 * 1024)},
        separators=(",", ":"),
    )
    pq.write_table(
        pa.Table.from_pylist(rows, schema=EVENT_SCHEMA),
        parquet_path,
        compression="ZSTD",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    assert parquet_path.stat().st_size < 64 * 1024
    manifest = _manifest(destination)
    manifest["raw_semantic_hash"] = semantic_events_hash(parquet_path)
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_integrity_closure(destination, ("raw/events.parquet",))
    monkeypatch.setattr(evidence_validation, "_MAX_RAW_ARTIFACT_BYTES", 64 * 1024)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("decoded column data" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize("simulated_reparse", [False, True])
def test_verifier_rejects_every_unexpected_regular_or_reparse_artifact(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
    simulated_reparse: bool,
) -> None:
    suffix = "reparse" if simulated_reparse else "regular"
    destination = _copy_run(diagnostic_runs, f"extra-{suffix}")
    unexpected = destination / "unexpected-artifact.txt"
    unexpected.write_text("NON_REPORTABLE_DIAGNOSTIC\n", encoding="utf-8")

    if simulated_reparse:
        original_check = is_symlink_or_reparse

        def identify_test_reparse(path: Path) -> bool:
            return path.name == unexpected.name or original_check(path)

        monkeypatch.setattr(
            verify_module,
            "is_symlink_or_reparse",
            identify_test_reparse,
        )

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    expected_fragment = "reparse" if simulated_reparse else "unexpected"
    assert any(expected_fragment in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize("allowlist_case", ["empty", "incomplete"])
def test_verifier_requires_exact_nonempty_manifest_artifact_allowlist(
    diagnostic_runs: DiagnosticRuns,
    allowlist_case: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"allowlist-{allowlist_case}")
    manifest = _manifest(destination)
    artifact_hashes = manifest.get("artifact_hashes")
    assert isinstance(artifact_hashes, dict)
    if allowlist_case == "empty":
        manifest["artifact_hashes"] = {}
    else:
        incomplete = {str(key): value for key, value in artifact_hashes.items()}
        incomplete.pop(next(iter(incomplete)))
        manifest["artifact_hashes"] = incomplete
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_integrity_closure(destination, ())

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("artifact_hashes" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_refreshed_raw_execution_cannot_claim_nonapprove_disposition(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "nonapprove-execution")

    parquet_path = destination / "raw" / "events.parquet"
    jsonl_path = destination / "raw" / "events.jsonl"
    rows = pq.read_table(parquet_path).to_pylist()
    escalated_action_id = next(
        str(row["action_id"])
        for row in rows
        if row["event_type"] == "safety_decision" and row["disposition"] == "ESCALATE"
    )
    execution_rows = [row for row in rows if row["event_type"] == "simulated_execution"]
    assert len(execution_rows) == 1
    execution_rows[0]["action_id"] = escalated_action_id
    execution_rows[0]["disposition"] = "ESCALATE"

    jsonl_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(rows, schema=EVENT_SCHEMA),
        parquet_path,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    manifest = _manifest(destination)
    manifest["raw_semantic_hash"] = semantic_events_hash(parquet_path)
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_integrity_closure(
        destination,
        ("raw/events.jsonl", "raw/events.parquet"),
    )

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any(
        "does not match reconstructed disposition" in error.lower() for error in result.errors
    )
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    [
        ("status_reportable", "exact completed diagnostic contract"),
        ("manifest_reportable", "provenance or identity mismatch: reportable"),
        (
            "policy_adapter",
            "controlled repository",
        ),
        ("policy_network", "controlled repository"),
    ],
)
def test_verifier_rejects_unsafe_mode_tampering_with_refreshed_integrity_closure(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"unsafe-{tamper_kind}")
    changed_artifacts: tuple[str, ...]

    if tamper_kind == "status_reportable":
        relative_name = "status.json"
        status_path = destination / relative_name
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert isinstance(status, dict)
        status["reportable"] = True
        _write_canonical_json(status_path, status)
        changed_artifacts = (relative_name,)
    elif tamper_kind == "manifest_reportable":
        manifest = _manifest(destination)
        manifest["reportable"] = True
        _write_canonical_json(destination / "manifest.json", manifest)
        changed_artifacts = ()
    else:
        relative_name = "canonical_config.json"
        canonical_path = destination / relative_name
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        assert isinstance(canonical, dict)
        policy = canonical.get("safety_policy")
        assert isinstance(policy, dict)
        if tamper_kind == "policy_adapter":
            policy["execution_adapter"] = "external_adapter"
        else:
            policy["network_enabled"] = True
        _write_canonical_json(canonical_path, canonical)
        changed_artifacts = (relative_name,)

    _refresh_integrity_closure(destination, changed_artifacts)
    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any(expected_error in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_each_executed_approve_requires_a_same_action_verified_event(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "unrelated-verification")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()

    execution_rows = [row for row in rows if row["event_type"] == "simulated_execution"]
    assert len(execution_rows) == 1
    executed_action_id = execution_rows[0]["action_id"]
    verified_rows = [
        row
        for row in rows
        if row["event_type"] == "verification"
        and row["disposition"] == "VERIFIED"
        and row["outcome"] == "verified"
    ]
    assert len(verified_rows) == 1
    assert verified_rows[0]["action_id"] == executed_action_id
    unrelated_action_id = next(
        row["action_id"]
        for row in rows
        if row["event_type"] == "safety_decision" and row["action_id"] != executed_action_id
    )
    verified_rows[0]["action_id"] = unrelated_action_id

    _rewrite_raw_events_with_refreshed_closure(destination, rows)
    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("does not match reconstructed action_id" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    [
        ("adapter", "payload does not match reconstructed event semantics"),
        ("network", "payload does not match reconstructed event semantics"),
    ],
)
def test_verifier_rejects_unsafe_execution_payload_with_refreshed_integrity_closure(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"unsafe-raw-{tamper_kind}")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()
    execution_rows = [row for row in rows if row["event_type"] == "simulated_execution"]
    assert execution_rows

    for row in execution_rows:
        payload = json.loads(str(row["payload_json"]))
        assert isinstance(payload, dict)
        if tamper_kind == "adapter":
            payload["adapter"] = "external_adapter"
        else:
            payload["network_enabled"] = True
        row["payload_json"] = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    _rewrite_raw_events_with_refreshed_closure(destination, rows)
    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any(expected_error in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_duplicate_manifest_key_with_refreshed_checksum(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "duplicate-manifest-key")
    manifest_path = destination / "manifest.json"
    original = manifest_path.read_text(encoding="utf-8")
    duplicate = f'{{"seed":{_manifest(destination)["seed"]},' + original[1:]
    manifest_path.write_text(duplicate, encoding="utf-8")
    _refresh_manifest_checksum_only(destination)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("duplicate json key" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    [
        ("extra_key", "keys are not exact"),
        ("commit", "code_commit"),
        ("dirty", "dirty_state"),
        ("python", "python_version"),
        ("lock", "lockfile_hash"),
    ],
)
def test_verifier_rejects_manifest_schema_and_provenance_forgery(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"manifest-forgery-{tamper_kind}")
    manifest = _manifest(destination)
    if tamper_kind == "extra_key":
        manifest["untrusted_claim"] = "accepted"
    elif tamper_kind == "commit":
        manifest["code_commit"] = "1" * 40
    elif tamper_kind == "dirty":
        manifest["dirty_state"] = not bool(manifest["dirty_state"])
    elif tamper_kind == "python":
        manifest["python_version"] = "0.0.0-forged"
    else:
        manifest["lockfile_hash"] = "2" * 64
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_manifest_checksum_only(destination)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any(expected_error in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_duplicate_payload_key_after_integrity_refresh(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "duplicate-payload-key")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()
    candidate = next(row for row in rows if row["event_type"] == "candidate_action")
    payload_text = str(candidate["payload_json"])
    candidate["payload_json"] = '{"action_type":"forged",' + payload_text[1:]
    _rewrite_raw_events_with_refreshed_closure(destination, rows)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("duplicate json key" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_relabelled_candidate_after_integrity_refresh(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "relabelled-candidate")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()
    candidate = next(
        row
        for row in rows
        if row["event_type"] == "candidate_action" and row["action_id"] == "action-allowed"
    )
    payload = json.loads(str(candidate["payload_json"]))
    assert isinstance(payload, dict)
    payload["action_type"] = "external_network_scan"
    payload["requested_authority"] = "prohibited"
    payload["reversible"] = False
    candidate["payload_json"] = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    _rewrite_raw_events_with_refreshed_closure(destination, rows)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("reconstructed event semantics" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_resequenced_identity_and_duplicate_execution(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "forged-event-chain")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()
    execution_index = next(
        index for index, row in enumerate(rows) if row["event_type"] == "simulated_execution"
    )
    rows.insert(execution_index + 1, dict(rows[execution_index]))
    for sequence, row in enumerate(rows, start=1):
        row["sequence"] = sequence
    rows[2]["run_id"] = "forged-run-id"
    _rewrite_raw_events_with_refreshed_closure(destination, rows)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("reconstructed diagnostic chain" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_raw_run_identity_mutation_after_integrity_refresh(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "forged-run-identity")
    rows = pq.read_table(destination / "raw" / "events.parquet").to_pylist()
    rows[2]["run_id"] = "forged-run-id"
    _rewrite_raw_events_with_refreshed_closure(destination, rows)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("run_id" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_requires_a_clean_controlled_checkout(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    dirty_probe = diagnostic_runs.workspace.repo_root / "task-created-dirty-probe.txt"
    dirty_probe.write_text("test-only\n", encoding="utf-8")
    try:
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
        )
    finally:
        dirty_probe.unlink()

    assert not result.valid
    assert any("clean controlled checkout" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
def test_verifier_rejects_fully_refreshed_controlled_configuration_substitution(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "refreshed-config-closure")

    canonical_path = destination / "canonical_config.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    assert isinstance(canonical, dict)
    scenario = canonical["scenario"]
    assert isinstance(scenario, dict)
    scenario["name"] = "forged-self-consistent-scenario"
    _write_canonical_json(canonical_path, canonical)
    config_hash = sha256_file(canonical_path)

    raw_parquet = destination / "raw" / "events.parquet"
    raw_rows = pq.read_table(raw_parquet).to_pylist()
    for row in raw_rows:
        row["config_hash"] = config_hash
    raw_jsonl = destination / "raw" / "events.jsonl"
    raw_jsonl.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for row in raw_rows
        ),
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(raw_rows, schema=EVENT_SCHEMA),
        raw_parquet,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )

    summary_parquet = destination / "derived" / "episode_summary.parquet"
    summary_table = pq.read_table(summary_parquet)
    summary_rows = summary_table.to_pylist()
    assert len(summary_rows) == 1
    summary_rows[0]["config_hash"] = config_hash
    pq.write_table(
        pa.Table.from_pylist(summary_rows, schema=summary_table.schema),
        summary_parquet,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    summary_csv = destination / "derived" / "episode_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_table.column_names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    manifest = _manifest(destination)
    configuration_hashes = manifest["configuration_hashes"]
    assert isinstance(configuration_hashes, dict)
    configuration_hashes.update(
        {
            "aggregate": config_hash,
            "scenario": canonical_sha256(scenario),
            "safety_policy": canonical_sha256(canonical["safety_policy"]),
            "baseline_definition": canonical_sha256(canonical["baseline_definition"]),
            "metric_definition": canonical_sha256(canonical["metric_definition"]),
        }
    )
    manifest["config_hash_start"] = config_hash
    manifest["config_hash_end"] = config_hash
    manifest["baseline_definition_hash"] = configuration_hashes["baseline_definition"]
    manifest["metric_definition_hash"] = configuration_hashes["metric_definition"]
    manifest["raw_semantic_hash"] = semantic_events_hash(raw_parquet)
    manifest["summary_semantic_hash"] = semantic_summary_hash(summary_parquet)
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_complete_integrity_closure(destination)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("controlled repository" in error.lower() for error in result.errors)
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)

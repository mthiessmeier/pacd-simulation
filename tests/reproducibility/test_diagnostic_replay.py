"""Semantic replay and retained SHA-256 verification checks."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns

from pacd_sim.audit.writer import EVENT_SCHEMA
from pacd_sim.reproducibility import verify as verify_module
from pacd_sim.reproducibility.manifest import (
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
)
from pacd_sim.reproducibility.paths import is_symlink_or_reparse
from pacd_sim.reproducibility.verify import verify_run


def _manifest(run_dir: Path) -> dict[str, object]:
    value = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


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
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / "tampered-run"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    status_path = destination / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert isinstance(status, dict)
    status["post_run_tampering_probe"] = True
    status_path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("Checksum mismatch: status.json" in error for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error_fragment"),
    [
        ("component", "baseline"),
        ("protocol", "protocol"),
        ("seed", "seed"),
        ("label", "label"),
    ],
)
def test_verifier_rejects_cross_artifact_semantic_tampering_even_with_fresh_checksums(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error_fragment: str,
) -> None:
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / f"semantic-tamper-{tamper_kind}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)

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
@pytest.mark.parametrize("simulated_reparse", [False, True])
def test_verifier_rejects_every_unexpected_regular_or_reparse_artifact(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
    simulated_reparse: bool,
) -> None:
    source = diagnostic_runs.same_seed_a.run_dir
    suffix = "reparse" if simulated_reparse else "regular"
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / f"extra-{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
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
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / f"allowlist-{allowlist_case}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
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
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / "nonapprove-execution"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)

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
        "execution" in error.lower() and "approve" in error.lower() for error in result.errors
    )
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    [
        ("status_reportable", "status must declare reportable=false"),
        ("manifest_reportable", "manifest must declare reportable=false"),
        (
            "policy_adapter",
            "safety policy must require execution_adapter=simulated_only",
        ),
        ("policy_network", "safety policy must require network_enabled=false"),
    ],
)
def test_verifier_rejects_unsafe_mode_tampering_with_refreshed_integrity_closure(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error: str,
) -> None:
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / f"unsafe-{tamper_kind}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
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
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / "unrelated-verification"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
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
    assert any(
        "lacks a same-action verified verification event" in error.lower()
        for error in result.errors
    )
    assert not any("checksum mismatch" in error.lower() for error in result.errors)
    assert not any("raw-event semantics differ" in error.lower() for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    [
        ("adapter", "execution payload must declare adapter=simulated_only"),
        ("network", "execution payload must declare network_enabled=false"),
    ],
)
def test_verifier_rejects_unsafe_execution_payload_with_refreshed_integrity_closure(
    diagnostic_runs: DiagnosticRuns,
    tamper_kind: str,
    expected_error: str,
) -> None:
    source = diagnostic_runs.same_seed_a.run_dir
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / f"unsafe-raw-{tamper_kind}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
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

"""Instrumented regression tests for terminal, single-pass Parquet ingestion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns

import pacd_sim.reproducibility.verify as verify_module
from pacd_sim.audit.writer import EVENT_SCHEMA
from pacd_sim.metrics.summarize import SUMMARY_SCHEMA
from pacd_sim.reproducibility import evidence_validation
from pacd_sim.reproducibility.manifest import (
    semantic_events_hash,
    semantic_summary_hash,
    sha256_file,
)
from pacd_sim.reproducibility.receipts import verify_execution_receipt
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
    checksums: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines()[1:]:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        assert match is not None
        digest, relative_name = match.groups()
        checksums[relative_name] = digest
    for relative_name in changed_artifacts:
        checksums[relative_name] = sha256_file(run_dir / relative_name)
    checksums["manifest.json"] = sha256_file(manifest_path)
    checksum_path.write_text(
        "# evidence_label=NON_REPORTABLE_DIAGNOSTIC\n"
        + "".join(
            f"{digest}  {relative_name}\n" for relative_name, digest in sorted(checksums.items())
        ),
        encoding="utf-8",
    )


def _copy_run(diagnostic_runs: DiagnosticRuns, name: str) -> Path:
    case_id = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    parent = diagnostic_runs.workspace.root / "var" / "tmp" / case_id
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / diagnostic_runs.same_seed_a.run_dir.name
    shutil.copytree(diagnostic_runs.same_seed_a.run_dir, destination)
    return destination


def _parquet_source_path(source: object) -> Path:
    candidate = getattr(source, "name", source)
    if not isinstance(candidate, (str, Path)):
        raise TypeError("Instrumented Parquet source has no filesystem path")
    return Path(candidate).resolve()


def _instrument_parquet_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[Path], list[Path], list[Path]]:
    original_parquet_file = pq.ParquetFile
    open_calls: list[Path] = []
    read_calls: list[Path] = []
    read_table_calls: list[Path] = []

    class InstrumentedParquetFile:
        def __init__(self, source: Path | str, *args: Any, **kwargs: Any) -> None:
            self.path = _parquet_source_path(source)
            open_calls.append(self.path)
            self._inner = original_parquet_file(source, *args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

        def read(self, *args: Any, **kwargs: Any) -> pa.Table:
            read_calls.append(self.path)
            return self._inner.read(*args, **kwargs)

    def reject_read_table(source: Path | str, *args: Any, **kwargs: Any) -> pa.Table:
        read_table_calls.append(_parquet_source_path(source))
        raise AssertionError("verify_run must not call pq.read_table")

    monkeypatch.setattr(pq, "ParquetFile", InstrumentedParquetFile)
    monkeypatch.setattr(pq, "read_table", reject_read_table)
    return open_calls, read_calls, read_table_calls


@pytest.mark.reproducibility
def test_raw_decoded_cap_failure_is_terminal_before_any_parquet_materialization(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "r01-raw-decoded-cap")
    raw_path = destination / "raw" / "events.parquet"
    rows = pq.read_table(raw_path).to_pylist()
    rows[0]["payload_json"] = json.dumps(
        {"padding": "x" * (512 * 1024)},
        separators=(",", ":"),
    )
    pq.write_table(
        pa.Table.from_pylist(rows, schema=EVENT_SCHEMA),
        raw_path,
        compression="ZSTD",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    assert raw_path.stat().st_size < 64 * 1024
    manifest = _manifest(destination)
    manifest["raw_semantic_hash"] = semantic_events_hash(raw_path)
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_integrity_closure(destination, ("raw/events.parquet",))
    monkeypatch.setattr(evidence_validation, "_MAX_RAW_ARTIFACT_BYTES", 64 * 1024)
    _opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("Raw Parquet decoded column data" in error for error in result.errors)
    assert reads == []
    assert read_tables == []


@pytest.mark.reproducibility
def test_derived_decoded_cap_failure_is_terminal_before_any_parquet_materialization(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "r01-derived-decoded-cap")
    summary_path = destination / "derived" / "episode_summary.parquet"
    rows = pq.read_table(summary_path).to_pylist()
    rows[0]["completion_status"] = "x" * (512 * 1024)
    pq.write_table(
        pa.Table.from_pylist(rows, schema=SUMMARY_SCHEMA),
        summary_path,
        compression="ZSTD",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    assert summary_path.stat().st_size < 64 * 1024
    manifest = _manifest(destination)
    manifest["summary_semantic_hash"] = semantic_summary_hash(summary_path)
    _write_canonical_json(destination / "manifest.json", manifest)
    _refresh_integrity_closure(destination, ("derived/episode_summary.parquet",))
    monkeypatch.setattr(evidence_validation, "_MAX_SUMMARY_ARTIFACT_BYTES", 64 * 1024)
    _opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("Derived summary Parquet decoded column data" in error for error in result.errors)
    assert reads == []
    assert read_tables == []


@pytest.mark.reproducibility
def test_aggregate_encoded_cap_failure_opens_or_materializes_no_parquet(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(evidence_validation, "_MAX_PARQUET_AGGREGATE_ENCODED_BYTES", 1)
    opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    result = verify_run(
        diagnostic_runs.same_seed_a.run_dir,
        workspace_root=diagnostic_runs.workspace.root,
    )

    assert not result.valid
    assert any("Aggregate encoded Parquet size" in error for error in result.errors)
    assert opens == []
    assert reads == []
    assert read_tables == []


@pytest.mark.reproducibility
def test_accepted_parquet_is_materialized_once_per_artifact_and_never_reopened(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    raw_path = (run_dir / "raw" / "events.parquet").resolve()
    summary_path = (run_dir / "derived" / "episode_summary.parquet").resolve()
    opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    result = verify_run(run_dir, workspace_root=diagnostic_runs.workspace.root)

    assert result.valid, result.errors
    assert read_tables == []
    assert Counter(opens) == Counter({raw_path: 1, summary_path: 1})
    assert Counter(reads) == Counter({raw_path: 1, summary_path: 1})


@pytest.mark.reproducibility
def test_rejected_materialized_raw_table_prevents_summary_materialization(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    raw_path = (run_dir / "raw" / "events.parquet").resolve()
    summary_path = (run_dir / "derived" / "episode_summary.parquet").resolve()
    original_parquet_file = pq.ParquetFile
    oversized_rows = original_parquet_file(raw_path).read().to_pylist()
    oversized_rows[0]["payload_json"] = json.dumps(
        {"padding": "x" * (512 * 1024)},
        separators=(",", ":"),
    )
    oversized_raw = pa.Table.from_pylist(oversized_rows, schema=EVENT_SCHEMA)
    read_calls: list[Path] = []

    class UnderreportedParquetFile:
        def __init__(self, source: Path | str, *args: Any, **kwargs: Any) -> None:
            self.path = _parquet_source_path(source)
            self._inner = original_parquet_file(source, *args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

        def read(self, *args: Any, **kwargs: Any) -> pa.Table:
            read_calls.append(self.path)
            if self.path == raw_path:
                return oversized_raw
            return self._inner.read(*args, **kwargs)

    def reject_read_table(*_args: Any, **_kwargs: Any) -> pa.Table:
        raise AssertionError("verify_run must not call pq.read_table")

    monkeypatch.setattr(evidence_validation, "_MAX_RAW_ARTIFACT_BYTES", 64 * 1024)
    monkeypatch.setattr(pq, "ParquetFile", UnderreportedParquetFile)
    monkeypatch.setattr(pq, "read_table", reject_read_table)

    result = verify_run(run_dir, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("Materialized Raw Parquet exceeds" in error for error in result.errors)
    assert read_calls == [raw_path]
    assert summary_path not in read_calls


@pytest.mark.reproducibility
def test_hard_linked_raw_parquet_is_rejected_before_materialization(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "r01-hard-linked-raw")
    raw_path = destination / "raw" / "events.parquet"
    held = diagnostic_runs.workspace.root / "var" / "tmp" / "r01-hard-link-source.parquet"
    raw_path.rename(held)
    try:
        os.link(held, raw_path)
    except OSError as error:
        held.rename(raw_path)
        pytest.skip(f"hard links are unavailable on this host: {error}")
    _opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    try:
        result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)
    finally:
        raw_path.unlink()
        held.rename(raw_path)

    assert not result.valid
    assert any("singly linked" in error for error in result.errors)
    assert reads == []
    assert read_tables == []


@pytest.mark.reproducibility
def test_parquet_path_substitution_after_ingestion_fails_final_identity_check(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    raw_path = (run_dir / "raw" / "events.parquet").resolve()
    held = diagnostic_runs.workspace.root / "var" / "tmp" / "original-raw-parquet-held"
    original_receipt_check = verify_execution_receipt
    substituted = False

    def substitute_after_receipt(**kwargs: Any) -> Any:
        nonlocal substituted
        receipt = original_receipt_check(**kwargs)
        raw_path.rename(held)
        try:
            shutil.copyfile(held, raw_path)
        except Exception:
            held.rename(raw_path)
            raise
        substituted = True
        return receipt

    monkeypatch.setattr(
        verify_module,
        "verify_execution_receipt",
        substitute_after_receipt,
    )
    _opens, reads, read_tables = _instrument_parquet_materialization(monkeypatch)

    try:
        result = verify_module.verify_run(
            run_dir,
            workspace_root=diagnostic_runs.workspace.root,
        )
    finally:
        if substituted:
            raw_path.unlink()
            held.rename(raw_path)

    assert substituted
    assert not result.valid
    assert any("changed during complete verification" in error for error in result.errors)
    assert Counter(reads) == Counter(
        {
            raw_path: 1,
            (run_dir / "derived" / "episode_summary.parquet").resolve(): 1,
        }
    )
    assert read_tables == []

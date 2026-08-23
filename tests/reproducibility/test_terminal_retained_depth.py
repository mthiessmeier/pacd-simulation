"""N-03 regressions for terminal, depth-bounded retained-evidence rejection."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns

import pacd_sim.cli as cli_module
import pacd_sim.reproducibility.evidence_validation as evidence_validation_module
import pacd_sim.reproducibility.verify as verify_module
from pacd_sim.reproducibility.canonical import canonical_json_bytes
from pacd_sim.reproducibility.evidence_validation import strict_json_loads
from pacd_sim.reproducibility.manifest import (
    MAX_RETAINED_PAYLOAD_DEPTH,
    semantic_events_hash,
)
from pacd_sim.reproducibility.verify import VerificationResult, verify_run


def _nested_json(depth: int, shape: str = "object") -> str:
    if shape == "object":
        return '{"nested":' * depth + "0" + "}" * depth
    if shape == "array":
        return "[" * depth + "0" + "]" * depth
    if shape == "mixed":
        openings: list[str] = []
        closings: list[str] = []
        for index in range(depth):
            if index % 2:
                openings.append("[")
                closings.append("]")
            else:
                openings.append('{"nested":')
                closings.append("}")
        return "".join(openings) + "0" + "".join(reversed(closings))
    raise AssertionError(f"unknown nesting shape: {shape}")


def _copy_run(diagnostic_runs: DiagnosticRuns, name: str) -> Path:
    parent = diagnostic_runs.workspace.root / "var" / "tmp" / name
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / diagnostic_runs.same_seed_a.run_dir.name
    shutil.copytree(diagnostic_runs.same_seed_a.run_dir, destination)
    return destination


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _refresh_checksum_closure(run_dir: Path) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest = cast(
        dict[str, object],
        json.loads(manifest_path.read_text(encoding="utf-8")),
    )
    hashes = manifest.get("artifact_hashes")
    assert isinstance(hashes, dict)
    manifest["artifact_hashes"] = {
        str(name): _sha256(run_dir / str(name)) for name in sorted(hashes)
    }
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    checksum_names = sorted({str(name) for name in hashes} | {"manifest.json"})
    lines = ["# evidence_label=NON_REPORTABLE_DIAGNOSTIC"]
    lines.extend(f"{_sha256(run_dir / name)}  {name}" for name in checksum_names)
    (run_dir / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _replace_raw_payload(run_dir: Path, payload_text: str, *, parquet: bool = True) -> None:
    raw_path = run_dir / "raw" / "events.parquet"
    raw_table = pq.read_table(raw_path)
    rows = cast(list[dict[str, object]], raw_table.to_pylist())
    target = next(
        row
        for row in rows
        if row.get("event_type") == "audit" and row.get("action_id") == "action-allowed"
    )
    target["payload_json"] = payload_text
    if parquet:
        pq.write_table(
            pa.Table.from_pylist(rows, schema=raw_table.schema),
            raw_path,
            compression="NONE",
            use_dictionary=False,
            write_statistics=False,
        )
    (run_dir / "raw" / "events.jsonl").write_bytes(
        b"\n".join(canonical_json_bytes(row) for row in rows) + b"\n"
    )


@pytest.mark.reproducibility
@pytest.mark.parametrize("shape", ["object", "array", "mixed"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_retained_depth_limit_is_exact_for_every_container_shape(
    shape: str,
    offset: int,
) -> None:
    depth = MAX_RETAINED_PAYLOAD_DEPTH + offset
    text = _nested_json(depth, shape)

    if offset <= 0:
        strict_json_loads(text, source=f"{shape}-{depth}")
    else:
        with pytest.raises(ValueError, match=r"documented maximum depth 64 exceeded"):
            strict_json_loads(text, source=f"{shape}-{depth}")


@pytest.mark.reproducibility
def test_recursive_semantic_normalization_has_an_iterative_depth_preflight() -> None:
    nested: object = 0
    for _ in range(MAX_RETAINED_PAYLOAD_DEPTH + 1):
        nested = {"nested": nested}

    with pytest.raises(ValueError, match=r"documented maximum depth 64 exceeded"):
        semantic_events_hash([{"sequence": 1, "unexpected": nested}])


@pytest.mark.reproducibility
@pytest.mark.parametrize("shape", ["object", "array", "mixed"])
def test_semantic_hash_accepts_payload_at_the_exact_documented_depth(shape: str) -> None:
    digest = semantic_events_hash(
        [
            {
                "sequence": 1,
                "payload_json": _nested_json(MAX_RETAINED_PAYLOAD_DEPTH, shape),
            }
        ]
    )

    assert len(digest) == 64


@pytest.mark.reproducibility
def test_complete_verify_accepts_exact_depth_before_local_receipt_binding(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "exact-depth")
    payload_text = _nested_json(MAX_RETAINED_PAYLOAD_DEPTH)
    _replace_raw_payload(
        destination,
        payload_text,
    )
    original_expected_rows = evidence_validation_module._expected_event_rows

    def expected_rows_with_bounded_payload(
        canonical_config: dict[str, object],
        seed: int,
    ) -> list[dict[str, object]]:
        rows = original_expected_rows(canonical_config, seed)
        target = next(
            row
            for row in rows
            if row.get("event_type") == "audit" and row.get("action_id") == "action-allowed"
        )
        target["payload"] = strict_json_loads(payload_text, source="exact-depth payload")
        return rows

    monkeypatch.setattr(
        evidence_validation_module,
        "_expected_event_rows",
        expected_rows_with_bounded_payload,
    )
    manifest_path = destination / "manifest.json"
    manifest = cast(
        dict[str, object],
        json.loads(manifest_path.read_text(encoding="utf-8")),
    )
    manifest["raw_semantic_hash"] = semantic_events_hash(destination / "raw" / "events.parquet")
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    _refresh_checksum_closure(destination)

    result = verify_run(
        destination,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert result.semantic_content_valid
    assert result.raw_semantic_hash == manifest["raw_semantic_hash"]
    assert not result.execution_identity_assured
    assert not result.valid
    assert not result.reportable
    assert not any("nested" in error.casefold() for error in result.errors)


@pytest.mark.reproducibility
def test_exact_1500_level_review_payload_is_terminal_for_every_downstream_consumer(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "x")
    payload = _nested_json(1_500, "object")
    assert len(payload.encode("utf-8")) == 16_501
    _replace_raw_payload(destination, payload)
    _refresh_checksum_closure(destination)

    def unexpected_consumer(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("strictly rejected retained rows reached a downstream consumer")

    for name in (
        "_parse_sha256s",
        "_stable_artifact_snapshot",
        "_verify_labelled_rows",
        "canonical_sha256",
        "semantic_events_hash",
        "semantic_summary_hash",
        "summary_from_raw_table",
        "verify_execution_receipt",
    ):
        monkeypatch.setattr(verify_module, name, unexpected_consumer)

    result = verify_run(
        destination,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert isinstance(result, VerificationResult)
    assert not result.valid
    assert not result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.reportable
    assert result.raw_semantic_hash is None
    assert result.summary_semantic_hash is None
    assert result.receipt_path is None
    assert any("documented maximum depth 64 exceeded" in error for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("failure_mode", "expected_error", "expected_artifact"),
    [
        ("missing", "artifact set is incomplete", "canonical_config.json"),
        ("empty", "artifact set is incomplete", "canonical_config.json"),
        ("extra", "Unexpected run artifact", "unexpected.bin"),
    ],
)
def test_invalid_artifact_inventory_is_terminal_for_every_downstream_consumer(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
    expected_error: str,
    expected_artifact: str,
) -> None:
    destination = _copy_run(diagnostic_runs, f"strict-{failure_mode}")
    canonical_path = destination / "canonical_config.json"
    if failure_mode == "missing":
        canonical_path.unlink()
    elif failure_mode == "empty":
        canonical_path.write_bytes(b"")
    else:
        (destination / expected_artifact).write_bytes(b"unexpected retained artifact")

    def unexpected_consumer(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("incomplete strict evidence reached a later consumer")

    for name in (
        "validate_retained_evidence",
        "_parse_sha256s",
        "_stable_artifact_snapshot",
        "_verify_labelled_rows",
        "canonical_sha256",
        "semantic_events_hash",
        "semantic_summary_hash",
        "summary_from_raw_table",
        "verify_execution_receipt",
    ):
        monkeypatch.setattr(verify_module, name, unexpected_consumer)

    result = verify_run(
        destination,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert isinstance(result, VerificationResult)
    assert not result.valid
    assert not result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.reportable
    assert any(expected_error in error for error in result.errors)
    assert any(expected_artifact in error for error in result.errors)


@pytest.mark.reproducibility
def test_deep_jsonl_payload_is_rejected_during_strict_ingestion(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    destination = _copy_run(diagnostic_runs, "j")
    _replace_raw_payload(
        destination,
        _nested_json(MAX_RETAINED_PAYLOAD_DEPTH + 1),
        parquet=False,
    )

    result = verify_run(
        destination,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert not result.valid
    assert not result.semantic_content_valid
    assert not result.reportable
    assert any("raw/events.jsonl payload_json" in error for error in result.errors)
    assert any("documented maximum depth 64 exceeded" in error for error in result.errors)


@pytest.mark.reproducibility
@pytest.mark.parametrize(
    ("relative_name", "unexpected_key", "expected_document_reads"),
    [
        ("canonical_config.json", "zz_unexpected", ("canonical_config.json",)),
        (
            "manifest.json",
            "zz_unexpected",
            (
                "canonical_config.json",
                "seed_registry.json",
                "status.json",
                "manifest.json",
            ),
        ),
    ],
)
def test_deep_canonical_document_and_manifest_unexpected_data_are_terminal(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
    relative_name: str,
    unexpected_key: str,
    expected_document_reads: tuple[str, ...],
) -> None:
    destination = _copy_run(diagnostic_runs, "c" if relative_name.startswith("canonical") else "m")
    target = destination / relative_name
    original = target.read_text(encoding="utf-8")
    assert original.endswith("}")
    target.write_text(
        original[:-1]
        + f',"{unexpected_key}":'
        + _nested_json(MAX_RETAINED_PAYLOAD_DEPTH + 1)
        + "}",
        encoding="utf-8",
        newline="\n",
    )

    document_reads: list[str] = []
    original_read = evidence_validation_module._read_strict_object

    def tracked_read(path: Path) -> Any:
        document_reads.append(path.name)
        return original_read(path)

    def unexpected_consumer(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("strict document failure reached a later consumer")

    monkeypatch.setattr(evidence_validation_module, "_read_strict_object", tracked_read)
    for name in ("_validate_document_shapes", "_ingest_bounded_parquet"):
        monkeypatch.setattr(evidence_validation_module, name, unexpected_consumer)
    for name in (
        "_parse_sha256s",
        "_stable_artifact_snapshot",
        "_verify_labelled_rows",
        "canonical_sha256",
        "semantic_events_hash",
        "semantic_summary_hash",
        "summary_from_raw_table",
        "verify_execution_receipt",
    ):
        monkeypatch.setattr(verify_module, name, unexpected_consumer)

    result = verify_run(
        destination,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert not result.valid
    assert not result.semantic_content_valid
    assert not result.reportable
    assert tuple(document_reads) == expected_document_reads
    assert any(relative_name in error for error in result.errors)
    assert any("documented maximum depth 64 exceeded" in error for error in result.errors)


@pytest.mark.reproducibility
def test_public_cli_emits_structured_invalid_for_deep_retained_payload(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "l")
    _replace_raw_payload(destination, _nested_json(1_500))
    _refresh_checksum_closure(destination)
    monkeypatch.setattr(
        cli_module,
        "_default_repo_root",
        lambda: diagnostic_runs.workspace.repo_root,
    )
    monkeypatch.setattr(
        cli_module,
        "infer_workspace_root",
        lambda _repository: diagnostic_runs.workspace.root,
    )
    emitted: list[object] = []
    monkeypatch.setattr(cli_module, "_emit_json", lambda value: emitted.append(value))

    exit_code = cli_module.main(
        [
            "verify",
            str(destination),
            "--workspace-root",
            str(diagnostic_runs.workspace.root),
        ]
    )
    assert len(emitted) == 1
    payload = cast(dict[str, object], emitted[0])

    assert exit_code == 1
    assert payload["status"] == "INVALID"
    assert payload["valid"] is False
    assert payload["semantic_content_valid"] is False
    assert payload["reportable"] is False
    errors = payload["errors"]
    assert isinstance(errors, tuple)
    assert any("documented maximum depth 64 exceeded" in str(error) for error in errors)


@pytest.mark.reproducibility
def test_final_recursion_boundary_returns_a_structured_invalid_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_recursion(*_args: Any, **_kwargs: Any) -> Any:
        raise RecursionError("defensive-boundary-probe")

    monkeypatch.setattr(verify_module, "_verify_run_impl", raise_recursion)

    result = verify_module.verify_run(Path("bounded-hostile-run"))

    assert isinstance(result, VerificationResult)
    assert not result.valid
    assert not result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.reportable
    assert any("defensive-boundary-probe" in error for error in result.errors)

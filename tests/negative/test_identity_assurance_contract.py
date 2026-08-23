"""Governing N-02 cooperative local-identity assurance contract."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from conftest import DiagnosticRuns

import pacd_sim.cli as cli_module
from pacd_sim.reproducibility.canonical import canonical_json_bytes
from pacd_sim.reproducibility.receipts import (
    HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED,
    IDENTITY_ASSURANCE_SCOPE,
)
from pacd_sim.reproducibility.verify import VerificationResult, verify_run


def _assert_scope(result: VerificationResult) -> None:
    assert result.identity_assurance_scope == ("LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING")
    assert result.identity_assurance_scope == IDENTITY_ASSURANCE_SCOPE
    assert result.historical_control_file_inode_continuity_assured is False
    assert result.historical_control_file_inode_continuity_assured is (
        HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED
    )
    assert result.reportable is False


def _control_path(diagnostic_runs: DiagnosticRuns, kind: str) -> Path:
    run = diagnostic_runs.same_seed_a
    if kind == "receipt":
        assert run.receipt_path is not None
        return run.receipt_path
    if kind == "ownership":
        return (
            diagnostic_runs.workspace.root
            / "var"
            / "invocations"
            / run.invocation_id
            / "ownership.json"
        )
    raise AssertionError(f"unknown control kind: {kind}")


@contextmanager
def _replace_control_file(
    diagnostic_runs: DiagnosticRuns,
    kind: str,
    replacement: bytes | None,
    *,
    hard_link: bool = False,
) -> Iterator[tuple[Path, Path]]:
    path = _control_path(diagnostic_runs, kind)
    original = path.read_bytes()
    held_root = diagnostic_runs.workspace.root / "var" / "tmp" / "n02-held"
    held_root.mkdir(parents=True, exist_ok=True)
    held = held_root / f"{diagnostic_runs.same_seed_a.invocation_id}-{kind}.held"
    assert not held.exists()
    before = path.stat(follow_symlinks=False)
    path.replace(held)
    try:
        if hard_link:
            try:
                os.link(held, path)
            except OSError as error:
                pytest.skip(f"hard links are unavailable on this host: {error}")
        elif replacement is not None:
            with path.open("xb") as handle:
                handle.write(replacement)
                handle.flush()
                os.fsync(handle.fileno())
        if path.exists():
            after = path.stat(follow_symlinks=False)
            if hard_link:
                assert after.st_ino == before.st_ino
            else:
                assert after.st_ino != before.st_ino
            assert after.st_nlink == (2 if hard_link else 1)
        yield path, held
    finally:
        if path.exists():
            path.unlink()
        held.replace(path)
        assert path.read_bytes() == original
        assert path.stat(follow_symlinks=False).st_nlink == 1


@pytest.mark.negative
@pytest.mark.parametrize("kind", ["receipt", "ownership"])
def test_byte_identical_same_path_control_replacement_preserves_cooperative_binding(
    diagnostic_runs: DiagnosticRuns,
    kind: str,
) -> None:
    original = _control_path(diagnostic_runs, kind).read_bytes()
    with _replace_control_file(diagnostic_runs, kind, original):
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )

    assert result.semantic_content_valid
    assert result.execution_identity_assured
    assert result.valid
    _assert_scope(result)


@pytest.mark.negative
@pytest.mark.parametrize("kind", ["receipt", "ownership"])
def test_hard_linked_control_file_fails_current_binding(
    diagnostic_runs: DiagnosticRuns,
    kind: str,
) -> None:
    with _replace_control_file(diagnostic_runs, kind, None, hard_link=True):
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )

    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.valid
    _assert_scope(result)
    assert any("singly linked" in error for error in result.errors)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("final_run_path", "C:\\invalid-local-binding"),
        ("run_id", "diagnostic-mismatched-run"),
        ("canonical_config_hash", "0" * 64),
        ("seed", 424243),
        ("raw_semantic_hash", "0" * 64),
    ],
)
def test_changed_receipt_run_configuration_seed_or_hash_binding_fails(
    diagnostic_runs: DiagnosticRuns,
    field: str,
    replacement: object,
) -> None:
    path = _control_path(diagnostic_runs, "receipt")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value[field] = replacement
    changed = canonical_json_bytes(value)
    assert changed != path.read_bytes()

    with _replace_control_file(diagnostic_runs, "receipt", changed):
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )

    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.valid
    _assert_scope(result)
    assert any("receipt" in error.lower() for error in result.errors)


@pytest.mark.negative
@pytest.mark.parametrize("kind", ["receipt", "ownership"])
def test_changed_control_file_bytes_fail_current_binding(
    diagnostic_runs: DiagnosticRuns,
    kind: str,
) -> None:
    path = _control_path(diagnostic_runs, kind)
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value["seed"] = 424243
    changed = canonical_json_bytes(value)
    assert changed != path.read_bytes()

    with _replace_control_file(diagnostic_runs, kind, changed):
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )

    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.valid
    _assert_scope(result)


@pytest.mark.negative
def test_changed_control_path_fails_but_keeps_fixed_scope(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    with _replace_control_file(diagnostic_runs, "receipt", None):
        result = verify_run(
            diagnostic_runs.same_seed_a.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )

    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.valid
    _assert_scope(result)
    assert any("missing" in error.lower() for error in result.errors)


@pytest.mark.negative
def test_structured_fields_exist_for_valid_and_early_invalid_results(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    valid = verify_run(
        diagnostic_runs.same_seed_a.run_dir,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )
    invalid = verify_run(
        diagnostic_runs.workspace.output_root / "absent-run",
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert valid.valid
    assert not invalid.valid
    for result in (valid, invalid):
        _assert_scope(result)
        payload = result.to_dict()
        assert payload["identity_assurance_scope"] == IDENTITY_ASSURANCE_SCOPE
        assert payload["historical_control_file_inode_continuity_assured"] is False
        assert payload["reportable"] is False


@pytest.mark.negative
def test_cli_serializes_fixed_scope_without_positive_attestation_claims(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "_default_repo_root",
        lambda: diagnostic_runs.workspace.repo_root,
    )
    monkeypatch.setattr(
        cli_module,
        "_resolve_diagnostic_workspace",
        lambda _repository, _requested: diagnostic_runs.workspace.root,
    )
    emitted: list[object] = []
    monkeypatch.setattr(cli_module, "_emit_json", lambda value: emitted.append(value))

    exit_code = cli_module.main(
        [
            "verify",
            str(diagnostic_runs.same_seed_a.run_dir),
            "--workspace-root",
            str(diagnostic_runs.workspace.root),
        ]
    )
    assert exit_code == 0
    assert len(emitted) == 1
    payload = emitted[0]
    assert isinstance(payload, dict)
    assert payload["status"] == "VERIFIED"
    assert payload["execution_identity_assured"] is True
    assert payload["identity_assurance_scope"] == IDENTITY_ASSURANCE_SCOPE
    assert payload["historical_control_file_inode_continuity_assured"] is False
    assert payload["reportable"] is False
    for prohibited_key in (
        "author_signed",
        "externally_timestamped",
        "worm_storage_assured",
        "malicious_same_user_resistant",
        "cryptographic_execution_attested",
    ):
        assert prohibited_key not in payload

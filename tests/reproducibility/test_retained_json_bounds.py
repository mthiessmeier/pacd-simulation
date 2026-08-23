"""Regressions for terminal bounded reads of retained JSON documents."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from conftest import DiagnosticRuns

import pacd_sim.reproducibility.verify as verify_module
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.verify import verify_run


def _copy_run(diagnostic_runs: DiagnosticRuns, name: str) -> Path:
    destination = diagnostic_runs.workspace.root / "var" / "tmp" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(diagnostic_runs.same_seed_a.run_dir, destination)
    return destination


def _reject_later_text_read(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
) -> None:
    original = Path.read_text
    expected = target.resolve()

    def guarded(path: Path, *args: Any, **kwargs: Any) -> str:
        if path.resolve() == expected:
            raise AssertionError("rejected retained JSON was read again")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)

    def reject_any_later_snapshot(_path: Path) -> Any:
        raise AssertionError("rejected retained JSON reached a later artifact consumer")

    monkeypatch.setattr(verify_module, "_stable_artifact_snapshot", reject_any_later_snapshot)


@pytest.mark.reproducibility
def test_oversized_retained_json_is_not_materialized_by_later_consumers(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "retained-json-oversized")
    target = destination / "canonical_config.json"
    target.write_bytes(b'{"padding":"' + b"x" * (4 * 1024 * 1024) + b'"}')
    _reject_later_text_read(monkeypatch, target)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("not bounded and singly linked" in error for error in result.errors)


@pytest.mark.reproducibility
def test_excessively_nested_retained_json_returns_invalid_verdict(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _copy_run(diagnostic_runs, "retained-json-nested")
    target = destination / "canonical_config.json"
    target.write_bytes(b"[" * 10_000 + b"0" + b"]" * 10_000)
    _reject_later_text_read(monkeypatch, target)

    result = verify_run(destination, workspace_root=diagnostic_runs.workspace.root)

    assert not result.valid
    assert any("Excessively nested JSON" in error for error in result.errors)


@pytest.mark.reproducibility
def test_configuration_path_substitution_after_receipt_is_rejected(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    target = (run_dir / "canonical_config.json").resolve()
    held = diagnostic_runs.workspace.root / "var" / "tmp" / "original-config-held.json"
    original_receipt_check = verify_execution_receipt
    substituted = False

    def substitute_after_receipt(**kwargs: Any) -> Any:
        nonlocal substituted
        receipt = original_receipt_check(**kwargs)
        target.rename(held)
        try:
            shutil.copyfile(held, target)
        except Exception:
            held.rename(target)
            raise
        substituted = True
        return receipt

    monkeypatch.setattr(
        verify_module,
        "verify_execution_receipt",
        substitute_after_receipt,
    )

    try:
        result = verify_module.verify_run(
            run_dir,
            workspace_root=diagnostic_runs.workspace.root,
        )
    finally:
        if substituted:
            target.unlink()
            held.rename(target)

    assert substituted
    assert not result.valid
    assert any("changed during complete verification" in error for error in result.errors)

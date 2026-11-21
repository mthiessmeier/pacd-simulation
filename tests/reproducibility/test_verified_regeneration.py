"""Regeneration releases only the summary and digests verified in one pass."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest
from conftest import REPO_ROOT, DiagnosticRuns

from pacd_sim.metrics.summarize import write_episode_summary
from pacd_sim.reproducibility import paths, verify
from pacd_sim.reproducibility.manifest import sha256_file
from pacd_sim.reproducibility.receipts import ReceiptVerification

SCRIPT = REPO_ROOT / "docs" / "application_demo" / "regenerate.py"


@pytest.mark.reproducibility
def test_command_regenerates_without_reopening_verified_evidence(
    diagnostic_runs: DiagnosticRuns,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = diagnostic_runs.same_seed_a.run_dir
    workspace = diagnostic_runs.workspace
    verify_snapshot = verify.verify_run_with_summary
    expected = {p.name: sha256_file(p) for p in (run / "derived").iterdir()}
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        assert not path.is_relative_to(run), "reopened a retained input after verification"
        return original_open(path, *args, **kwargs)

    def forbid_parquet_path(*_args: object, **_kwargs: object) -> None:
        pytest.fail("regeneration called the unbounded Parquet reader")

    def verify_fixture(
        path: Path, *, workspace_root: Path, repo_root: Path
    ) -> tuple[verify.VerificationResult, verify.VerifiedSummary | None]:
        assert (path, workspace_root, repo_root) == (run, workspace.root, REPO_ROOT)
        verified = verify_snapshot(
            path, workspace_root=workspace.root, repo_root=workspace.repo_root
        )
        assert verified[0].valid
        monkeypatch.setattr(Path, "open", guarded_open)
        monkeypatch.setattr(pq, "read_table", forbid_parquet_path)
        return verified

    monkeypatch.setattr(paths, "infer_workspace_root", lambda _repo: workspace.root)
    monkeypatch.setattr(verify, "verify_run_with_summary", verify_fixture)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(run)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    output = json.loads(capsys.readouterr().out)
    destination = Path(output["directory"])
    assert destination.parent == workspace.root / "var" / "tmp"
    assert output["summary"]["seed"] == diagnostic_runs.same_seed_a.seed
    assert output["sha256"] == expected
    assert {p.name: sha256_file(p) for p in destination.iterdir()} == expected


@pytest.mark.negative
def test_regeneration_material_is_withheld_after_late_failure(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace
    run = diagnostic_runs.same_seed_a.run_dir
    monkeypatch.setattr(
        verify,
        "verify_execution_receipt",
        lambda **_: ReceiptVerification(False, ("local receipt unavailable",), None),
    )
    result, material = verify.verify_run_with_summary(
        run, workspace_root=workspace.root, repo_root=workspace.repo_root
    )
    assert result.semantic_content_valid and not result.valid
    assert material is None
    assert "local receipt unavailable" in result.errors


@pytest.mark.negative
def test_corrupt_run_creates_no_regenerated_directory(
    diagnostic_runs: DiagnosticRuns, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = diagnostic_runs.workspace.root
    run = workspace / "var" / "runs" / "empty-regeneration-input"
    run.mkdir()
    before = set((workspace / "var" / "tmp").iterdir())
    monkeypatch.setattr(paths, "infer_workspace_root", lambda _repo: workspace)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(run)])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code == 1
    assert set((workspace / "var" / "tmp").iterdir()) == before


@pytest.mark.negative
def test_digest_mismatch_and_output_collision_preserve_files(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    workspace = diagnostic_runs.workspace
    _, material = verify.verify_run_with_summary(
        diagnostic_runs.same_seed_a.run_dir,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
    )
    assert material is not None
    destination = workspace.root / "var" / "tmp" / "regeneration-output-boundary"
    with pytest.raises(ValueError, match="digests"):
        write_episode_summary(
            material.episode, destination, workspace_root=workspace.root, expected_hashes={}
        )
    assert not destination.exists()
    destination.mkdir()
    existing = destination / "episode_summary.parquet"
    existing.write_bytes(b"pre-existing")
    with pytest.raises(FileExistsError):
        write_episode_summary(material.episode, destination, workspace_root=workspace.root)
    assert existing.read_bytes() == b"pre-existing"
    assert set(destination.iterdir()) == {existing}

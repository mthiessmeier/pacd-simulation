"""Transactional finalization and exact diagnostic output-root regressions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, tzinfo
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.harness import run as run_module
from pacd_sim.harness.run import ConfigurationError, run_diagnostic
from pacd_sim.reproducibility.paths import PathBoundaryError


def _run(workspace: IsolatedWorkspace) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    run_diagnostic(
        scenario,
        policy,
        seeds,
        workspace.output_root,
        seed=424242,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
    )


@pytest.mark.negative
def test_final_checksum_failure_retains_only_failed_overall_status(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_checksum_write(*_args: object, **_kwargs: object) -> Path:
        raise RuntimeError("synthetic finalization failure")

    monkeypatch.setattr(run_module, "git_commit", lambda _repo: "0" * 40)
    monkeypatch.setattr(run_module, "git_is_dirty", lambda _repo: False)
    monkeypatch.setattr(run_module, "write_sha256s", fail_checksum_write)

    with pytest.raises(RuntimeError, match="synthetic finalization failure"):
        _run(isolated_workspace)

    run_directories = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]
    assert len(run_directories) == 1
    run_dir = run_directories[0]
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert isinstance(status, dict)
    assert status["completion_status"] == "FAILED"
    assert status["reportable"] is False
    assert not (run_dir / "SHA256SUMS.txt").exists()

    summary_rows = pq.read_table(run_dir / "derived" / "episode_summary.parquet").to_pylist()
    assert len(summary_rows) == 1
    assert summary_rows[0]["completion_status"] == "EVENT_CHAIN_COMPLETED"
    assert summary_rows[0]["completion_status"] != status["completion_status"]


@pytest.mark.negative
def test_failure_immediately_after_staging_creation_leaves_no_unlabelled_residue(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_first_initialization_write(
        path: Path,
        text: str,
        workspace_root: Path,
    ) -> Path:
        del path, text, workspace_root
        raise RuntimeError("synthetic staging initialization failure")

    monkeypatch.setattr(run_module, "_write_labelled_text", fail_first_initialization_write)

    with pytest.raises(RuntimeError, match="synthetic staging initialization failure"):
        _run(isolated_workspace)

    staging_root = isolated_workspace.root / "var" / "tmp"
    staging_residue = list(staging_root.glob("*.staging")) if staging_root.exists() else []
    retained_runs = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]

    assert staging_residue == []
    assert len(retained_runs) <= 1
    if retained_runs:
        status = json.loads((retained_runs[0] / "status.json").read_text(encoding="utf-8"))
        assert isinstance(status, dict)
        assert status["completion_status"] == "FAILED"


@pytest.mark.negative
def test_preexisting_staging_collision_preserves_sentinel_byte_for_byte(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_instant = datetime(2026, 8, 23, 12, 34, 56, 789012, tzinfo=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> FixedDateTime:
            return cls(2026, 8, 23, 12, 34, 56, 789012, tzinfo=tz)

    seed = 424242
    run_id = f"diagnostic-{fixed_instant.strftime('%Y%m%dT%H%M%S.%fZ')}-seed-{seed}"
    staging_dir = isolated_workspace.root / "var" / "tmp" / f"{run_id}.staging"
    staging_dir.mkdir(parents=True)
    sentinel = staging_dir / "PREEXISTING_SENTINEL.bin"
    sentinel_bytes = b"pre-existing staging data\x00must remain untouched\n"
    sentinel.write_bytes(sentinel_bytes)
    original_listing = tuple(
        sorted(path.relative_to(staging_dir).as_posix() for path in staging_dir.rglob("*"))
    )
    final_dir = isolated_workspace.output_root / run_id
    monkeypatch.setattr(run_module, "datetime", FixedDateTime)

    with pytest.raises(FileExistsError, match="existing staging directory"):
        _run(isolated_workspace)

    assert staging_dir.is_dir()
    assert sentinel.read_bytes() == sentinel_bytes
    assert (
        tuple(sorted(path.relative_to(staging_dir).as_posix() for path in staging_dir.rglob("*")))
        == original_listing
    )
    assert not (staging_dir / "status.json").exists()
    assert not (staging_dir / "manifest.json").exists()
    assert not final_dir.exists()


@pytest.mark.negative
@pytest.mark.parametrize(
    "invalid_location",
    [
        "repo",
        "configs",
        "git_metadata",
        "package",
        "temporary",
        "runs_descendant",
    ],
)
def test_diagnostic_denies_every_output_root_except_exact_var_runs(
    isolated_workspace: IsolatedWorkspace,
    invalid_location: str,
) -> None:
    locations = {
        "repo": isolated_workspace.repo_root,
        "configs": isolated_workspace.config_root / "protocol",
        "git_metadata": isolated_workspace.repo_root / ".git",
        "package": isolated_workspace.root / "package",
        "temporary": isolated_workspace.root / "var" / "tmp",
        "runs_descendant": isolated_workspace.output_root / "nested",
    }
    invalid_output = locations[invalid_location]

    with pytest.raises((ConfigurationError, PathBoundaryError)):
        _run_with_output(isolated_workspace, invalid_output)


def _run_with_output(workspace: IsolatedWorkspace, output_root: Path) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    run_diagnostic(
        scenario,
        policy,
        seeds,
        output_root,
        seed=424242,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
    )

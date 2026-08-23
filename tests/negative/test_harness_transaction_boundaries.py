"""Transactional finalization and exact diagnostic output-root regressions."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, tzinfo
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.harness import run as run_module
from pacd_sim.harness.run import (
    ConfigurationError,
)
from pacd_sim.harness.run import (
    _run_diagnostic_worker as run_diagnostic,
)
from pacd_sim.reproducibility.paths import PathBoundaryError, path_has_symlink_or_reparse


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


@pytest.mark.negative
def test_public_diagnostic_timeout_preemptively_terminates_worker(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    monkeypatch.setattr(
        run_module,
        "default_workspace_root",
        lambda: isolated_workspace.root.resolve(),
    )
    monkeypatch.setattr(run_module, "_MAX_DIAGNOSTIC_SECONDS", 0.0)
    started = time.perf_counter()

    with pytest.raises(run_module.DiagnosticTimeoutError):
        run_module.run_diagnostic(
            scenario,
            policy,
            seeds,
            isolated_workspace.output_root,
            seed=424242,
            workspace_root=isolated_workspace.root,
            repo_root=isolated_workspace.repo_root,
            baseline_path=baseline,
            metric_path=metrics,
        )

    assert time.perf_counter() - started < 10.0
    staging_root = isolated_workspace.root / "var" / "tmp"
    assert not list(staging_root.glob("*.staging")) if staging_root.exists() else True
    retained = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]
    assert len(retained) <= 1
    if retained:
        status = json.loads((retained[0] / "status.json").read_text(encoding="utf-8"))
        assert status["completion_status"] == "FAILED"
        assert status["error_type"] == "DiagnosticTimeoutError"


@pytest.mark.negative
def test_timeout_retains_task_created_raw_evidence(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    invocation_token = "a" * 32
    run_id, staging_dir, final_dir = run_module._new_run_directory(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
        invocation_token=invocation_token,
    )
    assert run_id.endswith(invocation_token)
    raw_dir = staging_dir / "raw"
    raw_dir.mkdir()
    evidence = raw_dir / "e.bin"
    evidence.write_bytes(b"partial timeout evidence\n")

    run_module._retain_timeout_evidence(isolated_workspace.root, invocation_token)

    assert not staging_dir.exists()
    assert final_dir.is_dir()
    assert (final_dir / "raw" / evidence.name).read_bytes() == b"partial timeout evidence\n"
    status = json.loads((final_dir / "status.json").read_text(encoding="utf-8"))
    assert status["completion_status"] == "FAILED"
    assert status["error_type"] == "DiagnosticTimeoutError"


@pytest.mark.negative
def test_parent_failure_marks_atomically_finalized_evidence_failed_without_raw_loss(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    invocation_token = "b" * 32
    _run_id, staging_dir, final_dir = run_module._new_run_directory(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
        invocation_token=invocation_token,
    )
    raw_dir = staging_dir / "raw"
    raw_dir.mkdir()
    evidence = raw_dir / "e.bin"
    evidence.write_bytes(b"finalized before parent channel failure\n")
    staging_dir.replace(final_dir)

    run_module._retain_parent_failure(
        isolated_workspace.root,
        invocation_token,
        RuntimeError("worker exited without a result"),
    )

    assert final_dir.is_dir()
    assert (final_dir / "raw" / evidence.name).read_bytes() == (
        b"finalized before parent channel failure\n"
    )
    status = json.loads((final_dir / "status.json").read_text(encoding="utf-8"))
    assert status["completion_status"] == "FAILED"
    assert status["error_type"] == "RuntimeError"


@pytest.mark.negative
def test_failed_run_retention_never_appends_to_a_log_outside_owned_run(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    invocation_token = "c" * 32
    _run_id, staging_dir, final_dir = run_module._new_run_directory(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
        invocation_token=invocation_token,
    )
    outside_log = isolated_workspace.root / "var" / "outside.log"
    outside_log.write_text("sentinel\n", encoding="utf-8")

    run_module._retain_failed_run(
        staging_dir,
        final_dir,
        isolated_workspace.root,
        424242,
        RuntimeError("test failure"),
        log_path=outside_log,
    )

    assert outside_log.read_text(encoding="utf-8") == "sentinel\n"
    status = json.loads((final_dir / "status.json").read_text(encoding="utf-8"))
    assert status["completion_status"] == "FAILED"


@pytest.mark.negative
def test_failed_run_retention_rejects_indirect_metadata_before_write(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation_token = "d" * 32
    _run_id, staging_dir, final_dir = run_module._new_run_directory(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
        invocation_token=invocation_token,
    )
    status_path = staging_dir / "status.json"

    def identify_indirect_status(path: Path | str) -> bool:
        candidate = Path(path)
        return candidate == status_path or path_has_symlink_or_reparse(candidate)

    monkeypatch.setattr(
        run_module,
        "path_has_symlink_or_reparse",
        identify_indirect_status,
    )

    with pytest.raises(RuntimeError, match="metadata path is indirect"):
        run_module._retain_failed_run(
            staging_dir,
            final_dir,
            isolated_workspace.root,
            424242,
            RuntimeError("test failure"),
        )

    assert not status_path.exists()
    assert staging_dir.is_dir()
    assert not final_dir.exists()


@pytest.mark.negative
def test_governor_approved_probe_cannot_execute_without_defender_proposal(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    source = scenario.read_text(encoding="utf-8")
    source = source.replace(
        "services:\n",
        "  - id: session-synthetic-benign\n"
        "    identity_id: identity-synthetic-admin\n"
        "    service_id: service-synthetic-saas\n"
        "services:\n",
        1,
    )
    source = source.replace(
        "target_id: session-synthetic-001",
        "target_id: session-synthetic-benign",
        1,
    )
    scenario.write_text(source, encoding="utf-8")

    with pytest.raises(RuntimeError, match="was not proposed by the defender"):
        run_diagnostic(
            scenario,
            policy,
            seeds,
            isolated_workspace.output_root,
            seed=424242,
            workspace_root=isolated_workspace.root,
            repo_root=isolated_workspace.repo_root,
            baseline_path=baseline,
            metric_path=metrics,
        )

    retained = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]
    assert len(retained) == 1
    rows = [
        json.loads(line)
        for line in (retained[0] / "raw" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        row["event_type"] == "safety_decision"
        and row["action_id"] == "action-allowed"
        and row["disposition"] == "APPROVE"
        for row in rows
    )
    assert not any(row["event_type"] == "simulated_execution" for row in rows)

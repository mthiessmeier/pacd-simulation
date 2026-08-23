"""Parent-owned invocation and local receipt identity regressions."""

from __future__ import annotations

import json
import multiprocessing
import shutil
from datetime import datetime, tzinfo
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns, IsolatedWorkspace, controlled_config_files

import pacd_sim.harness.run as run_module
from pacd_sim.reproducibility.manifest import sha256_file
from pacd_sim.reproducibility.receipts import (
    verify_execution_receipt,
)
from pacd_sim.reproducibility.reportable import ReportableModeDenied
from pacd_sim.reproducibility.verify import verify_run


def _manifest(run_dir: Path) -> dict[str, object]:
    value = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def _write_canonical(path: Path, value: object) -> None:
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


def _refresh_complete_closure(run_dir: Path, manifest: dict[str, object]) -> None:
    artifact_names = tuple(
        sorted(
            path.relative_to(run_dir).as_posix()
            for path in run_dir.rglob("*")
            if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}
        )
    )
    manifest["artifact_hashes"] = {name: sha256_file(run_dir / name) for name in artifact_names}
    _write_canonical(run_dir / "manifest.json", manifest)
    checksums = {name: sha256_file(run_dir / name) for name in (*artifact_names, "manifest.json")}
    (run_dir / "SHA256SUMS.txt").write_text(
        "# evidence_label=NON_REPORTABLE_DIAGNOSTIC\n"
        + "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )


@pytest.mark.negative
def test_same_content_reruns_have_distinct_authenticated_invocations(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    first = diagnostic_runs.same_seed_a
    second = diagnostic_runs.same_seed_b
    assert first.raw_semantic_hash == second.raw_semantic_hash
    assert first.summary_semantic_hash == second.summary_semantic_hash
    assert first.invocation_id != second.invocation_id
    assert first.receipt_path is not None
    assert second.receipt_path is not None
    assert first.receipt_path != second.receipt_path
    assert verify_execution_receipt(
        workspace_root=diagnostic_runs.workspace.root,
        run_dir=first.run_dir,
        manifest=_manifest(first.run_dir),
    ).identity_assured
    assert verify_execution_receipt(
        workspace_root=diagnostic_runs.workspace.root,
        run_dir=second.run_dir,
        manifest=_manifest(second.run_dir),
    ).identity_assured


@pytest.mark.negative
def test_missing_receipt_removes_identity_assurance_only(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    assert run.receipt_path is not None
    held = run.receipt_path.with_suffix(".held")
    run.receipt_path.replace(held)
    try:
        result = verify_run(
            run.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )
    finally:
        held.replace(run.receipt_path)
    assert not result.valid
    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert any("missing" in error.lower() for error in result.errors)
    assert result.reportable is False


@pytest.mark.negative
def test_duplicate_receipt_creation_is_exclusive_and_preserves_original(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    invocation_id = "d" * 32
    monkeypatch.setattr(
        run_module,
        "uuid4",
        lambda: SimpleNamespace(hex=invocation_id),
    )
    receipt = isolated_workspace.root / "var" / "receipts" / f"{invocation_id}.json"
    receipt.parent.mkdir(parents=True)
    original = b"pre-existing-receipt-sentinel"
    receipt.write_bytes(original)

    with pytest.raises(FileExistsError):
        run_module._run_diagnostic_in_process(
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
    assert receipt.read_bytes() == original


@pytest.mark.negative
def test_excessively_nested_receipt_fails_closed_without_recursion_escape(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    assert run.receipt_path is not None
    held = run.receipt_path.with_suffix(".held")
    run.receipt_path.replace(held)
    try:
        run.receipt_path.write_bytes(b"[" * 2_000 + b"0" + b"]" * 2_000)
        result = verify_run(
            run.run_dir,
            workspace_root=diagnostic_runs.workspace.root,
            repo_root=diagnostic_runs.workspace.repo_root,
        )
    finally:
        run.receipt_path.unlink()
        held.replace(run.receipt_path)
    assert not result.valid
    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert result.reportable is False


@pytest.mark.negative
def test_receipt_copied_between_runs_does_not_bind(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    first = diagnostic_runs.same_seed_a
    second = diagnostic_runs.same_seed_b
    assert first.receipt_path is not None
    assert second.receipt_path is not None
    held = second.receipt_path.with_suffix(".held")
    second.receipt_path.replace(held)
    try:
        shutil.copyfile(first.receipt_path, second.receipt_path)
        result = verify_execution_receipt(
            workspace_root=diagnostic_runs.workspace.root,
            run_dir=second.run_dir,
            manifest=_manifest(second.run_dir),
        )
    finally:
        if second.receipt_path.exists():
            second.receipt_path.unlink()
        held.replace(second.receipt_path)
    assert not result.identity_assured
    assert any("bind" in error.lower() for error in result.errors)


@pytest.mark.negative
def test_replaced_run_directory_loses_execution_identity(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    run = run_module._run_diagnostic_in_process(
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
    held = isolated_workspace.root / "var" / "tmp" / "original-owned-directory"
    run.run_dir.rename(held)
    try:
        shutil.copytree(held, run.run_dir)
        result = verify_run(
            run.run_dir,
            workspace_root=isolated_workspace.root,
            repo_root=isolated_workspace.repo_root,
        )
        assert not result.valid
        assert result.semantic_content_valid
        assert not result.execution_identity_assured
        assert any("directory identity" in error.lower() for error in result.errors)
    finally:
        if run.run_dir.exists():
            shutil.rmtree(run.run_dir)
        held.rename(run.run_dir)


@pytest.mark.negative
def test_renamed_retimestamped_clone_has_no_execution_identity(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    source = diagnostic_runs.same_seed_a.run_dir
    clone_id = "9" * 32
    clone_name = f"diagnostic-20990101T000000.000000Z-seed-424242-{clone_id}"
    clone = diagnostic_runs.workspace.output_root / clone_name
    shutil.copytree(source, clone)
    refreshed_manifest = _manifest(clone)
    refreshed_manifest["run_id"] = clone_name
    refreshed_manifest["started_at"] = "2099-01-01T00:00:00+00:00"
    refreshed_manifest["ended_at"] = "2099-01-01T00:00:01+00:00"

    raw_path = clone / "raw" / "events.parquet"
    raw_table = pq.read_table(raw_path)
    raw_rows = raw_table.to_pylist()
    for row in raw_rows:
        row["run_id"] = clone_name
    pq.write_table(
        pa.Table.from_pylist(raw_rows, schema=raw_table.schema),
        raw_path,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    (clone / "raw" / "events.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for row in raw_rows
        ),
        encoding="utf-8",
    )

    _refresh_complete_closure(clone, refreshed_manifest)

    result = verify_run(
        clone,
        workspace_root=diagnostic_runs.workspace.root,
        repo_root=diagnostic_runs.workspace.repo_root,
    )

    assert not result.valid
    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert any("missing" in error.lower() for error in result.errors)


@pytest.mark.negative
def test_preexisting_exact_final_path_sentinel_is_never_claimed(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation_id = "8" * 32

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> FixedDateTime:
            return cls(2026, 8, 23, 13, 14, 15, 161718, tzinfo=tz)

    timestamp = "20260823T131415.161718Z"
    run_id = f"diagnostic-{timestamp}-seed-424242-{invocation_id}"
    final_dir = isolated_workspace.output_root / run_id
    final_dir.mkdir()
    sentinel = final_dir / "SENTINEL.bin"
    sentinel_bytes = b"pre-existing exact final path\x00unchanged\n"
    sentinel.write_bytes(sentinel_bytes)
    monkeypatch.setattr(run_module, "datetime", FixedDateTime)

    with pytest.raises(FileExistsError, match="existing final run path"):
        run_module._create_invocation_ownership(
            isolated_workspace.output_root,
            isolated_workspace.root,
            424242,
            invocation_id=invocation_id,
        )

    assert sentinel.read_bytes() == sentinel_bytes
    assert not (isolated_workspace.root / "var" / "tmp" / f"{run_id}.staging").exists()
    assert not (isolated_workspace.root / "var" / "invocations" / invocation_id).exists()


@pytest.mark.negative
def test_prefix_and_sibling_lookalikes_are_untouched_during_retention(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    invocation_id = "7" * 32
    ownership = run_module._create_invocation_ownership(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
        invocation_id=invocation_id,
    )
    lookalikes = (
        ownership.staging_dir.with_name(f"prefix-{ownership.staging_dir.name}"),
        ownership.staging_dir.with_name(f"{ownership.staging_dir.name}-sibling"),
        ownership.final_run_dir.with_name(f"{ownership.final_run_dir.name}-sentinel"),
    )
    sentinels: list[tuple[Path, bytes]] = []
    for index, directory in enumerate(lookalikes):
        directory.mkdir()
        sentinel = directory / "SENTINEL.bin"
        value = f"lookalike-{index}\n".encode()
        sentinel.write_bytes(value)
        sentinels.append((sentinel, value))

    run_module._retain_parent_failure(
        isolated_workspace.root,
        ownership,
        RuntimeError("synthetic parent failure"),
    )

    assert ownership.final_run_dir.is_dir()
    for sentinel, expected in sentinels:
        assert sentinel.read_bytes() == expected


class _FakeSender:
    def close(self) -> None:
        pass


class _FakeReceiver:
    def __init__(self, envelope: object, *, eof: bool) -> None:
        self.envelope = envelope
        self.eof = eof

    def poll(self) -> bool:
        return True

    def recv(self) -> object:
        if self.eof:
            raise EOFError
        return self.envelope

    def close(self) -> None:
        pass


class _FakeProcess:
    exitcode = 0

    def start(self) -> None:
        pass

    def join(self, _timeout: float | None = None) -> None:
        pass

    def is_alive(self) -> bool:
        return False

    def close(self) -> None:
        pass


class _FakeContext:
    def __init__(self, envelope: object, *, eof: bool) -> None:
        self.receiver = _FakeReceiver(envelope, eof=eof)

    def Pipe(self, *, duplex: bool) -> tuple[_FakeReceiver, _FakeSender]:  # noqa: N802
        assert duplex is False
        return self.receiver, _FakeSender()

    def Process(self, **_kwargs: Any) -> _FakeProcess:  # noqa: N802
        return _FakeProcess()


class _StartFailureProcess(_FakeProcess):
    def start(self) -> None:
        raise OSError("synthetic spawn failure")


class _StartFailureContext(_FakeContext):
    def Process(self, **_kwargs: Any) -> _FakeProcess:  # noqa: N802
        return _StartFailureProcess()


@pytest.mark.negative
@pytest.mark.parametrize(
    ("envelope", "eof", "error_pattern"),
    [
        (None, True, "result channel failed"),
        ({"not_ok": True}, False, "invalid result envelope"),
    ],
)
def test_parent_eof_and_malformed_envelope_retain_only_exact_invocation(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    envelope: object,
    eof: bool,
    error_pattern: str,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    fake_context = _FakeContext(envelope, eof=eof)
    monkeypatch.setattr(multiprocessing, "get_context", lambda _kind: fake_context)

    with pytest.raises(RuntimeError, match=error_pattern):
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

    retained = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]
    assert len(retained) == 1
    status = json.loads((retained[0] / "status.json").read_text(encoding="utf-8"))
    assert status["completion_status"] == "FAILED"
    assert not list((isolated_workspace.root / "var" / "tmp").glob("*.staging"))


@pytest.mark.negative
def test_process_start_failure_retains_parent_created_invocation(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    fake_context = _StartFailureContext(None, eof=False)
    monkeypatch.setattr(multiprocessing, "get_context", lambda _kind: fake_context)

    with pytest.raises(OSError, match="synthetic spawn failure"):
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

    retained = [path for path in isolated_workspace.output_root.iterdir() if path.is_dir()]
    assert len(retained) == 1
    status = json.loads((retained[0] / "status.json").read_text(encoding="utf-8"))
    assert status["completion_status"] == "FAILED"
    assert status["error_type"] == "OSError"


@pytest.mark.negative
def test_worker_cannot_self_provision_invocation_ownership(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )

    with pytest.raises(TypeError, match="_ownership"):
        run_module._run_diagnostic_worker(  # type: ignore[call-arg]
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

    assert not list(isolated_workspace.output_root.iterdir())


@pytest.mark.negative
def test_worker_authority_excludes_parent_receipt_capability(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ownership = run_module._create_invocation_ownership(
        isolated_workspace.output_root,
        isolated_workspace.root,
        424242,
    )

    worker_ownership = run_module._worker_ownership(ownership)

    assert ownership.receipt_capability is not None
    assert worker_ownership.capability == ownership.capability
    assert worker_ownership.receipt_capability is None
    marker = json.loads(ownership.marker_path.read_text(encoding="utf-8"))
    assert ownership.receipt_capability not in ownership.marker_path.read_text(encoding="utf-8")
    assert marker["receipt_capability_sha256"] != marker["capability_sha256"]


@pytest.mark.negative
def test_reportable_denial_precedes_all_invocation_and_receipt_creation(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )

    with pytest.raises(ReportableModeDenied, match="absent"):
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
            reportable=True,
        )

    assert not list(isolated_workspace.output_root.iterdir())
    assert not (isolated_workspace.root / "var" / "invocations").exists()
    assert not (isolated_workspace.root / "var" / "receipts").exists()

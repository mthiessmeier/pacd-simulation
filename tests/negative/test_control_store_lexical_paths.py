"""Real NTFS-junction regressions for exact lexical local control stores."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

import pacd_sim.cli as cli_module
import pacd_sim.harness.run as run_module
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_exact_control_path,
    path_has_symlink_or_reparse,
)
from pacd_sim.reproducibility.receipts import IDENTITY_ASSURANCE_SCOPE
from pacd_sim.reproducibility.verify import verify_run

pytestmark = [
    pytest.mark.negative,
    pytest.mark.skipif(os.name != "nt", reason="NTFS junction regression requires Windows"),
]


def _manifest(run_dir: Path) -> dict[str, object]:
    value = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def _target_snapshot(target: Path) -> dict[str, tuple[str, bytes]]:
    snapshot: dict[str, tuple[str, bytes]] = {}
    for path in sorted(target.rglob("*")):
        relative_name = path.relative_to(target).as_posix()
        if path.is_file():
            snapshot[relative_name] = ("file", path.read_bytes())
        elif path.is_dir():
            snapshot[relative_name] = ("directory", b"")
        else:
            snapshot[relative_name] = ("other", b"")
    return snapshot


@contextmanager
def _real_junction(
    link: Path,
    target: Path,
    *,
    replace_existing: bool,
    copy_original_to_target: bool = False,
) -> Iterator[dict[str, tuple[str, bytes]]]:
    """Create one workspace-local junction and always restore an ordinary path."""

    held = link.with_name(f"{link.name}.n01-held") if replace_existing else None
    held_moved = False
    target_created = False
    before: dict[str, tuple[str, bytes]] = {}
    try:
        if held is not None:
            assert link.is_dir()
            assert not path_has_symlink_or_reparse(link)
            assert not held.exists()
            link.rename(held)
            held_moved = True
        else:
            assert not link.exists()
        target.mkdir(parents=True, exist_ok=False)
        target_created = True
        if copy_original_to_target:
            assert held is not None
            shutil.copytree(held, target, dirs_exist_ok=True)
        sentinel = target / "SENTINEL.bin"
        sentinel.write_bytes(b"N-01 junction target sentinel\x00must remain unchanged\n")
        before = _target_snapshot(target)
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        assert link.is_junction()
        assert path_has_symlink_or_reparse(link)
        yield before
    finally:
        try:
            if link.is_junction():
                link.rmdir()
            elif held_moved and link.exists():
                link.rmdir()
            if held_moved:
                assert held is not None
                assert held.is_dir()
                assert not path_has_symlink_or_reparse(held)
                held.rename(link)
            elif target_created and not link.exists():
                link.mkdir(parents=True, exist_ok=False)
            if held_moved or target_created:
                assert link.is_dir()
                assert not path_has_symlink_or_reparse(link)
        finally:
            if target_created and target.exists():
                shutil.rmtree(target)


def _run(workspace: IsolatedWorkspace) -> run_module.RunResult:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    return run_module._run_diagnostic_in_process(
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


def _assert_cli_indirect_diagnostic_denial(
    workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    emitted: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_emit_json",
        lambda value, **_kwargs: emitted.append(value),
    )
    monkeypatch.setattr(
        cli_module,
        "infer_workspace_root",
        lambda _repository: workspace.root.resolve(),
    )
    monkeypatch.setattr(
        cli_module,
        "run_diagnostic",
        run_module._run_diagnostic_in_process,
    )

    exit_code = cli_module.main(
        [
            "diagnostic",
            "--repo-root",
            str(workspace.repo_root),
            "--workspace-root",
            str(workspace.root),
            "--scenario",
            str(scenario),
            "--policy",
            str(policy),
            "--seeds",
            str(seeds),
            "--baseline",
            str(baseline),
            "--metrics",
            str(metrics),
            "--output-root",
            str(workspace.output_root),
            "--seed",
            "424242",
        ]
    )

    assert exit_code == 2
    assert len(emitted) == 1
    payload = emitted[0]
    assert isinstance(payload, dict)
    assert payload["status"] == "INVALID"
    assert payload["valid"] is False
    assert payload["semantic_content_valid"] is False
    assert payload["execution_identity_assured"] is False
    assert payload["identity_assurance_scope"] == IDENTITY_ASSURANCE_SCOPE
    assert payload["historical_control_file_inode_continuity_assured"] is False
    assert payload["reportable"] is False
    assert "control-store path is indirect" in str(payload["reason"])


def _assert_indirect_identity_failure(workspace: IsolatedWorkspace, run_dir: Path) -> None:
    result = verify_run(
        run_dir,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
    )
    assert result.semantic_content_valid
    assert not result.execution_identity_assured
    assert not result.valid
    assert result.identity_assurance_scope == IDENTITY_ASSURANCE_SCOPE
    assert result.historical_control_file_inode_continuity_assured is False
    assert result.reportable is False
    assert any("control-store path is indirect" in error for error in result.errors)


def test_preexisting_receipts_root_junction_never_writes_target(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = isolated_workspace.root / "var" / "receipts"
    target = isolated_workspace.root / "var" / "n01-targets" / "pre-receipts"
    with _real_junction(link, target, replace_existing=False) as before:
        _assert_cli_indirect_diagnostic_denial(isolated_workspace, monkeypatch)
        with pytest.raises(PathBoundaryError, match="receipts control-store path is indirect"):
            _run(isolated_workspace)
        assert _target_snapshot(target) == before


def test_preexisting_invocations_root_junction_never_writes_target(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = isolated_workspace.root / "var" / "invocations"
    target = isolated_workspace.root / "var" / "n01-targets" / "pre-invocations"
    with _real_junction(link, target, replace_existing=False) as before:
        _assert_cli_indirect_diagnostic_denial(isolated_workspace, monkeypatch)
        with pytest.raises(PathBoundaryError, match="invocations control-store path is indirect"):
            _run(isolated_workspace)
        assert _target_snapshot(target) == before
        assert list(isolated_workspace.output_root.iterdir()) == []


def test_post_run_receipts_root_junction_removes_identity_only(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    run = _run(isolated_workspace)
    link = isolated_workspace.root / "var" / "receipts"
    target = isolated_workspace.root / "var" / "n01-targets" / "post-receipts"
    with _real_junction(
        link,
        target,
        replace_existing=True,
        copy_original_to_target=True,
    ) as before:
        _assert_indirect_identity_failure(isolated_workspace, run.run_dir)
        assert _target_snapshot(target) == before
    assert verify_run(
        run.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    ).valid


def test_post_run_invocations_root_junction_removes_identity_only(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    run = _run(isolated_workspace)
    link = isolated_workspace.root / "var" / "invocations"
    target = isolated_workspace.root / "var" / "n01-targets" / "post-invocations"
    with _real_junction(
        link,
        target,
        replace_existing=True,
        copy_original_to_target=True,
    ) as before:
        _assert_indirect_identity_failure(isolated_workspace, run.run_dir)
        assert _target_snapshot(target) == before
    assert verify_run(
        run.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    ).valid


def test_nested_invocation_junction_removes_identity_and_restores_directory(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    run = _run(isolated_workspace)
    link = isolated_workspace.root / "var" / "invocations" / run.invocation_id
    target = isolated_workspace.root / "var" / "n01-targets" / "nested-invocation"
    with _real_junction(
        link,
        target,
        replace_existing=True,
        copy_original_to_target=True,
    ) as before:
        _assert_indirect_identity_failure(isolated_workspace, run.run_dir)
        assert _target_snapshot(target) == before
    assert verify_run(
        run.run_dir,
        workspace_root=isolated_workspace.root,
        repo_root=isolated_workspace.repo_root,
    ).valid


def test_preexisting_nested_invocation_junction_never_writes_target(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    invocation_id = "a" * 32
    ownership_root = isolated_workspace.root / "var" / "invocations"
    ownership_root.mkdir(parents=True)
    link = ownership_root / invocation_id
    target = isolated_workspace.root / "var" / "n01-targets" / "pre-nested-invocation"
    with _real_junction(link, target, replace_existing=False) as before:
        with pytest.raises(PathBoundaryError, match="invocations control-store path is indirect"):
            run_module._create_invocation_ownership(
                isolated_workspace.output_root,
                isolated_workspace.root,
                424242,
                invocation_id=invocation_id,
            )
        assert _target_snapshot(target) == before
        staging_root = isolated_workspace.root / "var" / "tmp"
        assert not list(staging_root.glob("*.staging")) if staging_root.exists() else True


def test_prefix_lookalike_junctions_are_not_control_store_components(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    receipt_link = isolated_workspace.root / "var" / "receipts-prefix-lookalike"
    receipt_target = isolated_workspace.root / "var" / "n01-targets" / "prefix-receipts"
    invocation_link = isolated_workspace.root / "var" / "invocations-prefix-lookalike"
    invocation_target = isolated_workspace.root / "var" / "n01-targets" / "prefix-invocations"
    with _real_junction(receipt_link, receipt_target, replace_existing=False) as receipts_before:
        with _real_junction(
            invocation_link,
            invocation_target,
            replace_existing=False,
        ) as invocations_before:
            run = _run(isolated_workspace)
            result = verify_run(
                run.run_dir,
                workspace_root=isolated_workspace.root,
                repo_root=isolated_workspace.repo_root,
            )
            assert result.valid
            assert result.execution_identity_assured
            assert _target_snapshot(receipt_target) == receipts_before
            assert _target_snapshot(invocation_target) == invocations_before


@pytest.mark.parametrize(
    "candidate",
    [
        "ads",
        "device",
        "traversal",
    ],
)
def test_control_store_rejects_alternate_lexical_spelling(
    isolated_workspace: IsolatedWorkspace,
    candidate: str,
) -> None:
    expected = isolated_workspace.root / "var" / "receipts"
    spellings = {
        "ads": Path(f"{expected}:stream"),
        "device": Path(f"\\\\?\\{expected}"),
        "traversal": expected / ".." / "receipts",
    }
    with pytest.raises(PathBoundaryError):
        assert_exact_control_path(
            spellings[candidate],
            isolated_workspace.root,
            "receipts",
        )

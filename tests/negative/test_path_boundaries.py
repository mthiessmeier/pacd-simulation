"""Fail-closed path-jail checks for all diagnostic writes."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.reproducibility.paths import PathBoundaryError, assert_write_path


@pytest.mark.negative
def test_write_path_inside_explicit_workspace_is_allowed(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    candidate = isolated_workspace.output_root / "diagnostic-run" / "manifest.json"

    assert_write_path(candidate, workspace_root=isolated_workspace.root)


@pytest.mark.negative
@pytest.mark.parametrize(
    "candidate_factory",
    [
        lambda root: root.parent / "outside" / "artifact.json",
        lambda root: Path(f"{root}-lookalike") / "artifact.json",
        lambda root: root / "var" / "runs" / ".." / ".." / ".." / "escape.json",
    ],
)
def test_write_path_rejects_outside_lookalike_and_traversal(
    isolated_workspace: IsolatedWorkspace,
    candidate_factory: object,
) -> None:
    candidate = candidate_factory(isolated_workspace.root)  # type: ignore[operator]

    with pytest.raises(PathBoundaryError):
        assert_write_path(candidate, workspace_root=isolated_workspace.root)


@pytest.mark.negative
@pytest.mark.parametrize(
    "relative_protected",
    [
        Path("Desktop"),
        Path("Documents"),
        Path("Downloads"),
        Path("OneDrive") / "Desktop",
        Path("OneDrive") / "Documents",
        Path("OneDrive") / "Downloads",
    ],
)
def test_workspace_beneath_protected_user_folders_is_rejected(
    relative_protected: Path,
) -> None:
    protected_workspace = Path.home() / relative_protected / "PACD-Simulation"
    candidate = protected_workspace / "var" / "runs" / "artifact.json"

    with pytest.raises(PathBoundaryError):
        assert_write_path(candidate, workspace_root=protected_workspace)

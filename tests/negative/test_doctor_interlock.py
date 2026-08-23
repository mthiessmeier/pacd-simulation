"""Doctor must surface malformed reportable authorization as a failed gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.reproducibility import doctor as doctor_module
from pacd_sim.reproducibility.doctor import run_doctor


@pytest.mark.negative
def test_doctor_fails_reportable_interlock_for_malformed_approval(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approval = isolated_workspace.config_root / "protocol" / "frozen" / "APPROVAL.json"
    approval.write_text("{malformed approval", encoding="utf-8")
    monkeypatch.setattr(doctor_module, "git_commit", lambda _repo: "0" * 40)
    monkeypatch.setattr(doctor_module, "git_is_dirty", lambda _repo: False)
    monkeypatch.setattr(
        doctor_module,
        "_git_branch",
        lambda _repo: "codex/environment-bootstrap-v1",
    )

    report = run_doctor(
        isolated_workspace.repo_root,
        workspace_root=isolated_workspace.root,
    )
    interlock = next(check for check in report.checks if check.name == "reportable_mode_interlock")

    assert not interlock.passed
    assert not report.passed


@pytest.mark.negative
@pytest.mark.parametrize("placement", ["outside_workspace", "package_subtree"])
def test_doctor_rejects_repository_outside_explicit_workspace_repo_subtree(
    isolated_workspace: IsolatedWorkspace,
    placement: str,
) -> None:
    if placement == "outside_workspace":
        invalid_repo = isolated_workspace.root.parent / "outside-doctor-repository"
    else:
        invalid_repo = isolated_workspace.root / "package" / "not-a-work-repository"
    invalid_repo.mkdir(parents=True)

    report = run_doctor(invalid_repo, workspace_root=isolated_workspace.root)
    boundary = next(
        check for check in report.checks if check.name == "repository_workspace_boundary"
    )

    assert not boundary.passed
    assert not report.passed


@pytest.mark.negative
def test_doctor_rejects_reparse_workspace_repo_boundary_before_resolution(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_repo_boundary = isolated_workspace.root / "repo"

    def identify_mock_reparse(path: Path) -> bool:
        return Path(path) == workspace_repo_boundary

    monkeypatch.setattr(
        doctor_module,
        "path_has_symlink_or_reparse",
        identify_mock_reparse,
    )

    report = run_doctor(
        isolated_workspace.repo_root,
        workspace_root=isolated_workspace.root,
    )
    boundary = next(
        check for check in report.checks if check.name == "repository_workspace_boundary"
    )

    assert not boundary.passed
    assert "symlink or reparse point" in boundary.detail.lower()
    assert not report.passed

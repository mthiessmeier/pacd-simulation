"""The public diagnostic CLI may not redefine the designated workspace root."""

from __future__ import annotations

from pathlib import Path

import pytest

from pacd_sim import cli
from pacd_sim.harness import run as run_module
from pacd_sim.harness.run import run_diagnostic
from pacd_sim.reproducibility.paths import PathBoundaryError, path_has_symlink_or_reparse


@pytest.mark.negative
def test_cli_diagnostic_rejects_a_broader_caller_supplied_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    authorized = tmp_path / "PACD-Workspaces" / "PACD-Simulation"
    repository = authorized / "repo" / "pacd-simulation"
    repository.mkdir(parents=True)
    broader = authorized.parent
    monkeypatch.setattr(cli, "infer_workspace_root", lambda _repository: authorized.resolve())

    exit_code = cli.main(
        [
            "diagnostic",
            "--repo-root",
            str(repository),
            "--workspace-root",
            str(broader),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "cannot redefine" in captured.err
    assert not (broader / "var" / "runs").exists()


def test_cli_diagnostic_accepts_only_the_inferred_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorized = (tmp_path / "PACD-Workspaces" / "PACD-Simulation").resolve()
    repository = authorized / "repo" / "pacd-simulation"
    monkeypatch.setattr(cli, "infer_workspace_root", lambda _repository: authorized)

    assert cli._resolve_diagnostic_workspace(repository, None) == authorized
    assert cli._resolve_diagnostic_workspace(repository, authorized) == authorized

    with pytest.raises(PathBoundaryError, match="cannot redefine"):
        cli._resolve_diagnostic_workspace(repository, authorized.parent)


@pytest.mark.negative
@pytest.mark.parametrize("workspace_offset", ["broader", "nested-repository"])
def test_run_diagnostic_rejects_caller_broadened_workspace_authority(
    tmp_path: Path,
    workspace_offset: str,
) -> None:
    authorized = tmp_path / "PACD-Workspaces" / "PACD-Simulation"
    if workspace_offset == "broader":
        workspace = tmp_path
        repository = authorized / "repo" / "pacd-simulation"
    else:
        workspace = authorized
        repository = workspace / "repo" / "organization" / "pacd-simulation"
    repository.mkdir(parents=True)

    with pytest.raises(PathBoundaryError, match="author-designated"):
        run_diagnostic(
            repository / "missing-scenario.yaml",
            repository / "missing-policy.yaml",
            repository / "missing-seeds.json",
            workspace / "var" / "runs",
            workspace_root=workspace,
            repo_root=repository,
        )

    assert not (workspace / "var" / "runs").exists()


@pytest.mark.negative
@pytest.mark.parametrize("indirect_component", ["repository", "workspace", "scenario"])
def test_public_diagnostic_rejects_indirect_authority_paths_before_worker_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    indirect_component: str,
) -> None:
    authorized = tmp_path / "PACD-Workspaces" / "PACD-Simulation"
    repository = authorized / "repo" / "pacd-simulation"
    repository.mkdir(parents=True)
    scenario = repository / "configs" / "scenarios" / "diagnostic.yaml"

    def identify_indirect(path: Path | str) -> bool:
        candidate = Path(path)
        selected = {
            "repository": repository,
            "workspace": authorized,
            "scenario": scenario,
        }[indirect_component]
        return candidate == selected or path_has_symlink_or_reparse(candidate)

    monkeypatch.setattr(run_module, "path_has_symlink_or_reparse", identify_indirect)

    with pytest.raises(PathBoundaryError, match="symlink or reparse point"):
        run_diagnostic(
            scenario,
            repository / "missing-policy.yaml",
            repository / "missing-seeds.json",
            authorized / "var" / "runs",
            workspace_root=authorized,
            repo_root=repository,
        )

    assert not (authorized / "var" / "runs").exists()

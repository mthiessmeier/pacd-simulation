"""Shared command entry point for hermetic diagnostic scenario tests."""

from collections.abc import Callable
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.harness import run as harness


@pytest.fixture
def command(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., dict[str, Any]]:
    ws = isolated_workspace
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda value, **kwargs: output.append(value))

    def run(*args: str, code: int = 0) -> dict[str, Any]:
        assert cli.main(list(args)) == code, output[-1:]
        return output[-1]

    return run

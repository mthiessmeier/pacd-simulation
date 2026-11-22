"""Shared fixtures for bounded PACD bootstrap acceptance tests."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from pacd_sim.harness.run import RunResult
from pacd_sim.harness.run import _run_diagnostic_in_process as run_diagnostic

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPO_ROOT / "configs"


@dataclass(frozen=True)
class IsolatedWorkspace:
    """Task-created writable paths used by tests instead of user folders."""

    root: Path
    repo_root: Path
    config_root: Path
    output_root: Path


@dataclass(frozen=True)
class DiagnosticRuns:
    """Three completed hermetic runs used across scenario and replay checks."""

    workspace: IsolatedWorkspace
    same_seed_a: RunResult
    same_seed_b: RunResult
    different_seed: RunResult
    input_hashes_before: dict[Path, str]


def file_sha256(path: Path) -> str:
    """Return a small fixture file's SHA-256 digest."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def controlled_config_files(config_root: Path) -> tuple[Path, ...]:
    """Return the exact diagnostic inputs consumed by the bootstrap harness."""

    return (
        config_root / "scenarios" / "diagnostic_identity_smoke.yaml",
        config_root / "policies" / "diagnostic_safety.yaml",
        config_root / "seeds" / "diagnostic_seeds.json",
        config_root / "defenders" / "diagnostic_baseline.yaml",
        config_root / "metrics" / "diagnostic_metrics.yaml",
    )


def run_committed_scenario(workspace: IsolatedWorkspace) -> RunResult:
    """Bind a synthetic scenario edit to its temporary Git repo and run it in process."""
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "synthetic scenario fixture",
            "--",
            str(scenario.relative_to(workspace.repo_root)),
        ],
        cwd=workspace.repo_root,
        check=True,
    )
    return run_diagnostic(
        scenario,
        policy,
        seeds,
        workspace.output_root,
        workspace_root=workspace.root,
        repo_root=workspace.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
        seed=424242,
    )


def _create_isolated_workspace(root: Path) -> IsolatedWorkspace:
    repo_root = root / "repo" / "pacd-simulation"
    config_root = repo_root / "configs"
    repo_root.mkdir(parents=True)
    shutil.copytree(CONFIG_ROOT, config_root)
    shutil.copy2(REPO_ROOT / "pyproject.toml", repo_root / "pyproject.toml")
    lockfile = REPO_ROOT / "uv.lock"
    if lockfile.is_file():
        shutil.copy2(lockfile, repo_root / "uv.lock")
    subprocess.run(
        ["git", "-C", str(repo_root), "init", "--quiet"],
        check=True,
        capture_output=True,
        shell=False,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "add", "configs", "pyproject.toml", "uv.lock"],
        check=True,
        capture_output=True,
        shell=False,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "test fixture",
        ],
        check=True,
        capture_output=True,
        shell=False,
    )
    output_root = root / "var" / "runs"
    output_root.mkdir(parents=True)
    return IsolatedWorkspace(
        root=root,
        repo_root=repo_root,
        config_root=config_root,
        output_root=output_root,
    )


@pytest.fixture
def isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IsolatedWorkspace:
    """Create an explicit PACD-shaped workspace beneath pytest's temporary root."""

    root = tmp_path / "PACD-Workspaces" / "PACD-Simulation"
    monkeypatch.setenv("PACD_WORKSPACE_ROOT", str(root))
    monkeypatch.setattr("pacd_sim.harness.run.default_workspace_root", lambda: root.resolve())
    workspace = _create_isolated_workspace(root)
    # In-process diagnostics use the test fixture's committed checkout identity.
    monkeypatch.setattr(
        "pacd_sim.harness.run.__file__", str(workspace.repo_root / "src/pacd_sim/harness/run.py")
    )
    return workspace


@pytest.fixture(scope="session")
def diagnostic_runs(tmp_path_factory: pytest.TempPathFactory) -> DiagnosticRuns:
    """Run two equal seeds and one distinct seed in a wholly temporary workspace."""

    root = (
        tmp_path_factory.mktemp("pacd-diagnostic-workspace") / "PACD-Workspaces" / "PACD-Simulation"
    )
    workspace = _create_isolated_workspace(root)
    scenario, policy, seeds, baseline, metrics = controlled_config_files(workspace.config_root)
    input_hashes = {
        path: file_sha256(path) for path in (scenario, policy, seeds, baseline, metrics)
    }

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setenv("PACD_WORKSPACE_ROOT", str(root))
        patcher.setattr(
            "pacd_sim.harness.run.__file__",
            str(workspace.repo_root / "src/pacd_sim/harness/run.py"),
        )
        patcher.setattr(
            "pacd_sim.harness.run.default_workspace_root",
            lambda: root.resolve(),
        )

        def run(selected_seed: int) -> RunResult:
            return run_diagnostic(
                scenario,
                policy,
                seeds,
                workspace.output_root,
                seed=selected_seed,
                workspace_root=workspace.root,
                repo_root=workspace.repo_root,
                baseline_path=baseline,
                metric_path=metrics,
            )

        same_seed_a = run(424242)
        same_seed_b = run(424242)
        different_seed = run(424243)

    return DiagnosticRuns(
        workspace=workspace,
        same_seed_a=same_seed_a,
        same_seed_b=same_seed_b,
        different_seed=different_seed,
        input_hashes_before=input_hashes,
    )

"""Bind launched diagnostics to the source checkout in the parent, worker and receipt."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.receipts import receipt_path_for
from pacd_sim.reproducibility.reportable import git_commit
from pacd_sim.reproducibility.verify import verify_run


def advance_commit(repository: Path) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "independent synthetic revision",
        ],
        check=True,
    )


@pytest.mark.negative
def test_unplanned_public_entry_cannot_borrow_another_checkout(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ws = isolated_workspace
    sibling = ws.repo_root.with_name("different-source")
    subprocess.run(
        ["git", "clone", "-q", "--no-hardlinks", str(ws.repo_root), str(sibling)], check=True
    )
    advance_commit(sibling)
    assert git_commit(sibling) != git_commit(ws.repo_root)
    config = sibling / "configs"
    _, _, seeds, _, metrics = controlled_config_files(config)
    with pytest.raises(harness.ConfigurationError, match="checkout running this harness"):
        harness.run_diagnostic(
            config / "scenarios/diagnostic_sensing_nominal.yaml",
            config / "policies/diagnostic_sensing.yaml",
            seeds,
            ws.output_root,
            workspace_root=ws.root,
            repo_root=sibling,
            baseline_path=config / "defenders/sensing_fixed.yaml",
            metric_path=metrics,
        )
    assert not any(ws.output_root.iterdir())
    assert not (ws.root / "var/invocations").exists()
    assert not (ws.root / "var/receipts").exists()


@pytest.mark.negative
@pytest.mark.parametrize("stage", ["worker", "receipt", "receipt_manifest"])
def test_revision_drift_or_unbound_manifest_preserves_failed_attempt(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    ws = isolated_workspace
    _, _, seeds, _, metrics = controlled_config_files(ws.config_root)
    if stage == "worker":
        run_worker = harness._run_diagnostic_worker

        def changed_checkout(*args: Any, **kwargs: Any) -> harness.RunResult:
            advance_commit(ws.repo_root)
            return run_worker(*args, **kwargs)

        monkeypatch.setattr(harness, "_run_diagnostic_worker", changed_checkout)
    else:
        read_manifest = harness._read_parent_manifest
        changed = False

        def before_receipt(path: Path) -> dict[str, object]:
            nonlocal changed
            manifest = read_manifest(path)
            if not changed:
                changed = True
                if stage == "receipt":
                    advance_commit(ws.repo_root)
                else:
                    manifest.pop("producer_commit")
            return manifest

        monkeypatch.setattr(harness, "_read_parent_manifest", before_receipt)
    invocation = "9" * 32
    with pytest.raises(RuntimeError, match="producer (checkout|revision)"):
        harness._run_diagnostic_in_process(
            ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml",
            ws.config_root / "policies/diagnostic_sensing.yaml",
            seeds,
            ws.output_root,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            baseline_path=ws.config_root / "defenders/sensing_fixed.yaml",
            metric_path=metrics,
            invocation_id=invocation,
        )
    (run_dir,) = ws.output_root.iterdir()
    assert json.loads((run_dir / "status.json").read_bytes())["completion_status"] == "FAILED"
    assert not receipt_path_for(ws.root, invocation).exists()


@pytest.mark.negative
def test_dirty_unplanned_legacy_is_retained_and_sensing_is_refused(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ws = isolated_workspace
    (ws.repo_root / "uncommitted.txt").write_text("synthetic fixture", encoding="utf8")
    scenario, policy, seeds, baseline, metrics = controlled_config_files(ws.config_root)
    with pytest.raises(harness.ConfigurationError, match="clean producer checkout"):
        harness.run_diagnostic(
            ws.config_root / "scenarios/diagnostic_sensing_nominal.yaml",
            ws.config_root / "policies/diagnostic_sensing.yaml",
            seeds,
            ws.output_root,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            baseline_path=ws.config_root / "defenders/sensing_fixed.yaml",
            metric_path=metrics,
        )
    assert not (ws.root / "var/invocations").exists()
    result = harness._run_diagnostic_in_process(
        scenario,
        policy,
        seeds,
        ws.output_root,
        workspace_root=ws.root,
        repo_root=ws.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
    )
    manifest = json.loads(result.manifest_path.read_bytes())
    assert manifest["dirty_state"] is True and "producer_commit" not in manifest
    assert not verify_run(result.run_dir, workspace_root=ws.root, repo_root=ws.repo_root).valid

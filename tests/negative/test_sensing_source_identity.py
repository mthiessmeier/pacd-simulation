"""Reserved sensing names must identify the governed operator at launch and replay."""

import json
import subprocess

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.harness import run as harness
from pacd_sim.reproducibility.doctor import run_doctor
from pacd_sim.reproducibility.receipts import verify_execution_receipt
from pacd_sim.reproducibility.verify import verify_run_with_summary


@pytest.mark.negative
@pytest.mark.parametrize("name", ["diagnostic_sensing_nominal", "diagnostic_sensing_costly"])
def test_legacy_isolation_cannot_claim_a_sensing_identity(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    ws = isolated_workspace
    scenario = ws.config_root / "scenarios/diagnostic_guarded_benign.yaml"
    source = scenario.read_text(encoding="utf-8")
    assert "sensing_operator:" not in source
    scenario.write_text(
        source.replace("name: diagnostic_guarded_benign", f"name: {name}"), encoding="utf-8"
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PACD Test",
            "-c",
            "user.email=pacd-test@example.invalid",
            "commit",
            "-qm",
            "record mislabelled synthetic source fixture",
            "--",
            str(scenario.relative_to(ws.repo_root)),
        ],
        cwd=ws.repo_root,
        check=True,
    )
    _, policy, seeds, _, metrics = controlled_config_files(ws.config_root)
    baseline = ws.config_root / "defenders/static_review.yaml"

    def launch() -> harness.RunResult:
        return harness._run_diagnostic_in_process(
            scenario,
            policy,
            seeds,
            ws.output_root,
            workspace_root=ws.root,
            repo_root=ws.repo_root,
            seed=424242,
            baseline_path=baseline,
            metric_path=metrics,
        )

    report = run_doctor(ws.repo_root, workspace_root=ws.root)
    assert not next(check for check in report.checks if check.name == "configuration_schema").passed
    with pytest.raises(
        harness.ConfigurationError, match="governed filenames, roles and identities"
    ):
        launch()
    assert not list(ws.output_root.iterdir())
    assert all(not (ws.root / "var" / path).exists() for path in ("receipts", "invocations"))

    # Reproduce the old producer for this already committed fixture. A genuine receipt
    # cannot authorize release when the checked-out file declares another scenario's name.
    with monkeypatch.context() as patcher:
        patcher.setattr(harness, "_validate_sensing_sources", lambda *_: None)
        old = launch()
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=old.run_dir,
        manifest=json.loads(old.manifest_path.read_bytes()),
    ).identity_assured
    verification, material = verify_run_with_summary(
        old.run_dir, ws.root, repo_root=ws.repo_root, include_comparison_inputs=True
    )
    assert material is None and not verification.semantic_content_valid
    assert any(
        "governed filenames, roles and identities" in reason for reason in verification.errors
    )

"""Duplicate candidate identifiers must fail before any run output is created."""

from __future__ import annotations

import pytest
from conftest import IsolatedWorkspace, controlled_config_files

from pacd_sim.harness.run import ConfigurationError, run_diagnostic


@pytest.mark.negative
def test_duplicate_action_ids_fail_configuration_before_output(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    scenario, policy, seeds, baseline, metrics = controlled_config_files(
        isolated_workspace.config_root
    )
    source = scenario.read_text(encoding="utf-8")
    duplicate = source.replace("id: action-escalated", "id: action-allowed", 1)
    assert duplicate != source
    scenario.write_text(duplicate, encoding="utf-8")

    with pytest.raises(ConfigurationError, match="[Dd]uplicate .*action"):
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

    assert list(isolated_workspace.output_root.iterdir()) == []

"""Strict configuration-schema and safe-YAML acceptance checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import IsolatedWorkspace
from pydantic import ValidationError

from pacd_sim.harness.run import load_yaml_config, run_diagnostic
from pacd_sim.schema import StrictFrozenModel


class _ExampleConfig(StrictFrozenModel):
    name: str
    count: int


def test_strict_model_rejects_extra_fields_and_type_coercion() -> None:
    with pytest.raises(ValidationError):
        _ExampleConfig.model_validate({"name": "synthetic", "count": 1, "extra": True})

    with pytest.raises(ValidationError):
        _ExampleConfig.model_validate({"name": "synthetic", "count": "1"})


def test_strict_model_is_frozen() -> None:
    config = _ExampleConfig(name="synthetic", count=1)

    with pytest.raises(ValidationError):
        config.count = 2


def test_yaml_loader_rejects_unsafe_python_tags(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("value: !!python/name:builtins.str\n", encoding="utf-8")

    with pytest.raises((ValueError, TypeError)):
        load_yaml_config(unsafe)


def test_yaml_loader_rejects_excessive_aliases(tmp_path: Path) -> None:
    aliases = tmp_path / "aliases.yaml"
    aliases.write_text(
        "anchor: &safe synthetic\n"
        + "\n".join(f"alias_{index}: *safe" for index in range(21))
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="alias"):
        load_yaml_config(aliases, max_aliases=20)


def test_diagnostic_rejects_unknown_scenario_fields(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    source = isolated_workspace.config_root / "scenarios" / "diagnostic_identity_smoke.yaml"
    scenario = isolated_workspace.config_root / "scenarios" / "scenario-with-extra.yaml"
    scenario.write_text(
        source.read_text(encoding="utf-8") + "\nunexpected_bootstrap_field: rejected\n",
        encoding="utf-8",
    )

    with pytest.raises((ValidationError, ValueError)):
        run_diagnostic(
            scenario,
            isolated_workspace.config_root / "policies" / "diagnostic_safety.yaml",
            isolated_workspace.config_root / "seeds" / "diagnostic_seeds.json",
            isolated_workspace.output_root,
            workspace_root=isolated_workspace.root,
            repo_root=isolated_workspace.repo_root,
        )

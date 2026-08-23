"""Common defender contract and architectural import-boundary checks."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from pathlib import Path

from conftest import REPO_ROOT

from pacd_sim.defenders.base import Defender
from pacd_sim.defenders.baselines.null import NullDefender
from pacd_sim.defenders.pacd.diagnostic import DiagnosticPACDDefender


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _parameter_contract(
    method: Callable[..., object],
) -> tuple[tuple[str, inspect._ParameterKind], ...]:
    signature = inspect.signature(method)
    return tuple((parameter.name, parameter.kind) for parameter in signature.parameters.values())


def test_baseline_and_pacd_defenders_share_runtime_typed_interface() -> None:
    expected_parameters = _parameter_contract(Defender.decide)

    for defender_type in (NullDefender, DiagnosticPACDDefender):
        defender = defender_type()
        assert isinstance(defender, Defender)
        assert _parameter_contract(defender_type.decide) == expected_parameters
        assert (
            inspect.signature(defender_type.decide).return_annotation is not inspect.Signature.empty
        )


def test_defenders_cannot_import_evaluation_or_control_modules() -> None:
    defender_root = REPO_ROOT / "src" / "pacd_sim" / "defenders"
    forbidden_prefixes = (
        "pacd_sim.harness",
        "pacd_sim.metrics",
        "pacd_sim.governance",
        "pacd_sim.reproducibility.paths",
    )

    violations: list[str] = []
    for path in sorted(defender_root.rglob("*.py")):
        for imported in _imported_modules(path):
            if imported.startswith(forbidden_prefixes):
                violations.append(f"{path.relative_to(REPO_ROOT)} imports {imported}")

    assert violations == []


def test_governor_does_not_depend_on_any_defender_implementation() -> None:
    governor_path = REPO_ROOT / "src" / "pacd_sim" / "governance" / "governor.py"

    assert all(
        not imported.startswith("pacd_sim.defenders")
        for imported in _imported_modules(governor_path)
    )


def test_safety_governor_is_not_defined_inside_pacd_planner() -> None:
    pacd_root = REPO_ROOT / "src" / "pacd_sim" / "defenders" / "pacd"
    class_names: set[str] = set()
    for path in pacd_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        class_names.update(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

    assert "SafetyGovernor" not in class_names
    assert "SafetyPolicy" not in class_names

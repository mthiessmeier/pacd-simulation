"""Static fail-closed checks for simulation-only execution code."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from conftest import REPO_ROOT

from pacd_sim.execution.broker import SimulatedExecutionBroker

_SIMULATION_MODULES = (
    "actions",
    "agents",
    "defenders",
    "engine",
    "environment",
    "evidence",
    "execution",
    "governance",
    "hypotheses",
    "orchestration",
    "oversight",
    "polymorphism",
    "state",
    "telemetry",
)
_FORBIDDEN_IMPORT_ROOTS = {
    "aiohttp",
    "ftplib",
    "httpx",
    "paramiko",
    "pickle",
    "requests",
    "socket",
    "subprocess",
    "telnetlib",
    "urllib",
}
_FORBIDDEN_BUILTIN_CALLS = {"__import__", "compile", "eval", "exec"}


def _trees() -> list[tuple[Path, ast.AST]]:
    source_root = REPO_ROOT / "src" / "pacd_sim"
    trees: list[tuple[Path, ast.AST]] = []
    for module in _SIMULATION_MODULES:
        for path in sorted((source_root / module).rglob("*.py")):
            trees.append((path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))))
    return trees


@pytest.mark.negative
def test_simulation_modules_import_no_network_socket_or_subprocess_clients() -> None:
    violations: list[str] = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            imported_names: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                imported_names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names = (node.module,)
            for name in imported_names:
                if name.split(".", maxsplit=1)[0] in _FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"{path.relative_to(REPO_ROOT)} imports {name}")

    assert violations == []


@pytest.mark.negative
def test_simulation_modules_do_not_dynamically_execute_configuration() -> None:
    violations: list[str] = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_BUILTIN_CALLS:
                violations.append(f"{path.relative_to(REPO_ROOT)} calls {node.func.id}")
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "system"
            ):
                violations.append(f"{path.relative_to(REPO_ROOT)} calls os.system")

    assert violations == []


@pytest.mark.negative
def test_execution_package_exposes_only_simulated_broker_classes() -> None:
    execution_root = REPO_ROOT / "src" / "pacd_sim" / "execution"
    broker_or_adapter_names: set[str] = set()
    for path in execution_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        broker_or_adapter_names.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and (node.name.endswith("Broker") or node.name.endswith("Adapter"))
        )

    assert broker_or_adapter_names == {"SimulatedExecutionBroker"}
    assert SimulatedExecutionBroker.__module__ == "pacd_sim.execution.broker"

"""Metrics remain downstream of retained raw records and outside run state."""

from __future__ import annotations

import ast
import inspect

from conftest import REPO_ROOT

from pacd_sim.metrics.summarize import SUMMARY_SCHEMA, summary_from_raw


def test_raw_summary_api_accepts_no_live_state_or_configuration() -> None:
    signature = inspect.signature(summary_from_raw)

    assert tuple(signature.parameters) == ("raw_events_path",)
    assert SUMMARY_SCHEMA.metadata[b"derived_only_from"] == b"raw/events.parquet"


def test_metrics_module_imports_no_live_simulation_control_layer() -> None:
    metrics_root = REPO_ROOT / "src" / "pacd_sim" / "metrics"
    forbidden = (
        "pacd_sim.defenders",
        "pacd_sim.environment",
        "pacd_sim.execution",
        "pacd_sim.governance",
        "pacd_sim.harness",
    )
    violations: list[str] = []
    for path in metrics_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = (node.module,)
            for module in modules:
                if module.startswith(forbidden):
                    violations.append(f"{path.relative_to(REPO_ROOT)} imports {module}")

    assert violations == []

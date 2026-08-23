"""Property checks against common-prefix and traversal jail escapes."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.reproducibility.paths import PathBoundaryError, assert_write_path

_SAFE_COMPONENT = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=20,
)


@pytest.mark.property
@given(_SAFE_COMPONENT)
@settings(max_examples=40, deadline=None)
def test_common_prefix_siblings_never_enter_workspace(suffix: str) -> None:
    temporary_root = Path(tempfile.gettempdir()) / "pacd-path-jail-property"
    workspace = temporary_root / "PACD-Simulation"
    outside = temporary_root / f"PACD-Simulation-{suffix}" / "artifact.json"

    with pytest.raises(PathBoundaryError):
        assert_write_path(outside, workspace_root=workspace)


@pytest.mark.property
@given(st.integers(min_value=1, max_value=8), _SAFE_COMPONENT)
@settings(max_examples=40, deadline=None)
def test_parent_traversal_that_resolves_outside_is_always_rejected(
    parent_count: int,
    filename: str,
) -> None:
    temporary_root = Path(tempfile.gettempdir()) / "pacd-path-jail-property"
    workspace = temporary_root / "PACD-Simulation"
    nested = workspace.joinpath("var", "runs", *(".." for _ in range(parent_count + 3)))
    candidate = nested / f"{filename}.json"

    with pytest.raises(PathBoundaryError):
        assert_write_path(candidate, workspace_root=workspace)

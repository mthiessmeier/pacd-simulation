"""Bootstrap must never create a false frozen-protocol approval marker."""

from __future__ import annotations

from conftest import REPO_ROOT


def test_frozen_protocol_directory_contains_readme_only() -> None:
    frozen = REPO_ROOT / "configs" / "protocol" / "frozen"
    entries = {path.name for path in frozen.iterdir()}

    assert entries == {"README.md"}
    assert "author" in (frozen / "README.md").read_text(encoding="utf-8").lower()
    assert not (frozen / "APPROVAL.json").exists()

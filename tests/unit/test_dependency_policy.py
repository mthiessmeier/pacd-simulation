"""Offline lock validation and stable-only dependency policy remain explicit."""

from __future__ import annotations

import tomllib

from conftest import REPO_ROOT
from packaging.version import Version


def test_uv_policy_disallows_prereleases_and_lock_contains_only_stable_versions() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    uv_policy = project.get("tool", {}).get("uv", {})

    assert uv_policy.get("prerelease") == "disallow"

    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_versions = [
        (str(package["name"]), Version(str(package["version"])))
        for package in lock["package"]
        if "version" in package
    ]
    assert locked_versions
    assert [
        (name, version)
        for name, version in locked_versions
        if version.is_prerelease or version.is_devrelease
    ] == []


def test_readme_contains_standalone_offline_lock_check() -> None:
    lines = {
        line.strip() for line in (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    }

    assert "uv lock --check --offline --no-cache --prerelease disallow" in lines

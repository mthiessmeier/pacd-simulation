"""Fail-closed authorization gate for any future reportable execution."""

from __future__ import annotations

import json
import os
import re
import shutil

# Subprocess use is limited to fixed, read-only, shell-free local Git queries.
import subprocess  # nosec B404
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportableModeDenied(PermissionError):
    """Raised before output creation when reportable authorization is invalid."""


_REQUIRED_APPROVAL_KEYS = frozenset(
    {
        "author",
        "approval_timestamp",
        "git_commit",
        "protocol_version",
        "config_hash",
        "seed_registry_hash",
        "baseline_definition_hash",
        "metric_definition_hash",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _run_git(repo_root: Path, arguments: tuple[str, ...]) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise ReportableModeDenied("Git state could not be established")
    command = [git_executable, "-C", str(repo_root), *arguments]
    try:
        # Callers are private fixed argument tuples; shell expansion is disabled.
        completed = subprocess.run(  # nosec B603
            command,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ReportableModeDenied("Git state could not be established") from error
    if completed.returncode != 0:
        raise ReportableModeDenied("Git state could not be established")
    return completed.stdout.strip()


def _git_commit(repo_root: Path) -> str:
    """Return the exact current commit using one fixed Git invocation."""
    commit = _run_git(repo_root, ("rev-parse", "--verify", "HEAD"))
    if not _COMMIT_RE.fullmatch(commit):
        raise ReportableModeDenied("Git returned a noncanonical commit identifier")
    return commit


def _git_is_dirty(repo_root: Path) -> bool:
    """Return whether tracked or untracked repository state is not clean."""
    status = _run_git(
        repo_root,
        ("status", "--porcelain=v1", "--untracked-files=normal"),
    )
    return bool(status)


def git_commit(repo_root: Path | str) -> str:
    """Public read-only commit helper used by the manifest and doctor."""
    return _git_commit(Path(repo_root).resolve(strict=True))


def git_is_dirty(repo_root: Path | str) -> bool:
    """Public read-only dirty-state helper used by the manifest and doctor."""
    return _git_is_dirty(Path(repo_root).resolve(strict=True))


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReportableModeDenied(f"Approval contains duplicate key: {key}")
        result[key] = value
    return result


def _load_approval(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ReportableModeDenied("Author approval record is absent or not a regular file")
    if path.stat().st_size > 64 * 1024:
        raise ReportableModeDenied("Author approval record exceeds the 64 KiB limit")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReportableModeDenied(
            "Author approval record is unreadable or invalid JSON"
        ) from error
    if not isinstance(value, dict):
        raise ReportableModeDenied("Author approval record must be a JSON object")
    return {str(key): item for key, item in value.items()}


def _validate_timestamp(value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReportableModeDenied("approval_timestamp must be a nonempty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReportableModeDenied("approval_timestamp is not valid ISO-8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReportableModeDenied("approval_timestamp must include a timezone offset")


def _validate_expected_digest(name: str, value: str) -> None:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"Expected {name} is not a lowercase SHA-256 digest")


def validate_reportable_approval(
    repo_root: Path | str,
    *,
    config_hash: str,
    seed_registry_hash: str,
    baseline_definition_hash: str,
    metric_definition_hash: str,
    protocol_version: str,
    approval_path: Path | str | None = None,
) -> dict[str, object]:
    """Validate every approval field, exact clean commit, and current hashes.

    This function performs no writes and creates no approval record. Any ambiguity
    raises :class:`ReportableModeDenied`.
    """
    repository = Path(repo_root).resolve(strict=True)
    if not repository.is_dir():
        raise ReportableModeDenied("Repository root is not a directory")
    expected_approval = repository / "configs" / "protocol" / "frozen" / "APPROVAL.json"
    approval = (
        Path(os.path.abspath(Path(approval_path)))
        if approval_path is not None
        else Path(os.path.abspath(expected_approval))
    )
    if approval != Path(os.path.abspath(expected_approval)):
        raise ReportableModeDenied("Approval path is not the controlled frozen-protocol record")

    for name, digest in {
        "config_hash": config_hash,
        "seed_registry_hash": seed_registry_hash,
        "baseline_definition_hash": baseline_definition_hash,
        "metric_definition_hash": metric_definition_hash,
    }.items():
        _validate_expected_digest(name, digest)
    if not protocol_version:
        raise ValueError("Expected protocol_version may not be empty")

    record = _load_approval(approval)
    keys = frozenset(record)
    missing = sorted(_REQUIRED_APPROVAL_KEYS - keys)
    unexpected = sorted(keys - _REQUIRED_APPROVAL_KEYS)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected={','.join(unexpected)}")
        raise ReportableModeDenied("Approval schema mismatch: " + "; ".join(details))

    author = record["author"]
    if not isinstance(author, str) or not author.strip():
        raise ReportableModeDenied("Approval author must be a nonempty string")
    _validate_timestamp(record["approval_timestamp"])

    approved_commit = record["git_commit"]
    if not isinstance(approved_commit, str) or not _COMMIT_RE.fullmatch(approved_commit):
        raise ReportableModeDenied("Approval git_commit must be an exact 40-character hash")
    current_commit = _git_commit(repository)
    if approved_commit != current_commit:
        raise ReportableModeDenied("Approval git_commit does not match the current commit")
    if _git_is_dirty(repository):
        raise ReportableModeDenied("Repository is not clean; reportable mode is denied")

    expected_values = {
        "protocol_version": protocol_version,
        "config_hash": config_hash,
        "seed_registry_hash": seed_registry_hash,
        "baseline_definition_hash": baseline_definition_hash,
        "metric_definition_hash": metric_definition_hash,
    }
    for key, expected in expected_values.items():
        if record[key] != expected:
            raise ReportableModeDenied(f"Approval {key} does not match the current definition")
    return dict(record)

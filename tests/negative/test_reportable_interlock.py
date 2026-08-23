"""Fail-closed reportable-mode authorization tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pacd_sim.reproducibility import reportable
from pacd_sim.reproducibility.reportable import (
    ReportableModeDenied,
    validate_reportable_approval,
)

_COMMIT = "a" * 40
_CONFIG_HASH = "1" * 64
_SEED_HASH = "2" * 64
_BASELINE_HASH = "3" * 64
_METRIC_HASH = "4" * 64
_PROTOCOL_VERSION = "AUTHOR_APPROVED_TEST_PROTOCOL"


def _temporary_repository(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repository"
    approval = repo / "configs" / "protocol" / "frozen" / "APPROVAL.json"
    approval.parent.mkdir(parents=True)
    return repo, approval


def _record(**overrides: Any) -> dict[str, object]:
    record: dict[str, object] = {
        "author": "Synthetic Test Author",
        "approval_timestamp": "2026-08-23T00:00:00+00:00",
        "git_commit": _COMMIT,
        "protocol_version": _PROTOCOL_VERSION,
        "config_hash": _CONFIG_HASH,
        "seed_registry_hash": _SEED_HASH,
        "baseline_definition_hash": _BASELINE_HASH,
        "metric_definition_hash": _METRIC_HASH,
    }
    record.update(overrides)
    return record


def _validate(repo: Path) -> dict[str, object]:
    return validate_reportable_approval(
        repo,
        config_hash=_CONFIG_HASH,
        seed_registry_hash=_SEED_HASH,
        baseline_definition_hash=_BASELINE_HASH,
        metric_definition_hash=_METRIC_HASH,
        protocol_version=_PROTOCOL_VERSION,
    )


def _mock_clean_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reportable, "_git_commit", lambda _repo: _COMMIT)
    monkeypatch.setattr(reportable, "_git_is_dirty", lambda _repo: False)


@pytest.mark.negative
def test_reportable_mode_denied_when_approval_is_missing(tmp_path: Path) -> None:
    repo, _approval = _temporary_repository(tmp_path)

    with pytest.raises(ReportableModeDenied, match="absent"):
        _validate(repo)


@pytest.mark.negative
def test_reportable_mode_denied_for_malformed_approval(tmp_path: Path) -> None:
    repo, approval = _temporary_repository(tmp_path)
    approval.write_text("{not valid JSON", encoding="utf-8")

    with pytest.raises(ReportableModeDenied, match="invalid JSON"):
        _validate(repo)


@pytest.mark.negative
def test_reportable_mode_denied_for_hash_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, approval = _temporary_repository(tmp_path)
    approval.write_text(json.dumps(_record(config_hash="f" * 64)), encoding="utf-8")
    _mock_clean_commit(monkeypatch)

    with pytest.raises(ReportableModeDenied, match="config_hash"):
        _validate(repo)


@pytest.mark.negative
def test_reportable_mode_denied_for_extra_approval_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, approval = _temporary_repository(tmp_path)
    approval.write_text(json.dumps(_record(unexpected="rejected")), encoding="utf-8")
    _mock_clean_commit(monkeypatch)

    with pytest.raises(ReportableModeDenied, match="unexpected"):
        _validate(repo)


@pytest.mark.negative
def test_reportable_mode_denied_when_repository_is_dirty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, approval = _temporary_repository(tmp_path)
    approval.write_text(json.dumps(_record()), encoding="utf-8")
    monkeypatch.setattr(reportable, "_git_commit", lambda _repo: _COMMIT)
    monkeypatch.setattr(reportable, "_git_is_dirty", lambda _repo: True)

    with pytest.raises(ReportableModeDenied, match="not clean"):
        _validate(repo)


@pytest.mark.negative
@pytest.mark.parametrize("component_kind", ["symlink", "junction", "reparse"])
def test_reportable_mode_denied_when_approval_path_contains_indirection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component_kind: str,
) -> None:
    repo, approval = _temporary_repository(tmp_path)
    approval.write_text(json.dumps(_record()), encoding="utf-8")
    _mock_clean_commit(monkeypatch)

    def identify_indirection(path: Path) -> bool:
        return Path(path) == approval and component_kind in {"symlink", "junction", "reparse"}

    monkeypatch.setattr(
        reportable,
        "path_has_symlink_or_reparse",
        identify_indirection,
    )

    with pytest.raises(ReportableModeDenied, match="symlink, junction, or reparse"):
        _validate(repo)


@pytest.mark.negative
def test_reportable_mode_denied_for_actual_symlinked_approval_parent_when_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repository"
    frozen_parent = repo / "configs" / "protocol" / "frozen"
    frozen_parent.parent.mkdir(parents=True)
    outside = tmp_path / "outside-frozen"
    outside.mkdir()
    approval = outside / "APPROVAL.json"
    approval.write_text(json.dumps(_record()), encoding="utf-8")
    try:
        frozen_parent.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable on this host: {error}")
    _mock_clean_commit(monkeypatch)

    with pytest.raises(ReportableModeDenied, match="symlink, junction, or reparse"):
        _validate(repo)

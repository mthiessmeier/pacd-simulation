"""Cooperative local anchors for diagnostic execution-instance identity.

Receipts live outside evidence packages so a copied or renamed package cannot
manufacture a second execution identity by refreshing its internal checksums.
They are deliberately local bootstrap anchors: they are neither author-signed
nor externally timestamped and therefore never make evidence reportable.  The
assurance binds content, lexical path, run, and configuration at verification
time under cooperative harness use. It does not establish historical control-
file inode continuity, author signing, trustworthy external time, WORM storage,
malicious-same-user resistance, cryptographic attestation, or reportability. A
byte-identical, singly linked replacement at the same validated lexical path is
therefore not, by itself, an assurance failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import sha256_file
from pacd_sim.reproducibility.paths import (
    assert_exact_control_path,
    assert_write_path,
    is_symlink_or_reparse,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
)

IDENTITY_ASSURANCE_SCOPE = "LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING"
HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED = False
_RECEIPT_VERSION = "1.0"
_RECEIPT_KIND = "LOCAL_CONTROLLED_BOOTSTRAP_ANCHOR"
_ANCHOR_SCOPE = "local controlled bootstrap anchor; not author-signed or externally timestamped"
_MAX_RECEIPT_BYTES = 64 * 1024
_MAX_CLOSURE_MANIFEST_BYTES = 4 * 1024 * 1024
_MAX_CLOSURE_CHECKSUM_BYTES = 64 * 1024
_MAX_OWNERSHIP_MARKER_BYTES = 64 * 1024
_INVOCATION_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OWNERSHIP_KEYS = frozenset(
    {
        "capability_sha256",
        "created_at",
        "evidence_label",
        "final_run_path",
        "invocation_id",
        "ownership_version",
        "receipt_capability_sha256",
        "run_id",
        "schema_version",
        "seed",
        "staging_device",
        "staging_inode",
        "staging_path",
    }
)
_RECEIPT_KEYS = frozenset(
    {
        "anchor_scope",
        "canonical_config_hash",
        "code_commit",
        "completed_at",
        "evidence_label",
        "evidence_package_digest",
        "final_run_path",
        "invocation_id",
        "lockfile_hash",
        "manifest_ended_at",
        "owned_directory_device",
        "owned_directory_inode",
        "ownership_marker_sha256",
        "raw_semantic_hash",
        "receipt_kind",
        "receipt_version",
        "reportable",
        "run_id",
        "schema_version",
        "seed",
        "seed_registry_hash",
        "started_at",
        "summary_semantic_hash",
    }
)


@dataclass(frozen=True)
class ReceiptVerification:
    """Current cooperative binding, without historical inode continuity."""

    identity_assured: bool
    errors: tuple[str, ...]
    receipt_path: Path | None
    identity_assurance_scope: str = IDENTITY_ASSURANCE_SCOPE
    historical_control_file_inode_continuity_assured: bool = (
        HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED
    )
    reportable: bool = False


@dataclass(frozen=True)
class _ReceiptCreationAuthority:
    """Stable marker and directory identity observed by the parent."""

    marker_sha256: str
    directory_device: int
    directory_inode: int


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate receipt key: {key}")
        value[key] = item
    return value


def _validate_invocation_id(invocation_id: str) -> None:
    if _INVOCATION_ID.fullmatch(invocation_id) is None:
        raise ValueError("Execution receipt invocation ID is invalid")


def _receipt_control_path(
    workspace: Path,
    invocation_id: str | None = None,
) -> Path:
    """Return an exact lexical receipt root or receipt path."""

    root = assert_exact_control_path(
        workspace / "var" / "receipts",
        workspace,
        "receipts",
    )
    if invocation_id is None:
        return root
    name = f"{invocation_id}.json"
    return assert_exact_control_path(root / name, workspace, "receipts", name)


def _ownership_control_path(
    workspace: Path,
    invocation_id: str | None = None,
    *,
    marker: bool = False,
) -> Path:
    """Return an exact lexical invocation root, directory, or marker path."""

    root = assert_exact_control_path(
        workspace / "var" / "invocations",
        workspace,
        "invocations",
    )
    if invocation_id is None:
        if marker:
            raise ValueError("An ownership marker requires an invocation ID")
        return root
    invocation_dir = assert_exact_control_path(
        root / invocation_id,
        workspace,
        "invocations",
        invocation_id,
    )
    if not marker:
        return invocation_dir
    return assert_exact_control_path(
        invocation_dir / "ownership.json",
        workspace,
        "invocations",
        invocation_id,
        "ownership.json",
    )


def receipt_path_for(workspace_root: Path | str, invocation_id: str) -> Path:
    """Return the one controlled receipt path for an invocation ID."""

    _validate_invocation_id(invocation_id)
    workspace = resolve_workspace_root(workspace_root)
    return _receipt_control_path(workspace, invocation_id)


def read_stable_bytes(path: Path, *, max_bytes: int) -> bytes:
    """Read one small control record through one stable regular-file handle."""

    if path_has_symlink_or_reparse(path):
        raise ValueError("Controlled record path is indirect")
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > max_bytes:
        raise ValueError("Controlled record is not bounded and singly linked")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_nlink,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_nlink,
        ) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("Opened control-record identity differs from its path")
        payload = handle.read(max_bytes + 1)
        opened_after = os.fstat(handle.fileno())
    after = path.stat(follow_symlinks=False)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    if (
        len(payload) > max_bytes
        or before_identity
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        or before_identity
        != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        )
        or before_identity
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
    ):
        raise ValueError("Controlled record changed during its stable read")
    if path_has_symlink_or_reparse(path):
        raise ValueError("Controlled record path became indirect")
    return payload


def valid_ownership_shape(marker: dict[str, object]) -> bool:
    """Unplanned markers retain the v1 contract; planned markers add exactly one digest."""
    if marker.get("ownership_version") == "1.0":
        return marker.keys() == _OWNERSHIP_KEYS
    digest = marker.get("plan_sha256")
    return (
        marker.get("ownership_version") == "1.1"
        and marker.keys() == _OWNERSHIP_KEYS | {"plan_sha256"}
        and isinstance(digest, str)
        and _SHA256.fullmatch(digest) is not None
    )


def read_ownership_marker(workspace: Path, invocation_id: str) -> tuple[dict[str, object], str]:
    """Read the exact canonical marker and its content digest for one invocation."""
    _validate_invocation_id(invocation_id)
    path = _ownership_control_path(workspace, invocation_id, marker=True)
    encoded = read_stable_bytes(path, max_bytes=_MAX_OWNERSHIP_MARKER_BYTES)
    if _ownership_control_path(workspace, invocation_id, marker=True) != path:
        raise ValueError("Invocation ownership marker lexical path changed")
    marker = json.loads(encoded, object_pairs_hook=_unique_object)
    if not isinstance(marker, dict) or not valid_ownership_shape(marker):
        raise ValueError("Invocation ownership marker keys are not exact")
    if canonical_json_bytes(marker) != encoded:
        raise ValueError("Invocation ownership marker is not canonical JSON")
    return marker, hashlib.sha256(encoded).hexdigest()


def _stable_singly_linked_sha256(path: Path, *, max_bytes: int) -> str:
    """Hash one bounded closure file through a stable, singly linked handle."""

    if path_has_symlink_or_reparse(path):
        raise ValueError("Evidence package closure contains an indirect path")
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > max_bytes:
        raise ValueError("Evidence package closure file is not bounded and singly linked")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_nlink,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_nlink,
        ) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("Opened closure-file identity differs from its path")
        while chunk := handle.read(min(1024 * 1024, max_bytes + 1 - total)):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("Evidence package closure file exceeds its bounded limit")
            digest.update(chunk)
        opened_after = os.fstat(handle.fileno())
    after = path.stat(follow_symlinks=False)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    if (
        before_identity
        != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        or before_identity
        != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        )
        or before_identity
        != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        )
    ):
        raise ValueError("Evidence package closure changed during stable hashing")
    return digest.hexdigest()


def evidence_package_digest(run_dir: Path | str) -> str:
    """Digest the final manifest/checksum closure without reopening data files."""

    root = Path(run_dir).resolve(strict=True)
    manifest_path = root / "manifest.json"
    checksums_path = root / "SHA256SUMS.txt"
    return canonical_sha256(
        {
            "domain": "pacd-simulation/evidence-package/v1",
            "manifest_sha256": _stable_singly_linked_sha256(
                manifest_path,
                max_bytes=_MAX_CLOSURE_MANIFEST_BYTES,
            ),
            "sha256s_sha256": _stable_singly_linked_sha256(
                checksums_path,
                max_bytes=_MAX_CLOSURE_CHECKSUM_BYTES,
            ),
        }
    )


def _validate_receipt_creation_authority(
    *,
    workspace: Path,
    invocation_id: str,
    receipt_capability: str,
    final_run: Path,
    manifest: Mapping[str, object],
) -> _ReceiptCreationAuthority:
    """Require the parent-created marker and its undisclosed capability."""

    if _SHA256.fullmatch(receipt_capability) is None:
        raise ValueError("Receipt creation capability is invalid")
    marker_path = _ownership_control_path(workspace, invocation_id, marker=True)
    try:
        marker_bytes = read_stable_bytes(
            marker_path,
            max_bytes=_MAX_OWNERSHIP_MARKER_BYTES,
        )
        if _ownership_control_path(workspace, invocation_id, marker=True) != marker_path:
            raise ValueError("Invocation ownership marker lexical path changed")
        marker = json.loads(marker_bytes, object_pairs_hook=_unique_object)
    except RecursionError as error:
        raise ValueError("Invocation ownership marker is excessively nested") from error
    if not isinstance(marker, dict) or not valid_ownership_shape(marker):
        raise ValueError("Invocation ownership marker keys are not exact")
    if canonical_json_bytes(marker) != marker_bytes:
        raise ValueError("Invocation ownership marker is not canonical JSON")
    run_id = manifest.get("run_id")
    expected_staging = assert_write_path(
        workspace / "var" / "tmp" / f"{run_id}.staging",
        workspace,
    )
    expected_values: dict[str, object] = {
        "created_at": manifest.get("started_at"),
        "evidence_label": EVIDENCE_LABEL,
        "final_run_path": str(final_run),
        "invocation_id": invocation_id,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "seed": manifest.get("seed"),
        "staging_path": str(expected_staging),
    }
    for key, expected in expected_values.items():
        if marker.get(key) != expected:
            raise ValueError(f"Invocation ownership marker does not bind {key}")
    expected_capability_digest = hashlib.sha256(bytes.fromhex(receipt_capability)).hexdigest()
    marker_capability_digest = marker.get("receipt_capability_sha256")
    if not isinstance(marker_capability_digest, str) or not secrets.compare_digest(
        marker_capability_digest,
        expected_capability_digest,
    ):
        raise ValueError("Receipt creation capability does not match parent ownership")
    staging_device = marker.get("staging_device")
    staging_inode = marker.get("staging_inode")
    if (
        isinstance(staging_device, bool)
        or not isinstance(staging_device, int)
        or isinstance(staging_inode, bool)
        or not isinstance(staging_inode, int)
    ):
        raise ValueError("Invocation ownership directory identity is invalid")
    final_stat = final_run.stat(follow_symlinks=False)
    if not stat.S_ISDIR(final_stat.st_mode) or (
        final_stat.st_dev,
        final_stat.st_ino,
    ) != (staging_device, staging_inode):
        raise ValueError("Final evidence directory differs from invocation ownership")
    return _ReceiptCreationAuthority(
        marker_sha256=hashlib.sha256(marker_bytes).hexdigest(),
        directory_device=staging_device,
        directory_inode=staging_inode,
    )


def create_execution_receipt(
    *,
    workspace_root: Path | str,
    invocation_id: str,
    receipt_capability: str,
    run_dir: Path | str,
    manifest: Mapping[str, object],
    completed_at: str,
) -> Path:
    """Exclusively create a non-reportable local receipt for a completed run."""

    _validate_invocation_id(invocation_id)
    workspace = resolve_workspace_root(workspace_root)
    receipt_root = _receipt_control_path(workspace)
    receipt_path = receipt_path_for(workspace, invocation_id)
    _ownership_control_path(workspace, invocation_id, marker=True)
    lexical_run = Path(os.path.abspath(Path(run_dir)))
    if path_has_symlink_or_reparse(lexical_run):
        raise ValueError("Final evidence path is indirect")
    final_run = lexical_run.resolve(strict=True)
    expected_runs_root = (workspace / "var" / "runs").resolve(strict=True)
    if final_run.parent != expected_runs_root:
        raise ValueError("Receipt may anchor only a direct child of workspace/var/runs")
    if manifest.get("run_id") != final_run.name:
        raise ValueError("Receipt run identity differs from the manifest")
    authority = _validate_receipt_creation_authority(
        workspace=workspace,
        invocation_id=invocation_id,
        receipt_capability=receipt_capability,
        final_run=final_run,
        manifest=manifest,
    )

    if _receipt_control_path(workspace) != receipt_root:
        raise ValueError("Controlled receipt root changed before creation")
    receipt_root.mkdir(parents=True, exist_ok=True)
    if _receipt_control_path(workspace) != receipt_root:
        raise ValueError("Controlled receipt root changed during creation")
    receipt: dict[str, object] = {
        "anchor_scope": _ANCHOR_SCOPE,
        "canonical_config_hash": manifest.get("config_hash_start"),
        "code_commit": manifest.get("code_commit"),
        "completed_at": completed_at,
        "evidence_label": EVIDENCE_LABEL,
        "evidence_package_digest": evidence_package_digest(final_run),
        "final_run_path": str(final_run),
        "invocation_id": invocation_id,
        "lockfile_hash": manifest.get("lockfile_hash"),
        "manifest_ended_at": manifest.get("ended_at"),
        "owned_directory_device": authority.directory_device,
        "owned_directory_inode": authority.directory_inode,
        "ownership_marker_sha256": authority.marker_sha256,
        "raw_semantic_hash": manifest.get("raw_semantic_hash"),
        "receipt_kind": _RECEIPT_KIND,
        "receipt_version": _RECEIPT_VERSION,
        "reportable": False,
        "run_id": manifest.get("run_id"),
        "schema_version": SCHEMA_VERSION,
        "seed": manifest.get("seed"),
        "seed_registry_hash": manifest.get("seed_registry_hash"),
        "started_at": manifest.get("started_at"),
        "summary_semantic_hash": manifest.get("summary_semantic_hash"),
    }
    _validate_receipt_shape(receipt)
    receipt_bytes = canonical_json_bytes(receipt)
    if receipt_path_for(workspace, invocation_id) != receipt_path:
        raise ValueError("Controlled receipt lexical path changed before creation")
    with receipt_path.open("xb") as handle:
        opened = os.fstat(handle.fileno())
        if opened.st_nlink != 1:
            raise RuntimeError("New controlled receipt has an unexpected link count")
        handle.write(receipt_bytes)
        handle.flush()
        os.fsync(handle.fileno())
        completed = os.fstat(handle.fileno())
    if receipt_path_for(workspace, invocation_id) != receipt_path:
        raise RuntimeError("Controlled receipt lexical path changed during creation")
    receipt_stat = receipt_path.stat(follow_symlinks=False)
    if (
        completed.st_dev,
        completed.st_ino,
        completed.st_size,
        completed.st_nlink,
    ) != (
        receipt_stat.st_dev,
        receipt_stat.st_ino,
        receipt_stat.st_size,
        receipt_stat.st_nlink,
    ) or receipt_stat.st_nlink != 1:
        raise RuntimeError("New controlled receipt path identity changed")
    if receipt_path_for(workspace, invocation_id) != receipt_path:
        raise RuntimeError("Controlled receipt lexical path changed after creation")
    return receipt_path


def _validate_receipt_shape(receipt: Mapping[str, object]) -> None:
    if frozenset(receipt) != _RECEIPT_KEYS:
        raise ValueError("Execution receipt keys are not exact")
    if receipt.get("evidence_label") != EVIDENCE_LABEL:
        raise ValueError("Execution receipt evidence label is invalid")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Execution receipt schema version is invalid")
    if receipt.get("receipt_version") != _RECEIPT_VERSION:
        raise ValueError("Execution receipt version is invalid")
    if receipt.get("receipt_kind") != _RECEIPT_KIND:
        raise ValueError("Execution receipt kind is invalid")
    if receipt.get("anchor_scope") != _ANCHOR_SCOPE:
        raise ValueError("Execution receipt anchor scope is invalid")
    if receipt.get("reportable") is not False:
        raise ValueError("Bootstrap execution receipts must remain non-reportable")
    invocation_id = receipt.get("invocation_id")
    if not isinstance(invocation_id, str):
        raise ValueError("Execution receipt invocation ID is invalid")
    _validate_invocation_id(invocation_id)
    if isinstance(receipt.get("seed"), bool) or not isinstance(receipt.get("seed"), int):
        raise ValueError("Execution receipt seed is invalid")
    for key in (
        "canonical_config_hash",
        "lockfile_hash",
        "ownership_marker_sha256",
        "raw_semantic_hash",
        "seed_registry_hash",
        "summary_semantic_hash",
        "evidence_package_digest",
    ):
        value = receipt.get(key)
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"Execution receipt {key} is invalid")
    code_commit = receipt.get("code_commit")
    if not isinstance(code_commit, str) or re.fullmatch(r"[0-9a-f]{40}", code_commit) is None:
        raise ValueError("Execution receipt code commit is invalid")
    for key in (
        "run_id",
        "started_at",
        "manifest_ended_at",
        "completed_at",
        "final_run_path",
        "anchor_scope",
    ):
        if not isinstance(receipt.get(key), str) or not receipt[key]:
            raise ValueError(f"Execution receipt {key} is invalid")
    for key in ("owned_directory_device", "owned_directory_inode"):
        value = receipt.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Execution receipt {key} is invalid")
    started = _parse_receipt_timestamp(receipt["started_at"], "started_at")
    manifest_ended = _parse_receipt_timestamp(
        receipt["manifest_ended_at"],
        "manifest_ended_at",
    )
    completed = _parse_receipt_timestamp(receipt["completed_at"], "completed_at")
    if not started <= manifest_ended <= completed:
        raise ValueError("Execution receipt timestamps are not chronological")


def _parse_receipt_timestamp(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Execution receipt {name} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Execution receipt {name} is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Execution receipt {name} must include a UTC offset")
    return parsed


def verify_execution_receipt(
    *,
    workspace_root: Path | str,
    run_dir: Path | str,
    manifest: Mapping[str, object],
) -> ReceiptVerification:
    """Verify local execution identity separately from evidence semantics."""

    errors: list[str] = []
    receipt_path: Path | None = None
    try:
        workspace = resolve_workspace_root(workspace_root)
        run_id = manifest.get("run_id")
        if not isinstance(run_id, str):
            raise ValueError("Run identity is absent from the manifest")
        invocation_id = run_id.rsplit("-", 1)[-1]
        _validate_invocation_id(invocation_id)
        receipt_path = receipt_path_for(workspace, invocation_id)
        marker_path = _ownership_control_path(workspace, invocation_id, marker=True)
        lexical_run = Path(os.path.abspath(Path(run_dir)))
        if path_has_symlink_or_reparse(lexical_run):
            raise ValueError("Final evidence path is indirect")
        final_run = lexical_run.resolve(strict=True)
        expected_runs_root = (workspace / "var" / "runs").resolve(strict=True)
        if final_run.parent != expected_runs_root:
            raise ValueError("Run is not a direct child of workspace/var/runs")
        if run_id != final_run.name:
            raise ValueError("Run path identity differs from the manifest")
        if not receipt_path.is_file():
            raise ValueError("Execution-instance receipt is missing")
        before = receipt_path.stat(follow_symlinks=False)
        if before.st_nlink != 1 or is_symlink_or_reparse(receipt_path):
            raise ValueError("Execution receipt must be a singly linked regular file")
        if before.st_size > _MAX_RECEIPT_BYTES:
            raise ValueError("Execution receipt exceeds the 64 KiB limit")
        if receipt_path_for(workspace, invocation_id) != receipt_path:
            raise ValueError("Execution receipt lexical path changed before verification")
        with receipt_path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_nlink,
            ) != (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_nlink,
            ):
                raise ValueError("Opened execution receipt identity differs from its path")
            encoded = handle.read(_MAX_RECEIPT_BYTES + 1)
            opened_after = os.fstat(handle.fileno())
        if len(encoded) > _MAX_RECEIPT_BYTES:
            raise ValueError("Execution receipt exceeds the 64 KiB limit")
        after = receipt_path.stat(follow_symlinks=False)
        if receipt_path_for(workspace, invocation_id) != receipt_path:
            raise ValueError("Execution receipt lexical path changed during verification")
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        ) or (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_nlink,
        ) != (
            opened_after.st_dev,
            opened_after.st_ino,
            opened_after.st_size,
            opened_after.st_mtime_ns,
            opened_after.st_nlink,
        ):
            raise ValueError("Execution receipt changed during its stable read")
        receipt = json.loads(encoded, object_pairs_hook=_unique_object)
        if not isinstance(receipt, dict):
            raise ValueError("Execution receipt must be a JSON object")
        _validate_receipt_shape(receipt)
        if canonical_json_bytes(receipt) != encoded:
            raise ValueError("Execution receipt is not canonical JSON")

        if _ownership_control_path(workspace, invocation_id, marker=True) != marker_path:
            raise ValueError("Invocation ownership marker lexical path changed before verification")
        marker, marker_digest = read_ownership_marker(workspace, invocation_id)
        expected_staging = assert_write_path(
            workspace / "var" / "tmp" / f"{run_id}.staging",
            workspace,
        )
        marker_expected: dict[str, object] = {
            "created_at": receipt.get("started_at"),
            "evidence_label": EVIDENCE_LABEL,
            "final_run_path": str(final_run),
            "invocation_id": invocation_id,
            "run_id": run_id,
            "schema_version": SCHEMA_VERSION,
            "seed": manifest.get("seed"),
            "staging_device": receipt.get("owned_directory_device"),
            "staging_inode": receipt.get("owned_directory_inode"),
            "staging_path": str(expected_staging),
        }
        for key, expected_value in marker_expected.items():
            if marker.get(key) != expected_value:
                errors.append(f"Invocation ownership marker {key} does not bind this run")
        for key in ("capability_sha256", "receipt_capability_sha256"):
            marker_hash = marker.get(key)
            if not isinstance(marker_hash, str) or _SHA256.fullmatch(marker_hash) is None:
                errors.append(f"Invocation ownership marker {key} is invalid")
        if receipt.get("ownership_marker_sha256") != marker_digest:
            errors.append("Execution receipt does not bind the ownership marker")
        final_stat = final_run.stat(follow_symlinks=False)
        if not stat.S_ISDIR(final_stat.st_mode) or (
            final_stat.st_dev,
            final_stat.st_ino,
        ) != (
            receipt.get("owned_directory_device"),
            receipt.get("owned_directory_inode"),
        ):
            errors.append("Execution receipt does not bind the current run directory identity")

        expected: dict[str, object] = {
            "canonical_config_hash": manifest.get("config_hash_start"),
            "code_commit": manifest.get("code_commit"),
            "evidence_package_digest": evidence_package_digest(final_run),
            "final_run_path": str(final_run),
            "invocation_id": invocation_id,
            "lockfile_hash": manifest.get("lockfile_hash"),
            "manifest_ended_at": manifest.get("ended_at"),
            "raw_semantic_hash": manifest.get("raw_semantic_hash"),
            "run_id": run_id,
            "seed": manifest.get("seed"),
            "seed_registry_hash": manifest.get("seed_registry_hash"),
            "started_at": manifest.get("started_at"),
            "summary_semantic_hash": manifest.get("summary_semantic_hash"),
        }
        for key, expected_value in expected.items():
            if receipt.get(key) != expected_value:
                errors.append(f"Execution receipt {key} does not bind this run")
        if receipt_path_for(workspace, invocation_id) != receipt_path:
            errors.append("Execution receipt lexical path changed before assurance")
        if _ownership_control_path(workspace, invocation_id, marker=True) != marker_path:
            errors.append("Invocation ownership marker lexical path changed before assurance")
    except (
        OSError,
        RecursionError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        errors.append(str(error))
    return ReceiptVerification(
        identity_assured=not errors,
        errors=tuple(errors),
        receipt_path=receipt_path,
        identity_assurance_scope=IDENTITY_ASSURANCE_SCOPE,
        historical_control_file_inode_continuity_assured=(
            HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED
        ),
        reportable=False,
    )


def receipt_sha256(path: Path | str) -> str:
    """Expose a streamed receipt digest for status records and handoff evidence."""

    return sha256_file(path)

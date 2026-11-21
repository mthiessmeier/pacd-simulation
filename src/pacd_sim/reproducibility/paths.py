"""Write-path confinement for the bounded PACD workspace."""

from __future__ import annotations

import ctypes
import ntpath
import os
from functools import lru_cache
from pathlib import Path
from uuid import UUID

_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_CONTROL_STORE_NAMES = frozenset({"invocations", "receipts"})
_WINDOWS_DEVICE_NAMES = frozenset({"AUX", "CON", "NUL", "PRN"})


class PathBoundaryError(ValueError):
    """Raised when a requested write could escape the designated workspace."""


class _Guid(ctypes.Structure):
    _fields_ = (
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    )


@lru_cache(maxsize=1)
def _windows_known_protected_folders() -> tuple[Path, ...]:
    """Read Desktop/Documents/Downloads Known Folder paths without registry mutation."""
    if os.name != "nt":
        return ()
    folder_ids = (
        "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",  # Desktop
        "FDD39AD0-238F-46AF-ADB4-6C85480369C7",  # Documents
        "374DE290-123F-4565-9164-39C4925E467B",  # Downloads
    )
    discovered: list[Path] = []
    try:
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
    except (AttributeError, OSError):
        return ()
    for folder_id in folder_ids:
        guid = _Guid.from_buffer_copy(UUID(folder_id).bytes_le)
        value = ctypes.c_wchar_p()
        try:
            result = shell32.SHGetKnownFolderPath(
                ctypes.byref(guid),
                0,
                None,
                ctypes.byref(value),
            )
            if result == 0 and value.value:
                discovered.append(Path(value.value).resolve(strict=False))
        except (AttributeError, OSError, ValueError):
            continue
        finally:
            if value:
                ole32.CoTaskMemFree(value)
    return tuple(discovered)


def default_workspace_root(*, home: Path | None = None) -> Path:
    """Return the author-designated PACD workspace without creating it."""
    base = (home or Path.home()).expanduser()
    return (base / "PACD-Workspaces" / "PACD-Simulation").resolve(strict=False)


def protected_roots(*, home: Path | None = None) -> tuple[Path, ...]:
    """Return the small, explicit set of user folders that must remain read-only."""
    base = (home or Path.home()).expanduser().resolve(strict=False)
    candidates = {
        base / "Desktop",
        base / "Documents",
        base / "Downloads",
        base / "OneDrive" / "Desktop",
        base / "OneDrive" / "Documents",
        base / "OneDrive" / "Downloads",
    }
    for variable in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        one_drive = os.environ.get(variable)
        if one_drive:
            one_drive_root = Path(one_drive).expanduser()
            candidates.update(
                {
                    one_drive_root / "Desktop",
                    one_drive_root / "Documents",
                    one_drive_root / "Downloads",
                }
            )
    candidates.update(_windows_known_protected_folders())
    return tuple(sorted((path.resolve(strict=False) for path in candidates), key=str))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_symlink_or_reparse(path: Path | str) -> bool:
    """Detect a symlink, Windows junction, or other reparse-point path itself."""
    candidate = Path(path)
    try:
        if candidate.is_symlink() or candidate.is_junction():
            return True
        attributes = getattr(candidate.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def path_has_symlink_or_reparse(path: Path | str) -> bool:
    """Inspect every lexical path component before any resolution can hide indirection."""
    absolute = Path(os.path.abspath(Path(path).expanduser()))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if is_symlink_or_reparse(current):
            return True
    return False


def _has_windows_alternate_path_spelling(path: Path | str) -> bool:
    """Identify device, ADS, and reserved-device spellings before normalization."""

    if os.name != "nt":
        return False
    raw = os.fspath(path)
    windows = raw.replace("/", "\\")
    folded = windows.casefold()
    if folded.startswith(("\\\\?\\", "\\\\.\\", "\\??\\", "\\\\??\\")):
        return True
    _drive, tail = ntpath.splitdrive(windows)
    if ":" in tail:
        return True
    for component in windows.split("\\"):
        if not component:
            continue
        device_base = component.rstrip(" .").split(".", 1)[0].upper()
        if (
            device_base in _WINDOWS_DEVICE_NAMES
            or len(device_base) == 4
            and device_base[:3] in {"COM", "LPT"}
            and device_base[3] in "123456789"
        ):
            return True
    return False


def assert_exact_control_path(
    path: Path | str,
    workspace_root: Path | str,
    store_name: str,
    *descendants: str,
) -> Path:
    """Return one exact lexical control-store path without resolving it away.

    ``var/receipts`` and ``var/invocations`` are local identity controls. Every
    caller must retain their canonical lexical spelling so a junction cannot be
    hidden by an earlier ``resolve()``. Call this immediately before and after
    every consequential filesystem operation on the returned path.
    """

    if store_name not in _CONTROL_STORE_NAMES:
        raise PathBoundaryError("Unknown PACD control-store name")
    for descendant in descendants:
        if (
            not descendant
            or descendant in {".", ".."}
            or Path(descendant).name != descendant
            or _has_windows_alternate_path_spelling(descendant)
        ):
            raise PathBoundaryError("PACD control-store descendant is not one lexical component")

    workspace = resolve_workspace_root(workspace_root)
    expected = workspace / "var" / store_name
    for descendant in descendants:
        expected /= descendant
    lexical = Path(path)
    if _has_windows_alternate_path_spelling(lexical):
        raise PathBoundaryError("PACD control-store path uses an ADS or device spelling")
    if lexical != expected:
        raise PathBoundaryError(f"PACD control-store path is not exact: {expected}")
    if not lexical.is_absolute():
        raise PathBoundaryError("PACD control-store path must be absolute")
    if path_has_symlink_or_reparse(lexical):
        raise PathBoundaryError(f"PACD {store_name} control-store path is indirect")

    lexical_normalized = Path(os.path.abspath(lexical))
    if lexical_normalized != expected:
        raise PathBoundaryError(f"PACD control-store path is not lexically normalized: {expected}")
    resolved = lexical.resolve(strict=False)
    if resolved != lexical_normalized:
        raise PathBoundaryError(f"PACD {store_name} control-store path resolves indirectly")
    return lexical


def resolve_workspace_root(workspace_root: Path | str | None = None) -> Path:
    """Resolve and validate a workspace root without touching the filesystem.

    An explicit root is supported for isolated tests and alternate authorized hosts.
    It remains a real jail: all later targets must resolve beneath this exact root.
    """
    root = Path(workspace_root) if workspace_root is not None else default_workspace_root()
    root = root.expanduser().resolve(strict=False)
    if root == Path(root.anchor):
        raise PathBoundaryError("A filesystem root cannot be used as the PACD workspace")
    for protected in protected_roots():
        if root == protected or _is_within(root, protected):
            raise PathBoundaryError(f"PACD workspace resolves inside protected path: {protected}")
    return root


def infer_workspace_root(repo_root: Path | str) -> Path:
    """Infer the workspace only when the repository is beneath the mandated root."""
    repository = Path(repo_root).expanduser().resolve(strict=False)
    mandated = default_workspace_root()
    if _is_within(repository, mandated):
        return mandated
    raise PathBoundaryError(
        "Cannot infer an authorized workspace from this repository; pass workspace_root explicitly"
    )


def assert_write_path(
    path: Path | str,
    workspace_root: Path | str | None = None,
    *,
    allow_workspace_root: bool = False,
) -> Path:
    """Return a resolved path only if it is jailed beneath ``workspace_root``."""
    root = resolve_workspace_root(workspace_root)
    target = Path(path).expanduser().resolve(strict=False)
    if target == root and not allow_workspace_root:
        raise PathBoundaryError("Writes must target a child of the PACD workspace")
    if not _is_within(target, root):
        raise PathBoundaryError(f"Write target escapes PACD workspace: {target}")
    for protected in protected_roots():
        if target == protected or _is_within(target, protected):
            raise PathBoundaryError(f"Write target is protected: {target}")
    return target


def assert_direct_workspace_path(path: Path, workspace: Path) -> Path:
    """Confine an evaluator input before opening it, preserving its lexical spelling."""
    lexical = path.absolute()
    if (
        not lexical.is_relative_to(workspace)
        or ".." in path.parts
        or _has_windows_alternate_path_spelling(path)
        or path_has_symlink_or_reparse(lexical)
    ):
        raise PathBoundaryError("Evaluator input must be a direct workspace path")
    resolved = assert_write_path(lexical, workspace)
    if resolved != lexical:
        raise PathBoundaryError("Evaluator input resolves indirectly")
    return lexical


def ensure_directory(path: Path | str, workspace_root: Path | str | None = None) -> Path:
    """Create a confined directory tree and return its resolved path."""
    target = assert_write_path(path, workspace_root)
    target.mkdir(parents=True, exist_ok=True)
    return target


def assert_existing_run_directory(
    run_dir: Path | str, workspace_root: Path | str | None = None
) -> Path:
    """Validate a run directory for read-only verification."""
    target = assert_write_path(run_dir, workspace_root)
    if not target.is_dir():
        raise PathBoundaryError(f"Run directory does not exist: {target}")
    return target

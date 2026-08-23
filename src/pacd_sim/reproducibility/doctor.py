"""Narrow, local-only environment doctor for required bootstrap gates."""

from __future__ import annotations

import ctypes
import importlib.util
import os
import platform
import re
import shutil

# Subprocess use is limited to one fixed, read-only, shell-free local Git query.
import subprocess  # nosec B404
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.harness.run import validate_diagnostic_configuration_files
from pacd_sim.reproducibility.manifest import sha256_file
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_write_path,
    infer_workspace_root,
    path_has_symlink_or_reparse,
    protected_roots,
    resolve_workspace_root,
)
from pacd_sim.reproducibility.reportable import (
    ReportableModeDenied,
    git_commit,
    git_is_dirty,
    validate_reportable_approval,
)


@dataclass(frozen=True)
class DoctorCheck:
    """One bounded doctor gate."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    """Structured doctor result suitable for stable JSON output."""

    evidence_label: str
    passed: bool
    checks: tuple[DoctorCheck, ...]
    cpu_count: int
    worker_cap: int
    total_memory_bytes: int | None
    free_disk_bytes: int | None
    git_commit: str | None
    git_branch: str | None
    git_dirty: bool | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation."""
        return {
            "evidence_label": self.evidence_label,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
            "cpu_count": self.cpu_count,
            "worker_cap": self.worker_cap,
            "total_memory_bytes": self.total_memory_bytes,
            "free_disk_bytes": self.free_disk_bytes,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
        }


def _git_branch(repo_root: Path) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("Git branch could not be established")
    try:
        # The executable is resolved locally and the argument vector is fixed.
        completed = subprocess.run(  # nosec B603
            [
                git_executable,
                "-C",
                str(repo_root),
                "symbolic-ref",
                "--quiet",
                "--short",
                "HEAD",
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("Git branch could not be established") from error
    branch = completed.stdout.strip()
    if completed.returncode != 0 or not branch:
        raise RuntimeError("Git branch could not be established")
    return branch


def _total_memory_bytes() -> int | None:
    if os.name == "nt":

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        try:
            succeeded = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        except (AttributeError, OSError):
            return None
        return int(status.ullTotalPhys) if succeeded else None
    try:
        sysconf_value = getattr(os, "sysconf", None)
        if sysconf_value is None:
            return None
        sysconf = cast(Callable[[str], int], sysconf_value)
        page_size = sysconf("SC_PAGE_SIZE")
        page_count = sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None
    return int(page_size * page_count)


def _nearest_existing_parent(path: Path) -> Path | None:
    current = path
    while current != current.parent:
        if current.exists():
            return current
        current = current.parent
    return current if current.exists() else None


def _command_available(executable: str, module: str) -> bool:
    return shutil.which(executable) is not None or importlib.util.find_spec(module) is not None


_DEPENDENCY_SPEC = re.compile(r"^([A-Za-z0-9_.-]+)(.*)$")


def _dependency_specs(values: object) -> set[tuple[str, str]]:
    if not isinstance(values, list):
        raise ValueError("dependency declaration must be a list")
    result: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("dependency declaration must be a string")
        match = _DEPENDENCY_SPEC.fullmatch(value)
        if match is None:
            raise ValueError("dependency declaration is malformed")
        name, specifier = match.groups()
        result.add((name.lower().replace("_", "-"), specifier.replace(" ", "")))
    return result


def _locked_specs(values: object) -> set[tuple[str, str]]:
    if not isinstance(values, list):
        raise ValueError("locked dependency metadata must be a list")
    result: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("locked dependency metadata entry must be a mapping")
        name = value.get("name")
        specifier = value.get("specifier", "")
        if not isinstance(name, str) or not isinstance(specifier, str):
            raise ValueError("locked dependency metadata has invalid types")
        result.add((name.lower().replace("_", "-"), specifier.replace(" ", "")))
    return result


def _lock_matches_project(
    project_data: Mapping[str, object], lock_data: Mapping[str, object]
) -> bool:
    project = project_data.get("project")
    groups = project_data.get("dependency-groups")
    packages = lock_data.get("package")
    if not isinstance(project, Mapping) or not isinstance(groups, Mapping):
        return False
    if not isinstance(packages, list):
        return False
    project_name = project.get("name")
    root_package: Mapping[str, object] | None = None
    for package in packages:
        if isinstance(package, Mapping) and package.get("name") == project_name:
            root_package = package
            break
    if root_package is None:
        return False
    metadata = root_package.get("metadata")
    if not isinstance(metadata, Mapping):
        return False
    locked_dev = metadata.get("requires-dev")
    if not isinstance(locked_dev, Mapping):
        return False
    project_requires = str(project.get("requires-python", "")).replace(" ", "")
    lock_requires = str(lock_data.get("requires-python", "")).replace(" ", "")
    return (
        lock_data.get("version") == 1
        and lock_data.get("revision") == 3
        and project_requires == ">=3.13,<3.15"
        and lock_requires == project_requires
        and root_package.get("version") == project.get("version")
        and _dependency_specs(project.get("dependencies"))
        == _locked_specs(metadata.get("requires-dist"))
        and _dependency_specs(groups.get("dev")) == _locked_specs(locked_dev.get("dev"))
    )


def run_doctor(
    repo_root: Path | str,
    workspace_root: Path | str | None = None,
) -> DoctorReport:
    """Inspect only the repository and host capabilities required by the work order."""
    requested_repository = Path(repo_root).expanduser()
    requested_workspace = (
        Path(workspace_root).expanduser()
        if workspace_root is not None
        else Path.home() / "PACD-Workspaces" / "PACD-Simulation"
    )
    requested_repository_boundary = requested_workspace / "repo"
    if any(
        path_has_symlink_or_reparse(candidate)
        for candidate in (
            requested_workspace,
            requested_repository_boundary,
            requested_repository,
        )
    ):
        cpu_count = max(1, os.cpu_count() or 1)
        return DoctorReport(
            evidence_label=EVIDENCE_LABEL,
            passed=False,
            checks=(
                DoctorCheck(
                    "repository_workspace_boundary",
                    False,
                    "repository or workspace path contains a symlink or reparse point",
                ),
            ),
            cpu_count=cpu_count,
            worker_cap=min(8, max(1, cpu_count - 2)),
            total_memory_bytes=_total_memory_bytes(),
            free_disk_bytes=None,
            git_commit=None,
            git_branch=None,
            git_dirty=None,
        )
    repository = requested_repository.resolve(strict=True)
    workspace = (
        resolve_workspace_root(requested_workspace)
        if workspace_root is not None
        else infer_workspace_root(repository)
    )
    checks: list[DoctorCheck] = []
    repository_boundary = (workspace / "repo").resolve(strict=False)
    try:
        repository.relative_to(repository_boundary)
        repository_confined = True
    except ValueError:
        repository_confined = False
    boundary_check = DoctorCheck(
        "repository_workspace_boundary",
        repository_confined,
        "repository is confined beneath workspace/repo"
        if repository_confined
        else "repository is outside the explicit workspace/repo boundary",
    )
    checks.append(boundary_check)
    if not repository_confined:
        cpu_count = max(1, os.cpu_count() or 1)
        worker_cap = min(8, max(1, cpu_count - 2))
        disk_base = workspace if workspace.exists() else _nearest_existing_parent(workspace)
        boundary_free_disk = shutil.disk_usage(disk_base).free if disk_base is not None else None
        return DoctorReport(
            evidence_label=EVIDENCE_LABEL,
            passed=False,
            checks=tuple(checks),
            cpu_count=cpu_count,
            worker_cap=worker_cap,
            total_memory_bytes=_total_memory_bytes(),
            free_disk_bytes=boundary_free_disk,
            git_commit=None,
            git_branch=None,
            git_dirty=None,
        )

    python_version_path = repository / ".python-version"
    try:
        pinned_python = python_version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        pinned_python = "UNREADABLE"
    interpreter_ok = pinned_python == "3.13.15" and platform.python_version() == pinned_python
    checks.append(
        DoctorCheck(
            "interpreter_compatibility",
            interpreter_ok,
            f"running={platform.python_version()}; exact_pin={pinned_python}",
        )
    )

    lock_path = repository / "uv.lock"
    pyproject_path = repository / "pyproject.toml"
    lock_ok = lock_path.is_file() and pyproject_path.is_file()
    lock_detail = "uv.lock and pyproject.toml present but not yet validated"
    if lock_ok:
        try:
            project_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
            lock_ok = _lock_matches_project(project_data, lock_data)
            lock_detail = (
                "frozen lock metadata exactly matches project/runtime declarations; "
                f"lock_sha256={sha256_file(lock_path)}"
                if lock_ok
                else "frozen lock metadata does not match project/runtime declarations"
            )
        except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError):
            lock_ok = False
            lock_detail = "dependency metadata could not be parsed"
    checks.append(DoctorCheck("dependency_lock", lock_ok, lock_detail))

    try:
        probe = assert_write_path(workspace / "var" / "runs" / "_doctor_probe", workspace)
        existing_parent = _nearest_existing_parent(probe.parent)
        writable = existing_parent is not None and os.access(existing_parent, os.W_OK)
        path_detail = f"workspace confined; nearest output parent writable={writable}"
    except PathBoundaryError as error:
        writable = False
        path_detail = str(error)
    checks.append(DoctorCheck("workspace_write_boundary", writable, path_detail))

    protected_ok = all(
        workspace != protected and protected not in workspace.parents
        for protected in protected_roots()
    )
    checks.append(
        DoctorCheck(
            "protected_paths_not_work_roots",
            protected_ok,
            "workspace does not resolve into an explicit protected user folder",
        )
    )

    cpu_count = max(1, os.cpu_count() or 1)
    worker_cap = min(8, max(1, cpu_count - 2))
    total_memory = _total_memory_bytes()
    disk_base = workspace if workspace.exists() else _nearest_existing_parent(workspace)
    free_disk: int | None = None
    if disk_base is not None:
        free_disk = shutil.disk_usage(disk_base).free
    resources_ok = free_disk is not None and free_disk >= 20 * 1024**3
    checks.append(
        DoctorCheck(
            "host_resources",
            resources_ok,
            (
                f"cpu={cpu_count}; worker_cap={worker_cap}; "
                f"memory={total_memory}; free_disk={free_disk}"
            ),
        )
    )

    commit_value: str | None = None
    branch_value: str | None = None
    dirty_value: bool | None = None
    try:
        commit_value = git_commit(repository)
        branch_value = _git_branch(repository)
        dirty_value = git_is_dirty(repository)
        git_ok = True
        git_detail = f"commit and branch established; dirty={dirty_value}"
    except (OSError, RuntimeError, PermissionError, ValueError):
        git_ok = False
        git_detail = "commit or branch could not be established"
    checks.append(DoctorCheck("git_state", git_ok, git_detail))

    configuration_hashes: dict[str, str] = {}
    try:
        configuration_hashes = validate_diagnostic_configuration_files(repository)
        config_ok = True
        config_detail = (
            "all governed diagnostic inputs passed strict schema and semantic validation"
        )
    except (OSError, UnicodeError, ValueError):
        config_ok = False
        config_detail = "one or more governed diagnostic inputs failed full validation"
    checks.append(DoctorCheck("configuration_schema", config_ok, config_detail))

    raw_hash_ok = importlib.util.find_spec("pyarrow") is not None
    checks.append(
        DoctorCheck(
            "raw_output_and_hash_manifest",
            raw_hash_ok,
            "PyArrow and standard-library SHA-256 capability available",
        )
    )

    checks.append(
        DoctorCheck(
            "simulation_only_network_disabled",
            config_ok,
            "fully validated policy selects simulated_only and network_enabled=false",
        )
    )

    approval_path = repository / "configs" / "protocol" / "frozen" / "APPROVAL.json"
    approval_exists = approval_path.exists()
    interlock_ok = False
    if config_ok:
        try:
            validate_reportable_approval(
                repository,
                config_hash=configuration_hashes["config_hash"],
                seed_registry_hash=configuration_hashes["seed_registry_hash"],
                baseline_definition_hash=configuration_hashes["baseline_definition_hash"],
                metric_definition_hash=configuration_hashes["metric_definition_hash"],
                protocol_version=configuration_hashes["protocol_version"],
            )
            interlock_ok = approval_exists
            approval_detail = (
                "approval record passed exact hash and clean-commit validation; "
                "bootstrap reportable execution remains unavailable"
            )
        except ReportableModeDenied:
            interlock_ok = not approval_exists
            approval_detail = (
                "approval absent and reportable validation denied as required"
                if interlock_ok
                else "present approval record failed exact fail-closed validation"
            )
    else:
        approval_detail = "interlock expectations unavailable because configuration is invalid"
    checks.append(DoctorCheck("reportable_mode_interlock", interlock_ok, approval_detail))

    required_commands = {
        "ruff": ("ruff", "ruff"),
        "mypy": ("mypy", "mypy"),
        "pytest": ("pytest", "pytest"),
        "pip-audit": ("pip-audit", "pip_audit"),
        "bandit": ("bandit", "bandit"),
        "detect-secrets": ("detect-secrets", "detect_secrets"),
    }
    availability = {
        name: _command_available(executable, module)
        for name, (executable, module) in required_commands.items()
    }
    checks.append(
        DoctorCheck(
            "assurance_commands",
            all(availability.values()),
            ", ".join(f"{name}={available}" for name, available in availability.items()),
        )
    )

    return DoctorReport(
        evidence_label=EVIDENCE_LABEL,
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        cpu_count=cpu_count,
        worker_cap=worker_cap,
        total_memory_bytes=total_memory,
        free_disk_bytes=free_disk,
        git_commit=commit_value,
        git_branch=branch_value,
        git_dirty=dirty_value,
    )

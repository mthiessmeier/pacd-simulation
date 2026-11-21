"""Command-line entry points for bounded PACD diagnostics and verification."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.harness.run import ConfigurationError, run_diagnostic
from pacd_sim.reproducibility.doctor import run_doctor
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    infer_workspace_root,
    path_has_symlink_or_reparse,
    resolve_workspace_root,
)
from pacd_sim.reproducibility.receipts import (
    HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED,
    IDENTITY_ASSURANCE_SCOPE,
)
from pacd_sim.reproducibility.reportable import ReportableModeDenied
from pacd_sim.reproducibility.verify import verify_run


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _emit_json(value: object, *, stream: TextIO = sys.stdout) -> None:
    print(json.dumps(value, allow_nan=False, indent=2, sort_keys=True), file=stream)


def _failure_payload(
    status: str,
    reason: str,
    *,
    diagnostic: bool,
) -> dict[str, object]:
    """Return a structured failure, including local assurance state for diagnostics."""

    payload: dict[str, object] = {
        "evidence_label": EVIDENCE_LABEL,
        "status": status,
        "reason": reason,
    }
    if diagnostic:
        payload.update(
            {
                "valid": False,
                "semantic_content_valid": False,
                "execution_identity_assured": False,
                "identity_assurance_scope": IDENTITY_ASSURANCE_SCOPE,
                "historical_control_file_inode_continuity_assured": (
                    HISTORICAL_CONTROL_FILE_INODE_CONTINUITY_ASSURED
                ),
                "reportable": False,
            }
        )
    return payload


def _resolve_diagnostic_workspace(repository: Path, requested: Path | None) -> Path:
    """Return the designated workspace without letting a CLI argument redefine authority.

    The internal diagnostic worker may inject isolated roots for hermetic tests. The public
    CLI is stricter: its optional spelling of the workspace must resolve to the root already
    implied by the repository's location beneath the author-designated PACD workspace.
    """

    authorized = infer_workspace_root(repository)
    if requested is None:
        return authorized
    if path_has_symlink_or_reparse(requested):
        raise PathBoundaryError("Diagnostic workspace path contains a symlink or reparse point")
    candidate = resolve_workspace_root(requested)
    if candidate != authorized:
        raise PathBoundaryError(
            "Diagnostic --workspace-root cannot redefine the authorized PACD workspace"
        )
    return authorized


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pacd-sim",
        description="Local, synthetic-only PACD environment diagnostics",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="inspect only required local environment gates")
    doctor.add_argument("--repo-root", type=Path, default=_default_repo_root())
    doctor.add_argument("--workspace-root", type=Path)

    diagnostic = subparsers.add_parser(
        "diagnostic",
        help="run the bounded NON_REPORTABLE_DIAGNOSTIC smoke path",
    )
    diagnostic.add_argument("--repo-root", type=Path, default=_default_repo_root())
    diagnostic.add_argument("--workspace-root", type=Path)
    diagnostic.add_argument("--scenario", type=Path)
    diagnostic.add_argument("--policy", type=Path)
    diagnostic.add_argument("--seeds", type=Path)
    diagnostic.add_argument("--baseline", type=Path)
    diagnostic.add_argument("--metrics", type=Path)
    diagnostic.add_argument("--output-root", type=Path)
    diagnostic.add_argument("--seed", type=int)
    diagnostic.add_argument(
        "--reportable",
        action="store_true",
        help="request reportable mode (fails closed during bootstrap)",
    )

    verify = subparsers.add_parser("verify", help="verify one retained diagnostic run")
    verify.add_argument("run_dir", type=Path)
    verify.add_argument("--workspace-root", type=Path)
    verify.add_argument(
        "--show-event-sequence",
        action="store_true",
        help="include the ordered synthetic source events and their digest after verification",
    )
    return parser


def _doctor_command(arguments: argparse.Namespace) -> int:
    report = run_doctor(arguments.repo_root, workspace_root=arguments.workspace_root)
    _emit_json(report.to_dict())
    return 0 if report.passed else 1


def _diagnostic_command(arguments: argparse.Namespace) -> int:
    repository = arguments.repo_root.resolve(strict=True)
    workspace = _resolve_diagnostic_workspace(repository, arguments.workspace_root)
    scenario = (
        arguments.scenario
        or repository / "configs" / "scenarios" / "diagnostic_identity_smoke.yaml"
    )
    policy = arguments.policy or repository / "configs" / "policies" / "diagnostic_safety.yaml"
    seeds = arguments.seeds or repository / "configs" / "seeds" / "diagnostic_seeds.json"
    output_root = arguments.output_root or workspace / "var" / "runs"
    result = run_diagnostic(
        scenario,
        policy,
        seeds,
        output_root,
        seed=arguments.seed,
        workspace_root=workspace,
        repo_root=repository,
        baseline_path=arguments.baseline,
        metric_path=arguments.metrics,
        reportable=arguments.reportable,
    )
    _emit_json(result.to_dict())
    return 0


def _verify_command(arguments: argparse.Namespace) -> int:
    repository = _default_repo_root().resolve(strict=True)
    workspace = _resolve_diagnostic_workspace(repository, arguments.workspace_root)
    result = verify_run(
        arguments.run_dir,
        workspace_root=workspace,
        repo_root=repository,
        include_event_sequence=arguments.show_event_sequence,
    )
    payload = result.to_dict()
    payload["status"] = "VERIFIED" if result.valid else "INVALID"
    _emit_json(payload)
    return 0 if result.valid else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch a doctor, diagnostic, or read-only verification command."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "doctor":
            return _doctor_command(arguments)
        if arguments.command == "diagnostic":
            return _diagnostic_command(arguments)
        if arguments.command == "verify":
            return _verify_command(arguments)
    except ReportableModeDenied as error:
        _emit_json(
            _failure_payload(
                "DENIED",
                str(error),
                diagnostic=arguments.command == "diagnostic",
            ),
            stream=sys.stderr,
        )
        return 3
    except (ConfigurationError, PathBoundaryError, FileNotFoundError, ValueError) as error:
        _emit_json(
            _failure_payload(
                "INVALID",
                str(error),
                diagnostic=arguments.command == "diagnostic",
            ),
            stream=sys.stderr,
        )
        return 2
    except (OSError, RuntimeError) as error:
        _emit_json(
            _failure_payload(
                "FAILED",
                f"{type(error).__name__}: {error}",
                diagnostic=arguments.command == "diagnostic",
            ),
            stream=sys.stderr,
        )
        return 1
    parser.error("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())

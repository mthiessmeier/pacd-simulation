"""Command-line entry points for bounded PACD diagnostics and verification."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from pacd_sim.comparison import ComparisonPlan
from pacd_sim.constants import DEFAULT_SCENARIO_FILE, EVIDENCE_LABEL, policy_file_for_scenario
from pacd_sim.defenders.baselines.static import (
    MINIMUM_REVIEW_SIGNAL,
    STATIC_REVIEW_VERSION,
    propose_review,
)
from pacd_sim.defenders.observations import BaselineObservation
from pacd_sim.defenders.pacd import corroboration
from pacd_sim.evidence.context import evidence_trace
from pacd_sim.harness.run import ConfigurationError, run_diagnostic
from pacd_sim.metrics.dispositions import episode_dispositions
from pacd_sim.metrics.registered import load_register, registered_metrics
from pacd_sim.reproducibility.canonical import canonical_sha256
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
from pacd_sim.reproducibility.verify import verify_run, verify_run_with_summary


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
    diagnostic.add_argument(
        "--scenario", type=Path, help=f"synthetic scenario YAML (default: {DEFAULT_SCENARIO_FILE})"
    )
    diagnostic.add_argument("--policy", type=Path)
    diagnostic.add_argument("--seeds", type=Path)
    diagnostic.add_argument(
        "--baseline",
        type=Path,
        help="defender YAML, e.g. static_review.yaml or pacd_corroborated_review.yaml",
    )
    diagnostic.add_argument("--metrics", type=Path)
    diagnostic.add_argument("--output-root", type=Path)
    diagnostic.add_argument("--seed", type=int)
    diagnostic.add_argument("--plan", type=Path, help="workspace-local development comparison plan")
    diagnostic.add_argument("--plan-sha256", help="required canonical digest for planned launch")
    diagnostic.add_argument("--invocation-id", help="claim a fresh registered 32-hex invocation ID")
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
    for name, description in (
        ("baseline", "replay the static human-review rule on verified observations"),
        ("defender-trace", "trace the PACD planner's review proposals on verified observations"),
        ("evidence-trace", "inspect freshness and distinct sources of verified sensor readings"),
    ):
        replay = subparsers.add_parser(name, help=description)
        replay.add_argument("run_dir", type=Path)
        replay.add_argument("--workspace-root", type=Path)
    metrics = subparsers.add_parser("metrics", help="report one episode or a registered set")
    source = metrics.add_mutually_exclusive_group(required=True)
    source.add_argument("run_dir", nargs="?", type=Path)
    source.add_argument("--register", type=Path, help="workspace-local JSON register of attempts")
    source.add_argument(
        "--plan", type=Path, help="account for cells in a development comparison plan"
    )
    metrics.add_argument("--plan-sha256", help="require the canonical plan digest")
    metrics.add_argument("--register-sha256", help="require the canonical register digest")
    metrics.add_argument(
        "--sensing-freshness",
        action="store_true",
        help="include candidate and execution evidence ages for verified WP08 sensing episodes",
    )
    metrics.add_argument(
        "--mission-impact",
        action="store_true",
        help="include time-integrated mission loss weighted by criticality for guarded episodes",
    )
    metrics.add_argument(
        "--mission-recovery",
        action="store_true",
        help="include per-mission outage and restoration times for guarded episodes",
    )
    metrics.add_argument(
        "--critical-outage",
        action="store_true",
        help="include outage time for designated critical missions in guarded episodes",
    )
    metrics.add_argument(
        "--review-routing",
        action="store_true",
        help="include escalation routing and terminal review outcomes for guarded episodes",
    )
    metrics.add_argument(
        "--approval-burden",
        action="store_true",
        help="include admitted requests, waiting time, expiry and modeled review vetoes",
    )
    metrics.add_argument("--workspace-root", type=Path)
    return parser


def _doctor_command(arguments: argparse.Namespace) -> int:
    report = run_doctor(arguments.repo_root, workspace_root=arguments.workspace_root)
    _emit_json(report.to_dict())
    return 0 if report.passed else 1


def _diagnostic_command(arguments: argparse.Namespace) -> int:
    repository = arguments.repo_root.resolve(strict=True)
    workspace = _resolve_diagnostic_workspace(repository, arguments.workspace_root)
    scenario = arguments.scenario or repository / "configs" / "scenarios" / DEFAULT_SCENARIO_FILE
    policy = arguments.policy or repository / "configs" / "policies" / policy_file_for_scenario(
        scenario.name
    )
    seeds = arguments.seeds or repository / "configs" / "seeds" / "diagnostic_seeds.json"
    output_root = arguments.output_root or workspace / "var" / "runs"
    plan = None
    if (arguments.plan is None) != (arguments.plan_sha256 is None):
        raise ValueError("Planned launch requires both --plan and --plan-sha256")
    if arguments.plan is not None:
        plan, _ = load_register(arguments.plan, workspace, ComparisonPlan, arguments.plan_sha256)
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
        invocation_id=arguments.invocation_id,
        plan=plan,
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


def _static_report(observations: tuple[BaselineObservation, ...]) -> dict[str, object]:
    decisions = []
    proposal_count = 0
    for observation in observations:
        proposal = propose_review(observation)
        if proposal is not None:
            proposal_count += 1
        decisions.append(
            {
                "observation": observation.model_dump(mode="json"),
                "proposal": proposal.model_dump(mode="json") if proposal is not None else None,
            }
        )
    return {
        "policy": STATIC_REVIEW_VERSION,
        "mode": "retrospective_proposals",
        "minimum_signal": MINIMUM_REVIEW_SIGNAL,
        "observation_sha256": canonical_sha256(observations),
        "observation_count": len(decisions),
        "proposal_count": proposal_count,
        "decisions": decisions,
    }


def _defender_trace(observations: tuple[BaselineObservation, ...]) -> dict[str, object]:
    planner = corroboration.CorroboratedReviewPlanner()
    steps = [planner.observe(reading) for reading in observations]
    trace: dict[str, object] = {
        "policy": corroboration.POLICY,
        "mode": "retrospective_proposals",
        "minimum_signal": corroboration.MINIMUM_SIGNAL,
        "max_gap_ticks": corroboration.MAX_GAP_TICKS,
        "observation_count": len(steps),
        "proposal_count": sum(step.proposal is not None for step in steps),
        "observation_sha256": canonical_sha256(observations),
        "decisions": [step.model_dump(mode="json") for step in steps],
    }
    trace["trace_sha256"] = canonical_sha256(trace)
    return trace


def _verified_report_command(arguments: argparse.Namespace) -> int:
    repository = _default_repo_root().resolve(strict=True)
    workspace = _resolve_diagnostic_workspace(repository, arguments.workspace_root)
    if arguments.command == "metrics":
        if arguments.plan_sha256 is not None and arguments.plan is None:
            raise ValueError("--plan-sha256 requires --plan")
        if arguments.plan is not None:
            if arguments.register_sha256 is not None:
                raise ValueError("--register-sha256 requires --register")
            _emit_json(
                registered_metrics(
                    arguments.plan,
                    workspace,
                    repository,
                    arguments.plan_sha256,
                    planned=True,
                    include_sensing_freshness=arguments.sensing_freshness,
                    include_mission_impact=arguments.mission_impact,
                    include_mission_recovery=arguments.mission_recovery,
                    include_critical_outage=arguments.critical_outage,
                    include_review_routing=arguments.review_routing,
                    include_approval_burden=arguments.approval_burden,
                )
            )
            return 0
        if arguments.register is not None:
            report = registered_metrics(
                arguments.register,
                workspace,
                repository,
                arguments.register_sha256,
                include_sensing_freshness=arguments.sensing_freshness,
                include_mission_impact=arguments.mission_impact,
                include_mission_recovery=arguments.mission_recovery,
                include_critical_outage=arguments.critical_outage,
                include_review_routing=arguments.review_routing,
                include_approval_burden=arguments.approval_burden,
            )
            _emit_json(report)
            return 0
        if arguments.register_sha256 is not None:
            raise ValueError("--register-sha256 requires --register")
    verification, material = verify_run_with_summary(
        arguments.run_dir,
        workspace_root=workspace,
        repo_root=repository,
        include_observations=arguments.command in ("baseline", "defender-trace"),
        include_evidence_readings=arguments.command == "evidence-trace",
        include_sensing_freshness=arguments.command == "metrics" and arguments.sensing_freshness,
        include_mission_impact=arguments.command == "metrics" and arguments.mission_impact,
        include_mission_recovery=arguments.command == "metrics" and arguments.mission_recovery,
        include_critical_outage=arguments.command == "metrics" and arguments.critical_outage,
        include_review_routing=arguments.command == "metrics" and arguments.review_routing,
        include_approval_burden=arguments.command == "metrics" and arguments.approval_burden,
    )
    payload = verification.to_dict()
    if not verification.valid or material is None:
        payload["status"] = "INVALID"
        _emit_json(payload)
        return 1

    payload["status"] = "VERIFIED"
    if arguments.command == "metrics":
        metrics = episode_dispositions(material.episode, material.guarded_review)
        payload["run_id"] = verification.run_dir.name
        payload["metrics"] = metrics
        payload["metrics_sha256"] = canonical_sha256(metrics)
    elif arguments.command == "defender-trace":
        payload["defender_trace"] = _defender_trace(material.observations)
    elif arguments.command == "evidence-trace":
        payload["evidence_trace"] = evidence_trace(material.evidence_readings)
    else:
        payload["baseline"] = _static_report(material.observations)
    _emit_json(payload)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch local environment checks, diagnostics, verification and read-only reports."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "doctor":
            return _doctor_command(arguments)
        if arguments.command == "diagnostic":
            return _diagnostic_command(arguments)
        if arguments.command == "verify":
            return _verify_command(arguments)
        if arguments.command in ("baseline", "defender-trace", "evidence-trace", "metrics"):
            return _verified_report_command(arguments)
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

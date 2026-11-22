"""Drive the unmodified public PR22 CLI; retain local, non-reportable evidence.

Run this file from the documentation checkout using the pinned producer's
isolated Python environment. See README.md in this directory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path

REVISION = "31c1645ee28a7bbd2488dfb2d354be1fdea3fd25"
LABEL = "NON_REPORTABLE_DIAGNOSTIC"
SEED = 424242
METRIC_FLAGS = ["--sensing-freshness", "--mission-impact", "--review-routing", "--approval-burden"]
CASES = {
    "isolation": ("diagnostic_review_brief_isolation", "static_review"),
    "sensing": ("diagnostic_review_brief_sensing", "sensing_contextual"),
    "routing": ("diagnostic_review_contention", "static_review"),
    "burden": ("diagnostic_review_burden", "static_review"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value: object) -> None:
    # Every destination belongs to this invocation's newly allocated directory.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


class Demo:
    def __init__(self, producer: Path) -> None:
        self.producer = producer.resolve(strict=True)
        self.workspace = (Path.home() / "PACD-Workspaces" / "PACD-Simulation").resolve()
        require(
            self.producer.is_relative_to(self.workspace / "repo"),
            "Producer must be beneath the native home PACD workspace's repo directory.",
        )
        self.output = self.workspace / "var" / "tmp" / f"current-demo-{uuid.uuid4().hex}"
        self.output.mkdir(parents=True, exist_ok=False)
        self.env = os.environ.copy()
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        temporary = self.output / "process-temp"
        temporary.mkdir()
        for key in ("TMP", "TEMP", "TMPDIR"):
            self.env[key] = str(temporary)
        self.started = time.monotonic()
        self.steps = 0

    def command(
        self, label: str, args: list[str], *, expected: int = 0, parse: bool = True
    ) -> object:
        self.steps += 1
        prefix = self.output / f"{self.steps:02d}-{label}"
        remaining = 300 - (time.monotonic() - self.started)
        require(remaining > 0, "Five-minute demonstration budget exhausted; evidence retained.")
        command = [str(arg) for arg in args]
        record = {"argv": command, "cwd": str(self.producer), "expected_exit": expected}
        try:
            result = subprocess.run(
                command,
                cwd=self.producer,
                env=self.env,
                shell=False,
                capture_output=True,
                timeout=min(120, remaining),
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            prefix.with_suffix(".stdout.txt").write_bytes(error.stdout or b"")
            prefix.with_suffix(".stderr.txt").write_bytes(error.stderr or b"")
            save(prefix.with_suffix(".command.json"), {**record, "status": "TIMED_OUT"})
            raise RuntimeError(f"{label} timed out; output retained at {prefix}") from error
        prefix.with_suffix(".stdout.txt").write_bytes(result.stdout)
        prefix.with_suffix(".stderr.txt").write_bytes(result.stderr)
        save(prefix.with_suffix(".command.json"), {**record, "exit_code": result.returncode})
        require(
            result.returncode == expected,
            f"{label}: exit {result.returncode}, expected {expected}; inspect {prefix}",
        )
        text = (result.stdout if expected == 0 else result.stderr).decode("utf-8")
        return json.loads(text) if parse else text.strip()

    def cli(self, label: str, *args: str, expected: int = 0) -> dict:
        result = self.command(
            label,
            [sys.executable, "-m", "pacd_sim.cli", *args, "--workspace-root", str(self.workspace)],
            expected=expected,
        )
        require(isinstance(result, dict), f"{label}: expected a JSON object")
        return result

    def identity(self, label: str) -> dict:
        commit = self.command(f"{label}-commit", ["git", "rev-parse", "HEAD"], parse=False)
        branch = self.command(
            f"{label}-branch", ["git", "symbolic-ref", "--short", "HEAD"], parse=False
        )
        dirty = self.command(f"{label}-status", ["git", "status", "--porcelain"], parse=False)
        require(
            commit == REVISION and bool(branch) and dirty == "",
            "Producer must be a clean, named branch at the exact documented commit.",
        )
        return {"commit": commit, "branch": branch, "dirty": False}

    def inventory(self, runs: dict, receipts: list[Path]) -> dict[str, str]:
        paths = list(receipts)
        for run in runs.values():
            paths.extend(path for path in run.rglob("*") if path.is_file())
        return {str(path.relative_to(self.workspace)): digest(path) for path in sorted(paths)}

    def run(self) -> None:
        require(platform.python_version() == "3.13.15", "Use isolated CPython 3.13.15.")
        spec = importlib.util.find_spec("pacd_sim")
        require(
            spec is not None and spec.origin is not None,
            "Install the pinned producer with uv sync --frozen first.",
        )
        require(
            Path(spec.origin).resolve() == self.producer / "src" / "pacd_sim" / "__init__.py",
            "Installed pacd_sim does not originate in the pinned producer checkout.",
        )
        source = self.identity("before")
        doctor = self.cli("doctor", "doctor", "--repo-root", str(self.producer))
        require(
            doctor["passed"] and doctor["git_commit"] == REVISION and doctor["git_dirty"] is False,
            "Unmodified doctor must pass.",
        )

        attempts = [
            {"attempt_id": name, "invocation_id": uuid.uuid4().hex, "seed": SEED}
            for name in (*CASES, "reserved-unlaunched")
        ]
        register = self.output / "attempts.json"
        save(register, {"format": "pacd-attempt-register-v1", "attempts": attempts})
        preflight = self.cli(
            "register-before", "metrics", "--register", str(register), *METRIC_FLAGS
        )
        require(
            preflight["status_counts"]["INCOMPLETE"] == 5,
            "All five fresh registered attempts must initially be incomplete.",
        )
        register_sha = preflight["register_sha256"]
        register_file_sha = digest(register)
        runs, reports, extracts, manifests, receipts = {}, {}, {}, {}, []
        for attempt in attempts[:4]:
            name = attempt["attempt_id"]
            scenario, baseline = CASES[name]
            launched = self.cli(
                f"{name}-launch",
                "diagnostic",
                "--repo-root",
                str(self.producer),
                "--scenario",
                str(self.producer / "configs" / "scenarios" / f"{scenario}.yaml"),
                "--baseline",
                str(self.producer / "configs" / "defenders" / f"{baseline}.yaml"),
                "--seed",
                str(SEED),
                "--invocation-id",
                attempt["invocation_id"],
            )
            run = Path(launched["run_dir"]).resolve(strict=True)
            require(
                run.is_relative_to(self.workspace / "var" / "runs"),
                "CLI returned a run outside its expected retained output directory.",
            )
            runs[name] = run
            verified = self.cli(f"{name}-verify", "verify", str(run), "--show-event-sequence")
            require(
                verified["valid"]
                and verified["execution_identity_assured"]
                and verified["reportable"] is False,
                f"{name}: verification did not pass",
            )
            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            require(
                manifest["code_commit"] == REVISION
                and manifest["producer_commit"] == REVISION
                and manifest["dirty_state"] is False
                and manifest["reportable"] is False,
                f"{name}: unexpected manifest provenance",
            )
            manifests[name] = manifest
            receipt = Path(launched["receipt_path"]).resolve(strict=True)
            require(receipt.is_relative_to(self.workspace), "Receipt is outside the workspace")
            receipts.append(receipt)
            report = self.cli(f"{name}-metrics", "metrics", str(run), *METRIC_FLAGS)
            require(
                report["valid"] and report["status"] == "VERIFIED",
                f"{name}: metrics were not released by the verifier",
            )
            reports[name] = report
            trace = self.cli(f"{name}-evidence", "evidence-trace", str(run))
            require(
                trace["valid"] and trace["status"] == "VERIFIED",
                f"{name}: evidence trace failed verification",
            )
            # Inspect raw rows only after the public verifier accepts their retained run.
            rows = [
                json.loads(line)
                for line in (run / "raw" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            briefs, observations = [], []
            for row in rows:
                payload = json.loads(row["payload_json"])
                if row["event_type"] == "guarded_review" and row["outcome"] == "pending":
                    binding = payload.get("binding", {})
                    if "operator_brief" in binding:
                        briefs.append(
                            {
                                "tick": row["tick"],
                                "request_digest": payload["request_digest"],
                                "operator_brief": binding["operator_brief"],
                            }
                        )
                if row["event_type"] == "observation":
                    observations.append(
                        {
                            "tick": row["tick"],
                            "signal": payload["signal"],
                            "sensing_profile": payload.get("sensing_profile"),
                        }
                    )
            extracts[name] = {"briefs": briefs, "observations": observations}
            save(self.output / f"{name}-verified-extracts.json", extracts[name])

        observed = check_expected(reports, extracts)
        retained_before = self.inventory(runs, receipts)
        save(self.output / "retained-files-before.json", retained_before)
        registered_args = [
            "metrics",
            "--register",
            str(register),
            "--register-sha256",
            register_sha,
            *METRIC_FLAGS,
        ]
        final = self.cli("register-after", *registered_args)
        reread = self.cli("register-reread", *registered_args)
        require(final == reread, "Repeated reads of this retained set disagree.")
        require(
            final["status_counts"]
            == {"COMPLETED": 4, "FAILED": 0, "TIMED_OUT": 0, "INCOMPLETE": 1, "INVALID": 0},
            "Expected four completed and one unlaunched incomplete attempt.",
        )
        require(
            final["completion_fraction"]["numerator"] == 4
            and final["completion_fraction"]["denominator"] == 5,
            "Unlaunched attempt disappeared from the completion denominator.",
        )
        for row in final["attempts"]:
            name = row["attempt_id"]
            if name == "reserved-unlaunched":
                require(
                    row["metrics"] is None
                    and row["metrics_sha256"] is None
                    and row["run_id"] is None,
                    "Unlaunched metrics must remain null.",
                )
            else:
                require(
                    row["metrics"] == reports[name]["metrics"]
                    and row["metrics_sha256"] == reports[name]["metrics_sha256"],
                    f"{name}: registered and individual verified metrics disagree",
                )

        before_denial = {path.name for path in (self.workspace / "var" / "runs").iterdir()}
        denial = self.cli(
            "reportable-denied",
            "diagnostic",
            "--repo-root",
            str(self.producer),
            "--seed",
            str(SEED),
            "--reportable",
            expected=3,
        )
        require(
            denial["status"] == "DENIED" and denial["reportable"] is False,
            "Reportable mode must remain denied.",
        )
        require(
            before_denial == {path.name for path in (self.workspace / "var" / "runs").iterdir()},
            "Run allocation changed during the reportable-denial check.",
        )
        require(register_file_sha == digest(register), "Register changed after declaration.")
        retained_after = self.inventory(runs, receipts)
        save(self.output / "retained-files-after.json", retained_after)
        require(retained_before == retained_after, "Read-only reports changed retained evidence.")
        self.identity("after")
        summary = {
            "evidence_label": LABEL,
            "reportable": False,
            "producer": source,
            "python_version": platform.python_version(),
            "helper_sha256": digest(Path(__file__)),
            "lockfile_sha256": digest(self.producer / "uv.lock"),
            "seed": SEED,
            "output_directory": str(self.output),
            "run_directories": {name: str(path) for name, path in runs.items()},
            "register_sha256": register_sha,
            "report_sha256": final["report_sha256"],
            "status_counts": final["status_counts"],
            "completion_fraction": final["completion_fraction"],
            "observed": observed,
            "metrics_sha256": {name: report["metrics_sha256"] for name, report in reports.items()},
            "raw_semantic_sha256": {
                name: item["raw_semantic_hash"] for name, item in manifests.items()
            },
            "unchanged_retained_files": len(retained_before),
            "reportable_mode": "DENIED",
            "all_checks_passed": True,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
        }
        save(self.output / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))


def check_expected(reports: dict, extracts: dict) -> dict:
    metrics = {name: report["metrics"] for name, report in reports.items()}
    review = {name: item["guarded_review"] for name, item in metrics.items()}
    for name in CASES:
        counts = metrics[name]["counts"]
        require(
            counts["simulated_execution_count"] == 1
            and counts["verified_execution_count"] == 1
            and counts["prohibited_execution_count"] == 0,
            f"{name}: expected exactly one verified simulated execution and none prohibited",
        )
    mission = review["isolation"]["mission_impact"]
    require(
        mission["weighted_loss"] == 3.2
        and mission["possible_weighted_ticks"] == 8
        and mission["loss_fraction"] == 0.4,
        "Unexpected isolation mission impact",
    )
    sensing = review["sensing"]["sensing_operator"]
    fresh = review["sensing"]["sensing_freshness"]
    require(
        sensing["verified_switch_count"] == 1 and sensing["switch_cost_spent"] == 0.25,
        "Expected one verified sensing switch at cost 0.25",
    )
    require(
        fresh["candidate"]["fresh_count"] == 1 and fresh["execution"]["stale_count"] == 1,
        "Expected fresh proposal support and stale execution support",
    )
    readings = extracts["sensing"]["observations"]
    require(
        readings[0]["signal"] == 0.9
        and readings[0]["sensing_profile"] == "default"
        and readings[-1]["signal"] == 0.86
        and readings[-1]["sensing_profile"] == "alternate",
        "Expected the verified sensing change to alter later delivered precision",
    )
    require(
        review["sensing"]["mission_impact"]["weighted_loss"] == 0,
        "Sensing fixture unexpectedly interrupted its mission",
    )
    routing = review["routing"]["review_routing"]
    require(
        routing["routing_completeness"]["numerator"] == 1
        and routing["routing_completeness"]["denominator"] == 2
        and routing["outcome_counts"]["capacity"] == 1,
        "Expected one terminal review and one capacity rejection from two escalations",
    )
    burden = review["burden"]["approval_burden"]
    require(
        burden["request_count"] == 2
        and burden["observed_request_ticks"] == 7
        and burden["resolved_wait_denominator"] == 1
        and burden["mean_resolved_wait_ticks"] == 4
        and burden["wait_by_outcome"]["pending_at_horizon"]["count"] == 1
        and burden["override_count"] is None
        and burden["override_status"] == "unsupported",
        "Unexpected PR22 approval-burden accounting",
    )
    for name in ("isolation", "sensing", "burden"):
        require(bool(extracts[name]["briefs"]), f"{name}: missing operator brief")
        for item in extracts[name]["briefs"]:
            brief = item["operator_brief"]
            require(
                brief["format"] == "operator-preview-v1"
                and brief["uncertainty"]["compromise_probability"] is None,
                f"{name}: brief must preserve uncalibrated compromise probability as null",
            )
    isolation_brief = extracts["isolation"]["briefs"][0]["operator_brief"]
    preview = {
        item["mission_id"]: item["operational_if_applied"]
        for item in isolation_brief["impact_preview"]["missions"]
    }
    require(
        preview == {"mission-guarded-aux": True, "mission-guarded-core": False},
        "Isolation preview must expose the conditional interruption of the core mission",
    )
    return {
        "verified_simulated_executions": 4,
        "isolation_weighted_mission_loss": mission["weighted_loss"],
        "isolation_mission_loss_fraction": mission["loss_fraction"],
        "sensing_delivered_signals": [item["signal"] for item in readings],
        "sensing_switch_cost": sensing["switch_cost_spent"],
        "sensing_fresh_candidates": fresh["candidate"]["fresh_count"],
        "sensing_stale_executions": fresh["execution"]["stale_count"],
        "routing_completeness": routing["routing_completeness"],
        "approval_request_ticks": burden["observed_request_ticks"],
        "approval_mean_resolved_wait_ticks": burden["mean_resolved_wait_ticks"],
        "pending_review_requests_at_horizon": 1,
        "override_count": burden["override_count"],
        "operator_brief_compromise_probability": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--producer",
        type=Path,
        required=True,
        help="clean named-branch checkout of the exact PR22 commit",
    )
    arguments = parser.parse_args()
    demo = None
    try:
        demo = Demo(arguments.producer)
        demo.run()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        failure = {
            "evidence_label": LABEL,
            "reportable": False,
            "status": "FAILED",
            "error": f"{type(error).__name__}: {error}",
        }
        if demo is not None:
            save(demo.output / "failure.json", failure)
            failure["retained_output"] = str(demo.output)
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

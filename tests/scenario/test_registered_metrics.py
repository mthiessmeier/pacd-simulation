"""Prospective registration, failure accounting and the verified metric release boundary."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim import cli
from pacd_sim.harness import run as harness
from pacd_sim.metrics.registered import registered_metrics
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256


def entry(name: str, index: int) -> dict[str, object]:
    return {"attempt_id": name, "invocation_id": f"{index:032x}", "seed": 424242}


def register(path: Path, attempts: list[dict[str, object]]) -> str:
    doc = {"format": "pacd-attempt-register-v1", "attempts": attempts}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return canonical_sha256(doc)


@pytest.mark.reproducibility
def test_preregister_then_account_for_every_outcome(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = isolated_workspace
    monkeypatch.setattr(cli, "run_diagnostic", harness._run_diagnostic_in_process)
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda value, **kw: output.append(value))
    path = ws.root / "register.json"
    attempts = [
        entry(k, n) for n, k in enumerate(("retry", "failed", "timeout", "staged", "absent"), 1)
    ]
    pin = register(path, attempts)
    command = ["metrics", "--register", str(path), "--register-sha256", pin]
    assert cli.main(command) == 0
    assert output[-1]["status_counts"]["INCOMPLETE"] == 5
    assert output[-1]["observed_counts"] is None
    assert output[-1]["observed_escalation_fraction"]["value"] is None
    assert not (ws.root / "var/invocations").exists()

    completed = [
        "diagnostic",
        "--seed",
        "424242",
        "--invocation-id",
        str(attempts[0]["invocation_id"]),
    ]
    assert cli.main(completed) == 0, output[-1]
    run = output[-1]
    assert run["invocation_id"] == attempts[0]["invocation_id"]
    assert cli.main(completed) != 0
    for i in (1, 2, 3):
        own = harness._create_invocation_ownership(
            ws.output_root, ws.root, 424242, invocation_id=str(attempts[i]["invocation_id"])
        )
        if i == 1:
            harness._retain_interrupted_evidence(ws.root, own, RuntimeError("test interruption"))
        if i == 2:
            harness._retain_timeout_evidence(ws.root, own)
    assert cli.main(["metrics", run["run_dir"]]) == 0
    single = output[-1]
    assert cli.main(command) == cli.main(command) == 0
    report = output[-1]
    assert report == output[-2]
    assert report["report_sha256"] == canonical_sha256(
        {k: v for k, v in report.items() if k != "report_sha256"}
    )
    assert report["register_sha256"] == pin
    assert [a["attempt_id"] for a in report["attempts"]] == [a["attempt_id"] for a in attempts]
    assert [a["status"] for a in report["attempts"]] == [
        "COMPLETED",
        "FAILED",
        "TIMED_OUT",
        "INCOMPLETE",
        "INCOMPLETE",
    ]
    assert report["status_counts"] == {
        "COMPLETED": 1,
        "FAILED": 1,
        "TIMED_OUT": 1,
        "INCOMPLETE": 2,
        "INVALID": 0,
    }
    assert report["completion_fraction"]["value"] == 1 / 5
    row = report["attempts"][0]
    assert row["run_id"] == run["run_id"] and row["metrics_sha256"] == single["metrics_sha256"]
    assert row["metrics"] == single["metrics"]
    assert report["observed_counts"] == single["metrics"]["counts"]
    assert report["observed_escalation_fraction"] == single["metrics"]["escalation_fraction"]
    assert all(a["metrics"] is a["metrics_sha256"] is None for a in report["attempts"][1:])
    assert [a["reason"] for a in report["attempts"][1:]] == [
        "RuntimeError",
        "DiagnosticTimeoutError",
        "staging_only",
        "no_registered_invocation_observed",
    ]
    assert cli.main(["metrics", "--register", str(path), "--register-sha256", "0" * 64]) != 0
    assert "attempts" not in output[-1]

    # A changed status beside a valid receipt must fail verification; never release earlier counts.
    status = Path(run["run_dir"]) / "status.json"
    doc = json.loads(status.read_bytes())
    doc.update(completion_status="FAILED", error_type="RuntimeError")
    status.write_bytes(canonical_json_bytes(doc))
    assert cli.main(command) == 0
    assert output[-1]["attempts"][0]["status"] == "INVALID"
    assert output[-1]["observed_counts"] is None


@pytest.mark.negative
@pytest.mark.parametrize(
    "case",
    [
        "duplicate_label",
        "duplicate_invocation",
        "bad_id",
        "bool_seed",
        "empty",
        "oversize",
        "unknown",
        "duplicate_key",
        "bad_pin",
        "linked",
        "outside",
    ],
)
def test_reject_invalid_register_before_reading_evidence(
    isolated_workspace: IsolatedWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    ws = isolated_workspace
    path = ws.root / "register.json"
    attempts = [entry("first", 1), entry("second", 2)]
    if case == "duplicate_label":
        attempts[1]["attempt_id"] = "first"
    elif case == "duplicate_invocation":
        attempts[1]["invocation_id"] = attempts[0]["invocation_id"]
    elif case == "bad_id":
        attempts[0]["invocation_id"] = "../outside"
    elif case == "bool_seed":
        attempts[0]["seed"] = False
    elif case == "empty":
        attempts = []
    elif case == "oversize":
        attempts = [entry(f"r{i}", i) for i in range(101)]
    elif case == "unknown":
        attempts[0]["status"] = "COMPLETED"
    register(path, attempts)
    if case == "duplicate_key":
        path.write_text('{"attempts":[],"attempts":[]}', encoding="utf-8")
    if case == "linked":
        os.link(path, ws.root / "link.json")
    if case == "outside":
        path = ws.root.parent / "outside.json"
        register(path, attempts)
    monkeypatch.setattr(
        "pacd_sim.metrics.registered._observe",
        lambda *_: pytest.fail("Read evidence for invalid register"),
    )
    with pytest.raises(ValueError):
        registered_metrics(path, ws.root, ws.repo_root, "1" * 64 if case == "bad_pin" else None)


@pytest.mark.negative
def test_missing_or_conflicting_failure_evidence_is_visible(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    ws = isolated_workspace
    path = ws.root / "set.json"
    row = entry("partial", 1)
    register(path, [row])
    owned = harness._create_invocation_ownership(
        ws.output_root, ws.root, 424242, invocation_id=str(row["invocation_id"])
    )
    harness._retain_interrupted_evidence(ws.root, owned, ValueError("test"))
    final = owned.final_run_dir

    def result() -> Any:
        report: Any = registered_metrics(path, ws.root, ws.repo_root, None)
        return report["attempts"][0]

    assert result()["status"] == "FAILED"
    status = final / "status.json"
    status.rename(final / "saved-status")
    assert result()["reason"] == "no_terminal_status"
    status.write_bytes(canonical_json_bytes({"completion_status": "COMPLETED"}))
    assert result()["status"] == "INVALID"
    status.write_bytes((final / "saved-status").read_bytes())
    (final / "manifest.json").write_text("{}", encoding="utf-8")
    assert result()["status"] == "INVALID"
    register(path, [{**row, "seed": 42}])
    assert result()["metrics"] is None and result()["status"] == "INVALID"


def test_orphan_receipt_blocks_allocation(isolated_workspace: IsolatedWorkspace) -> None:
    ws = isolated_workspace
    key = "b" * 32
    store = ws.root / "var/receipts"
    store.mkdir()
    receipt = store / f"{key}.json"
    receipt.write_bytes(b"retained")
    with pytest.raises(FileExistsError, match="receipt"):
        harness._create_invocation_ownership(ws.output_root, ws.root, 424242, invocation_id=key)
    assert not (ws.root / "var/invocations").exists() and not list(ws.output_root.iterdir())
    assert receipt.read_bytes() == b"retained"

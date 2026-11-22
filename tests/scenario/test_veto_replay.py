"""Reject receipt-backed review records that contradict the governed override policy."""

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import IsolatedWorkspace

from pacd_sim.configuration import GuardedReviewConfig
from pacd_sim.harness import run as harness
from pacd_sim.harness.static_review import review_queue
from pacd_sim.oversight.guarded import GuardedReviewQueue, ReviewEvent
from pacd_sim.reproducibility.receipts import verify_execution_receipt

type Command = Callable[..., dict[str, Any]]


def _launch(ws: IsolatedWorkspace, command: Command, condition: str) -> Path:
    result = command(
        "diagnostic",
        "--scenario",
        str(ws.config_root / "scenarios" / f"diagnostic_review_override_{condition}.yaml"),
        "--baseline",
        str(ws.config_root / "defenders" / "static_review.yaml"),
        "--seed",
        "424242",
    )
    return Path(result["run_dir"])


def _expect_semantic_rejection(ws: IsolatedWorkspace, command: Command, run: Path) -> None:
    assert verify_execution_receipt(
        workspace_root=ws.root,
        run_dir=run,
        manifest=json.loads((run / "manifest.json").read_bytes()),
    ).identity_assured
    rejected = command("verify", str(run), code=1)
    assert rejected["status"] == "INVALID" and rejected["semantic_content_valid"] is False
    report = command("metrics", str(run), "--approval-burden", code=1)
    assert report["status"] == "INVALID" and "metrics" not in report


@pytest.mark.reproducibility
@pytest.mark.parametrize(("declared", "substitute"), [("veto", "retain"), ("retain", "veto")])
def test_replay_checks_the_governed_policy_even_when_all_downstream_rows_agree(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    monkeypatch: pytest.MonkeyPatch,
    declared: str,
    substitute: str,
) -> None:
    ws = isolated_workspace

    def changed_queue(
        config: GuardedReviewConfig, observe: Callable[[ReviewEvent], None]
    ) -> GuardedReviewQueue:
        assert config.override_policy == f"{declared}_approval"
        changed = config.model_copy(update={"override_policy": f"{substitute}_approval"})
        return review_queue(changed, observe)

    with monkeypatch.context() as producer:
        producer.setattr(harness, "review_queue", changed_queue)
        run = _launch(ws, command, declared)
    raw = (json.loads(line) for line in (run / "raw/events.jsonl").read_bytes().splitlines())
    reviews = [r for r in raw if r["event_type"] == "guarded_review"]
    (assessed,) = (r for r in reviews if r["outcome"] == "override_assessment")
    outcomes = [r["outcome"] for r in reviews if r["action_id"] == assessed["action_id"]]
    if substitute == "veto":
        assert outcomes == ["pending", "override_assessment", "denied"]
    else:
        assert outcomes[:3] == ["pending", "override_assessment", "approved"]
        assert "executed" in outcomes and "verified" in outcomes
    _expect_semantic_rejection(ws, command, run)


@pytest.mark.reproducibility
@pytest.mark.parametrize("fault", ["omitted", "duplicate", "wrong_request", "wrong_rationale"])
def test_replay_requires_one_complete_bound_assessment(
    isolated_workspace: IsolatedWorkspace,
    command: Command,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    record = GuardedReviewQueue._record

    def incorrect(queue: GuardedReviewQueue, event: ReviewEvent) -> ReviewEvent:
        if event.outcome == "override_assessment":
            if fault == "omitted":
                return event
            if fault == "duplicate":
                record(queue, event)
            elif fault == "wrong_request":
                event = replace(event, payload=dict(event.payload, request_digest="0" * 64))
            else:
                event = replace(
                    event, payload=dict(event.payload, rationale="retain_planned_response")
                )
        return record(queue, event)

    with monkeypatch.context() as producer:
        producer.setattr(GuardedReviewQueue, "_record", incorrect)
        run = _launch(isolated_workspace, command, "veto")
    _expect_semantic_rejection(isolated_workspace, command, run)

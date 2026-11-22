"""Receipt-backed projection of source freshness and dependence on the public read path."""

import json
from typing import Any

import pytest
import yaml
from conftest import (
    IsolatedWorkspace,
    controlled_config_files,
    run_committed_scenario,
)

from pacd_sim import cli
from pacd_sim.harness.run import _run_diagnostic_in_process, load_yaml_config
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256


def _capture_cli(ws: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    monkeypatch.setattr(cli, "_default_repo_root", lambda: ws.repo_root)
    monkeypatch.setattr("pacd_sim.reproducibility.paths.default_workspace_root", lambda: ws.root)
    output: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_emit_json", lambda report, **_: output.append(report))
    return output


@pytest.mark.scenario
@pytest.mark.parametrize("delay", [3, 4])
def test_cli_evidence_trace_binds_ties_subjects_and_age_to_verified_sensor_rows(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch, delay: int
) -> None:
    ws = isolated_workspace
    path = controlled_config_files(ws.config_root)[0]
    scenario = load_yaml_config(path)
    telemetry, events = scenario["telemetry"], scenario["events"]
    assert isinstance(telemetry, dict) and isinstance(events, list)
    telemetry["delay_ticks"] = delay
    first = events[0]
    events.extend(
        [
            {**first, "id": "tie-with-benign-label"},
            {**first, "id": "unattributed", "tick": 0, "identity_id": None},
        ]
    )
    path.write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    run = run_committed_scenario(ws)
    output = _capture_cli(ws, monkeypatch)
    assert cli.main(["baseline", str(run.run_dir)]) == 0
    baseline = output[-1]["baseline"]["decisions"]
    assert cli.main(["evidence-trace", str(run.run_dir)]) == 0
    assert output[-1]["status"] == "VERIFIED" and output[-1]["execution_identity_assured"]
    trace = output[-1]["evidence_trace"]
    assert trace["input_count"] == 4
    assert trace["trace_sha256"] == canonical_sha256(
        {key: value for key, value in trace.items() if key != "trace_sha256"}
    )
    for key, (step, decision, tick) in enumerate(
        zip(trace["decisions"], baseline, [0, 1, 1, 2], strict=True), start=1
    ):
        sensor = decision["observation"]
        assert step["reading"] == {
            "observation_key": key,
            "source_key": 1,
            "subject_id": sensor["subject_id"],
            "measured_tick": tick,
            "delivered_tick": sensor["tick"],
            "signal": sensor["signal"],
        }
        assert sensor["tick"] == tick + delay
        assert step["age_ticks"] == delay
        assert step["freshness"] == ("fresh" if delay == 3 else "stale")
    unidentified, first_read, tied_read, _ = trace["decisions"]
    assert unidentified["reading"]["subject_id"] is None
    assert unidentified["eligible_distinct_source_count"] == 0
    if delay == 3:
        assert [first_read["source_relation"], tied_read["source_relation"]] == [
            "first_source",
            "repeated_source",
        ]
        assert tied_read["eligible_distinct_source_count"] == 1
    else:
        assert all(step["eligible_distinct_source_count"] == 0 for step in trace["decisions"])
    assert cli.main(["evidence-trace", str(run.run_dir)]) == 0
    assert output[-1] == output[-2]


@pytest.mark.negative
@pytest.mark.parametrize("fault", ["missing_receipt", "altered_signal"])
def test_failed_receipt_or_changed_observation_withholds_evidence_trace(
    isolated_workspace: IsolatedWorkspace, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    ws = isolated_workspace
    scenario, policy, seeds, baseline, metrics = controlled_config_files(ws.config_root)
    run = _run_diagnostic_in_process(
        scenario,
        policy,
        seeds,
        ws.output_root,
        workspace_root=ws.root,
        repo_root=ws.repo_root,
        baseline_path=baseline,
        metric_path=metrics,
        seed=424242,
    )
    if fault == "missing_receipt":
        receipt = run.receipt_path
        assert receipt is not None
        receipt.rename(receipt.with_suffix(".held"))
    else:
        raw = run.run_dir / "raw/events.jsonl"
        rows = [json.loads(line) for line in raw.read_bytes().splitlines()]
        observation = next(row for row in rows if row["event_type"] == "observation")
        payload = json.loads(observation["payload_json"])
        payload["signal"] = 0.5
        observation["payload_json"] = canonical_json_bytes(payload).decode("utf-8")
        raw.write_bytes(b"".join(canonical_json_bytes(row) + b"\n" for row in rows))
    output = _capture_cli(ws, monkeypatch)
    monkeypatch.setattr(cli, "evidence_trace", lambda _: pytest.fail("unverified input"))
    assert cli.main(["evidence-trace", str(run.run_dir)]) == 1
    assert output[-1]["status"] == "INVALID" and "evidence_trace" not in output[-1]
    assert output[-1]["semantic_content_valid"] is (fault == "missing_receipt")

"""End-to-end acceptance checks for the bounded diagnostic artifact set."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns, controlled_config_files, file_sha256

from pacd_sim.constants import EVIDENCE_LABEL
from pacd_sim.metrics.summarize import summarize_raw_events, summary_from_raw
from pacd_sim.reproducibility.manifest import (
    semantic_summary_hash,
    sha256_file,
)

_EXPECTED_ARTIFACTS = {
    "NON_REPORTABLE_DIAGNOSTIC",
    "SHA256SUMS.txt",
    "canonical_config.json",
    "derived/episode_summary.csv",
    "derived/episode_summary.parquet",
    "logs/run.log",
    "manifest.json",
    "raw/events.jsonl",
    "raw/events.parquet",
    "seed_registry.json",
    "status.json",
}


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _events(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in (run_dir / "raw" / "events.jsonl").read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        assert isinstance(value, dict)
        rows.append(value)
    return rows


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(row["payload_json"])
    assert isinstance(value, dict)
    return value


def _is_ordered_subsequence(values: list[str], required: tuple[str, ...]) -> bool:
    position = 0
    for value in values:
        if position < len(required) and value == required[position]:
            position += 1
    return position == len(required)


@pytest.mark.scenario
def test_diagnostic_retains_exact_labelled_artifact_set(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    run_dir = run.run_dir
    actual = {path.relative_to(run_dir).as_posix() for path in run_dir.rglob("*") if path.is_file()}

    assert actual == _EXPECTED_ARTIFACTS
    assert run.evidence_label == EVIDENCE_LABEL
    assert run.elapsed_seconds < 300.0
    assert (run_dir / EVIDENCE_LABEL).read_text(encoding="utf-8").strip() == EVIDENCE_LABEL

    for name in ("canonical_config.json", "seed_registry.json", "status.json", "manifest.json"):
        assert _json_object(run_dir / name)["evidence_label"] == EVIDENCE_LABEL

    rows = _events(run_dir)
    assert rows
    assert all(row["evidence_label"] == EVIDENCE_LABEL for row in rows)

    for relative in ("raw/events.parquet", "derived/episode_summary.parquet"):
        table = pq.read_table(run_dir / relative)
        assert table.schema.metadata[b"evidence_label"].decode("ascii") == EVIDENCE_LABEL
        assert set(table.column("evidence_label").to_pylist()) == {EVIDENCE_LABEL}

    with (run_dir / "derived" / "episode_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        assert {row["evidence_label"] for row in csv.DictReader(handle)} == {EVIDENCE_LABEL}

    log_lines = (run_dir / "logs" / "run.log").read_text(encoding="utf-8").splitlines()
    assert log_lines
    assert all(EVIDENCE_LABEL in line for line in log_lines)
    assert (run_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()[0] == (
        f"# evidence_label={EVIDENCE_LABEL}"
    )


@pytest.mark.scenario
def test_required_event_chain_and_benign_negative_control_are_retained(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    rows = _events(diagnostic_runs.same_seed_a.run_dir)
    event_types = [str(row["event_type"]) for row in rows]
    required_chain = (
        "observation",
        "evidence",
        "state_update",
        "hypothesis",
        "candidate_action",
        "safety_decision",
        "simulated_execution",
        "verification",
        "audit",
        "manifest",
    )

    assert _is_ordered_subsequence(event_types, required_chain)
    assert [row["sequence"] for row in rows] == list(range(1, len(rows) + 1))
    assert {row["disposition"] for row in rows if row["event_type"] == "safety_decision"} >= {
        "APPROVE",
        "ESCALATE",
        "PROHIBIT",
    }

    benign_rows = [
        row
        for row in rows
        if row["event_type"] in {"evidence", "hypothesis"}
        and _payload(row).get("classification") == "benign_negative_control"
    ]
    assert {row["event_type"] for row in benign_rows} == {"evidence", "hypothesis"}
    assert all(row["outcome"] == "not_compromised" for row in benign_rows)
    benign_hypotheses = [row for row in benign_rows if row["event_type"] == "hypothesis"]
    assert all(float(_payload(row)["compromise_probability"]) < 0.5 for row in benign_hypotheses)


@pytest.mark.scenario
def test_prohibited_candidate_is_audited_and_never_executed(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    rows = _events(diagnostic_runs.same_seed_a.run_dir)
    candidate_ids = {row["action_id"] for row in rows if row["event_type"] == "candidate_action"}
    audit_ids = {row["action_id"] for row in rows if row["event_type"] == "audit"}
    execution_ids = {row["action_id"] for row in rows if row["event_type"] == "simulated_execution"}
    decisions = [row for row in rows if row["event_type"] == "safety_decision"]
    prohibited_ids = {row["action_id"] for row in decisions if row["disposition"] == "PROHIBIT"}
    escalated_ids = {row["action_id"] for row in decisions if row["disposition"] == "ESCALATE"}
    approved_ids = {row["action_id"] for row in decisions if row["disposition"] == "APPROVE"}

    assert prohibited_ids
    assert prohibited_ids <= candidate_ids
    assert prohibited_ids <= audit_ids
    assert not prohibited_ids & execution_ids
    assert not escalated_ids & execution_ids
    assert execution_ids <= approved_ids
    for row in rows:
        if row["event_type"] == "simulated_execution":
            payload = _payload(row)
            assert payload["adapter"] == "simulated_only"
            assert payload["network_enabled"] is False


@pytest.mark.scenario
def test_summary_is_reproducible_from_raw_without_mutating_inputs(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    raw_path = run_dir / "raw" / "events.parquet"
    canonical_path = run_dir / "canonical_config.json"
    raw_before = sha256_file(raw_path)
    canonical_before = sha256_file(canonical_path)
    expected = summary_from_raw(raw_path)
    retained = pq.read_table(run_dir / "derived" / "episode_summary.parquet").to_pylist()[0]

    assert retained == expected
    prohibited_execution_count = expected["prohibited_execution_count"]
    benign_negative_control_count = expected["benign_negative_control_count"]
    assert isinstance(prohibited_execution_count, int)
    assert isinstance(benign_negative_control_count, int)
    assert prohibited_execution_count == 0
    assert benign_negative_control_count >= 2

    rederived_parent = diagnostic_runs.workspace.root / "var" / "tmp" / "rederived"
    rederived_parent.mkdir(parents=True)
    rederived = summarize_raw_events(
        raw_path,
        rederived_parent / "derived",
        workspace_root=diagnostic_runs.workspace.root,
    )

    assert rederived == expected
    assert semantic_summary_hash(rederived_parent / "derived" / "episode_summary.parquet") == (
        diagnostic_runs.same_seed_a.summary_semantic_hash
    )
    assert sha256_file(raw_path) == raw_before
    assert sha256_file(canonical_path) == canonical_before
    assert all(
        file_sha256(path) == diagnostic_runs.input_hashes_before[path]
        for path in controlled_config_files(diagnostic_runs.workspace.config_root)
    )

    manifest = _json_object(run_dir / "manifest.json")
    assert manifest["config_hash_start"] == manifest["config_hash_end"]
    assert manifest["config_hash_start"] == canonical_before


@pytest.mark.scenario
def test_outputs_make_no_comparative_or_empirical_claims(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run_dir = diagnostic_runs.same_seed_a.run_dir
    canonical = _json_object(run_dir / "canonical_config.json")
    metrics = canonical["metric_definition"]
    assert isinstance(metrics, dict)
    assert metrics["comparative_claims"] is False

    forbidden_keys = {
        "benchmark_result",
        "comparative_result",
        "comparison",
        "effect_size",
        "hypothesis_status",
        "performance_claim",
        "winner",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {str(key) for key in value} | set().union(
                *(keys(child) for child in value.values())
            )
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    structured_values: list[object] = [
        canonical,
        _json_object(run_dir / "manifest.json"),
        _json_object(run_dir / "status.json"),
        *_events(run_dir),
    ]
    assert not forbidden_keys & set().union(*(keys(value) for value in structured_values))

    claim_pattern = re.compile(
        r"\b(?:outperform(?:s|ed)?|superior to|better than|worse than|"
        r"statistically significant|effect size|pacd performance)\b",
        flags=re.IGNORECASE,
    )
    text_artifacts = [
        path
        for path in run_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".jsonl", ".log", ".txt"}
    ]
    assert all(
        claim_pattern.search(path.read_text(encoding="utf-8")) is None for path in text_artifacts
    )

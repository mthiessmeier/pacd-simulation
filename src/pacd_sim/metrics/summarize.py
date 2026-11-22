"""Derive the bounded episode summary exclusively from retained raw events."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal

import pyarrow as pa
import pyarrow.parquet as pq

from pacd_sim.audit.writer import EVENT_SCHEMA
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.reproducibility.paths import (
    PathBoundaryError,
    assert_write_path,
    path_has_symlink_or_reparse,
)
from pacd_sim.schema import DiagnosticRecord, Sha256Digest, Signed64Count


class MetricRecord(DiagnosticRecord):
    """Absolute diagnostic counts for one seed and governed configuration."""

    seed: Signed64Count
    config_hash: Sha256Digest
    event_count: Signed64Count
    observation_count: Signed64Count
    evidence_count: Signed64Count
    state_update_count: Signed64Count
    hypothesis_count: Signed64Count
    candidate_action_count: Signed64Count
    approved_action_count: Signed64Count
    escalated_action_count: Signed64Count
    prohibited_action_count: Signed64Count
    simulated_execution_count: Signed64Count
    verified_execution_count: Signed64Count
    benign_negative_control_count: Signed64Count
    prohibited_execution_count: Signed64Count


class EpisodeRecord(MetricRecord):
    """Flat v1 summary with the completion marker observable in the raw stream."""

    completion_status: Literal["EVENT_CHAIN_COMPLETED", "INCOMPLETE"]


SUMMARY_FIELDS: Final[tuple[tuple[str, pa.DataType], ...]] = (
    ("evidence_label", pa.string()),
    ("schema_version", pa.string()),
    ("seed", pa.int64()),
    ("config_hash", pa.string()),
    ("completion_status", pa.string()),
    ("event_count", pa.int64()),
    ("observation_count", pa.int64()),
    ("evidence_count", pa.int64()),
    ("state_update_count", pa.int64()),
    ("hypothesis_count", pa.int64()),
    ("candidate_action_count", pa.int64()),
    ("approved_action_count", pa.int64()),
    ("escalated_action_count", pa.int64()),
    ("prohibited_action_count", pa.int64()),
    ("simulated_execution_count", pa.int64()),
    ("verified_execution_count", pa.int64()),
    ("benign_negative_control_count", pa.int64()),
    ("prohibited_execution_count", pa.int64()),
)
SUMMARY_SCHEMA: Final[pa.Schema] = pa.schema(
    [pa.field(name, data_type, nullable=False) for name, data_type in SUMMARY_FIELDS],
    metadata={
        b"evidence_label": EVIDENCE_LABEL.encode("ascii"),
        b"schema_version": SCHEMA_VERSION.encode("ascii"),
        b"derived_only_from": b"raw/events.parquet",
    },
)


def _event_count(rows: list[dict[str, object]], event_type: str) -> int:
    return sum(row.get("event_type") == event_type for row in rows)


def summary_from_raw_table(table: pa.Table) -> dict[str, object]:
    """Compute one summary row from an already bounded and materialized raw table."""
    expected_names = EVENT_SCHEMA.names
    if table.schema.names != expected_names:
        raise ValueError("Raw event columns do not match the fixed audit schema")
    rows = [{str(key): value for key, value in row.items()} for row in table.to_pylist()]
    if not rows:
        raise ValueError("Raw event artifact is empty")
    if any(row.get("evidence_label") != EVIDENCE_LABEL for row in rows):
        raise ValueError("Raw events contain a missing or invalid evidence label")

    seeds = {row.get("seed") for row in rows}
    config_hashes = {row.get("config_hash") for row in rows}
    if len(seeds) != 1 or len(config_hashes) != 1:
        raise ValueError("Raw events mix seeds or configuration hashes")
    seed = next(iter(seeds))
    config_hash = next(iter(config_hashes))
    if isinstance(seed, bool) or not isinstance(seed, int) or not isinstance(config_hash, str):
        raise ValueError("Raw event seed or config_hash has an invalid type")

    prohibited_actions = {
        str(row.get("action_id"))
        for row in rows
        if row.get("event_type") == "safety_decision" and row.get("disposition") == "PROHIBIT"
    }
    benign_negative_controls = 0
    reviewed_decisions: Counter[str] = Counter()
    reviewed_executions = reviewed_verifications = prohibited_reviewed_executions = 0
    for row in rows:
        payload_text = row.get("payload_json")
        if not isinstance(payload_text, str):
            raise ValueError("Raw event payload_json is not a string")
        payload = json.loads(payload_text)
        if isinstance(payload, dict) and payload.get("classification") == "benign_negative_control":
            benign_negative_controls += 1
        if row["event_type"] == "guarded_review":
            outcome = row["outcome"]
            if outcome in ("executed", "execution_failed", "unauthorized"):
                policy = payload.get("policy_decision") if isinstance(payload, dict) else None
                decision = policy.get("disposition") if isinstance(policy, dict) else None
                if decision not in ("APPROVE", "ESCALATE", "PROHIBIT"):
                    raise ValueError("Unknown governor disposition for reviewed concrete action")
                reviewed_decisions[decision] += 1
                reviewed_executions += outcome == "executed"
                prohibited_reviewed_executions += outcome == "executed" and decision == "PROHIBIT"
            reviewed_verifications += outcome == "verified"

    return EpisodeRecord.model_validate(
        {
            "evidence_label": EVIDENCE_LABEL,
            "schema_version": SCHEMA_VERSION,
            "seed": seed,
            "config_hash": config_hash,
            "completion_status": (
                "EVENT_CHAIN_COMPLETED"
                if any(row.get("event_type") == "manifest" for row in rows)
                else "INCOMPLETE"
            ),
            "event_count": len(rows),
            "observation_count": _event_count(rows, "observation"),
            "evidence_count": _event_count(rows, "evidence"),
            "state_update_count": _event_count(rows, "state_update"),
            "hypothesis_count": _event_count(rows, "hypothesis"),
            "candidate_action_count": _event_count(rows, "candidate_action")
            + reviewed_decisions.total(),
            "approved_action_count": sum(
                row.get("event_type") == "safety_decision" and row.get("disposition") == "APPROVE"
                for row in rows
            )
            + reviewed_decisions["APPROVE"],
            "escalated_action_count": sum(
                row.get("event_type") == "safety_decision" and row.get("disposition") == "ESCALATE"
                for row in rows
            )
            + reviewed_decisions["ESCALATE"],
            "prohibited_action_count": sum(
                row.get("event_type") == "safety_decision" and row.get("disposition") == "PROHIBIT"
                for row in rows
            )
            + reviewed_decisions["PROHIBIT"],
            "simulated_execution_count": _event_count(rows, "simulated_execution")
            + reviewed_executions,
            "verified_execution_count": sum(
                row.get("event_type") == "verification" and row.get("outcome") == "verified"
                for row in rows
            )
            + reviewed_verifications,
            "benign_negative_control_count": benign_negative_controls,
            "prohibited_execution_count": sum(
                row.get("event_type") == "simulated_execution"
                and str(row.get("action_id")) in prohibited_actions
                for row in rows
            )
            + prohibited_reviewed_executions,
        }
    ).model_dump()


def summary_from_raw(raw_events_path: Path | str) -> dict[str, object]:
    """Compute one summary row using no configuration or in-memory run state."""
    return summary_from_raw_table(pq.read_table(Path(raw_events_path)))


def summarize_raw_events(
    raw_events_path: Path | str,
    derived_dir: Path | str,
    *,
    workspace_root: Path | str,
) -> dict[str, object]:
    """Write fixed Parquet and CSV summaries created only from raw Parquet."""
    summary = summary_from_raw(raw_events_path)
    write_episode_summary(
        EpisodeRecord.model_validate(summary), derived_dir, workspace_root=workspace_root
    )
    return summary


def write_episode_summary(
    episode: EpisodeRecord,
    derived_dir: Path | str,
    *,
    workspace_root: Path | str,
    expected_hashes: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Serialize the bounded row and exclusively create both v1 summary files."""
    summary = episode.model_dump()
    table = pa.Table.from_pylist([summary], schema=SUMMARY_SCHEMA)
    parquet = pa.BufferOutputStream()
    pq.write_table(
        table,
        parquet,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    field_names = [name for name, _data_type in SUMMARY_FIELDS]
    csv_text = io.StringIO(newline="")
    writer = csv.DictWriter(csv_text, fieldnames=field_names, lineterminator="\n")
    writer.writeheader()
    writer.writerow(summary)
    encoded = {
        "episode_summary.parquet": parquet.getvalue().to_pybytes(),
        "episode_summary.csv": csv_text.getvalue().encode("utf-8"),
    }
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in encoded.items()}
    if expected_hashes is not None and hashes != expected_hashes:
        raise ValueError("Regenerated summary differs from the verified artifact digests")
    if path_has_symlink_or_reparse(derived_dir):
        raise PathBoundaryError("Summary output directory path contains a symlink or reparse point")
    output_dir = assert_write_path(derived_dir, workspace_root)
    output_dir.mkdir(parents=False, exist_ok=False)
    for name, data in encoded.items():
        target = output_dir / name
        if path_has_symlink_or_reparse(target):
            raise PathBoundaryError("Summary output file path contains a symlink or reparse point")
        with target.open("xb") as handle:
            handle.write(data)
    return hashes

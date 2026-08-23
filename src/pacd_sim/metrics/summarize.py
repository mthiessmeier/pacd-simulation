"""Derive the bounded episode summary exclusively from retained raw events."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Final

import pyarrow as pa
import pyarrow.parquet as pq

from pacd_sim.audit.writer import EVENT_SCHEMA
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.reproducibility.paths import assert_write_path

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


def summary_from_raw(raw_events_path: Path | str) -> dict[str, object]:
    """Compute one summary row using no configuration or in-memory run state."""
    raw_path = Path(raw_events_path)
    table = pq.read_table(raw_path)
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
    for row in rows:
        payload_text = row.get("payload_json")
        if not isinstance(payload_text, str):
            raise ValueError("Raw event payload_json is not a string")
        payload = json.loads(payload_text)
        if isinstance(payload, dict) and payload.get("classification") == "benign_negative_control":
            benign_negative_controls += 1

    return {
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
        "candidate_action_count": _event_count(rows, "candidate_action"),
        "approved_action_count": sum(
            row.get("event_type") == "safety_decision" and row.get("disposition") == "APPROVE"
            for row in rows
        ),
        "escalated_action_count": sum(
            row.get("event_type") == "safety_decision" and row.get("disposition") == "ESCALATE"
            for row in rows
        ),
        "prohibited_action_count": sum(
            row.get("event_type") == "safety_decision" and row.get("disposition") == "PROHIBIT"
            for row in rows
        ),
        "simulated_execution_count": _event_count(rows, "simulated_execution"),
        "verified_execution_count": sum(
            row.get("event_type") == "verification" and row.get("outcome") == "verified"
            for row in rows
        ),
        "benign_negative_control_count": benign_negative_controls,
        "prohibited_execution_count": sum(
            row.get("event_type") == "simulated_execution"
            and str(row.get("action_id")) in prohibited_actions
            for row in rows
        ),
    }


def summarize_raw_events(
    raw_events_path: Path | str,
    derived_dir: Path | str,
    *,
    workspace_root: Path | str,
) -> dict[str, object]:
    """Write fixed Parquet and CSV summaries created only from raw Parquet."""
    summary = summary_from_raw(raw_events_path)
    output_dir = assert_write_path(derived_dir, workspace_root)
    output_dir.mkdir(parents=False, exist_ok=False)
    parquet_path = assert_write_path(output_dir / "episode_summary.parquet", workspace_root)
    csv_path = assert_write_path(output_dir / "episode_summary.csv", workspace_root)

    table = pa.Table.from_pylist([summary], schema=SUMMARY_SCHEMA)
    pq.write_table(
        table,
        parquet_path,
        compression="NONE",
        data_page_version="1.0",
        use_dictionary=False,
        write_statistics=False,
    )
    field_names = [name for name, _data_type in SUMMARY_FIELDS]
    with csv_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_names, lineterminator="\n")
        writer.writeheader()
        writer.writerow(summary)
    return summary

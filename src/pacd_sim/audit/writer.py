"""Append-only diagnostic audit output with a fixed raw-event schema."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Final, Literal, TextIO, get_args

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, field_validator

from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.reproducibility.canonical import canonical_json_bytes
from pacd_sim.reproducibility.manifest import validate_retained_json_text_depth
from pacd_sim.reproducibility.paths import assert_write_path
from pacd_sim.schema import (
    DiagnosticRecord,
    NonNegativeFloat,
    Sha256Digest,
    Signed64Count,
    validate_audit_text,
)

EventType = Literal[
    "run_started",
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
]
EVENT_TYPES: Final[frozenset[str]] = frozenset(get_args(EventType))


class AuditEvent(DiagnosticRecord):
    """One v1 raw row, identified within its run by the one-based sequence."""

    run_id: Annotated[str, Field(min_length=1, max_length=200)]
    sequence: Annotated[int, Field(ge=1, lt=2**63)]
    tick: NonNegativeFloat
    seed: Signed64Count
    event_type: EventType
    entity_id: str
    action_id: str
    disposition: str
    outcome: str
    config_hash: Sha256Digest
    payload_json: Annotated[str, Field(max_length=64 * 1024)]

    @field_validator("entity_id", "action_id", "disposition", "outcome")
    @classmethod
    def _bound_event_text(cls, value: str) -> str:
        return validate_audit_text(value)

    @field_validator("payload_json")
    @classmethod
    def _canonical_payload(cls, value: str) -> str:
        data = value.encode("utf-8")
        if len(data) > 64 * 1024:
            raise ValueError("Audit payload exceeds the 64 KiB diagnostic cap")
        validate_retained_json_text_depth(value, source="audit payload_json")
        decoded = json.loads(value)
        if not isinstance(decoded, dict) or canonical_json_bytes(decoded) != data:
            raise ValueError("Audit payload must be a canonical JSON object")
        return value


EVENT_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        pa.field("evidence_label", pa.string(), nullable=False),
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("sequence", pa.int64(), nullable=False),
        pa.field("tick", pa.float64(), nullable=False),
        pa.field("seed", pa.int64(), nullable=False),
        pa.field("event_type", pa.string(), nullable=False),
        pa.field("entity_id", pa.string(), nullable=False),
        pa.field("action_id", pa.string(), nullable=False),
        pa.field("disposition", pa.string(), nullable=False),
        pa.field("outcome", pa.string(), nullable=False),
        pa.field("config_hash", pa.string(), nullable=False),
        pa.field("payload_json", pa.string(), nullable=False),
    ],
    metadata={
        b"evidence_label": EVIDENCE_LABEL.encode("ascii"),
        b"schema_version": SCHEMA_VERSION.encode("ascii"),
    },
)


class AuditWriter:
    """Write JSONL immediately and consolidate the same rows to fixed Parquet."""

    def __init__(
        self,
        run_dir: Path | str,
        run_id: str,
        config_hash: str,
        seed: int,
        *,
        workspace_root: Path | str,
    ) -> None:
        if not run_id or len(run_id) > 200:
            raise ValueError("run_id must contain 1-200 characters")
        if len(config_hash) != 64 or any(
            character not in "0123456789abcdef" for character in config_hash
        ):
            raise ValueError("config_hash must be a lowercase SHA-256 digest")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
            raise ValueError("seed must be a nonnegative signed 64-bit integer")

        self._workspace_root = Path(workspace_root)
        self._run_dir = assert_write_path(run_dir, workspace_root)
        raw_dir = assert_write_path(self._run_dir / "raw", workspace_root)
        raw_dir.mkdir(parents=False, exist_ok=False)
        self.jsonl_path = assert_write_path(raw_dir / "events.jsonl", workspace_root)
        self.parquet_path = assert_write_path(raw_dir / "events.parquet", workspace_root)
        self._jsonl: TextIO = self.jsonl_path.open("x", encoding="utf-8", newline="\n")
        self._run_id = run_id
        self._config_hash = config_hash
        self._seed = seed
        self._sequence = 0
        self._rows: list[dict[str, object]] = []
        self._closed = False

    @property
    def events(self) -> tuple[dict[str, object], ...]:
        """Return copies of rows emitted so far for diagnostics and tests."""
        return tuple(dict(row) for row in self._rows)

    def emit(
        self,
        event_type: str,
        *,
        tick: float,
        entity_id: str = "",
        action_id: str = "",
        disposition: str = "",
        outcome: str = "",
        payload: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Append one validated event to the human-readable raw stream."""
        if self._closed:
            raise RuntimeError("AuditWriter is closed")
        payload_dict = dict(payload or {})
        payload_text = canonical_json_bytes(payload_dict).decode("utf-8")
        record = AuditEvent.model_validate(
            {
                "evidence_label": EVIDENCE_LABEL,
                "schema_version": SCHEMA_VERSION,
                "run_id": self._run_id,
                "sequence": self._sequence + 1,
                "tick": tick,
                "seed": self._seed,
                "event_type": event_type,
                "entity_id": entity_id,
                "action_id": action_id,
                "disposition": disposition,
                "outcome": outcome,
                "config_hash": self._config_hash,
                "payload_json": payload_text,
            }
        )
        row = record.model_dump()
        self._jsonl.write(canonical_json_bytes(row).decode("utf-8") + "\n")
        self._jsonl.flush()
        self._rows.append(row)
        self._sequence = record.sequence
        return dict(row)

    def close(self) -> tuple[Path, Path]:
        """Close JSONL and create the deterministic fixed-schema Parquet peer."""
        if self._closed:
            return self.jsonl_path, self.parquet_path
        self._jsonl.flush()
        self._jsonl.close()
        if self.parquet_path.exists():
            raise FileExistsError(f"Refusing to overwrite raw event artifact: {self.parquet_path}")
        table = pa.Table.from_pylist(self._rows, schema=EVENT_SCHEMA)
        pq.write_table(
            table,
            self.parquet_path,
            compression="NONE",
            data_page_version="1.0",
            use_dictionary=False,
            write_statistics=False,
        )
        self._closed = True
        return self.jsonl_path, self.parquet_path

    def __enter__(self) -> AuditWriter:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if exc_type is None:
            self.close()
        elif not self._jsonl.closed:
            self._jsonl.flush()
            self._jsonl.close()

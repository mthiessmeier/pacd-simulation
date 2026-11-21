"""Wire compatibility and failure boundaries for the four v1 evidence records."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from conftest import DiagnosticRuns, IsolatedWorkspace
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from pacd_sim.actions.models import DefensiveAction
from pacd_sim.audit.writer import EVENT_SCHEMA, AuditEvent, AuditWriter
from pacd_sim.constants import EVIDENCE_LABEL, SCHEMA_VERSION
from pacd_sim.metrics.summarize import SUMMARY_SCHEMA, EpisodeRecord, MetricRecord
from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256
from pacd_sim.reproducibility.manifest import RunManifest, write_manifest


def _event(**overrides: object) -> dict[str, object]:
    return {
        "evidence_label": EVIDENCE_LABEL,
        "schema_version": SCHEMA_VERSION,
        "run_id": "synthetic-run",
        "sequence": 1,
        "tick": 0.0,
        "seed": 424242,
        "event_type": "audit",
        "entity_id": "",
        "action_id": "",
        "disposition": "",
        "outcome": "",
        "config_hash": "0" * 64,
        "payload_json": "{}",
        **overrides,
    }


def test_wire_models_match_v1_artifacts(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    for line in (run.run_dir / "raw" / "events.jsonl").read_bytes().splitlines():
        record = AuditEvent.model_validate_json(line)
        assert set(record.model_dump()) == set(EVENT_SCHEMA.names)
        assert canonical_json_bytes(record) == line
    summary = pq.read_table(run.run_dir / "derived" / "episode_summary.parquet").to_pylist()[0]
    episode = EpisodeRecord.model_validate(summary)
    assert set(episode.model_dump()) == set(SUMMARY_SCHEMA.names)
    assert episode.model_dump() == summary
    counts = MetricRecord.model_validate(episode.model_dump(exclude={"completion_status"}))
    assert counts.verified_execution_count == 1
    manifest_bytes = run.manifest_path.read_bytes()
    manifest = RunManifest.model_validate_json(manifest_bytes)
    assert canonical_json_bytes(manifest) == manifest_bytes
    # The bootstrap scenario bounds version text by document size, not by the ID length.
    long_version = "v" * 257
    assert (
        RunManifest.model_validate(
            manifest.model_dump() | {"protocol_version": long_version}
        ).protocol_version
        == long_version
    )


@pytest.mark.property
@given(
    st.dictionaries(
        st.text(alphabet="abcåé", min_size=1, max_size=6),
        st.integers(min_value=-1000, max_value=1000),
        max_size=10,
    ),
    st.integers(min_value=0, max_value=2**63 - 1),
)
@settings(max_examples=40, deadline=None)
def test_record_hash_survives_field_reordering(payload: dict[str, int], seed: int) -> None:
    wire = _event(seed=seed, payload_json=canonical_json_bytes(payload).decode("utf-8"))
    event = AuditEvent.model_validate(dict(reversed(wire.items())))
    assert canonical_sha256(event) == canonical_sha256(wire)
    assert AuditEvent.model_validate_json(canonical_json_bytes(event)) == event


@pytest.mark.negative
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("evidence_label", "REPORTABLE"),
        ("sequence", True),
        ("seed", 2**63),
        ("event_type", "unknown"),
        ("unexpected", 0),
        pytest.param("entity_id", "é" * 251, id="identifier-byte-bound"),
        ("tick", float("nan")),
        ("tick", float("inf")),
        ("tick", True),
        ("payload_json", '{"a":1,"a":1}'),
        ("payload_json", '{"x":1e999}'),
        ("payload_json", "[]"),
        pytest.param("payload_json", '{"x":' + "[" * 64 + "0" + "]" * 64 + "}", id="payload-depth"),
        pytest.param("payload_json", '{"x":"' + "é" * 32768 + '"}', id="payload-byte-bound"),
    ],
)
def test_invalid_wire_rows_fail_closed(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        AuditEvent.model_validate(_event(**{field: value}))


@pytest.mark.negative
def test_rejected_row_does_not_consume_sequence(isolated_workspace: IsolatedWorkspace) -> None:
    destination = isolated_workspace.output_root / "synthetic-run"
    destination.mkdir()
    with AuditWriter(
        destination, destination.name, "0" * 64, 424242, workspace_root=isolated_workspace.root
    ) as writer:
        with pytest.raises(ValueError):
            writer.emit("audit", tick=float("nan"))
        row = writer.emit("audit", tick=1.0)
    assert row["sequence"] == 1
    assert writer.jsonl_path.read_bytes().splitlines() == [canonical_json_bytes(row)]


@pytest.mark.negative
def test_manifest_is_deeply_frozen_and_rejects_false_provenance(
    diagnostic_runs: DiagnosticRuns,
) -> None:
    run = diagnostic_runs.same_seed_a
    wire = json.loads(run.manifest_path.read_bytes())
    parsed = RunManifest.model_validate(wire)
    with pytest.raises(ValidationError):
        parsed.artifact_hashes.configuration = "1" * 64
    with pytest.raises(ValidationError):
        parsed.configuration_hashes.aggregate = "1" * 64
    wire["artifact_hashes"]["raw/events.jsonl"] = "1" * 64
    assert parsed.artifact_hashes.events_jsonl != wire["artifact_hashes"]["raw/events.jsonl"]
    for change in (
        {"reportable": True},
        {"reportable": 0},
        {"config_hash_end": "0" * 64},
        {"ended_at": "2020-01-01"},
        {"ended_at": "2000-01-01T00:00:00Z"},
        {"artifact_hashes": {"unexpected": "0" * 64}},
        {"failure_type": "OSError"},
        {"completion_status": "FAILED"},
    ):
        with pytest.raises(ValidationError):
            RunManifest.model_validate(wire | change)
    failed = wire | {"completion_status": "FAILED", "failure_type": "OSError"}
    assert RunManifest.model_validate(failed).model_dump() == failed


@pytest.mark.negative
def test_manifest_writer_rejects_invalid_record_before_output(
    isolated_workspace: IsolatedWorkspace,
) -> None:
    target: Path = isolated_workspace.output_root / "synthetic-run"
    target.mkdir()
    with pytest.raises(ValueError):
        write_manifest(
            target, {"evidence_label": EVIDENCE_LABEL}, workspace_root=isolated_workspace.root
        )
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("cost", [float("-inf"), float("nan"), float("inf")])
def test_domain_model_rejects_nonfinite_action_cost(cost: float) -> None:
    with pytest.raises(ValidationError):
        DefensiveAction(
            id="example",
            action_type="isolate_session",
            target_id="session",
            reversible=True,
            requested_authority="automatic",
            mission_cost=cost,
        )

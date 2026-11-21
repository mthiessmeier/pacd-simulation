"""Immutable bootstrap constants."""

from typing import Final

EVIDENCE_LABEL: Final = "NON_REPORTABLE_DIAGNOSTIC"
SCHEMA_VERSION: Final = "1.0"
DEFAULT_PROTOCOL_VERSION: Final = "BOOTSTRAP_DRAFT_v1"
DEFAULT_SCENARIO_FILE: Final = "diagnostic_identity_smoke.yaml"
DIAGNOSTIC_SCENARIO_FILES: Final = (DEFAULT_SCENARIO_FILE, "diagnostic_maintenance_window.yaml")

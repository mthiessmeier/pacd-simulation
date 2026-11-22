"""Immutable bootstrap constants."""

from typing import Final

EVIDENCE_LABEL: Final = "NON_REPORTABLE_DIAGNOSTIC"
SCHEMA_VERSION: Final = "1.0"
DEFAULT_PROTOCOL_VERSION: Final = "BOOTSTRAP_DRAFT_v1"
DEFAULT_SCENARIO_FILE: Final = "diagnostic_identity_smoke.yaml"
DEFAULT_BASELINE_FILE: Final = "diagnostic_baseline.yaml"
SENSING_POLICY_FILE: Final = "diagnostic_sensing.yaml"
SELECTION_BASELINE_FILES: Final = ("sensing_contextual.yaml", "sensing_scheduled.yaml")
SENSING_BASELINE_FILES: Final = (
    "sensing_fixed.yaml",
    "sensing_adaptive.yaml",
    "sensing_disabled.yaml",
    *SELECTION_BASELINE_FILES,
)
SENSING_V1_SCENARIO_FILES: Final = (
    "diagnostic_sensing_nominal.yaml",
    "diagnostic_sensing_costly.yaml",
    "diagnostic_sensing_delayed.yaml",
)
REVIEW_BRIEF_SENSING_FILE: Final = "diagnostic_review_brief_sensing.yaml"
REVIEW_BRIEF_ISOLATION_FILE: Final = "diagnostic_review_brief_isolation.yaml"
SENSING_SCENARIO_FILES: Final = (*SENSING_V1_SCENARIO_FILES, REVIEW_BRIEF_SENSING_FILE)
DIAGNOSTIC_BASELINE_FILES: Final = (
    DEFAULT_BASELINE_FILE,
    "static_review.yaml",
    "pacd_corroborated_review.yaml",
    *SENSING_BASELINE_FILES,
)
GUARDED_SCENARIO_FILES: Final = (
    "diagnostic_guarded_benign.yaml",
    "diagnostic_guarded_adverse.yaml",
)
MISSION_WEIGHT_SCENARIO_FILES: Final = (
    "diagnostic_mission_core_high.yaml",
    "diagnostic_mission_core_low.yaml",
)
REVIEW_CONTENTION_FILE: Final = "diagnostic_review_contention.yaml"
REVIEW_BURDEN_FILE: Final = "diagnostic_review_burden.yaml"
REVIEW_OVERRIDE_FILES: Final = (
    "diagnostic_review_override_retain.yaml",
    "diagnostic_review_override_veto.yaml",
)
DIAGNOSTIC_SCENARIO_FILES: Final = (
    DEFAULT_SCENARIO_FILE,
    "diagnostic_maintenance_window.yaml",
    "diagnostic_repeated_readings.yaml",
    *GUARDED_SCENARIO_FILES,
    *SENSING_V1_SCENARIO_FILES,
    *MISSION_WEIGHT_SCENARIO_FILES,
    REVIEW_CONTENTION_FILE,
    REVIEW_BRIEF_ISOLATION_FILE,
    REVIEW_BRIEF_SENSING_FILE,
    REVIEW_BURDEN_FILE,
    *REVIEW_OVERRIDE_FILES,
)


def policy_file_for_scenario(scenario_file: str) -> str:
    if scenario_file in SENSING_SCENARIO_FILES:
        return SENSING_POLICY_FILE
    return "diagnostic_safety.yaml"


def diagnostic_pair_supported(scenario_file: str, defender_file: str) -> bool:
    if (
        scenario_file not in DIAGNOSTIC_SCENARIO_FILES
        or defender_file not in DIAGNOSTIC_BASELINE_FILES
    ):
        return False
    if (scenario_file in SENSING_SCENARIO_FILES) != (defender_file in SENSING_BASELINE_FILES):
        return False
    if scenario_file == "diagnostic_sensing_delayed.yaml":
        return defender_file in SELECTION_BASELINE_FILES
    if defender_file == DEFAULT_BASELINE_FILE:
        return scenario_file not in (
            *GUARDED_SCENARIO_FILES,
            *MISSION_WEIGHT_SCENARIO_FILES,
            REVIEW_CONTENTION_FILE,
            REVIEW_BRIEF_ISOLATION_FILE,
            REVIEW_BURDEN_FILE,
            *REVIEW_OVERRIDE_FILES,
        )
    return True

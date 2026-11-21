"""Validate the WP00 ledger against the supplied v1.0 handoff. Read-only, standard library."""

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CATEGORIES = {
    "implementation requirement",
    "acceptance/control requirement",
    "draft methodological definition",
    "source-explicitly deferred item",
    "historical instruction",
    "explanatory material",
    "table header",
    "duplicate/cross-reference",
}
STATES = {
    "accepted complete",
    "partial",
    "open",
    "not yet evidenced",
    "source-explicitly deferred",
    "draft methodology",
    "context",
}
SOURCE_FIELDS = (
    "source_unit_id",
    "source_alias",
    "source_file",
    "source_section",
    "source_export_line",
    "unit_kind",
    "original_metric_id",
    "original_text",
    "scope_disposition",
    "package_source_file",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main(package: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    template = package / "08_SOURCE_UNIT_RECONCILIATION.csv"
    check(
        hashlib.sha256(template.read_bytes()).hexdigest()
        == "259209d49e39ae3524fa8d2071a46f13182dcdc51965b12a39eebbaa4d03dd2f",
        "template differs from the preserved handoff",
    )
    original = read_rows(template)
    inventory = read_rows(package / "repository_snapshot/docs/PHASE2_ORIGINAL_SCOPE_INVENTORY.csv")
    rows = read_rows(root / "status/REMAINING_SCOPE_RECONCILIATION.csv")
    sources = {row["source_unit_id"] for row in original}
    check(len(sources) == len(rows) == len(inventory) == len(original) == 558, "source count")
    check(original[0].keys() == rows[0].keys(), "schema")
    exports = {
        path: (package / path).read_text(encoding="utf-8").splitlines()
        for path in {r["package_source_file"] for r in original}
    }
    register = json.loads((package / "07_WORK_PACKAGE_REGISTER.json").read_text(encoding="utf-8"))
    packages = {p["id"] for p in register["work_packages"]}
    streams = {f"SC-{i:02}" for i in range(1, 19)}
    seen_packages: set[str] = set()
    seen_streams: set[str] = set()
    requirement_ids: set[str] = set()
    links: set[str] = set()
    trees: dict[str, set[str]] = {}
    for row, orig, archived in zip(rows, original, inventory, strict=True):
        unit = row["source_unit_id"]
        for field in SOURCE_FIELDS:
            check(row[field] == orig[field], f"{unit} changed {field}")
            if field in archived:
                check(orig[field] == archived[field], f"{unit} source inventory mismatch {field}")
        source_line = exports[row["package_source_file"]][int(row["source_export_line"]) - 1]
        check(source_line.strip() == row["original_text"], f"{unit} source line")
        revision = row["accepted_commit"] or "d5a29699e14409bfd54d30c51117c81077639ee6"
        check(re.fullmatch(r"[a-f0-9]{40}", revision) is not None, f"{unit} evidence revision")
        if revision not in trees:
            listing = subprocess.check_output(
                ["git", "ls-tree", "-r", "-t", "--name-only", revision], cwd=root, text=True
            )
            trees[revision] = set(listing.splitlines())
        for column in ("code_paths", "test_paths"):
            for path in filter(None, row[column].split(" | ")):
                check(path in trees[revision], f"{unit} missing {path} at {revision}")
        category, state = row["unit_category"], row["requirement_status"]
        check(category in CATEGORIES and state in STATES, f"{unit} classification")
        check("PENDING_RECONCILIATION" not in row["current_reconciliation_state"], unit)
        ids = set(re.findall(r"R-(?:WO|TM|MD|EC|FM)-\d{3}(?:[.][a-z0-9]+)?", row["requirement_id"]))
        links.update(ids)
        if category != "duplicate/cross-reference":
            requirement_ids.update(ids)
        if category in {
            "implementation requirement",
            "acceptance/control requirement",
            "draft methodological definition",
            "source-explicitly deferred item",
            "duplicate/cross-reference",
        }:
            check(bool(ids), f"{unit} lacks requirement link")
        wp = set(re.findall(r"WP\d{2}", row["work_package_ids"]))
        sc = set(re.findall(r"SC-\d{2}", row["workstream_ids"]))
        check(wp <= packages and sc <= streams, f"{unit} unknown allocation")
        seen_packages.update(wp)
        seen_streams.update(sc)
        if state not in {"context", "source-explicitly deferred"}:
            check(bool(wp and sc), f"{unit} missing allocation")
        if state in {"partial", "open", "not yet evidenced", "draft methodology"}:
            for field in ("remaining_behavior", "acceptance_criteria", "dependencies"):
                check(bool(row[field].strip()), f"{unit} missing {field}")
        if state == "accepted complete":
            for field in (
                "code_paths",
                "test_paths",
                "accepted_commit",
                "review_record",
                "implementation_and_acceptance_evidence",
            ):
                check(bool(row[field].strip()), f"{unit} lacks accepted evidence in {field}")
    check(links <= requirement_ids, f"dangling requirement links {links - requirement_ids}")
    check(seen_packages == packages and seen_streams == streams, "scope coverage")
    families = {"SEC": 7, "MIS": 6, "POL": 7, "SAF": 6, "GOV": 5, "CAL": 6, "GEN": 5, "OPS": 5}
    metrics = Counter(row["original_metric_id"] for row in rows if row["original_metric_id"])
    check(
        metrics == Counter(f"{f}-{i:03}" for f, n in families.items() for i in range(1, n + 1)),
        "metric IDs",
    )
    print(
        f"{len(rows)} source units, {len(metrics)} metric IDs, "
        f"{len(seen_streams)} workstreams, {len(seen_packages)} packages"
    )
    print("Unit categories", dict(Counter(r["unit_category"] for r in rows)))
    print("Unit states", dict(Counter(r["requirement_status"] for r in rows)))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

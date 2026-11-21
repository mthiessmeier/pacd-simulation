"""Rebuild this diagnostic's derived files from verified raw records in a fresh directory."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from pacd_sim.metrics.summarize import summarize_raw_events
from pacd_sim.reproducibility.manifest import sha256_file
from pacd_sim.reproducibility.paths import infer_workspace_root, path_has_symlink_or_reparse
from pacd_sim.reproducibility.verify import verify_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="completed local diagnostic run directory")
    run = parser.parse_args().run_dir.absolute()
    repository = Path(__file__).resolve().parents[2]
    workspace = infer_workspace_root(repository)
    if run.parent != workspace / "var" / "runs" or path_has_symlink_or_reparse(run):
        parser.error("specify a direct, local child of the workspace var/runs directory")
    verification = verify_run(run, workspace_root=workspace, repo_root=repository)
    if not verification.valid:
        parser.exit(1, "Run verification failed: " + ", ".join(verification.errors) + "\n")

    destination = workspace / "var" / "tmp" / f"regenerated-{uuid4().hex}"
    if path_has_symlink_or_reparse(destination.parent):
        parser.error("the temporary output parent contains an indirect path")
    summary = summarize_raw_events(
        run / "raw" / "events.parquet", destination, workspace_root=workspace
    )
    rebuilt = {}
    for filename in ("episode_summary.csv", "episode_summary.parquet"):
        rebuilt[filename] = sha256_file(destination / filename)
        if rebuilt[filename] != sha256_file(run / "derived" / filename):
            parser.exit(1, f"Regenerated {filename} differs from the verified original\n")
    print(json.dumps({"summary": summary, "sha256": rebuilt, "directory": str(destination)}))


if __name__ == "__main__":
    main()

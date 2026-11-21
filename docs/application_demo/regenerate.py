"""Rebuild this diagnostic's derived files from verified raw records in a fresh directory."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from pacd_sim.metrics.summarize import write_episode_summary
from pacd_sim.reproducibility.paths import infer_workspace_root, path_has_symlink_or_reparse
from pacd_sim.reproducibility.verify import verify_run_with_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="completed local diagnostic run directory")
    run = parser.parse_args().run_dir.absolute()
    repository = Path(__file__).resolve().parents[2]
    workspace = infer_workspace_root(repository)
    if run.parent != workspace / "var" / "runs" or path_has_symlink_or_reparse(run):
        parser.error("specify a direct, local child of the workspace var/runs directory")
    verification, material = verify_run_with_summary(
        run, workspace_root=workspace, repo_root=repository
    )
    if not verification.valid or material is None:
        parser.exit(1, "Run verification failed: " + ", ".join(verification.errors) + "\n")

    destination = workspace / "var" / "tmp" / f"regenerated-{uuid4().hex}"
    try:
        rebuilt = write_episode_summary(
            material.episode,
            destination,
            workspace_root=workspace,
            expected_hashes={
                "episode_summary.csv": material.csv_sha256,
                "episode_summary.parquet": material.parquet_sha256,
            },
        )
    except (ValueError, OSError) as error:
        parser.exit(1, f"Summary regeneration failed: {error}\n")
    print(
        json.dumps(
            {
                "summary": material.episode.model_dump(),
                "sha256": rebuilt,
                "directory": str(destination),
            }
        )
    )


if __name__ == "__main__":
    main()

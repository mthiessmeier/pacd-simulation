# Retained evaluator verification: PR #10

Source: https://github.com/mthiessmeier/pacd-simulation/pull/10

Merged: 2026-11-21T20:24:20Z

The top-level README now pins the final Phase 2 evaluator checkout to accepted main `d5a29699e14409bfd54d30c51117c81077639ee6`. It links the acceptance record, checks that the diagnostic manifest names the clean accepted checkout, and includes the commands to replay the register and rebuild the CSV and Parquet summaries. [Evaluator walkthrough](https://github.com/mthiessmeier/pacd-simulation/blob/0a9ac71dff834ef3c781aceb267a73a58835db0a/README.md#reconstruct-inside-the-bounded-workspace)

## Verification

The two evaluator blocks were read from the committed GitHub README at `0a9ac71dff834ef3c781aceb267a73a58835db0a` and executed unchanged in one PowerShell session. The setup created a fresh clone on `reproduce-phase2`. Both the clean checkout and the retained run manifest recorded `d5a29699e14409bfd54d30c51117c81077639ee6`.

One of two registered attempts completed. The planner’s only candidate escalated and there were zero simulated executions. Replaying the pinned register returned the same report. Five independent CLI reads passed, and the regenerated CSV and Parquet files matched both the retained bytes and the accepted Phase 2 hashes. The offline lock check passed. The diff is limited to `README.md`.

Walkthrough receipt SHA-256 `4771e73f7220b5db64aa67dcbb85774be2f2fe45d4a87667bbf29a9b336c2f08`. [Phase 2 acceptance and full-suite results](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861)


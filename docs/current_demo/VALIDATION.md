# Public demonstration validation · 2026-11-22

**Documentation and focused unit checks passed. The four-case public CLI
walkthrough remains unexecuted in this environment.** Its final helper stopped at
the unmodified `doctor` resource check before declaring the attempt register or
launching any diagnostic case. This is a retained preflight failure, not a
successful simulation result.

## Exact checkpoint

| Item | Verified identity |
|---|---|
| Implementation | Merged [PR #22](https://github.com/mthiessmeier/pacd-simulation/pull/22), commit `31c1645ee28a7bbd2488dfb2d354be1fdea3fd25` |
| Producer state | Separate clean checkout on a named branch at that exact commit |
| Runtime | Isolated CPython 3.13.15; committed dependencies installed with `uv sync --frozen` using existing uv 0.13.9 |
| Dependency lock SHA-256 | `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69` |
| Helper SHA-256 | `5eb37dbea1c136e3c95869801c0f7f380df45bfff6e89e34f43f549a34026cfe` |
| Evidence classification | `NON_REPORTABLE_DIAGNOSTIC`; no protocol approval created |

The guide also documents the previously recorded Windows uv 0.12.5 toolchain.
This local preparation used the existing uv 0.13.9 executable and the same frozen
dependency lock. It is not a new cross-platform acceptance claim.

## Checks performed here

| Check | Result and limit |
|---|---|
| Exact producer and package origin | Passed before the helper invoked the public CLI. The producer was clean and its commit matched the pin. |
| Unmodified public `doctor` | **11 of 12 checks passed; exit 1.** Only `host_resources` failed. The native workspace had 4,509,523,968 bytes free, about 4.2 GiB; the implementation requires at least 20 GiB. |
| Helper failure retention | Exit 1 with `failure.json`, command records, stdout and stderr retained. No attempt register, diagnostic run, completed metrics report or success summary was produced. |
| Focused existing unit regressions | **49 passed in 0.53 seconds** across review briefs, approval burden, mission impact and review routing. These unit tests do not substitute for the blocked public CLI walkthrough. |
| Helper syntax, Ruff lint and formatting | Passed after import ordering and formatting corrections. |
| Original-source reconciliation validator | Passed: **558 source units, 47 metric IDs, 18 workstreams and 16 work packages**. |
| Independent documentation review | Guide/helper, architecture and progress records reviewed against the merged source. No blocking issue found; the resource-blocked execution remains explicitly outstanding. |

The unit command, run in the pinned producer's environment, was:

```text
python -m pytest tests/unit/test_review_brief.py tests/unit/test_approval_burden.py tests/unit/test_mission_impact.py tests/unit/test_review_routing.py -q -p no:cacheprovider --basetemp=<new-workspace-temporary-directory>
```

The reconciliation command used the unchanged validator and the original supplied
handoff package:

```text
python docs/work_orders/check_reconciliation.py <original-PACD_Codex_Handoff_v1.0-directory>
```

The [sanitized machine-readable record](validation_2026-11-22.json) includes the
check results and retained log digests. Full command records and host-local paths
remain in the task's local evidence directory. Their hashes identify those records;
they do not make the private raw records publicly available.

## Resource finding and remaining reproduction step

The native home workspace is on a roughly 4.9 GiB filesystem. The initial setup
free-space observation was taken on a different filesystem, so it did not satisfy
the required target-workspace preflight. The isolated environment had already been
prepared when the public doctor exposed that mismatch. No further installation,
cleanup, remount, home-directory substitution or guard change was performed.
Future setup must check space on the actual native workspace before installation.

Run the [documented walkthrough](README.md) on a workspace that passes the existing
doctor, then retain the four verified runs, the five-slot register, the two matching
registered reads, artifact inventories and `summary.json`. Review them before
adding an observed-results record. Preserve this blocked attempt as part of the
history. The expected numeric observations in the guide are derived from merged
fixture contracts and tests; they have not been newly observed in four public CLI
runs here. No new run IDs, semantic hashes or completion fraction are claimed.

Historical full-suite figures in [CURRENT_PROGRESS.md](../../status/CURRENT_PROGRESS.md)
are attributed to their public PR records. Those suites were not rerun here.

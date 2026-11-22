# Current public demonstration: guarded execution and its consequences

This demonstration exercises the implementation through merged **PR #22**, at
commit [`31c1645ee28a7bbd2488dfb2d354be1fdea3fd25`](https://github.com/mthiessmeier/pacd-simulation/commit/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25).
It follows synthetic evidence through a defender proposal, independent authorization,
a simulated review queue, execution, state verification, and consequences for
observability or mission availability. PR #21 contributes the operator decision
brief; PR #22 contributes approval-wait accounting.

All outputs remain **`NON_REPORTABLE_DIAGNOSTIC`**. These small fixtures demonstrate
implemented behavior and evidence handling. They do not establish operational
effectiveness, real-world safety, generalization, calibrated human burden, or a
comparative advantage for PACD. The reportable-mode interlock remains denied.

## What this walkthrough shows

The helper invokes the existing public CLI for four diagnostic runs at seed
`424242`. It declares all five attempt slots before launching anything. The fifth
slot deliberately remains unlaunched, preserving an incomplete outcome and null
metrics in the registered report.

| Case | Shipped scenario / defender | Expected verified observation |
|---|---|---|
| Guarded isolation and mission impact | `diagnostic_review_brief_isolation` / `static_review` | One verified isolation. The core mission loses four ticks of availability; the auxiliary mission stays available. Criticality-weighted loss is **3.2** out of **8** possible weighted ticks, or **0.4**. |
| Sensing change and freshness | `diagnostic_review_brief_sensing` / `sensing_contextual` | One verified sensing-profile switch, costing **0.25**. Delivered signal precision changes from **0.9** to **0.86**. Candidate evidence is fresh at referral; its reference is stale by execution. Mission loss is **0**. |
| Review routing under contention | `diagnostic_review_contention` / `static_review` | Two escalations compete for one review slot. One obtains a terminal review outcome and one encounters the capacity limit: routing completeness **1/2**. |
| Approval waiting and pending work | `diagnostic_review_burden` / `static_review` | Two admitted requests accumulate **7 request-ticks**: one resolves after **4 ticks**, while one is still pending after **3 ticks** at the horizon. Mean resolved wait is **4 ticks**; the pending request remains visible. |
| Declared, unlaunched attempt | `reserved-unlaunched` | `INCOMPLETE`, with `metrics: null`, `metrics_sha256: null`, and no run ID. Completion accounting is **4/5**, not 4/4. |

The isolation, sensing, and burden fixtures include `operator-preview-v1` briefs
at queue admission. A brief binds the proposed action, target, rationale, delivered
reading, evidence age, and a conditional immediate mission-availability preview.
For isolation, that preview exposes the core-mission interruption before execution.
`compromise_probability` remains **null** because no calibrated estimator exists.
The preview assumes later authorization and otherwise unchanged submission state;
the governor still rechecks the action at dispatch.

The sensing profile changes the rounding precision of a synthetic signal; it does
not train a detector or demonstrate a change in detection accuracy. In this fixture,
the prior reference is two ticks old at referral and four ticks old at execution;
the freshness limit is three ticks. CAL-006 records that change. The existing
fixture still executes under its implemented authorization rules, so this is a
visible freshness limitation, not evidence that stale support is automatically
rejected.

GOV-002 keeps capacity-limited and pending escalations in its denominator. OPS-003
measures simulated queue waiting, not staff work hours. At this exact revision,
`override_count` is **null** with `override_status: "unsupported"`; an unmerged
proposal is not counted as an implemented capability.

See the [retained preflight and validation record](VALIDATION.md) for the checks
performed during this documentation update. The public CLI walkthrough stopped at
the unmodified doctor's free-space gate before any diagnostic case was launched.
The observations above are expected fixture results, not a new four-run measurement
from this environment; they are encoded as explicit checks in [the helper](run_demo.py).

## Reproduce from a clean producer checkout

Use two checkouts: the **documentation checkout** contains this guide and helper;
the separate **producer checkout** contains the exact implementation commit above.
The helper did not exist at that earlier commit. Running it externally avoids
editing the producer or misidentifying its source revision.

Read [AGENTS.md](../../AGENTS.md) first. Reuse compatible installed tools, or install
an isolated side-by-side toolchain from official sources with the required local
installation record. The recorded Windows toolchain uses **uv 0.12.5** and
**CPython 3.13.15**. The unmodified `doctor` requires that exact Python patch version,
the frozen dependency declarations, a named Git branch, sufficient disk space, and
the workspace boundary. Do not change the source or bypass a failed check.

The public CLI requires a producer beneath the native user home workspace:

```text
<native user home>/PACD-Workspaces/PACD-Simulation/repo/<new producer checkout>
```

Keep at least **20 GiB free on the filesystem containing the actual native
workspace** before installation. This walkthrough remains within the repository's
5 GB installation/download and 2 GB diagnostic-output budgets.
Use a new producer path and a new virtual environment; retain existing checkouts,
environments, and run records. Work in a quiet local workspace so concurrent runs
do not interfere with the no-allocation check for denied reportable mode.

### Windows PowerShell

Start in the documentation checkout containing this file. Use the existing verified
uv executable below, or set `$uv` to another separately verified workspace-local
uv 0.12.5 executable. These commands create fresh subdirectories and a new local
branch. They do not modify the documentation checkout's tracked files.

```powershell
$ErrorActionPreference = 'Stop'
$docs = (Get-Location).Path
$helper = Join-Path $docs 'docs\current_demo\run_demo.py'
if (!(Test-Path $helper)) { throw 'Start in the documentation checkout' }
$revision = '31c1645ee28a7bbd2488dfb2d354be1fdea3fd25'
$w = Join-Path $env:USERPROFILE 'PACD-Workspaces\PACD-Simulation'
$tag = [Guid]::NewGuid().ToString('N')
$producer = Join-Path $w "repo\current-demo-$tag"
$branch = "reproduce/public-pr22-$tag"
$uv = Join-Path $w 'var\cache\tools\uv\0.12.5\uv.exe'
if (!(Test-Path $uv)) { throw 'Provide the verified workspace-local uv executable first' }
& $uv --version
if ($LASTEXITCODE) { throw 'uv could not be executed' }

$env:UV_CACHE_DIR = Join-Path $w "var\cache\demo-$tag\uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $w "var\cache\demo-$tag\python"
$env:TEMP = Join-Path $w "var\tmp\setup-$tag"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -ErrorAction Stop | Out-Null
& git -C $docs worktree add -b $branch $producer $revision
if ($LASTEXITCODE) { throw 'Pinned producer checkout could not be created' }
Set-Location $producer
& $uv python install 3.13.15
if ($LASTEXITCODE) { throw 'Isolated Python installation failed' }
& $uv sync --frozen --python 3.13.15
if ($LASTEXITCODE) { throw 'Frozen environment installation failed' }
& $uv run --frozen --no-sync python $helper --producer $producer
if ($LASTEXITCODE) { throw 'Demonstration failed; inspect its retained failure record' }
```

If the required interpreter and package cache already exist, reuse their verified
locations and use `uv sync --frozen --offline --python 3.13.15`; no new download is
then needed. Do not remove or replace an earlier runtime to make this work. The
environment variables above apply to the current shell only.

### POSIX shell

The same CLI can run in a compatible Linux or macOS environment. Start in the
documentation checkout and provide an already verified `uv` executable. These
steps preserve the native home directory; they do not redefine `HOME`.

```bash
set -e
docs="$PWD"
helper="$docs/docs/current_demo/run_demo.py"
test -f "$helper"
revision='31c1645ee28a7bbd2488dfb2d354be1fdea3fd25'
w="$HOME/PACD-Workspaces/PACD-Simulation"
tag="$(date -u +%Y%m%dT%H%M%SZ)-$$"
producer="$w/repo/current-demo-$tag"
branch="reproduce/public-pr22-$tag"
uv --version
export UV_CACHE_DIR="$w/var/cache/demo-$tag/uv"
export UV_PYTHON_INSTALL_DIR="$w/var/cache/demo-$tag/python"
export TMPDIR="$w/var/tmp/setup-$tag"
mkdir -p "$TMPDIR"
git -C "$docs" worktree add -b "$branch" "$producer" "$revision"
cd "$producer"
uv python install 3.13.15
uv sync --frozen --python 3.13.15
uv run --frozen --no-sync python "$helper" --producer "$producer"
```

For a new reviewer, obtain the documentation checkout from the public repository
under a separate, unused child of the same workspace's `repo` directory. Select
the documentation revision being reviewed, then use the commands above to create
the clean producer at the immutable implementation pin. A detached producer HEAD
does not satisfy the current doctor; the commands deliberately create a named
local branch.

## What the helper checks and retains

The [standard-library driver](run_demo.py) calls `python -m pacd_sim.cli` using the
producer's isolated interpreter. It does not import internal harness functions,
change configuration, replace validators, patch workspace policy, or create an
author-approved freeze record or `APPROVAL.json`. Its checks cover:

1. Exact Python version, installed package origin, a clean producer at the pinned
   commit, and an unmodified successful `doctor` run.
2. A five-attempt register written before the first launch, with a pinned canonical
   register digest used in subsequent reads.
3. Four public `diagnostic` invocations, each followed by `verify`, opt-in `metrics`,
   and `evidence-trace`. Every manifest must identify the same clean producer.
4. The expected observations above, including review briefs read from raw rows
   only after their retained run passes public verification.
5. Exact agreement between each individual metrics object and its registered
   counterpart, four completed attempts plus one incomplete attempt, and null
   measurements for that unlaunched slot.
6. Identical results and report hashes when the same retained register is read
   twice; unchanged retained run files and receipts; and a still-clean producer.
7. Exit code 3 and `DENIED` for a `--reportable` request, with no new retained run
   directory allocated by that request.

Command arguments, exit codes, stdout, stderr, the register, verified extracts,
artifact inventories, and `summary.json` are retained in a fresh directory:

```text
<workspace>/var/tmp/current-demo-<unique identifier>/
```

The simulator retains complete raw records, manifests, hashes, and local receipts
in its normal workspace locations. `summary.json` gives each run directory and
the relevant hashes. It contains host-local paths; inspect and sanitize those
before sharing it publicly. A failure writes `failure.json` and preserves whatever
evidence has already been produced. It never converts failed or unfinished work
into a successful measurement.

The same retained register should give the same report digest on rereading. A
fresh invocation uses new invocation IDs, run IDs, and timestamps, so its overall
registered report digest is not expected to equal an earlier invocation's digest.
This walkthrough checks stable rereading, not a second-run replay experiment.

To inspect a particular retained run independently, use the producer environment:

```text
python -m pacd_sim.cli verify <run-directory> --show-event-sequence
python -m pacd_sim.cli evidence-trace <run-directory>
python -m pacd_sim.cli metrics <run-directory> --sensing-freshness --mission-impact --review-routing --approval-burden
```

Run these commands from the same clean producer environment and keep its local
receipts. Execution identity assurance has a cooperative local threat model;
see [its documented boundary](../EXECUTION_IDENTITY_ASSURANCE.md).

## Scope and historical context

Current defenders are coded policies, the opponent is scripted, and the reviewer
is simulated. Mission dependencies and criticalities are synthetic inputs. This
registered walkthrough uses different fixtures to expose distinct capabilities;
it is not a controlled cross-condition comparison or a reportable study. The
remaining implementation and research obligations are tracked in the
[scope ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv) and
[implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md).

The [historical Phase 2 demonstration](../application_demo/README.md) remains
unchanged. Its earlier proposal-and-escalation example, including zero executions,
describes that earlier checkpoint. This current guide supplies a separate pinned
walkthrough of the later guarded execution, sensing, mission, and oversight work.

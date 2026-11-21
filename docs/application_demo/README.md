# Reproduce the PACD identity diagnostic

An action proposal has no authority to change a session on its own. This work sample follows a scripted isolation proposal through a policy decision, an in-memory execution broker and an exact-state verifier. It also records the disposition of two configured probes. The governing question for the schema change is whether valid inputs still produce the accepted diagnostic while invalid inputs fail before a run is allocated.

The accepted bootstrap supplied the scenario, actors, broker, verification, receipts and raw-to-derived metrics. This candidate adds typed contracts for the five configuration documents and for the audit row, metric counts, episode summary and run manifest. See [schema contracts](../../schemas/README.md), the [architecture map](../ARCHITECTURE.md) and the [project preflight](../../status/PHASE2_INCREMENT1.md).

## Setup

Use PowerShell in an authorized Windows workspace with the verified uv executable, managed Python 3.13.15 and the accepted package cache. An independent reviewer can clone the private branch into a new, unused child of `$w\repo`, then select the exact commit in the review packet. Run the following from that checkout. The repository's README describes the original tool provenance and workspace layout.

```powershell
$w = Join-Path $env:USERPROFILE 'PACD-Workspaces\PACD-Simulation'
$uv = Join-Path $w 'var\cache\tools\uv\0.12.5\uv.exe'
$env:PATH = "$(Split-Path -Parent $uv);$env:PATH"
$env:UV_CACHE_DIR = Join-Path $w 'var\cache\uv-project'
$env:UV_PYTHON_DOWNLOADS = 'never'
$env:TEMP = Join-Path $w 'var\tmp'
$env:TMP = $env:TEMP
& $uv lock --check --offline --no-cache --prerelease disallow
& $uv sync --frozen --offline --python 3.13.15
& $uv run --frozen --no-sync pacd-sim doctor --workspace-root $w
```

## Produce and replay

Each invocation allocates a separate retained directory. Check the exit status of each command. A current local receipt is required for execution identity assurance.

```powershell
$first = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $w --seed 424242 | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'First diagnostic failed' }
$replay = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $w --seed 424242 | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'Replay failed' }
& $uv run --frozen --no-sync pacd-sim verify $first.run_dir --workspace-root $w
if ($LASTEXITCODE) { throw 'First verification failed' }
& $uv run --frozen --no-sync pacd-sim verify $replay.run_dir --workspace-root $w
if ($LASTEXITCODE) { throw 'Replay verification failed' }
if ($first.raw_semantic_hash -ne $replay.raw_semantic_hash -or
    $first.summary_semantic_hash -ne $replay.summary_semantic_hash) { throw 'Replay differs' }
```

## Rebuild the summary from retained raw records

This separate command verifies the completed run, calls the existing raw-Parquet summarizer, writes fresh CSV and Parquet under `var/tmp`, and compares each regenerated file's SHA-256 with the retained original.

```powershell
& $uv run --frozen --no-sync python docs/application_demo/regenerate.py $first.run_dir
```

For the schema demonstration, run the contract and compatibility checks from the same environment. Use a new short directory name for each pytest invocation, because pytest clears its designated base temporary directory on startup.

```powershell
$fresh = Join-Path $w ('t\i1-' + [guid]::NewGuid().ToString('N').Substring(0,8))
& $uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp $fresh -q tests/unit/test_governed_configuration.py tests/unit/test_diagnostic_records.py tests/reproducibility/test_diagnostic_replay.py::test_v1_schema_migration_preserves_accepted_diagnostic
```

The accepted fixture uses two identities, one session, a service and one mission. The governor binds a decision to its policy, target and pre-state. The verifier checks the intended isolated session state. The defender context in this diagnostic includes immutable environment state and beliefs. A research comparison first needs an explicit observation-only interface and a documented ground-truth boundary.

Output classification is `NON_REPORTABLE_DIAGNOSTIC`. A local run shows how these components behave for one scripted case. A request left pending for human review has a visible completion cost. Mission harm and false-positive rates have no defined denominator in this fixture. The dated local reviewer packet contains the per-action trace, exact results, audit advisories and review disposition.

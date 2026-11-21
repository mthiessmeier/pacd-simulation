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

## Inspect the scripted event sequence

In the same checkout that produced the run, ask the verifier to release the
source events in the order their observations were recorded.

```powershell
$verified = & $uv run --frozen --no-sync pacd-sim verify $first.run_dir --workspace-root $w --show-event-sequence | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'Verification failed' }
$verified.event_sequence.events | Format-Table tick, id, kind, identity_id
$verified.event_sequence.sha256
```

The table uses source ticks. The shipped sensor records each observation one
tick later. The digest binds the format identifier `pacd-scripted-events-v1`
and the ordered list of event IDs, source ticks, kinds and nullable identity
IDs. It excludes the seed, sensor signal, actions and outcomes, so two verified
runs can share a script while their raw evidence differs. The verifier checks
the full retained evidence and the local execution receipt before returning
this view. The existing fixture gives its diagnostic classifier the event kind.
This demonstration makes no blinded comparison.

## Replay the maintenance-window fixture

The second governed scenario brackets a synthetic indicator on the user session
with two benign events on the administrator identity. The sessions share a service.
With the two-tick sensor delay, source ticks 3, 6 and 9 appear in the audit at
ticks 5, 8 and 11. The maintenance control checks the administrator's classification
and session state on both sides of the user's isolation.

```powershell
$scenario = 'configs/scenarios/diagnostic_maintenance_window.yaml'
$pair = foreach ($i in 1..2) {
    $run = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $w --scenario $scenario --seed 424242 | ConvertFrom-Json
    if ($LASTEXITCODE) { throw 'Maintenance diagnostic failed' }
    $check = & $uv run --frozen --no-sync pacd-sim verify $run.run_dir --workspace-root $w --show-event-sequence | ConvertFrom-Json
    if ($LASTEXITCODE -or !$check.valid) { throw 'Maintenance verification failed' }
    $check
}
$pair[0].event_sequence.events | Format-Table tick, id, kind, identity_id
if ($pair[0].event_sequence.sha256 -ne $pair[1].event_sequence.sha256 -or
    $pair[0].raw_semantic_hash -ne $pair[1].raw_semantic_hash -or
    $pair[0].summary_semantic_hash -ne $pair[1].summary_semantic_hash) { throw 'Replay differs' }
& $uv run --frozen --no-sync python docs/application_demo/regenerate.py $pair[0].run_dir
if ($LASTEXITCODE) { throw 'Maintenance summary regeneration failed' }
```

The verifier finds the governed scenario by matching the manifest's scenario
digest to a checked-in file. It also checks the entire retained configuration,
the reconstructed event rows and the local receipt. The same `verify` command
works for both fixtures. Event kinds are scripted labels visible to this
diagnostic's classifier. The benign control shows what happened in this episode.

## Rebuild the summary from retained raw records

This command derives one summary from the raw Parquet table held by the bounded verifier. After verification succeeds, it serializes that row, checks both output hashes against the verified artifact digests and writes fresh CSV and Parquet under `var/tmp`.

```powershell
& $uv run --frozen --no-sync python docs/application_demo/regenerate.py $first.run_dir
```

For the schema demonstration, run the contract and compatibility checks from the same environment. Use a new short directory name for each pytest invocation, because pytest clears its designated base temporary directory on startup.

```powershell
$fresh = Join-Path $w ('t\i1-' + [guid]::NewGuid().ToString('N').Substring(0,8))
& $uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp $fresh -q tests/unit/test_governed_configuration.py tests/unit/test_diagnostic_records.py tests/reproducibility/test_verified_regeneration.py tests/reproducibility/test_diagnostic_replay.py::test_v1_schema_migration_preserves_accepted_diagnostic
```

The accepted fixture uses two identities, one session, a service and one mission. The governor binds a decision to its policy, target and pre-state. The verifier checks the intended isolated session state. The defender context in this diagnostic includes immutable environment state and beliefs. A research comparison first needs an explicit observation-only interface and a documented ground-truth boundary.

Output classification is `NON_REPORTABLE_DIAGNOSTIC`. A local run shows how these components behave for one scripted case. A request left pending for human review has a visible completion cost. Mission harm and false-positive rates have no defined denominator in this fixture. The dated local reviewer packet contains the per-action trace, exact results, audit advisories and review disposition.

## Reproduce a mission interruption and continued service

The integration check runs the identity fixture with a positive session-to-service
dependency. It exercises the same isolation a second time with an additional
service assigned to the mission. Both variants retain a verified action and its
linked `mission_effect` record. These checks use temporary fixture checkouts.

```powershell
$fresh = Join-Path $w ('t\mission-' + [guid]::NewGuid().ToString('N').Substring(0,8))
& $uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp $fresh -q tests/reproducibility/test_diagnostic_replay.py::test_verified_mission_effect_tracks_actual_session_isolation
```

For a retained CLI demonstration, use a fresh workspace-local fixture checkout,
apply the [opt-in scenario fields](../../schemas/README.md#opt-in-availability-and-mission-continuity)
to its governed scenario and commit that configuration in the fixture checkout.
Use the produce, verify and regenerate commands above. For the redundant-service
case, add a second service with its own ID and the same `mission_id`.
The before/after counts and the transition classification are in
`raw/events.jsonl` and `raw/events.parquet`. The effect is linked to the
corresponding verification and execution by ID.

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

## Replay a static defense baseline

From the checkout that produced a retained run, evaluate a fixed triage rule
on its verified observations. The command below uses the maintenance run
created above.

```powershell
$report = & $uv run --frozen --no-sync pacd-sim baseline $pair[0].run_dir --workspace-root $w | ConvertFrom-Json
if ($LASTEXITCODE -or !$report.valid) { throw 'Baseline replay failed' }
$report.baseline.decisions | ConvertTo-Json -Depth 5
```

The baseline receives the delivery tick, observed subject ID and sensor signal
one observation at a time. At a signal of 0.75 or higher it proposes
`require_human_review` for an identified subject. Otherwise it abstains.
The v1 wire value `synthetic-unknown` represents a missing subject. A literal
ID with the same spelling also produces an abstention. Event kind, source
event ID, environment state, beliefs and later observations are outside the
policy input. The output includes the rule version and a canonical SHA-256
digest of its ordered inputs.

The `baseline` command reports the fixed rule's decisions on a completed run.
Use the following diagnostic to observe how the governor handles the same
rule's proposals as each synthetic reading arrives.

## Run the static rule prospectively

From the checkout and workspace configured above, produce two independent
invocations per scenario. Each verification reconstructs the scripted events,
sensor readings, decisions, and governed state from the selected inputs.

```powershell
$baseline = 'configs/defenders/static_review.yaml'
foreach ($name in 'diagnostic_identity_smoke', 'diagnostic_maintenance_window') {
    $scenario = "configs/scenarios/$name.yaml"
    $pair = foreach ($i in 1..2) {
        $run = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $w --scenario $scenario --baseline $baseline --seed 424242 | ConvertFrom-Json
        if ($LASTEXITCODE) { throw "Diagnostic failed for $name" }
        $check = & $uv run --frozen --no-sync pacd-sim verify $run.run_dir --workspace-root $w --show-event-sequence | ConvertFrom-Json
        if ($LASTEXITCODE -or !$check.execution_identity_assured) { throw "Verification failed for $name" }
        $check
    }
    if ($pair[0].run_dir -eq $pair[1].run_dir -or
        $pair[0].raw_semantic_hash -ne $pair[1].raw_semantic_hash -or
        $pair[0].summary_semantic_hash -ne $pair[1].summary_semantic_hash -or
        $pair[0].event_sequence.sha256 -ne $pair[1].event_sequence.sha256) { throw "Replay differs for $name" }
    & $uv run --frozen --no-sync pacd-sim baseline $pair[0].run_dir --workspace-root $w
    if ($LASTEXITCODE) { throw "Rule replay failed for $name" }
    & $uv run --frozen --no-sync python docs/application_demo/regenerate.py $pair[0].run_dir
    if ($LASTEXITCODE) { throw "Regeneration failed for $name" }
}
```

The identity fixture delivers observations at ticks 2 and 3. The maintenance
fixture delivers them at ticks 5, 8 and 11. With seed 424242, the rule requests
human review on the second observation in each fixture and abstains on the
others. Each `baseline_decision` in `raw/events.jsonl` binds its outcome to
the sensor input digest and any resulting candidate. The common governor
returns `ESCALATE`. The verification records equal before/after state digests,
and the audit records zero executions. Human completion times, resource
budgets and comparative performance are outside these diagnostic runs.

## Trace the Increment 5 PACD planner

The planner asks whether the same observed subject produced an elevated
signal on two distinct delivery ticks. Replay it on a verified run from
any governed fixture or defender condition. From the checkout and frozen
environment that produced `$first`, use the following commands.

```powershell
$result = & $uv run --frozen --no-sync pacd-sim defender-trace $first.run_dir --workspace-root $w | ConvertFrom-Json
if ($LASTEXITCODE -or !$result.execution_identity_assured) { throw 'Defender trace failed verification' }
$result.defender_trace.decisions | ConvertTo-Json -Depth 5
$result.defender_trace.trace_sha256
```

The planner receives one delivery tick, observed subject and sensor signal at
a time. A reading at or above 0.75 starts a pending episode for that subject.
A second elevated reading on a distinct tick within three ticks proposes human
review. Each elevated reading refreshes the window. After referral, further
elevated readings in the same episode suppress duplicate proposals. A lower
same-subject signal or a gap longer than three ticks clears the episode.
Missing subjects abstain. The trace records the prior qualifying tick when
available, the decision and any proposal. Its digest binds the policy version,
rule settings, ordered readings and decisions.

The identity smoke and maintenance fixtures each have a single elevated reading for their user at the two
registered seeds. A reviewer can see the planner wait for more evidence and
the episode end without a referral. This illustrates the cost of requiring
confirmation. The threshold and window are diagnostic design choices. The
command reads verified evidence and keeps the source run's decisions and
state transitions intact.

## Run the PACD planner under the shared governor

Select `configs/defenders/pacd_corroborated_review.yaml` to run a fresh
planner inside each diagnostic. Each delivered reading produces a
`defender_decision` in the audit before the next sensor reading is generated.
A proposal creates one human-review candidate for the shared governor.

```powershell
$policy = 'configs/defenders/pacd_corroborated_review.yaml'
foreach ($case in 'identity_smoke', 'maintenance_window', 'repeated_readings') {
    $scenario = "configs/scenarios/diagnostic_$case.yaml"
    $pair = foreach ($i in 1..2) {
        $run = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $w --scenario $scenario --baseline $policy --seed 424242 | ConvertFrom-Json
        if ($LASTEXITCODE) { throw "Diagnostic failed for $case" }
        $verified = & $uv run --frozen --no-sync pacd-sim verify $run.run_dir --workspace-root $w --show-event-sequence | ConvertFrom-Json
        if ($LASTEXITCODE -or !$verified.execution_identity_assured) { throw "Verification failed for $case" }
        $trace = & $uv run --frozen --no-sync pacd-sim defender-trace $run.run_dir --workspace-root $w | ConvertFrom-Json
        if ($LASTEXITCODE -or !$trace.valid) { throw "Defender replay failed for $case" }
        [pscustomobject]@{Run=$run; Events=$verified.event_sequence.sha256; Trace=$trace.defender_trace.trace_sha256}
    }
    if ($pair[0].Run.run_id -eq $pair[1].Run.run_id -or
        $pair[0].Run.raw_semantic_hash -ne $pair[1].Run.raw_semantic_hash -or
        $pair[0].Run.summary_semantic_hash -ne $pair[1].Run.summary_semantic_hash -or
        $pair[0].Events -ne $pair[1].Events -or $pair[0].Trace -ne $pair[1].Trace) { throw "Replay differs for $case" }
    & $uv run --frozen --no-sync python docs/application_demo/regenerate.py $pair[0].Run.run_dir
    if ($LASTEXITCODE) { throw "Regeneration failed for $case" }
}
```

The repeated-reading YAML is the exact fixture from the earlier reviewer
demonstration, now selectable from the same checkout. At seed 424242 the two
elevated readings at tick 3 leave the planner waiting. The tick-4 reading
produces `action-pacd-review-4`. The governor returns `ESCALATE` and
verification records equal before/after state digests. Tick 5 records
`already_referred`. To inspect the action, filter `raw/events.jsonl`
on that action ID and on `event_type == "defender_decision"` for the five
decisions. The fixture ends with one pending human review and zero executions.

## Inspect one episode's disposition metrics

From the checkout that produced the diagnostic, run the following read-only
command on its retained directory. The verifier checks the local receipt and
reconstructs the episode summary from the same raw event snapshot before the
CLI releases any metric.

```powershell
$report = & $uv run --frozen --no-sync pacd-sim metrics $first.run_dir --workspace-root $w | ConvertFrom-Json
if ($LASTEXITCODE -or !$report.execution_identity_assured) { throw 'Episode metrics unavailable' }
$report.run_id
$report.metrics | ConvertTo-Json -Depth 4
$report.metrics_sha256
```

The `pacd-episode-dispositions-v1` view counts candidate actions, each
governor disposition, simulated executions, verified executions, and executions
linked to a prohibited action. The escalation fraction divides the count of
`ESCALATE` decisions by all candidate actions in that episode. Every
candidate must have one disposition. With zero candidates the counts remain
zero and the fraction value is JSON `null`. A valid episode with candidates
and zero escalations has value 0. Prohibited executions remain visible as an
absolute count for the verified run ID.

At seed 424242 the original identity diagnostic has one escalation among
three candidates. The PACD planner has zero candidates on identity smoke
and one escalation on one candidate in repeated readings. The static
condition escalates four of four on those same repeated readings. These
fractions describe the governor's decisions in the scripted episode.
Human review duration and completion are unmeasured.

The top-level `metrics_sha256` covers the entire `metrics` object, including
its format, configuration hash and seed. Distinct invocations have distinct
run IDs and may reproduce the same metric digest. The verification report
also carries the raw and summary semantic hashes. Incomplete, failed,
corrupt or unauthenticated input returns a nonzero exit and no metrics.
The original attempt remains available for inspection.

## Account for a registered set of attempts

An evaluator can declare up to 100 attempts in a workspace-local UTF-8 JSON
file before the first run. The [top-level walkthrough](../../README.md#run-the-diagnostic)
creates a register, records its digest, runs one slot and replays the set.
The version is `pacd-attempt-register-v1`. Each row names one unique
`attempt_id` (lowercase letter first, up to 64 letters, digits, underscores
or hyphens), one unique 32-character lowercase hexadecimal `invocation_id`,
and its nonnegative integer seed. The register is limited to 64 KiB.

Use `pacd-sim metrics --register FILE` to read the canonical
`register_sha256`. Retain that digest before launching any diagnostics.
Pass the registered invocation ID and seed to `diagnostic`. Supply
`--register-sha256 DIGEST` on later set reads. Changing membership, order,
IDs or seeds changes the digest. A retry needs a fresh invocation ID and a
separate slot. The ordinary diagnostic still generates a fresh ID by default.

| Row status | Evidence and treatment |
| --- | --- |
| COMPLETED | Full content and execution-receipt verification succeeded. The row exposes the single-run metric object and its digest. |
| FAILED | The parent-owned final directory contains a retained failure declaration. The row names the error type. |
| TIMED_OUT | The retained failure type is `DiagnosticTimeoutError`. |
| INCOMPLETE | No invocation was observed, allocation or staging is unfinished, or the bound run lacks a terminal record. The reason distinguishes these cases. |
| INVALID | Evidence is corrupt, contradictory or fails its binding, including a completed status with a missing or invalid receipt. |

Each declared attempt gets one row in register order. A failure declaration
has local ownership evidence and carries no success receipt. Every row outside
COMPLETED has null episode metrics. Failure after raw events have been written
still leaves their outcomes unmeasured. Missing evidence cannot distinguish
an attempt that never launched from one that failed before allocation.

The completion fraction is verified completions divided by all registered
attempts. The observed escalation fraction is the sum of escalations divided
by the sum of candidate actions in verified episodes. The absolute counts,
including prohibited executions, remain visible by run ID. With no verified
episodes the observed counts are null. A verified episode with zero
candidates contributes observed zeros, and any zero-denominator fraction has
a null value. A valid accounting report exits zero even if it contains an
INVALID row. Check the status counts to determine completion.

`report_sha256` covers the entire set report except that digest itself,
including invocation identities and the evidence visible at read time.
Re-reading an unchanged set reproduces it. Reading during a run can show
a later status on the next read. The pin identifies membership, order and seeds.
The completed row supplies the observed configuration hash. A reviewer who
needs evidence of when the set was declared must retain the pre-run pin
separately. All results are local synthetic diagnostics.

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

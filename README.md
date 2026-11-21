# PACD Simulation

**Reproduce the current work sample.** The [checkout instructions](#reconstruct-inside-the-bounded-workspace)
pin the Increment 6 implementation at [`5eb554c`](https://github.com/mthiessmeier/pacd-simulation/commit/5eb554c21b008038ecc50d0f7433977bef64ba7a).
The [diagnostic walkthrough](#run-the-diagnostic) registers two attempts and runs
the accepted planner on repeated sensor readings in one. Expect one verified completion
and one incomplete attempt. The completed episode has one escalated candidate and zero executions.

This private repository contains a bounded, local-first, CPU-only PACD simulation environment.
Its current outputs are environment diagnostics only. They do not establish PACD effectiveness,
safety, generalization, operational readiness, or publication readiness.

Every bootstrap run is labeled `NON_REPORTABLE_DIAGNOSTIC`. Reportable mode fails closed unless
an author-approved freeze record matches the exact commit and governed hashes. This bootstrap
does not create that approval record.

## Local execution identity assurance

Bootstrap verification separates retained-content validity from cooperative local execution
identity assurance and from reportability. Its structured result includes these fixed-scope
fields:

```json
{
  "identity_assurance_scope": "LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING",
  "historical_control_file_inode_continuity_assured": false,
  "reportable": false
}
```

`execution_identity_assured=true` means that, at verification time, the retained run and its
configuration and hash bindings match local control records in the exact validated control-store
paths. It is a cooperative local content, path, run, and configuration binding. It is not proof
that a receipt or ownership-marker file has retained the same inode throughout its history. A
byte-identical, singly linked control-file replacement at the same correctly validated lexical path
does not by itself defeat this local binding. Changed bytes or bindings, a changed path, a hard
link, a reparse point, a changed run-directory identity, or a receipt/run/configuration/seed/hash
mismatch must fail assurance.

This bootstrap does not claim author identity or signing, trustworthy external time,
write-once-read-many (WORM) storage, malicious-same-user resistance, cryptographic execution
attestation, or reportable status. See
[Local execution identity assurance](docs/EXECUTION_IDENTITY_ASSURANCE.md) for the complete
contract and interpretation rules.

## Reconstruct inside the bounded workspace

Use Git, authenticated private-repository access and the project's verified
uv 0.12.5, CPython 3.13.15 and frozen package cache. The following PowerShell
block creates a fresh checkout on a named local branch so the doctor can
record the branch and commit.
Begin outside protected Desktop, Documents, Downloads, and redirected equivalents:

```powershell
$WorkspaceRoot = Join-Path $env:USERPROFILE 'PACD-Workspaces\PACD-Simulation'
$Revision = '5eb554c21b008038ecc50d0f7433977bef64ba7a'
$RepoParent = Join-Path $WorkspaceRoot 'repo'
$RepoRoot = Join-Path $RepoParent ('evaluator-i6-' + [guid]::NewGuid().ToString('N').Substring(0,10))
$uv = Join-Path $WorkspaceRoot 'var\cache\tools\uv\0.12.5\uv.exe'
$UvCache = Join-Path $WorkspaceRoot 'var\cache\uv-project'
$PreCommitCache = Join-Path $WorkspaceRoot 'var\cache\pre-commit'
$TaskTemp = Join-Path $WorkspaceRoot ('var\tmp\evaluator-' + [guid]::NewGuid().ToString('N'))
$MatplotlibCache = Join-Path $WorkspaceRoot 'var\cache\matplotlib'

foreach ($DirectoryToCreate in @($RepoParent, $UvCache, $PreCommitCache, $TaskTemp, $MatplotlibCache)) {
    if (-not (Test-Path -LiteralPath $DirectoryToCreate)) {
        New-Item -ItemType Directory -Path $DirectoryToCreate | Out-Null
    }
}

$env:UV_CACHE_DIR = $UvCache
$env:UV_PYTHON_DOWNLOADS = 'never'
$env:PATH = (Split-Path -Parent $uv) + ';' + $env:PATH
$env:PRE_COMMIT_HOME = $PreCommitCache
$env:TEMP = $TaskTemp
$env:TMP = $TaskTemp
$env:MPLCONFIGDIR = $MatplotlibCache

if (Test-Path -LiteralPath $RepoRoot) { throw 'Choose an unused checkout path' }
git clone --no-checkout https://github.com/mthiessmeier/pacd-simulation.git $RepoRoot
if ($LASTEXITCODE) { throw 'Private repository clone failed' }
Set-Location -LiteralPath $RepoRoot
git switch --create reproduce-increment6 $Revision
if ($LASTEXITCODE -or (git rev-parse HEAD) -ne $Revision) { throw 'Reproduction checkout failed' }
& $uv sync --frozen --offline --python 3.13.15
if ($LASTEXITCODE) { throw 'Frozen environment setup failed' }
& $uv run --frozen --no-sync pacd-sim doctor --workspace-root $WorkspaceRoot
if ($LASTEXITCODE) { throw 'Environment verification failed' }
```

The pin includes the complete implementation and its [detailed demo](docs/application_demo/README.md).
The follow-up README commit records that immutable revision. The last accepted
Increment 5 merge is [`9c9dfce`](https://github.com/mthiessmeier/pacd-simulation/commit/9c9dfcec659870c41aa7cc95846d6760d9c31df7).

## Check the lock without network access

The project-level uv policy disallows prerelease packages. This read-only check is self-contained:
it compares `pyproject.toml` with the existing `uv.lock` while network access is disabled and does
not update either file.

```powershell
uv lock --check --offline --no-cache --prerelease disallow
```

## Validate

Keep process caches and test temporary files under the same bounded workspace:

```powershell
uv lock --check --offline --no-cache --prerelease disallow
uv sync --frozen
uv run --frozen --no-sync ruff format --check . --no-cache
uv run --frozen --no-sync ruff check . --no-cache
uv run --frozen --no-sync mypy src tests --no-incremental --cache-dir "$WorkspaceRoot\var\cache\mypy"
uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp "$TaskTemp\pytest" -q
uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp "$TaskTemp\pytest-coverage" --cov=pacd_sim --cov-report=term-missing --cov-report=html
uv run --frozen --no-sync bandit -c pyproject.toml -r src
uv run --frozen --no-sync detect-secrets scan --all-files
uv run --frozen --no-sync pip-audit --local --skip-editable
```

## Run the diagnostic

From the pinned checkout, declare the attempt IDs and their seeds before running
the first slot. The second slot stays open so its contribution to the completion
denominator is visible. Verify the first episode, replay the planner and read both reports.
The diagnostic writes to the authorized workspace's `var/runs` directory.

```powershell
$RunRoot = Join-Path $WorkspaceRoot 'var\runs'
$Invocation = [guid]::NewGuid().ToString('N')
$RegisterPath = Join-Path $TaskTemp 'attempt-register.json'
$Register = @{
    format = 'pacd-attempt-register-v1'
    attempts = @(
        @{attempt_id='repeated-reading'; invocation_id=$Invocation; seed=424242}
        @{attempt_id='reserved-control'; invocation_id=[guid]::NewGuid().ToString('N'); seed=424242}
    )
}
[IO.File]::WriteAllText($RegisterPath, ($Register | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
$Before = & $uv run --frozen --no-sync pacd-sim metrics --register $RegisterPath --workspace-root $WorkspaceRoot | ConvertFrom-Json
if ($LASTEXITCODE -or $Before.status_counts.INCOMPLETE -ne 2) { throw 'Register preflight failed' }
$RegisterPin = $Before.register_sha256
$Diagnostic = & $uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $WorkspaceRoot --output-root $RunRoot --scenario configs/scenarios/diagnostic_repeated_readings.yaml --baseline configs/defenders/pacd_corroborated_review.yaml --seed 424242 --invocation-id $Invocation | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'Diagnostic failed' }
$Verified = & $uv run --frozen --no-sync pacd-sim verify $Diagnostic.run_dir --workspace-root $WorkspaceRoot --show-event-sequence | ConvertFrom-Json
if ($LASTEXITCODE -or !$Verified.execution_identity_assured) { throw 'Run verification failed' }
$Trace = & $uv run --frozen --no-sync pacd-sim defender-trace $Diagnostic.run_dir --workspace-root $WorkspaceRoot | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'Planner replay failed' }
$Trace.defender_trace.decisions | Select-Object outcome, previous_elevated_tick
$Report = & $uv run --frozen --no-sync pacd-sim metrics $Diagnostic.run_dir --workspace-root $WorkspaceRoot | ConvertFrom-Json
if ($LASTEXITCODE -or !$Report.valid) { throw 'Metric verification failed' }
$Report.metrics | ConvertTo-Json -Depth 4
$SetReport = & $uv run --frozen --no-sync pacd-sim metrics --register $RegisterPath --register-sha256 $RegisterPin --workspace-root $WorkspaceRoot | ConvertFrom-Json
if ($LASTEXITCODE -or $SetReport.status_counts.COMPLETED -ne 1 -or $SetReport.status_counts.INCOMPLETE -ne 1) { throw 'Registered attempt accounting failed' }
$SetReport.attempts | Select-Object attempt_id, status, reason
$SetReport.completion_fraction
$SetReport.observed_escalation_fraction
```

The completion fraction is 1/2. The escalation fraction is 1/1 and counts
only candidate actions from verified completions. Re-reading the same register
with its pin reproduces `report_sha256` while the retained evidence is unchanged.
The [set report definition](docs/application_demo/README.md#account-for-a-registered-set-of-attempts)
also covers failed, timed-out and invalid episodes.

Reportable mode is intentionally denied during bootstrap and must not create a run directory:

```powershell
uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $WorkspaceRoot --output-root $RunRoot --scenario configs/scenarios/diagnostic_identity_smoke.yaml --reportable
```

Architecture, evidence boundaries, retained status records, and exact validation outcomes are
documented under `docs/` and `status/`.

# PACD Simulation

This private repository contains a bounded, local-first, CPU-only PACD simulation environment.
Its current outputs are environment diagnostics only. They do not establish PACD effectiveness,
safety, generalization, operational readiness, or publication readiness.

Every bootstrap run is labeled `NON_REPORTABLE_DIAGNOSTIC`. Reportable mode fails closed unless
an author-approved freeze record matches the exact commit and governed hashes. This bootstrap
does not create that approval record.

## Reconstruct inside the bounded workspace

Prerequisites are Git, authenticated private-repository access, and a verified `uv` executable.
Begin outside protected Desktop, Documents, Downloads, and redirected equivalents:

```powershell
$WorkspaceRoot = Join-Path $env:USERPROFILE 'PACD-Workspaces\PACD-Simulation'
$RepoParent = Join-Path $WorkspaceRoot 'repo'
$RepoRoot = Join-Path $RepoParent 'pacd-simulation'
$UvCache = Join-Path $WorkspaceRoot 'var\cache\uv-project'
$PreCommitCache = Join-Path $WorkspaceRoot 'var\cache\pre-commit'
$TaskTemp = Join-Path $WorkspaceRoot 'var\tmp'
$MatplotlibCache = Join-Path $WorkspaceRoot 'var\cache\matplotlib'

foreach ($DirectoryToCreate in @($RepoParent, $UvCache, $PreCommitCache, $TaskTemp, $MatplotlibCache)) {
    if (-not (Test-Path -LiteralPath $DirectoryToCreate)) {
        New-Item -ItemType Directory -Path $DirectoryToCreate | Out-Null
    }
}

$env:UV_CACHE_DIR = $UvCache
$env:PRE_COMMIT_HOME = $PreCommitCache
$env:TEMP = $TaskTemp
$env:TMP = $TaskTemp
$env:MPLCONFIGDIR = $MatplotlibCache

Set-Location -LiteralPath $RepoParent
git clone https://github.com/<account>/pacd-simulation.git pacd-simulation
Set-Location -LiteralPath $RepoRoot
git switch codex/environment-bootstrap-v1
uv python install 3.13.15 --no-bin --no-registry
uv sync --frozen
uv run --frozen --no-sync pacd-sim doctor --workspace-root $WorkspaceRoot
```

The clone command fails rather than replacing an existing destination. Inventory any existing
path before choosing a different versioned child.

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

The output root is restricted to `var/runs` beneath the PACD workspace:

```powershell
$RunRoot = Join-Path $WorkspaceRoot 'var\runs'
$DiagnosticJson = uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $WorkspaceRoot --output-root $RunRoot --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
$Diagnostic = $DiagnosticJson | ConvertFrom-Json
$DiagnosticJson
uv run --frozen --no-sync pacd-sim verify $Diagnostic.run_dir --workspace-root $WorkspaceRoot
```

Reportable mode is intentionally denied during bootstrap and must not create a run directory:

```powershell
uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $WorkspaceRoot --output-root $RunRoot --scenario configs/scenarios/diagnostic_identity_smoke.yaml --reportable
```

Architecture, evidence boundaries, retained status records, and exact validation outcomes are
documented under `docs/` and `status/`.

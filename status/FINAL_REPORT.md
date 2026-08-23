# PACD Environment Bootstrap — Final Report

**Acceptance classification:** Not yet assigned; GH-05 private PR delivery is pending
**Date/time:** 2026-08-23T02:14:55-04:00
**Repository/branch/PR:** private `pacd-simulation` / `codex/environment-bootstrap-v1` / pending
**Workspace root:** `%USERPROFILE%\PACD-Workspaces\PACD-Simulation`
**Evidence label:** `NON_REPORTABLE_DIAGNOSTIC`

## 1. Governing scope

The PACD v1.0 bootstrap package governed this work. Only host/toolchain validation, isolated
repository construction, acceptance testing, and one bounded diagnostic with replay checks were
authorized. No reportable PACD experiment, real target, real telemetry, external scan, production
adapter, cloud compute, inbound port, paid service, or public-license decision was used.

## 2. Host summary

Windows Pro 25H2 x64 supplied 24 logical CPUs, 63.36 GiB RAM, and more than 204 GiB free disk.
The implementation caps workers at 8. The workspace is outside Desktop, Documents, Downloads,
and OneDrive-redirected equivalents.

## 3. Existing software preserved

PowerShell Core 7.6.4, Windows PowerShell 5.1, bundled Git 2.53.0.windows.3, bundled Python
3.12.13, WSL, WindowsApps aliases, browser state, and security controls were not changed.
No existing software was uninstalled, repaired, upgraded, downgraded, replaced, or reconfigured.
Within the scope of actions retained in the command and work logs, no protected-folder content or
pre-existing software was deleted or modified. This statement is explicitly limited to bootstrap
actions and is corroborated by the doctor and path-jail tests, rather than asserted beyond the
available evidence.

## 4. New components installed

| Component | Version | Source/publisher | Scope | Hash/signature evidence | Reason |
|---|---|---|---|---|---|
| GitHub CLI | 2.98.0 | Official GitHub release | Workspace-local portable | SHA-256 `c28c7b3...561eb1`; valid GitHub Authenticode | Private repository delivery |
| uv | 0.12.5 | Official Astral release | Workspace-local portable | SHA-256 `4c4d49d...df39a`; official SLSA provenance | Locked isolated toolchain |
| CPython | 3.13.15 | uv catalog / python-build-standalone | Separate user-scoped managed runtime; no bin/registry | Archive SHA-256 `07c977bb...45e6`; official SLSA provenance | Required stable Python |
| Project environment | 73 packages | Official PyPI plus local project | New repository `.venv` | `uv.lock` SHA-256 `12372a81...f290` | Runtime and assurance tooling |
| Reconstruction environment | same 73 packages | Offline verified cache | New task-local environment | Frozen lock; 108 tests passed | Clean reconstruction gate |

Exact sources, hashes, versions, and declared licenses are retained in
`SOURCE_AND_DOWNLOAD_HASHES.txt`, `INSTALLED_COMPONENTS.json`, and
`status/DEPENDENCY_INVENTORY.json`. No legal-sufficiency conclusion is made.

## 5. Repository and architecture delivered

The private repository contains a typed Python package with strict schemas; synthetic telemetry,
evidence, state, hypotheses, candidate actions, defenders, independent safety governance,
simulated-only execution, verification/rollback, audit/metrics, deterministic harness, doctor,
closed-world verifier, reportable interlock, documentation, and acceptance tests. Harness,
defender, safety, execution, and metrics boundaries are independent. No GitHub Actions workflow,
public/open-source license grant, production adapter, or approval marker exists.

## 6. Setup, doctor, tests, diagnostic, verification, and reconstruction commands

```powershell
$WorkspaceRoot = Join-Path $env:USERPROFILE 'PACD-Workspaces\PACD-Simulation'
$Repository = Join-Path $WorkspaceRoot 'repo\pacd-simulation'
$Uv = Join-Path $WorkspaceRoot 'var\cache\tools\uv\0.12.5\uv.exe'
$env:UV_CACHE_DIR = Join-Path $WorkspaceRoot 'var\cache\uv-project'
Set-Location $Repository

# Setup and doctor
& $Uv sync --frozen
& $Uv run --frozen --no-sync pacd-sim doctor --workspace-root $WorkspaceRoot

# Quality and test gates
$TaskTemp = Join-Path $WorkspaceRoot ('var\tmp\acceptance-' + [guid]::NewGuid().ToString('N'))
& $Uv run --frozen --no-sync ruff format --check . --no-cache
& $Uv run --frozen --no-sync ruff check . --no-cache
& $Uv run --frozen --no-sync mypy src tests --no-incremental --cache-dir (Join-Path $TaskTemp 'mypy')
& $Uv run --frozen --no-sync pytest -p no:cacheprovider --basetemp (Join-Path $TaskTemp 'pytest') -q
& $Uv run --frozen --no-sync bandit -c pyproject.toml -r src
$SecretExclude = '(^|[\\/])(uv\.lock|status[\\/](DEPENDENCY_INVENTORY|VULNERABILITY_AUDIT|SOURCE_AND_DOWNLOAD_HASHES|DIAGNOSTIC_RUN_REPORT|DOCTOR_REPORT|INSTALLED_COMPONENTS)\.(json|txt))$'
& $Uv run --frozen --no-sync detect-secrets scan --no-verify --exclude-files $SecretExclude
& $Uv run --frozen --no-sync pip-audit --local --skip-editable

# Bounded diagnostic and artifact verification
$RunRoot = Join-Path $WorkspaceRoot 'var\runs'
$DiagnosticJson = & $Uv run --frozen --no-sync pacd-sim diagnostic --workspace-root $WorkspaceRoot --output-root $RunRoot --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
$Diagnostic = $DiagnosticJson | ConvertFrom-Json
& $Uv run --frozen --no-sync pacd-sim verify $Diagnostic.run_dir --workspace-root $WorkspaceRoot

# Clean offline reconstruction; the target must be absent
$ReconstructionTarget = Join-Path $WorkspaceRoot 'var\tmp\reconstruction-venv-next'
if (Test-Path -LiteralPath $ReconstructionTarget) {
    throw 'Choose a new absent task-only reconstruction target.'
}
$env:UV_PROJECT_ENVIRONMENT = $ReconstructionTarget
& $Uv lock --check --offline
& $Uv sync --frozen --offline
& (Join-Path $ReconstructionTarget 'Scripts\python.exe') -m pytest -p no:cacheprovider --basetemp (Join-Path $TaskTemp 'reconstruction-pytest') -q
```

The executed reconstruction used the previously absent retained target
`var/tmp/reconstruction-venv-final`, installed 73 packages, and passed all 108 tests on CPython
3.13.15. The documented rerun deliberately names a different absent target and refuses overwrite.

## 7. Validation performed

| Gate group | Result | Evidence | Notes |
|---|---|---|---|
| Host safety | PASS | Preflight, logs, doctor | No protected-path, privilege, security-control, existing-software, or resource violation |
| Toolchain | PASS | Components, dependency inventory, doctor | Exact Python/lock and isolated clean reconstruction |
| Architecture | PASS | Architecture, tests, verifier | All AR-01 through AR-09 pass |
| Quality/security | PASS | Quality, coverage, Bandit, secrets, audit reports | 108 tests; strict types; zero scan findings/candidates/vulnerabilities |
| Diagnostic | PASS | Diagnostic report and three retained run roots | All DR-01 through DR-10 pass |
| GitHub delivery | PENDING | Branch local; PR not yet opened | GH-02 current privacy and GH-05 will be closed during delivery |

The full gate-by-gate disposition is in `VALIDATION_REPORT.md`.

## 8. Diagnostic run

Exactly three executions were used to validate one bounded smoke scenario: seeds 424242, 424242,
and 424243. All are explicitly `NON_REPORTABLE_DIAGNOSTIC`, completed in 2.164–2.295 seconds,
retained raw JSONL/Parquet and derived CSV/Parquet, and passed independent verification. The two
same-seed semantic hashes match; the different seed is distinguishable. Each 23-event chain has
one allowed simulated execution, one escalation that was not executed, and one prohibited
external-network-scan candidate that was not executed. The simulated adapter declares
`network_enabled=false`.

No empirical PACD claim is authorized or made.

## 9. Guardrail compliance evidence

Workspace path checks, strict write jails, reparse-point rejection, transactional staging,
closed-world manifests, aggregate output limits, exact action/config binding, immutable hashes,
simulated-only policy, reportable denial, and sanitized logs are retained. Original package
payloads and the workspace copy matched the package manifest before work and will be rechecked
after delivery.

## 10. Escalations and dispositions

E-001 (unsigned uv executable provenance) and E-002 (GitHub OAuth prerequisite) were resolved
after explicit authorization. The official SLSA attestation verified exact uv bytes; OAuth used
the official device flow, secure keyring storage was verified, the token was not displayed, and
persistent Git credential integration was declined. No other boundary required escalation.

## 11. Vulnerabilities, license issues, and remaining decisions

The dependency audit reported no known vulnerabilities in 72 third-party packages. Static
security and secret scans reported no findings. Third-party declared-license metadata is
retained, but legal sufficiency was not assessed. `LICENSE_PENDING.md` leaves the public-license
choice to the author. A future frozen protocol and reportable approval remain separate author
decisions; bootstrap created neither.

Coverage is 74% branch-aware without an invented threshold. The valid reportable-approval path
was intentionally unexecuted, and the minimal smoke path does not constitute a red-agent,
orchestration, oversight, polymorphism, or comparative PACD experiment.

## 12. Rollback information

No automatic rollback or cleanup was performed because deletion or software removal was not
authorized. Task-created components are isolated to the workspace plus the separately managed
CPython 3.13.15 directory recorded in `INSTALLED_COMPONENTS.json`. Any future removal should
first inventory those exact targets and obtain separate authorization; existing host software
must remain untouched.

## 13. Final evidence statement

All local mandatory acceptance gates pass. The report intentionally withholds the final
acceptance classification until the current private-repository state is reverified, the feature
branch is pushed without history rewriting, and an open unmerged PR is confirmed.

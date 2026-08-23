# PACD Local Simulation Environment Bootstrap — Codex Work Order

**Document ID:** PACD-SIM-ENV-CODEX-001  
**Version:** 1.0  
**Date:** 2026-08-22  
**Status:** Author-directed execution specification  
**Owner and final decision authority:** Michael Thiessmeier

## 1. Governing source and scope

This work order is governed by the author’s explicit 2026-08-22 instruction, followed by the current PACD Decision Register, current project controls, the PACD Simulation Development Plan, the PACD Simulation Software/Compute/Cost Plan, and the monograph’s evaluation architecture.

The Decision Register previously scheduled simulator development after monograph lock. The current explicit author instruction authorizes **environment preparation now**. It does not authorize reportable experiments or weaken the empirical controls. Empirical findings must remain in a separately versioned Technical Report supported by a frozen protocol, fair baselines, retained raw records, sensitivity analysis, negative controls, and independent reproduction or challenge review.

### Authorized outcome

Codex shall leave the machine with a safe, isolated, documented, and reproducible local development environment capable of loading and running a small deterministic PACD simulation diagnostic.

### In scope

- inspect relevant host development capabilities without changing them;
- create a dedicated PACD workspace outside Desktop, Documents, and Downloads;
- locate or create the appropriate private GitHub repository under the GitHub rules;
- install missing software from official sources, preferring user-scoped side-by-side installation;
- create a project-local Python environment and locked dependencies;
- establish the PACD repository skeleton and architectural boundaries;
- create a minimal simulation-only diagnostic harness if no implementation exists;
- run lint, unit, property, negative, reproducibility, security, and deterministic smoke checks appropriate to the bootstrap;
- retain logs, hashes, manifests, and a final report;
- push a branch and open a pull request without merging.

### Out of scope

- full simulator construction;
- reportable experimental runs;
- protocol freeze or changes to hypotheses, metrics, baselines, primary comparisons, exclusion criteria, statistical methods, or seed ranges;
- empirical claims, charts intended for publication, or updates to the monograph;
- use of earlier draft results as evidence;
- public repository visibility, public release, DOI, package publication, or license selection;
- cloud compute, paid services, GPU use, Docker/WSL/Podman installation, cyber-range deployment, or production integrations;
- real network activity beyond ordinary software downloads and GitHub access.

## 2. Required operating posture

Codex may work autonomously inside the defined workspace and permissions. It must not ask for confirmation for ordinary, reversible, user-scoped actions that comply with `AGENTS.md`. It must stop and escalate for every boundary condition listed there.

The task must follow the PACD principle of guarded agency: reason and propose broadly, execute only inside explicit bounds, verify every consequential action, preserve rollback, and maintain an accountability record.

## 3. Phase 0 — Read controls and establish the work log

Before any host change:

1. Read the entire package.
2. Restate the workspace root, protected paths, installation boundary, GitHub boundary, browser boundary, and escalation conditions in `status/PREFLIGHT.md`.
3. Create `status/WORKLOG.md`, `status/DECISIONS.md`, `status/COMMAND_LOG.md`, `status/ESCALATIONS.md`, and `status/private/` in a temporary task folder under the authorized workspace root.
4. Add `status/private/` to `.gitignore` before any sensitive inventory is collected.
5. Record the exact package version and SHA-256 values.

Do not continue if the package is incomplete or its hashes cannot be verified.

## 4. Phase 1 — Read-only host preflight

Collect only the development information needed for this task:

- Windows edition, build, and architecture;
- logical CPU count, total RAM, and free space on the intended workspace drive;
- relevant existing commands and versions: PowerShell, Git, GitHub CLI, Python launchers/runtimes, `uv`, VS Code or another editor, and any existing container tooling;
- current user-scoped PATH entries relevant to those tools;
- whether the Chrome plugin is connected, without inspecting unrelated browser content;
- GitHub CLI authentication status and the active account, without displaying tokens;
- whether a PACD simulation repository already exists in the authorized GitHub account.

Do not enumerate all installed applications, all files, browser history, unrelated repositories, personal data, or protected-folder contents.

Record an inventory table with status values: `present-compatible`, `present-do-not-modify`, `missing`, `ambiguous`, or `blocked`.

### Preflight gates

- At least 20 GB free disk is required.
- No administrator elevation or reboot may be assumed.
- Any existing Python, Node, Git, CUDA, NVIDIA, Docker, WSL, editor, or browser installation is pre-existing software and must remain unchanged.
- If the system is not Windows, adapt the workspace syntax but preserve all semantic guardrails and document the divergence.

## 5. Phase 2 — Create the bounded workspace

Use:

`%USERPROFILE%\PACD-Workspaces\PACD-Simulation`

Create these top-level directories without touching protected folders:

```text
PACD-Simulation/
  repo/
  package/
  var/
    downloads/
    cache/
    tmp/
    runs/
  local-backups/
  bootstrap-status/
```

Copy this package into `package/`; never move the original. If the root or `repo/` already contains content, do not overwrite it. Inventory it and either use a new versioned child directory or escalate when purpose/ownership is ambiguous.

All transient commands must run with the current directory under this workspace.

## 6. Phase 3 — Resolve the GitHub repository safely

1. Search the authenticated account for exact and close matches to `pacd-simulation` and `PACD`.
2. If one unambiguous repository exists, clone it into `repo/` using HTTPS or existing GitHub CLI authentication. Do not execute its scripts yet.
3. Inspect repository metadata, branches, recent commits, workflows, dependency files, source notices, and existing `AGENTS.md` read-only.
4. Treat existing code, configurations, and results as unverified provenance until reconciled with current controls.
5. If multiple repositories, organizations, confidential product repositories, or conflicting histories are present, escalate.
6. If none exists, create a private `pacd-simulation` repository. Do not add a public license. Initialize with a minimal README only if GitHub requires it.
7. Create branch `codex/environment-bootstrap-v1` from the default branch.
8. Never merge or change the default branch.

Before running any cloned code, inspect for destructive scripts, post-install hooks, external network calls, secrets, real target data, and stale empirical outputs. If found, quarantine by non-execution and record; do not delete.

## 7. Phase 4 — Install the minimum toolchain

### 7.1 Core tools

Required capabilities:

- Git;
- GitHub CLI;
- `uv` for project/Python management;
- a stable CPython runtime;
- an existing editor, with VS Code acceptable but not required.

Use existing compatible Git and editor installations without modifying them. Install missing GitHub CLI or `uv` user-scoped from official sources. Prefer an official Windows package-manager entry after confirming its publisher and exact package identity. If a package manager would upgrade or alter an existing package, do not proceed; install side-by-side or escalate.

### 7.2 Python policy

- Do not modify or remove existing Python versions.
- Use a `uv`-managed side-by-side Python in the tool’s normal per-user location.
- Default compatibility target: the latest stable Python 3.13 maintenance release.
- Project requirement: `>=3.13,<3.15`, unless the existing repository has a justified, compatible lock requiring another stable release.
- Do not use Python 3.15 prereleases.
- Pin the exact interpreter with `.python-version` and record its checksum/version.

If Python 3.14 is clearly required or provides materially better compatibility, Codex may select it only after resolving the full dependency set and recording the rationale. This is an implementation decision, not an empirical result.

### 7.3 No container or GPU dependency

Do not install or require Docker Desktop, Podman, WSL, CUDA, GPU libraries, a hypervisor, or a commercial modeling platform. The first simulator is local-first and CPU-only. A container specification may be drafted later after the native environment is stable, but no container runtime is required for this bootstrap.

## 8. Phase 5 — Create the isolated Python project

Use `uv` and a repository-local `.venv`. Do not use global `pip` or alter global packages.

Create or reconcile:

- `pyproject.toml`;
- `uv.lock`;
- `.python-version`;
- `.editorconfig`;
- `.gitattributes`;
- `.gitignore`;
- `LICENSE_PENDING.md`;
- root `AGENTS.md` from this package;
- `README.md` with explicit nonempirical status.

### 8.1 Initial runtime dependencies

The preferred transparent Release 1 stack is:

- `simpy` — discrete-event scheduler;
- `numpy` — stochastic and numerical operations;
- `pandas` — tabular aggregation;
- `scipy` — statistical calculations;
- `networkx` — graph state and path operations;
- `matplotlib` — generated figures for later analysis;
- `pydantic` — typed configuration and record schemas;
- `pyyaml` — human-readable configuration input;
- `pyarrow` — Parquet event and result records.

Use the Python standard library for CLI parsing, logging, JSON/JSONL, SQLite metadata, hashing, multiprocessing/concurrent execution, timestamps, and path management unless a dependency produces a clear reproducibility or safety advantage.

### 8.2 Development and assurance dependencies

- `pytest`;
- `pytest-cov`;
- `hypothesis`;
- `ruff`;
- `mypy`;
- `pre-commit`;
- `pip-audit`;
- `bandit` or equivalent static security checks;
- `detect-secrets` or equivalent secret scan.

Pin all transitive dependencies through `uv.lock`. Use official PyPI packages only. Do not install from an arbitrary Git URL, local wheel from Downloads, untrusted mirror, or mutable branch without approval.

### 8.3 Dependency policy

- Keep the core dependency set small.
- Do not add Jupyter, TensorFlow, PyTorch, Ray, Dask, Spark, Neo4j, Kafka, a browser UI framework, or live LLM SDK during bootstrap.
- Generate a dependency inventory and license summary; do not assert legal sufficiency.
- Run vulnerability scanning and record unresolved findings. Do not silently downgrade or upgrade pre-existing host software to address a project dependency.

## 9. Phase 6 — Establish the repository architecture

Create the structure defined in `PACD_Local_Simulation_Environment_Architecture_v1.0.md`. The key invariant is separation of experimental control from defender logic.

At minimum, create:

```text
configs/
  protocol/draft/
  protocol/frozen/
  scenarios/
  topologies/
  missions/
  adversaries/
  defenders/
  policies/
  metrics/
  seeds/
schemas/
src/pacd_sim/
  cli.py
  harness/
  engine/
  environment/
  telemetry/
  evidence/
  state/
  hypotheses/
  actions/
  polymorphism/
  orchestration/
  governance/
  oversight/
  execution/
  audit/
  metrics/
  analysis/
  reproducibility/
  agents/red/
  defenders/baselines/
  defenders/pacd/
tests/
  unit/
  property/
  scenario/
  negative/
  reproducibility/
docs/
status/
var/              # gitignored
artifacts/        # gitignored diagnostic outputs
```

The `protocol/frozen/` directory must remain empty except for a README explaining the author-approval requirement. Codex may not promote any configuration to frozen status.

## 10. Phase 7 — Implement the environment doctor and diagnostic smoke path

If a current implementation already exists, adapt these checks to it without overwriting or deleting existing code. If no implementation exists, create only the minimum non-reportable diagnostic needed to prove the environment.

### 10.1 `pacd-sim doctor`

Provide a command that reports:

- interpreter and dependency-lock compatibility;
- writable workspace paths;
- protected paths not used as work roots;
- available CPU/RAM/disk thresholds;
- Git commit and branch;
- configuration-schema load status;
- raw-output and hash-manifest capability;
- network-disabled/simulation-only execution adapter status;
- reportable-mode interlock status;
- security/lint/test command availability.

The doctor must not inspect unrelated user files or transmit telemetry.

### 10.2 Reportable-mode interlock

Implement a hard CLI guard:

- `--reportable` mode must fail closed unless `configs/protocol/frozen/APPROVAL.json` exists;
- the file must contain author, approval timestamp, exact Git commit, exact configuration hash, seed-registry hash, and protocol version;
- the referenced hashes must match current files;
- bootstrap must not create this approval file.

### 10.3 Diagnostic scenario

Create `configs/scenarios/diagnostic_identity_smoke.yaml` containing a tiny synthetic identity-centric environment. It may include synthetic identities, a session, a SaaS resource, one mission function, noisy telemetry, a benign administrative event, a simulated adversary event, and reversible simulated actions.

The diagnostic must:

- use synthetic data only;
- run in under five minutes;
- write event-level raw records, summary records, and a manifest;
- demonstrate configuration validation, event scheduling, graph updates, candidate-action handling, independent safety decision, simulated execution, verification, audit, and hash generation;
- include a benign negative control;
- be labeled `NON_REPORTABLE_DIAGNOSTIC` in every output;
- produce no claim comparing PACD with a baseline.

### 10.4 Determinism check

Run the same diagnostic twice with the same seed. After normalizing run timestamps and paths, the event and summary hashes must match. Run once with a different seed and confirm that the manifest records the difference.

## 11. Phase 8 — Validation

Execute every applicable acceptance test in the separate acceptance document. At minimum:

- `uv sync --frozen` or equivalent lock verification;
- unit tests;
- property tests for schema, admissibility, and hash stability;
- negative tests for protected paths, reportable-mode denial, prohibited action denial, and network-disabled execution;
- deterministic diagnostic replay;
- lint, formatting check, type check, coverage, dependency audit, static security scan, and secret scan;
- Git clean-status and branch verification;
- output manifest and SHA-256 validation.

Do not fix failed tests by weakening them, excluding them, disabling security checks, or deleting evidence. Record failed and blocked tests.

## 12. Phase 9 — GitHub delivery

1. Review the diff for secrets, host-specific paths, personal identifiers, stale empirical results, confidential material, and generated raw output.
2. Ensure `var/`, `.venv/`, `artifacts/`, local package downloads, sensitive inventories, and diagnostic raw records are gitignored unless a small sanitized fixture is intentionally tracked.
3. Commit in coherent changesets with descriptive messages.
4. Push only the working branch.
5. Open a pull request titled `Bootstrap bounded local PACD simulation environment`.
6. The PR body must summarize scope, installed components, architecture, tests, evidence status, security boundaries, and remaining decisions.
7. Do not merge.
8. Do not enable public visibility, Releases, Pages, Packages, or automatic full-run workflows.

## 13. Phase 10 — Final report

`status/FINAL_REPORT.md` must contain:

- governing sources and scope;
- target machine summary without sensitive identifiers;
- workspace path;
- existing tools preserved;
- software installed, exact versions, sources, scopes, and hashes where available;
- repository and branch/PR details;
- architecture created;
- commands for setup, doctor, tests, diagnostic run, and artifact verification;
- validation results with evidence paths;
- explicit statement that no reportable experiment was run;
- explicit statement that no protected folder content or pre-existing software was deleted or modified, qualified by the retained command/work log rather than unsupported assertion;
- unresolved vulnerabilities, license questions, compatibility issues, and open decisions;
- every escalation and its disposition;
- rollback instructions limited to task-created workspace content and task-installed user-scoped software, with any actual uninstallation left to the author unless separately approved.

## 14. Definition of done

The bootstrap is complete only when:

1. the dedicated workspace exists outside protected folders;
2. existing host software remains unchanged;
3. a private GitHub repository and unmerged working PR exist;
4. the Python interpreter and full dependency graph are pinned;
5. the environment can be reconstructed with one documented command;
6. the doctor passes;
7. all applicable tests pass;
8. the diagnostic run is deterministic and clearly non-reportable;
9. raw diagnostic records, manifest, and hashes are retained;
10. reportable mode fails closed without author approval;
11. no secret, personal data, confidential source, stale empirical result, or generated bulk output is committed;
12. the final report and validation record are complete.

If any gate cannot pass without crossing a guardrail, the correct outcome is a documented escalation—not a workaround.

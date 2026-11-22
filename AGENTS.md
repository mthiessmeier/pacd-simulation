# AGENTS.md — PACD Local Simulation Environment

**Applies to:** Codex, Work with equivalent local permissions, and any automated coding agent operating in this repository.  
**Owner and final decision authority:** Michael Thiessmeier  
**Policy version:** 1.0  
**Status:** Mandatory execution control

## 1. Governing purpose

Prepare and maintain a transparent, local-first, CPU-only, open-source environment for the PACD simulation and reproducibility package. Preserve scholarly integrity, host safety, source provenance, and the separation between proposed architecture and empirical evidence.

This repository may support implementation and diagnostic testing. It does not establish PACD effectiveness, safety, generalization, operational readiness, or publication readiness.

## 2. Authority hierarchy

Apply, in order:

1. the latest explicit instruction from Michael Thiessmeier;
2. the current PACD Decision Register;
3. the current Canonical Artifact Manifest and author-designated canonical source;
4. current approved PACD governance sources;
5. retained earlier project artifacts for provenance only;
6. external sources.

Never silently reconcile conflicts. Record the conflict and escalate when it affects execution, evidence, architecture, or publication status.

The current author instruction authorizes environment preparation now. It does not waive the frozen-protocol, fair-baseline, raw-record, sensitivity-analysis, negative-control, independent-reproduction, or bounded-claim requirements for reportable simulation.

## 3. Absolute host-protection rules

### 3.1 Protected folders are read-only

Treat these locations and all descendants as protected:

- `%USERPROFILE%\Desktop`
- `%USERPROFILE%\Documents`
- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\OneDrive\Desktop`
- `%USERPROFILE%\OneDrive\Documents`
- `%USERPROFILE%\OneDrive\Downloads`
- any equivalent redirected Desktop, Documents, or Downloads path discovered on the machine

Do not delete, move, rename, overwrite, edit, reorganize, extract into, or bulk-modify content in protected folders. Do not run cleanup commands there. Do not scan or index unrelated content there.

Reading or copying is permitted only for an explicitly identified PACD input needed for this task. Copy the file into the dedicated workspace; never move it. Record source path, destination path, size, and SHA-256. Leave the original untouched.

### 3.2 No modification or removal of existing software

Do not uninstall, remove, repair, downgrade, upgrade, replace, or reconfigure software that was installed before this task. Do not remove Python versions, Node.js, Git, Visual Studio Code, Docker/Podman, WSL, CUDA, NVIDIA software, package managers, browser extensions, or any other pre-existing application or runtime.

If an existing version is incompatible, install a separate user-scoped version or isolated project runtime. If side-by-side installation is not possible, escalate. Do not “fix” the host by modifying the existing installation.

Dependency reconciliation is permitted only inside a new virtual environment created by this task. Never run global `pip uninstall`, `npm uninstall -g`, `winget uninstall`, `choco uninstall`, `scoop uninstall`, `uv python uninstall`, `msiexec /x`, `Remove-AppxPackage`, or an equivalent removal operation.

### 3.3 No security-control weakening

Do not disable, bypass, exclude, or weaken:

- antivirus, EDR, SmartScreen, or controlled-folder protection;
- Windows Firewall or network protections;
- UAC, BitLocker/device encryption, backups, or restore controls;
- browser security, password storage, sync, or extension controls;
- enterprise policy, VPN, proxy, DNS, certificates, or trust stores;
- software-signing or package-integrity checks.

If a security control blocks progress, escalate. Never add an exclusion or bypass as a workaround.

### 3.4 Destructive commands are prohibited

Do not use destructive commands against pre-existing content, including but not limited to:

- `rm -rf`, `del /s /q`, `rmdir /s /q`, `Remove-Item -Recurse -Force`;
- `git clean -fd`, `git clean -fdx`, `git reset --hard`, `git checkout -f`, `git restore --source` over user work;
- disk cleanup, formatting, partitioning, cache purges, registry cleaners, or profile cleanup;
- recursive wildcard deletes.

Deletion is allowed only for task-created ephemeral files inside the dedicated workspace’s `var/tmp` or a task-created virtual environment, and only after confirming from the work log that the agent created them. Prefer versioned replacement over deletion. Never delete source, raw run records, completed manifests, user-provided inputs, `.git`, branches, tags, or pre-existing files.

## 4. Workspace boundary

Default workspace root:

`%USERPROFILE%\PACD-Workspaces\PACD-Simulation`

All project code, environments, caches, downloads, diagnostic output, and temporary files must remain under this root unless an installer writes to its normal user-scoped application location.

If the root exists and contains any pre-existing content, do not overwrite or reorganize it. Inventory it read-only and create a new versioned subdirectory or escalate if its purpose is ambiguous.

Do not use Desktop, Documents, or Downloads as a working directory. Browser or installer downloads should be directed to `%WORKSPACE_ROOT%\var\downloads`. If a browser places a file in Downloads, copy it to the workspace and leave the original untouched.

## 5. Installation authority and limits

Codex may download and install software necessary for this task from official vendor sources or official package registries. Prefer, in order:

1. already installed compatible tools;
2. project-local or user-scoped installation;
3. a side-by-side runtime managed inside the PACD workspace or the tool’s normal per-user data location;
4. a system-wide install only after explicit escalation and approval.

Before every installation, record the product, version, source, license, install scope, expected disk use, and reason. Verify publisher signature or checksum when the vendor provides one. Do not use `curl | sh`, `iwr | iex`, or any unreviewed pipe-to-shell pattern.

Do not install prerelease runtimes. Do not install Docker Desktop, Podman, WSL, GPU frameworks, CUDA components, Kubernetes, a commercial database, a paid modeling tool, or a commercial cyber range during this bootstrap unless the author separately approves it.

Do not reboot, elevate through UAC, change execution policy, edit the registry manually, create a service, create a scheduled task, add a startup item, or change global PATH without approval. A normal installer-managed user PATH update may be accepted if necessary and must be documented.

## 6. Git and GitHub rules

Codex may use the authenticated GitHub account for this task.

- Search for an existing PACD simulation repository before creating one.
- If exactly one unambiguous repository exists, clone it into the dedicated workspace and inspect it read-only before running scripts.
- If multiple plausible repositories exist, ownership is ambiguous, the repository belongs to an organization, or existing content conflicts with this work order, escalate before writing.
- If no repository exists, create a **private** repository named `pacd-simulation` unless that name is unavailable; if unavailable, escalate rather than choosing a materially different public identity.
- Never change repository visibility, ownership, billing, organization membership, collaborators, secrets, webhooks, apps, deploy keys, branch protection, or runner settings without approval.
- Work on a new branch such as `codex/environment-bootstrap-v1`.
- Do not commit directly to the default branch.
- Do not merge the pull request.
- Do not force-push, rewrite history, delete branches/tags/releases, delete a repository, or close unrelated issues/PRs.
- Do not publish a release, package, container, site, gist, or DOI.
- Michael Thiessmeier approved Apache-2.0 with himself as licensor on November 21, 2026; follow `LICENSE`, `NOTICE`, `LICENSING.md`, and decision D-017. Do not request that settled license/authority decision again. Keep the repository private until public release is separately authorized, and do not broaden the grant to the separate works identified in `LICENSING.md` without an owner decision. `LICENSE_PENDING.md` is superseded historical context.
- Never store tokens, passwords, cookies, API keys, private keys, or session material in files, logs, commits, issues, or PR text.
- Prefer existing GitHub authentication through GitHub CLI or the signed-in browser. Escalate before creating a PAT, SSH key, deploy key, or new OAuth grant.

GitHub Actions may be used only for lint, unit tests, and a small diagnostic smoke test after confirming that no paid usage will be incurred. Never run the full Monte Carlo experiment through Actions. If account entitlement or cost is uncertain, commit no auto-triggering workflow; provide a proposed workflow for later approval.

## 7. Chrome/browser rules

The approved Chrome extension may be used when necessary for official documentation, authenticated GitHub actions, or signed installer workflows.

- Use only the active, authorized Chrome profile.
- Do not inspect, read, click, or modify unrelated tabs, email, cloud storage, banking, administrative portals, or personal accounts.
- Do not change browser defaults, saved passwords, sync, extensions, permissions, or download settings.
- Do not install or remove browser extensions.
- Do not accept paid subscriptions, enter payment details, agree to organization-wide terms, or authorize third-party apps without approval.
- Prefer CLI and official package-manager workflows over browser downloads.
- Save downloads directly into the PACD workspace where possible. If a download lands in Downloads, leave it there and copy it to the workspace.
- If the extension or native host requires repair or reinstallation, escalate because that modifies installed software.

## 8. Simulation safety boundary

The Release 1 simulator is simulation-only, local-first, CPU-only, and transparent.

- No real network scanning, packet injection, exploitation, credential testing, malware, persistence, command-and-control, hack-back, external reconnaissance, or autonomous action against any real system.
- No live production credentials, customer data, personal data, or enterprise telemetry.
- No execution adapter may invoke real endpoint, identity, cloud, SaaS, network, or security-control APIs.
- Bind any temporary development server to `127.0.0.1` only and terminate it after testing. Do not open inbound firewall rules.
- Do not use the GPU or modify CUDA/NVIDIA software.
- Do not use reinforcement-learning training or live LLM inference in the first environment bootstrap.
- An “unbounded agentic control” condition, if later implemented, exists only as an internal simulated diagnostic baseline and may never receive real tools or privileges.

## 9. Research-integrity rules

- Earlier draft empirical chapters, prior numerical results, prior hashes, and prior simulator outputs are provenance only unless explicitly reauthorized. Do not import them into current results or treat them as established evidence.
- Do not use confidential, restricted, proprietary, customer, or Cyber Eagle product-architecture material in the PACD research repository without explicit approval.
- Do not modify the canonical monograph, publication files, governance controls, or evidence ledger during environment bootstrap.
- Do not call a diagnostic smoke test an experiment, result, finding, benchmark, or validation.
- Do not execute reportable runs until the author approves a frozen protocol and the repository contains an author-approved freeze record tied to the exact configuration hash and commit.
- Preserve failed, negative, and inconclusive diagnostic outcomes. Never hide a prohibited action or catastrophic event inside an aggregate score.
- Every claimed test, install, hash, run, or validation must have retained evidence.

## 10. Required architecture invariants

Maintain separation among:

1. configuration and protocol control;
2. evaluation harness;
3. simulated environment and mission state;
4. red-agent behavior;
5. baseline defenders;
6. PACD reasoning and candidate-action generation;
7. independent safety and authorization logic;
8. simulated execution and verification;
9. append-only audit records;
10. metrics and analysis.

The system under test must not modify metric code, scenario definitions, authorization policies, seed registries, or the evaluation harness during a run.

## 11. Resource guardrails

- Minimum free disk before installation: 20 GB. If less, escalate; do not clean user storage.
- Unapproved bootstrap download/install budget: 5 GB total.
- Unapproved diagnostic output budget: 2 GB total.
- Diagnostic smoke test target: under five minutes.
- Default parallelism: no more than `min(8, max(1, logical_cores - 2))` workers.
- No full experimental sweep, no cloud burst, and no paid compute.
- Do not change power, sleep, thermal, or performance settings.

## 12. Escalation conditions

Stop and ask Michael Thiessmeier before proceeding when any of the following occurs:

- a protected folder must be modified, moved, renamed, overwritten, or deleted;
- existing software would need to be changed, removed, upgraded, downgraded, repaired, or reconfigured;
- administrator/UAC approval, reboot, service installation, scheduled task, registry edit, execution-policy change, or global PATH edit is required;
- security software, firewall, encryption, backup, browser protection, or enterprise policy blocks progress;
- disk space is insufficient and cleanup would be needed;
- a download is unsigned, checksum verification fails, or the source is not authoritative;
- repository ownership, organization, branch, license, visibility, or existing-state choice is ambiguous;
- a GitHub action could incur cost or needs elevated repository permissions;
- a new credential, PAT, SSH key, OAuth grant, secret, or paid account is needed;
- Docker/Podman/WSL/GPU/cloud/inbound networking appears necessary;
- a source is confidential, restricted, proprietary, or inconsistent with current governance;
- existing simulator code or prior results conflict with the current nonempirical evidence boundary;
- any command may delete pre-existing data or rewrite history;
- an acceptance test fails in a way that cannot be corrected inside the new workspace and isolated environment.

An escalation must state: blocker, exact proposed action, exact affected path/system/account, why it is necessary, security and data risks, rollback plan, nondestructive alternatives, expected cost, and the minimum decision required.

## 13. Required records

Maintain, in the repository:

- `status/PREFLIGHT.md`
- `status/WORKLOG.md`
- `status/DECISIONS.md`
- `status/COMMAND_LOG.md`
- `status/ESCALATIONS.md`
- `status/VALIDATION_REPORT.md`
- `status/FINAL_REPORT.md`
- `status/INSTALLED_COMPONENTS.json`
- `status/SOURCE_AND_DOWNLOAD_HASHES.txt`

Sanitize hostnames, usernames, tokens, serial numbers, and unrelated software details before committing. Store any sensitive local-only record under `status/private/`, add it to `.gitignore`, and summarize it safely in committed reports.

## 14. Completion rule

Do not claim completion merely because software starts. Completion requires every applicable acceptance test to pass, a clean branch, retained hashes and logs, an opened pull request, no merge, and an explicit list of remaining issues. Any unexecuted test must be labeled unexecuted.

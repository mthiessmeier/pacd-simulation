# PACD Environment Bootstrap — Preflight

**Date/time:** 2026-08-23T00:00:49.3529527-04:00
**Final reconciliation update:** 2026-08-23T02:37:12-04:00
**Agent/session:** Codex desktop task (sanitized)
**Package version/hash:** PACD-SIM-ENV-CODEX-PKG-001 v1.0; PACKAGE_MANIFEST.json SHA-256 a774484bb217f6a968191f914466013421d490ae2256e8c672928adad6d595e7
**Workspace root:** `%USERPROFILE%\PACD-Workspaces\PACD-Simulation`
**GitHub account (sanitized):** Expected personal account authenticated through approved OAuth; token stored in Windows keyring; login retained only in private evidence

## Governing boundaries acknowledged

- Protected paths: Desktop, Documents, Downloads, OneDrive-redirected equivalents, and discovered shell-folder equivalents are read-only; only the explicitly identified PACD package was copied out, never moved or altered.
- Existing-software rule: preserve all pre-existing software; use it unchanged or install a separate user-scoped/workspace-local version; reconcile dependencies only in the new project virtual environment.
- Security-control rule: do not weaken, bypass, reconfigure, or exclude antivirus/EDR, firewall, UAC, encryption, backup, browser, OS, or enterprise controls.
- Installation boundary: official sources only; user-scoped or workspace-local; no elevation, reboot, service, scheduled task, registry/execution-policy/global-PATH change, prerelease runtime, container/GPU/cloud/commercial stack, or >5 GB unapproved install/download total.
- GitHub rule: select one unambiguous repository or create private `pacd-simulation`; work only on `codex/environment-bootstrap-v1`; no default-branch commit, merge, force-push, history rewrite, deletion, visibility/ownership/billing/security change, public license, release, or uncertain-cost workflow.
- Browser rule: authorized Chrome profile only for official documentation, GitHub, or signed installer flow; no unrelated content, setting/extension/security changes, new grants, payments, or subscriptions.
- Reportable-run rule: bootstrap may run only a clearly labeled `NON_REPORTABLE_DIAGNOSTIC`; reportable mode must fail closed without an author-approved, hash-matching freeze record, which bootstrap must not create.
- Escalation rule: stop for every guardrail trigger and report blocker, exact action and target, necessity, risk, rollback, nondestructive alternatives, cost, and minimum author decision.

## Relevant host inventory

| Capability | Status | Version/path (sanitized) | Action |
|---|---|---|---|
| Windows | present-compatible | Windows Pro 25H2, build 26200.9106, x64 | Preserve |
| CPU/RAM/free disk | present-compatible | 24 logical CPUs; 63.36 GiB RAM; 205.93 GiB free of 952.17 GiB on C: | Worker cap 8; monitor disk |
| PowerShell | present-compatible | Bundled PowerShell Core 7.6.4; Windows PowerShell 5.1 present-do-not-modify | Preserve |
| Git | present-compatible | Bundled Git 2.53.0.windows.3 at a sanitized Codex runtime path | Use unchanged |
| GitHub CLI | present-compatible | Workspace-local 2.98.0; checksum/signature valid; expected account authenticated in keyring | Use bounded API/Git operations; no persistent Git helper |
| Python runtimes | present-do-not-modify | Bundled Python 3.12.13; WindowsApps aliases present; no `py`/PEP 514 host runtime | Preserve; install uv-managed stable 3.13 separately |
| uv | present-compatible | Workspace-local 0.12.5; official checksum and SLSA provenance attestation verified | Execute after resolution record; no persistent PATH change |
| Editor | present-compatible | Active Codex desktop task provides repository editing; no separate editor detected | Preserve; no editor install |
| Container tools (preserve only) | present-do-not-modify | WSL 2.7.10.0 present; Docker and Podman absent; no distributions enumerated | Do not use or modify |
| Chrome plugin | present-compatible | Existing Chrome connection established without tab/history inspection | Use only if CLI/official flow later requires it |
| GitHub repository | present-compatible | Targeted personal-account search returned zero PACD matches; exact name available | Create private `pacd-simulation` |
| WinGet | blocked | Alias present but execution not established in sandbox | Do not use; portable official archives selected |
| User PATH | present-do-not-modify | Only relevant user entry is `%USERPROFILE%\AppData\Local\Microsoft\WindowsApps` | No persistent PATH change |

## Resolved protected locations (contents not enumerated)

- `%USERPROFILE%\Desktop` — registered; absent.
- `%USERPROFILE%\Documents` — present and protected.
- `%USERPROFILE%\Downloads` — present and protected; supplied PACD package remained untouched.
- `%ONEDRIVE_ROOT_1%\Desktop` — present and protected.
- `%ONEDRIVE_ROOT_1%\Documents` — present and protected.
- `%ONEDRIVE_ROOT_1%\Downloads` — absent but protected if created.

## Preflight gates

- [x] Free disk >= 20 GB
- [x] Workspace is outside protected folders
- [x] No administrator/reboot requirement identified
- [x] Repository selection unambiguous — zero PACD matches; exact private repository creation selected
- [x] Installation plan uses official, workspace-local sources and no persistent PATH change
- [x] No reportable run planned

## Resolved preflight items

- Targeted personal-account search found no PACD repository, so the exact authorized private `pacd-simulation` repository was created.
- Michael Thiessmeier authorized the official GitHub CLI OAuth device flow; secure keyring storage was verified and persistent Git credential integration was declined.
- Pinned CPython 3.13.15, lock resolution, frozen synchronization, and clean offline reconstruction all passed in isolated task-created environments.
- The repository was reverified private and unarchived after delivery; PR #1 is open and unmerged from the required feature branch to `main`.

# PACD Environment Bootstrap Acceptance Tests

**Document ID:** PACD-SIM-ENV-TEST-001  
**Version:** 1.0  
**Date:** 2026-08-22  
**Status:** Mandatory completion gates

## 1. Host-safety gates

| ID | Test | Pass condition | Evidence |
|---|---|---|---|
| HS-01 | Workspace boundary | All working paths resolve under `%USERPROFILE%\PACD-Workspaces\PACD-Simulation` except normal user-scoped installer locations. | Preflight and command log. |
| HS-02 | Protected folders | No command wrote, moved, renamed, overwrote, or deleted content in Desktop, Documents, Downloads, or redirected equivalents. | Command log and path-write tests. |
| HS-03 | Existing software | No pre-existing application/runtime was uninstalled, upgraded, downgraded, repaired, replaced, or reconfigured. | Preflight versus installed-components record. |
| HS-04 | Security controls | No antivirus/EDR/firewall/UAC/encryption/backup/browser/enterprise control was weakened or bypassed. | Work log and escalation log. |
| HS-05 | Privilege | No unapproved elevation, reboot, service, scheduled task, registry edit, execution-policy change, or global PATH edit occurred. | Command log. |
| HS-06 | Resource limits | Free disk stayed above threshold; downloads and diagnostic outputs stayed within budget. | Preflight and final report. |

A claim that these gates passed must be based on retained logs. If Codex cannot establish a gate, mark it `not established`, not passed.

## 2. Git/GitHub gates

| ID | Test | Pass condition |
|---|---|---|
| GH-01 | Repository selection | Existing repository choice is unambiguous or a private `pacd-simulation` repo was created. |
| GH-02 | Visibility | Repository remains private. |
| GH-03 | Branch | All changes are on a new non-default branch. |
| GH-04 | History | No force-push, reset of user work, branch/tag/release deletion, or history rewrite. |
| GH-05 | Delivery | A PR is open and unmerged. |
| GH-06 | Secrets | Secret scan passes; no token or host-sensitive information is committed. |
| GH-07 | License | No public license was selected; `LICENSE_PENDING.md` records the open decision. |
| GH-08 | CI cost | No full simulation workflow exists; any CI run is small and known not to incur paid usage. |

## 3. Toolchain gates

| ID | Test | Pass condition |
|---|---|---|
| TC-01 | Git | `git --version` succeeds. |
| TC-02 | GitHub CLI | `gh --version` succeeds and authenticated account is confirmed without exposing credentials. |
| TC-03 | uv | `uv --version` succeeds. |
| TC-04 | Python | Pinned stable Python starts through `uv`; existing Python installations remain untouched. |
| TC-05 | Lock | `uv sync --frozen` or equivalent succeeds from a clean environment. |
| TC-06 | Isolation | Project dependencies are inside the new `.venv`; no global package mutation. |
| TC-07 | Inventory | Exact direct/transitive versions and licenses are recorded. |
| TC-08 | Vulnerability audit | Dependency audit executes; all findings are retained and dispositioned. |

## 4. Architecture gates

| ID | Test | Pass condition |
|---|---|---|
| AR-01 | Harness separation | Evaluation harness is a separate module and cannot be imported from defender code to mutate control state. |
| AR-02 | Defender interface | Baselines and PACD implement a common typed interface. |
| AR-03 | Safety independence | Safety-governor rules are outside PACD planner modules. |
| AR-04 | Execution boundary | Only simulated execution exists; no production API adapter or external target support. |
| AR-05 | Metrics isolation | Metrics read completed records and do not modify run state or configs. |
| AR-06 | Config immutability | Canonical configuration is hashed at start and verified at end. |
| AR-07 | Reportable interlock | `--reportable` fails without a valid author approval record. |
| AR-08 | Protocol state | `configs/protocol/frozen/` contains no false approval marker. |
| AR-09 | Evidence label | Every bootstrap output is labeled `NON_REPORTABLE_DIAGNOSTIC`. |

## 5. Code-quality and security gates

Required commands may vary, but the following evidence must exist:

- formatter/linter check passes;
- static type check passes or every limitation is documented;
- unit tests pass;
- property tests pass;
- negative safety tests pass;
- scenario diagnostic tests pass;
- reproducibility tests pass;
- coverage report is generated; no arbitrary minimum should be invented, but uncovered safety-critical paths must be identified;
- static security scan executes;
- secret scan executes;
- no dynamic evaluation from configuration;
- no untrusted pickle loading;
- no unrestricted subprocess or shell execution in simulation modules;
- write paths are constrained to the workspace.

## 6. Diagnostic-run gates

| ID | Test | Pass condition |
|---|---|---|
| DR-01 | Runtime | Diagnostic completes in under five minutes. |
| DR-02 | Synthetic data | No real identity, customer, network, credential, or telemetry data. |
| DR-03 | Event chain | Observation, evidence, state, hypothesis, candidate action, safety decision, simulated execution, verification, audit, and manifest events are present. |
| DR-04 | Negative control | Benign administrative activity is not treated as automatic compromise. |
| DR-05 | Prohibited action | At least one prohibited candidate is denied and never executed. |
| DR-06 | Same-seed replay | Normalized raw and summary output hashes match across two same-seed runs. |
| DR-07 | Different seed | Different-seed run is distinguishable and the seed is recorded. |
| DR-08 | Raw retention | Raw diagnostic records are retained and generate all summaries. |
| DR-09 | Hashes | All output hashes validate. |
| DR-10 | No claim | No comparison, effect size, hypothesis status, or PACD performance claim is generated. |

## 7. Documentation gates

- README contains exact reconstruction, doctor, test, diagnostic, and verification commands.
- Architecture document maps code modules to the eleven PACD layers and the independent harness.
- Preflight, work log, command log, decision log, escalation log, validation report, and final report exist.
- Installed-components record distinguishes pre-existing preserved software from task-installed software.
- Every source/download used has a source and hash record when available.
- Every unexecuted test is labeled unexecuted.
- Remaining issues and author decisions are explicit.

## 8. Final acceptance classification

Use one of:

- `PASSED — environment bootstrap complete`: every mandatory gate passed.
- `CONDITIONALLY PASSED — environment usable, noncritical issues retained`: no safety, integrity, reportable-mode, or reproducibility gate failed; remaining issues are explicitly accepted by the author.
- `BLOCKED — escalation required`: one or more gates cannot be completed inside current authority.
- `FAILED — unsafe or irreproducible`: a safety, integrity, or reproducibility gate failed and was not corrected.

Never use `complete`, `ready`, or `validated` without the classification and evidence paths.

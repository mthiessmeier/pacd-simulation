# PACD Environment Bootstrap — Validation Report

**Generated:** 2026-08-23T02:14:55-04:00
**Evidence label:** `NON_REPORTABLE_DIAGNOSTIC`
**Validated implementation commit:** `39cc2bcb04e36dee9133e66e71bd03ef33596e83`
**Branch:** `codex/environment-bootstrap-v1`
**Pre-delivery status:** All local mandatory gates pass. Current repository privacy and the open-unmerged PR gate will be verified during the authorized delivery step.

No reportable PACD experiment was executed. Results below validate only environment safety,
reproducibility, architecture, and diagnostic plumbing; they do not support a PACD performance or
effectiveness claim.

## Numbered acceptance gates

| ID | Result | Retained evidence | Disposition |
|---|---|---|---|
| HS-01 | PASS | `status/DOCTOR_REPORT.json`; `PREFLIGHT.md`; command log | Repository, environments, temporary output, and runs resolve under the dedicated workspace except the separate uv-managed runtime. |
| HS-02 | PASS | Command/work logs; protected-path doctor check; path-jail tests | The supplied package was read/copied only; no protected-folder artifact was changed. |
| HS-03 | PASS | `INSTALLED_COMPONENTS.json`; preflight | Existing Git, PowerShell, Python 3.12, WSL, browser state, and host tools were preserved. |
| HS-04 | PASS | Work and escalation logs | No security control was weakened, excluded, or reconfigured. |
| HS-05 | PASS | Command log | No elevation, reboot, service, scheduled task, registry edit, execution-policy change, or persistent PATH change occurred. |
| HS-06 | PASS | `INSTALLED_COMPONENTS.json`; run report | 219,232,276,480 bytes remained free at doctor time; downloads were 57,303,699 bytes and all diagnostic outputs 103,540 bytes. |
| GH-01 | PASS | Work/decision logs | Targeted personal-account search found no PACD match; exact private `pacd-simulation` repository created. |
| GH-02 | PENDING DELIVERY CHECK | Creation evidence | Repository was private at creation; current state will be queried immediately before/after PR creation. |
| GH-03 | PASS | Doctor and Git evidence | All changes are on `codex/environment-bootstrap-v1`; default branch was not modified. |
| GH-04 | PASS | Command/work logs and local Git graph | No force-push, history rewrite, reset of user work, deletion, merge, or release operation occurred. |
| GH-05 | PENDING DELIVERY | Authorized next step | Feature branch has not yet been pushed and the PR has not yet been opened. |
| GH-06 | PASS | `status/SECRET_SCAN.json` | Final candidate scan returned zero secrets; private host evidence is ignored. |
| GH-07 | PASS | `LICENSE_PENDING.md` | No public license selected; author decision remains open. |
| GH-08 | PASS | Repository tree and command log | No workflow exists; no CI, Actions, cloud compute, or paid usage was invoked. |
| TC-01 | PASS | Preflight | Preserved Git 2.53.0.windows.3 executes successfully. |
| TC-02 | PASS | Escalation/work logs | Workspace-local gh 2.98.0 executes; expected account authenticated through secure keyring without token exposure. |
| TC-03 | PASS | Component inventory | Verified workspace-local uv 0.12.5 executes successfully. |
| TC-04 | PASS | Doctor; component inventory | Exact stable CPython 3.13.15 runs separately; existing Python 3.12 was untouched. |
| TC-05 | PASS | `status/QUALITY_GATES.json` | New offline reconstruction environment installed all 73 locked packages and passed 108 tests. |
| TC-06 | PASS | Component inventory; doctor | Dependencies are isolated in new primary and reconstruction environments; no global package mutation. |
| TC-07 | PASS | `status/DEPENDENCY_INVENTORY.json` | Exact direct/transitive versions, sources, and declared licenses retained. |
| TC-08 | PASS | `status/VULNERABILITY_AUDIT.json` | 72 third-party packages audited; no known vulnerabilities reported. |
| AR-01 | PASS | Architecture document and tests | Harness is independent and defender code cannot mutate harness control state. |
| AR-02 | PASS | Typed defender protocol and tests | Baselines and PACD implement the common typed interface. |
| AR-03 | PASS | `pacd_sim.governance`; architecture/tests | Safety rules are independent of planner modules. |
| AR-04 | PASS | Broker, governor, verifier, tests | Only `simulated_only` execution exists; `network_enabled=false`; no production adapter. |
| AR-05 | PASS | Metrics tests | Metrics consume completed records without mutating run/configuration state. |
| AR-06 | PASS | Three manifests and verifier | Canonical configuration hash is fixed and checked through finalization. |
| AR-07 | PASS | Negative tests and manual denial | Reportable request exited 3 before output because the author approval record is absent. |
| AR-08 | PASS | `configs/protocol/frozen/README.md` | No `APPROVAL.json` or false approval marker exists. |
| AR-09 | PASS | Three run roots and report | Every diagnostic artifact/record uses `NON_REPORTABLE_DIAGNOSTIC`. |
| DR-01 | PASS | `status/DIAGNOSTIC_RUN_REPORT.json` | Runs completed in 2.164, 2.257, and 2.295 seconds, each under five minutes. |
| DR-02 | PASS | Scenario/configuration and raw records | Only synthetic entities, identities, telemetry, and targets are present. |
| DR-03 | PASS | Raw event records | All required stages are present in each 23-event chain. |
| DR-04 | PASS | Summary and raw records | Benign administrative activity produced retained `not_compromised` negative controls. |
| DR-05 | PASS | Safety/verification records | Prohibited external-network-scan candidate was denied and never executed. |
| DR-06 | PASS | Run report | Two seed-424242 runs have matching raw and summary semantic hashes. |
| DR-07 | PASS | Run report | Seed 424243 is recorded and has distinct raw and summary semantic hashes. |
| DR-08 | PASS | Run directories | Raw JSONL/Parquet are retained and summaries are generated from raw events. |
| DR-09 | PASS | Three verifier results; manifests; SHA256SUMS | Closed-world hashes and all artifact checksums validate. |
| DR-10 | PASS | Run summaries and report | Only plumbing/count/status evidence was generated; no comparison, effect size, hypothesis status, or performance claim. |

## Code-quality and security gates

- Ruff formatting and lint: PASS across the current 100-file candidate set.
- Strict mypy: PASS across 78 source/test files.
- Unit, property, negative-safety, scenario, and reproducibility tests: PASS; 108 total.
- Branch-aware coverage: 74% aggregate; no arbitrary minimum imposed. Safety-critical limitations
  are documented in `status/COVERAGE_SUMMARY.md`.
- Bandit: PASS; 4,546 source lines, zero findings, four narrow reviewed local-Git-query
  suppressions.
- Secret scan: PASS; zero final candidates after fixed-string false-positive review.
- Dependency audit: PASS; zero known vulnerabilities.
- No dynamic evaluation from configuration, untrusted pickle loading, unrestricted simulation
  subprocess/shell execution, external target adapter, or unconstrained write root was found.

## Documentation gates

- README includes exact frozen reconstruction, doctor, quality, diagnostic, denial, and verification commands.
- `docs/ARCHITECTURE.md` maps all eleven PACD layers and the independent harness.
- Preflight, installation/component/source records, work/command/decision/escalation logs,
  validation report, diagnostic report, doctor report, and final report are retained.
- Unexecuted reportable positive-path validation is explicitly labeled and remains outside
  bootstrap authority.
- Remaining author decisions are the public-license choice and any future protocol/approval.

## Known limitations

- The valid reportable-approval positive path was intentionally not executed.
- The minimal smoke path does not exercise red-agent, orchestration, oversight, or polymorphism
  seams as an empirical experiment.
- CLI dispatch is covered by retained manual doctor, denial, diagnostic, and verifier invocations;
  rare operating-system I/O failure paths remain partially uncovered.
- Legal sufficiency of third-party license metadata was not determined.

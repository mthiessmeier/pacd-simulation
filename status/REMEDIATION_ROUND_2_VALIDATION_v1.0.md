# PACD Bootstrap Remediation Round 2 Validation v1.0

## 1. Validation identity and isolation

This is builder validation, not an independent reclassification.

- Controlling independently reviewed head:
  `613bc65861fb428e8df45f509e568421a8547273`
- Exact clean implementation-validation head:
  `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff`
- Branch: `codex/environment-bootstrap-v1`
- Base: `main`
- Controlling classification: **FAIL — bootstrap not acceptable for merge**
- Validation root:
  `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\round2-validation-cf2dae8-20260823`
- No-hardlink checkout:
  `...\round2-validation-cf2dae8-20260823\checkout`
- Clean offline environments:
  `...\round2-validation-cf2dae8-20260823\env1` and
  `...\round2-validation-cf2dae8-20260823\env2`

`git clone --no-hardlinks` produced the review checkout, which was detached at the exact
implementation head. `fsutil hardlink list uv.lock` listed only the checkout path. The feature
checkout and review checkout were clean during exact-head validation.

Environment identity:

| Item | Exact result |
|---|---|
| Python | CPython `3.13.15` |
| uv | `uv 0.12.5 (210d1f678 2026-08-14 x86_64-pc-windows-msvc)` |
| `uv.lock` SHA-256 | `12372A81D459EC112417B7A76B7FC65A32F5E0DA865B39A466C443563A28F290` |
| Lock resolution | 73 packages, offline, no cache, prereleases disallowed |

The exact tools were:

- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\cache\tools\uv\0.12.5\uv.exe`
- `C:\Users\mthie\AppData\Roaming\uv\python\cpython-3.13.15-windows-x86_64-none\python.exe`

## 2. Environment reconstruction

The normalized command ledger was:

```powershell
git clone --no-hardlinks <feature-checkout> <validation-root>\checkout
git -C <validation-root>\checkout switch --detach cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff
uv lock --check --offline --no-cache --prerelease disallow
uv sync --frozen --offline --cache-dir <workspace-cache> --python <python-3.13.15> --prerelease disallow
uv sync --frozen --offline --cache-dir <workspace-cache> --python <python-3.13.15> --prerelease disallow
pacd-sim doctor
```

The two `uv sync` invocations targeted separate previously absent environments. Each installed
the same 73 locked packages without network access. Doctor was run from the reconstructed tool
environment against the exact clean feature checkout in its required direct-child
`<workspace>/repo` placement; all 12 checks passed, including exact commit, clean branch,
workspace boundary, approval absence, evidence label, and simulated-only execution.

## 3. Quality, tests, coverage, and security

| Check | Result |
|---|---|
| `uv lock --check --offline --no-cache --prerelease disallow` | PASS |
| Two frozen offline reconstructions | PASS — 73 packages each |
| `pacd-sim doctor` | PASS — 12/12 |
| `ruff format --check src tests` | PASS — 85 files |
| `ruff check src tests` | PASS |
| strict `mypy src tests` | PASS — 85 files |
| complete `pytest` | PASS — 183 passed, 1 skipped in 63.81 seconds |
| branch-aware coverage | PASS — 77% overall |
| Bandit recursive source scan | PASS — zero findings |
| detect-secrets all-file scan | PASS after candidate review — no credential material |
| `pip-audit --local --skip-editable` | PASS — no known vulnerabilities |

Coverage retained at `<validation-root>\coverage.json`:

| Measure | Covered / total | Result |
|---|---:|---:|
| Statements | 3,316 / 4,108 | 80.72% |
| Branches | 971 / 1,486 | 65.34% |
| Combined display | — | 77% |

The sole skip was the real Windows directory-symlink case. The non-elevated host returned
`WinError 1314`; no privilege or host policy was changed. Junction/reparse and mocked symlink
paths remained covered.

detect-secrets candidates were reviewed as generated cache tags, governance/status terminology and
hashes, or a fixed property-test literal. None was a credential. No ownership or receipt
capability is retained in committed source, diagnostics, or status output.

## 4. Diagnostic replay and retained-evidence verification

Three fresh runs were created only under the authorized workspace and were explicitly labeled
`NON_REPORTABLE_DIAGNOSTIC`:

| Invocation | Seed | Raw semantic SHA-256 | Summary semantic SHA-256 | Verification |
|---|---:|---|---|---|
| `4c17ca1c5965430f986aa9a49616087b` | 424242 | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` | semantic valid; local identity assured; non-reportable |
| `2eb81a01bceb4e879f23ad58b6211504` | 424242 | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` | semantic valid; local identity assured; non-reportable |
| `4d7a4835b2f843febd258055f0d2e676` | 424243 | `7f7a0eb3d22387a74f4b8fb1dba56715406ef4da81a65e5aefd181f2675b0347` | `3228bda10bc24eb94be30fea5d6010a991996a672f7f4f082e9febfcf27deff6` | semantic valid; local identity assured; non-reportable |

The same-seed semantic hashes matched exactly; both different-seed hashes differed. Each run had a
separate invocation ID and exclusive external receipt.

Full retained-artifact verification at the exact clean head returned:

- `valid=true`;
- `semantic_content_valid=true`;
- `execution_identity_assured=true`;
- `reportable=false`; and
- zero errors.

An old-head diagnostic
`diagnostic-20260823T100919.674020Z-seed-424242-f3ff9a97c6304e73afb87b983922c4d1`
was rejected against the implementation head for code-commit mismatch and missing execution
receipt. An absent-approval reportable attempt exited 3 with `DENIED`; invocation and receipt
counts were unchanged and `configs/protocol/frozen/APPROVAL.json` remained absent.

The review checkout itself is intentionally under `var/tmp`, not the required direct-child
`<workspace>/repo` placement. A bare CLI verify invocation from that checkout therefore rejected
its inferred repository placement. The exact verifier API with explicit clean direct-child
`repo_root` passed all three runs; this was an invocation-context correction, not a weakened
workspace check.

## 5. R-01 through R-04 regression evidence

The explicit round-two regression command selected:

```text
tests/reproducibility/test_parquet_bounded_ingestion.py
tests/reproducibility/test_retained_json_bounds.py
tests/negative/test_invocation_receipts.py
tests/negative/test_harness_transaction_boundaries.py
tests/negative/test_reportable_interlock.py
```

Result: **52 passed, 1 skipped in 27.40 seconds**. The skip was only the real Windows
directory-symlink privilege case.

The tests cover raw/derived decoded caps, aggregate encoded cap, sole accepted materialization,
stable identity after ingestion, JSON terminality, pre-existing staging/final sentinels,
sibling/prefix lookalikes, missing/duplicate/copied/mismatched receipts,
renamed/retimestamped clones, same-content distinct invocations, timeouts before/after raw
evidence, EOF/malformed envelopes, worker receipt-capability separation, and approval hard links.

The instrumented Parquet tests patch every verifier-reachable `pq.read_table` and
`ParquetFile.read` call. Rejected raw, rejected derived, and aggregate-encoded failures perform
zero table materializations; accepted raw and derived artifacts are each materialized exactly once.

Current path/jail equivalents in `test_path_boundaries.py`,
`test_cli_workspace_authority.py`, and `test_path_jail_properties.py` passed 19/19.

## 6. Original and first-remediation challenge-script reruns

The five preserved scripts were copied into
`<validation-root>\challenge-rerun` before adaptation. Prior independent evidence was not
overwritten. Hard-coded source, environment, scratch, and output paths were changed only in the
task-created copies.

| Script | Result at `cf2dae8` | Interpretation |
|---|---|---|
| `authorization_rechallenge.py` | 62/62 checks passed | Forged, copied, stale, context/policy/action/config/state mismatches and collateral mutation failed closed. The arbitrary in-process alternate-governor seam and exact same-prestate replay remain possible as documented boundaries; the public harness owns its trusted governor. |
| `adversarial_rechallenge.py` unchanged assertions | 19 passed, 1 host skip, 15 failed legacy expectations | One “failure” is affirmative remediation: the old exploit expected approval hard-link acceptance, but the current loader rejected it. Fourteen invoke removed private/token/fake-parent APIs (`_new_run_directory` and pre-ownership process shapes). They do not reach current controls. Current equivalent path/ownership/transaction/interlock tests passed 52+19; the historical script was retained rather than rewritten to manufacture a green total. |
| `evidence_rechallenge.py` | Valid baseline; 68/68 expected outcomes; zero setup exceptions | The final copy used a short scratch path and a clean direct-child no-hardlink checkout, and asserted baseline validity before mutations. Duplicate/noncanonical/extra/malformed, provenance, semantic, replay, row/schema, JSONL/Parquet, audit, verification, and metric mutations failed as expected. Results: `<validation-root>\cr\e2\results.json`. |
| `addendum_six_cases.py` | 6/6 rejected; zero setup exceptions | Duplicate/noncanonical/extra JSONL, malformed raw/derived Parquet, and refreshed execution-count cases failed closed. Results: `<validation-root>\cr\e2\addendum-results.json`. |
| `resource_boundary_probe.py` | Raw and derived cap failures were terminal | The meaningful rerun used compact workspace `<validation-root>\rbw` and a clean no-hardlink direct-child checkout. Raw was 5,167 encoded / 536,614 decoded bytes; derived was 4,323 encoded / 524,809 decoded bytes; reduced cap was 65,536 bytes. Instrumentation observed two metadata `ParquetFile` constructions and zero `pq.read_table` or `ParquetFile.read` materializations after rejection. |

The unchanged resource probe's original `var/tmp` repository topology was first rejected by the
workspace-placement guard before reaching Parquet. The compact rerun corrected only topology so
the hostile artifacts reached the target control. The evidence script likewise required a short
Windows scratch path before it could execute its mutation matrix.

Temporary junction and `Q:` SUBST path challenges were removed after the run. All three review
checkouts remained clean at the exact head. No controlled approval, reportable run, network call,
external target, or external execution occurred.

## 7. Transparent retries and corrections

Procedural failures were retained in the audit narrative rather than represented as product
failures:

1. At precursor head `52328b9`, one pytest invocation used a nonexistent `--basetemp` parent
   and produced setup errors. A short existing workspace temp path corrected the invocation; the
   complete exact-head suite then passed 183/1.
2. An initial coverage command had an invalid PowerShell argument and collected no tests. The
   corrected branch-aware command passed the full suite and produced the retained JSON totals.
3. Bandit at `52328b9` found one Low/B101 production assertion. Additive commit `cf2dae8`
   replaced it with an optimization-safe denial; the exact-head Bandit rerun had zero findings.
4. Bare CLI verification inferred the intentionally misplaced review checkout. Explicit
   clean direct-child repository authority corrected the context while preserving the placement
   guardrail.
5. The first resumed focused and evidence-script scratch roots exceeded Windows path limits.
   Short workspace-contained roots corrected those invocation errors without weakening any bound.
6. Legacy scripts that hard-code removed private APIs are reported with their compatibility
   failures; current equivalent tests were executed rather than silently relabeling those failures.

## 8. Unexecuted or physically blocked tests

- A real Windows directory symlink was not created because the host denied it with WinError 1314.
  No elevation or security-policy change was requested. Junction/reparse and mocked cases passed.
- Open-handle approval replacement was skipped because Windows denied replacement. In-place
  mutation and stable repeated-read tests passed.
- A controlled hard link at the forbidden approval path was not created. The same loader behavior
  was exercised with a safe non-controlled hard link, and public reportable execution remained
  denied before output creation.
- Fourteen literal legacy private-API assertions could not exercise current controls because the
  referenced APIs no longer exist or now require parent-created authority. Their current semantic
  equivalents are covered by the passing round-two and path/jail suites.
- No reportable experiment, real protected-path/device/ADS write, real network/cloud/endpoint/
  identity call, real external target, production adapter, or shell adapter was executed.
- The local receipt was not represented as author-signed or adversary-resistant. Separate
  same-user threat probes confirmed that a caller with arbitrary direct write access to both local
  control stores can forge cooperative records; this is documented as a trust-boundary limitation,
  not hidden as an unexecuted guarantee.

## 9. Repository and host state

At implementation validation:

- the repository was private;
- PR #1 was open, not draft, unmerged, base `main`, head
  `codex/environment-bootstrap-v1`;
- no `.github/workflows` path existed;
- no `APPROVAL.json` existed;
- the only execution broker was `SimulatedExecutionBroker`;
- the adapter name was `simulated_only`, `network_enabled=false`, and the sole supported
  transition was synthetic `isolate_session`;
- the prohibited `external_network_scan` token existed only as a denied synthetic scenario;
- source had no socket/HTTP/cloud/endpoint/identity client, shell execution, dynamic loader/FFI
  adapter, or production credential path; and
- subprocess use was limited to fixed `shell=False`, bounded, read-only local Git provenance
  queries; multiprocessing was limited to the bounded local diagnostic worker.

This static/runtime inventory establishes the absence of an application-exposed external
execution path. It does not claim that arbitrary Python packages or the host operating system are
incapable of networking when separately invoked.

## 10. Validation conclusion

Round-two builder validation passes at the exact clean implementation head. That is not an
independent merge classification. The accepted classification remains:

**FAIL — bootstrap not acceptable for merge**

The exact pushed report-bearing head requires a new complete independent re-challenge while PR #1
remains open and unmerged.

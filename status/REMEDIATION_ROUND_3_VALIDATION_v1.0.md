# PACD Bootstrap Remediation Round 3 Validation v1.0

## 1. Validation identity and isolation

This is builder validation, not an independent reclassification.

- Controlling independently reviewed head:
  `4cba65779753a3096e2bd7551e7d4ff7321df4a2`
- Exact clean implementation-validation head:
  `edd016cdca8a182d7014adf3ef47c8648b9f9e5d`
- Branch/base: `codex/environment-bootstrap-v1` / `main`
- Controlling classification: **FAIL — bootstrap not acceptable for merge**
- No-hardlink validation checkout:
  `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\repo\pacd-simulation-round3-validation-edd016cd`
- Validation root:
  `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\round3-validation-edd016cd`
- Previously absent reconstructed environments: `env1` and `env2` below that validation root

`git clone --no-hardlinks --branch codex/environment-bootstrap-v1 --single-branch` created the
validation checkout. It had no object alternates, retained the named branch required by doctor,
resolved to the exact implementation head, and was clean before and after validation.

Environment identity:

| Item | Exact result |
|---|---|
| Python | CPython `3.13.15` |
| uv | `uv 0.12.5 (210d1f678 2026-08-14 x86_64-pc-windows-msvc)` |
| `uv.lock` SHA-256 | `12372A81D459EC112417B7A76B7FC65A32F5E0DA865B39A466C443563A28F290` |
| Offline resolution | 73 packages; no cache for lock check; prereleases disallowed |

## 2. Command ledger and environment reconstruction

Normalized exact-head commands were:

```powershell
git clone --no-hardlinks --branch codex/environment-bootstrap-v1 --single-branch `
  <feature-checkout> <direct-child-validation-checkout>
git -C <validation-checkout> rev-parse HEAD
git -C <validation-checkout> status --porcelain=v1
uv lock --project <validation-checkout> --check --offline --no-cache --prerelease disallow

$env:UV_PROJECT_ENVIRONMENT = <previously-absent-env1>
uv sync --project <validation-checkout> --frozen --offline `
  --cache-dir <workspace-uv-cache> --python <CPython-3.13.15> --prerelease disallow

$env:UV_PROJECT_ENVIRONMENT = <previously-absent-env2>
uv sync --project <validation-checkout> --frozen --offline `
  --cache-dir <workspace-uv-cache> --python <CPython-3.13.15> --prerelease disallow

pacd-sim doctor --repo-root <validation-checkout> --workspace-root <workspace>
```

Both frozen offline synchronizations succeeded and installed the same 73 locked packages. Doctor
passed all 12 checks, including exact clean branch/commit, workspace confinement, lock identity,
strict governed configuration, simulated-only/network-disabled policy, and absent approval.

## 3. Quality, complete tests, coverage, and security

Commands and exact outcomes:

| Command | Result |
|---|---|
| `ruff format --check . --no-cache` | PASS — 118 files already formatted |
| `ruff check . --no-cache` | PASS |
| `mypy src tests --no-incremental --cache-dir <external-cache>` | PASS — 88 source files |
| complete `pytest -p no:cacheprovider` | PASS — 230 passed, 1 skipped in 61.00 s |
| complete `pytest --cov=pacd_sim --cov-branch` | PASS — 230 passed, 1 skipped in 74.03 s |
| `bandit -c pyproject.toml -r src` | PASS — zero issues; 8,424 lines scanned |
| `detect-secrets scan --all-files` | PASS — exit 0; no credential material |
| `pip-audit --local --skip-editable` | PASS — no known vulnerabilities |

Branch-aware aggregate coverage, retained at
`...\round3-validation-edd016cd\coverage.json`:

| Measure | Covered / total | Result |
|---|---:|---:|
| Statements | 3,489 / 4,319 | 80.78% |
| Branches | 1,054 / 1,620 | 65.06% |
| Combined | — | 76.49% (`76%` display) |

The sole skip was the real Windows directory-symlink test. The non-elevated host returned
`WinError 1314`; no elevation or host-security change was requested. Real NTFS junction tests ran
and passed.

detect-secrets candidates were existing governance terminology, committed status/review hashes,
and a fixed property-test literal. None was a credential. The newly preserved independent review
caused expected high-entropy hash candidates; it was not changed to suppress them.

## 4. Focused remediation and regression suites

Each focused suite was rerun separately at the exact clean implementation head:

| Boundary | Tests | Result |
|---|---|---|
| N-01 exact lexical control stores | `test_control_store_lexical_paths.py` | 10 passed |
| N-03 nested/terminal retained data | `test_terminal_retained_depth.py`, `test_retained_json_bounds.py` | 26 passed |
| R-01 bounded Parquet | `test_parquet_bounded_ingestion.py` | 7 passed |
| R-04 reportable/approval hard links | `test_reportable_interlock.py` | 10 passed, 1 identical host skip |
| Receipt lifecycle/transactions/assurance | three receipt and transaction suites | 46 passed |
| Authorization/governor/state/defender/execution | seven negative, property, and unit suites | 46 passed |

The N-01 suite uses real non-elevated NTFS junctions and asserts structured CLI denial, no target
entry or byte change, and ordinary-directory restoration. The N-03 suite includes the exact
1,500-level review payload, exact depth 64 acceptance, depth 65 rejection, terminal inventory and
strict-document failures, structured CLI/API results, and monkeypatched proof of zero downstream
consumers. R-01 retains instrumented zero-materialization and at-most-once accepted-materialization
proof. R-04 retains stable single-link approval reads and unconditional bootstrap denial.

## 5. Same-seed, different-seed, and exact-head verification

Three fresh runs were created only in `<workspace>\var\runs` and labeled
`NON_REPORTABLE_DIAGNOSTIC`:

| Invocation | Seed | Raw semantic SHA-256 | Summary semantic SHA-256 |
|---|---:|---|---|
| `95881fbe0e4a401db8b851255c9be89b` | 424242 | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` |
| `d37589ccb45e45f0b47a4876042a7caa` | 424242 | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` |
| `16c8f0a1c707449c8bbb02acca0ca00b` | 424243 | `7f7a0eb3d22387a74f4b8fb1dba56715406ef4da81a65e5aefd181f2675b0347` | `3228bda10bc24eb94be30fea5d6010a991996a672f7f4f082e9febfcf27deff6` |

Same-seed raw and summary hashes matched exactly. Both different-seed hashes differed. Complete
verification of every fresh run returned:

- `status=VERIFIED`;
- `valid=true`;
- `semantic_content_valid=true`;
- `execution_identity_assured=true`;
- `identity_assurance_scope=LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING`;
- `historical_control_file_inode_continuity_assured=false`;
- `reportable=false`; and
- zero errors.

This is cooperative local binding, not historical inode continuity or reportable attestation.

## 6. Old-head rejection and absent-approval denial

The preserved diagnostic
`diagnostic-20260823T173646.199584Z-seed-424242-88b6d20deb1b418bbbbd2a467f02c908`
records code head `4cba65779753a3096e2bd7551e7d4ff7321df4a2`. Verification against
`edd016cdca8a182d7014adf3ef47c8648b9f9e5d` returned structured `INVALID`,
`valid=false`, both semantic and identity flags false, historical continuity false,
`reportable=false`, and the exact error:

```text
Manifest code_commit does not match the controlled checkout
```

With `configs/protocol/frozen/APPROVAL.json` absent, a public `--reportable` request exited `3`
with structured `DENIED`, `valid=false`, `execution_identity_assured=false`, the exact cooperative
scope, historical continuity false, and reportable false. Direct child counts were unchanged:

| Store | Before | After |
|---|---:|---:|
| Runs | 33 | 33 |
| Receipts | 10 | 10 |
| Invocations | 10 | 10 |

The forbidden approval path remained absent.

## 7. Independent patch audit and transparent retries

A separate read-only patch audit found and prompted correction of four pre-commit issues:

1. strict-document failure initially allowed later strict reads/checksum inspection;
2. missing, empty, or extra artifact inventory initially allowed later consumers;
3. exact depth 64 was initially charged again for an enclosing semantic event record; and
4. the real-junction fixture initially did not guarantee restoration after partial setup failure
   or detect empty-directory writes.

Each was corrected before the implementation commit and received a regression. The final audit
reported no remaining actionable N-01, N-02, N-03, cleanup, or scope defect.

Procedural retries are not represented as product failures:

- two preliminary pytest basetemps were too long or had a missing parent on Windows; short
  workspace-local basetemps passed;
- the first exact-depth verifier test intentionally mutated a retained payload but had not yet
  supplied the same bounded payload to independent event reconstruction; the regression was
  corrected to isolate the depth-envelope boundary; and
- the first hermetic receipts-junction CLI case spawned a child that did not inherit test-only
  workspace monkeypatches; CLI serialization was retained while the hermetic test routed the
  diagnostic in-process to exercise the intended boundary.

After those corrections, the final clean no-hardlink checkout completed every required command
with the outcomes above.

## 8. Repository, host, and research-integrity state

At validation time:

- GitHub reported the repository private and PR #1 open, not draft, unmerged, base `main`, head
  `codex/environment-bootstrap-v1`;
- the clean validation checkout remained exactly at `edd016cd...` with the unchanged lock hash;
- no `.github/workflows` directory or `APPROVAL.json` existed;
- the implementation delta from `4cba657...` contained only the preserved review, documentation,
  intended simulator/verifier hardening, and tests;
- no production adapter, real target, network/cloud/endpoint/identity operation, external
  integration, credential, public license, or host-security change was introduced; and
- no reportable experiment was executed.

The validation creates only non-reportable local diagnostic evidence and does not establish an
effect, safety, benchmark, generalization, publication, or operational-readiness claim.

## 9. Validation conclusion

Round-three builder validation passes at the exact clean implementation head. That is not an
independent merge classification. The accepted classification remains:

**FAIL — bootstrap not acceptable for merge**

The exact pushed report-bearing head requires a new complete independent re-challenge while PR #1
remains open and unmerged.

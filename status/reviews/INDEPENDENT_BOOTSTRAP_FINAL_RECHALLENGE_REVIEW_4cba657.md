# Independent PACD Bootstrap Final Re-Challenge Review

**Review date:** 2026-08-23 (America/New_York)  
**Repository:** `mthiessmeier/pacd-simulation` (private)  
**Pull request:** PR #1 — Bootstrap bounded local PACD simulation environment  
**Base/head:** `main` / `codex/environment-bootstrap-v1`  
**Exact reviewed head:** `4cba65779753a3096e2bd7551e7d4ff7321df4a2`  
**Prior independently reviewed head:** `613bc65861fb428e8df45f509e568421a8547273`  
**Builder implementation-validation head:** `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff`  
**Evidence class used:** `NON_REPORTABLE_DIAGNOSTIC`

This was an independent review-only challenge. The feature checkout was not modified, no commit or merge was made, no controlled `APPROVAL.json` was created, and no reportable or external execution was attempted. `CURRENT_STATUS_v1.1.md`, `REMEDIATION_ROUND_2_REPORT_v1.0.md`, and `REMEDIATION_ROUND_2_VALIDATION_v1.0.md` were treated as builder claims, not proof.

## 1. Outcome

The locked environment reconstructed twice offline, doctor passed 12/12, all quality and security gates passed, the authoritative complete suite passed 183 tests with one host-privilege skip, branch-aware coverage was 77%, exact-head diagnostics reproduced, old-head evidence was rejected, and reportable mode was denied before output creation.

R-01 terminal bounded Parquet ingestion and R-04 approval hard-link rejection held under independent challenge. The parent-owned worker transaction, receipt exclusivity, clone rejection, timeout handling, raw-evidence retention, and most R-02/R-03 controls also held.

Merge is nevertheless blocked by three current-scope findings:

1. Real NTFS parent junctions at `var/receipts` and `var/invocations` bypass the intended lexical controlled-location checks while verification can still return `execution_identity_assured=true` and `valid=true`.
2. A byte-identical, singly linked replacement receipt with a different inode—and the same replacement of its ownership marker—retains identity assurance. This does not establish malicious-same-user attestation, but it fails the expressly challenged inode-mismatch behavior of the local anchor.
3. A small retained raw payload containing 1,500 nested JSON objects makes `verify_run()` raise an uncaught `RecursionError` instead of returning a structured invalid verdict. The strict validator detects the excessive nesting, but later semantic hashing reprocesses the rejected payload.

The first two affect current controlled-path and local execution-identity assurance; the third affects current hostile-evidence/resource handling and verifier fail-closed behavior. They cannot be deferred as future reportable-mode or cryptographic-attestation conditions.

## 2. Repository, PR, checkout, and history

Authoritative GitHub queries returned:

| Property | Independent result |
|---|---|
| Remote PR head | `4cba65779753a3096e2bd7551e7d4ff7321df4a2` |
| Privacy | `PRIVATE`, `isPrivate=true` |
| Default branch | `main` |
| PR state | `OPEN`, `isDraft=false`, `mergedAt=null` |
| Base/head | `main` / `codex/environment-bootstrap-v1` |
| Merge state at review | `CLEAN` |

A fresh local no-hardlink clone was created as the required direct child:

`C:\Users\mthie\PACD-Workspaces\PACD-Simulation\repo\pacd-simulation-final-review-4cba657`

It used review-only branch `independent-final-rechallenge-4cba657` at the exact SHA. A scan of all 137 tracked regular files found no link count other than one. The review checkout and the untouched feature checkout were clean at the same exact head at final hygiene.

The additive parent chain is:

| Commit | Exact parent | Subject / role |
|---|---|---|
| `613bc65861fb428e8df45f509e568421a8547273` | `cfeb5137a397294a310199f93b165b25bc5a03d6` | Prior reviewed status head |
| `c2b2272d898a8d2314871f85744c065d4cc8f84e` | `613bc65861fb428e8df45f509e568421a8547273` | Preserve prior independent review |
| `01451792ef28ad99c3be630a19f42d66cd6fa293` | `c2b2272d898a8d2314871f85744c065d4cc8f84e` | Reject hard-linked approval records |
| `52328b904accfc46c711085b0862c0421aacc1e0` | `01451792ef28ad99c3be630a19f42d66cd6fa293` | Bounded evidence and parent-owned receipts |
| `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff` | `52328b904accfc46c711085b0862c0421aacc1e0` | Optimization-safe receipt-authority denial |
| `4cba65779753a3096e2bd7551e7d4ff7321df4a2` | `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff` | Versioned round-two status/validation records |

`git merge-base 613bc658... 4cba657...` returned exactly `613bc658...`; `git rev-list --merges` returned none. The GitHub PR timeline contained 13 commit events and no force-push or merge event. This is affirmative evidence of a linear additive history and no observed force-push/rebase/rewrite; Git metadata cannot prove a universal negative beyond the retained ancestry and GitHub event record.

The exact `cf2dae85..4cba657` delta contains only:

- `status/CURRENT_STATUS_v1.1.md`
- `status/REMEDIATION_ROUND_2_REPORT_v1.0.md`
- `status/REMEDIATION_ROUND_2_VALIDATION_v1.0.md`
- `status/reviews/INDEPENDENT_BOOTSTRAP_RECHALLENGE_REVIEW_613bc658.md.sha256`

No simulator source, test, configuration, or dependency file changed in that delta. The preserved prior review hash independently matched its companion record: `6D1F4756DA2EA427FA601DC3215C1586C9A07057C92F1780C019FE8E5FDB253B`.

## 3. Environment reconstruction

| Item | Exact result |
|---|---|
| `uv.lock` SHA-256 | `12372A81D459EC112417B7A76B7FC65A32F5E0DA865B39A466C443563A28F290` |
| Python | CPython `3.13.15` |
| uv | `0.12.5 (210d1f678 2026-08-14 x86_64-pc-windows-msvc)` |
| Lock check | PASS; 73 packages; offline; no cache; prereleases disallowed |
| Frozen reconstruction 1 | PASS; previously absent `env1`; 73 locked packages |
| Frozen reconstruction 2 | PASS; previously absent `env2`; 73 locked packages |

Exact tool paths were:

- uv: `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\cache\tools\uv\0.12.5\uv.exe`
- base Python: `C:\Users\mthie\AppData\Roaming\uv\python\cpython-3.13.15-windows-x86_64-none\python.exe`
- reconstructed environments: `...\var\tmp\final-rechallenge-4cba657\env1` and `env2`

The first synchronization attempt intentionally remained offline but pointed at `var/cache/uv`, which lacked the locked SciPy wheel. uv refused rather than using the network. After resolving and verifying the two exact task environment paths, the incomplete task-created directory was removed; both paths were confirmed absent, then each was reconstructed sequentially from `var/cache/uv-project`. This was a transparent cache-selection retry, not a product or lock failure.

`pacd-sim doctor --repo-root $REVIEW --workspace-root $WS` passed all 12 checks. It reported exact Python and lock pin, clean Git state, direct-child workspace placement, confined output, protected-path exclusion, strictly validated configuration, `simulated_only`, `network_enabled=false`, absent approval/reportable denial, and all assurance commands present.

## 4. Standard checks

| Check | Result |
|---|---|
| `uv lock --check --offline --no-cache --prerelease disallow` | PASS; 73 packages |
| Ruff format | PASS; 85 files already formatted |
| Ruff lint | PASS |
| strict mypy | PASS; 85 source/test files |
| complete pytest | PASS; 183 passed, 1 skipped in 43.16 s |
| branch-aware pytest/coverage | PASS; 183 passed, 1 skipped in 47.64 s |
| coverage | 3,316/4,108 statements; 971/1,486 branches; displayed total 77% |
| Bandit recursive source scan | PASS; zero findings |
| detect-secrets all-file scan | PASS after candidate review; no credential material |
| pip-audit local environment | PASS; no known vulnerabilities; editable project skipped |

The sole test skip was a real Windows directory-symlink case denied by the non-elevated host with `WinError 1314`; no elevation or policy weakening was requested. A first full pytest invocation used an overlong review `--basetemp` and produced three Windows path-length setup errors after 180 passes and one skip. The unchanged-code authoritative rerun used the short `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\t\fpr2` base and passed 183/1. Coverage used the same short-root correction. These were invocation-path errors, not hidden test failures.

detect-secrets candidates were manually identified as generated Ruff cache metadata, governance/hash terminology, committed status hashes, and a fixed property-test literal. No secret, capability, token, or credential material was found.

## 5. Diagnostic replay, exact-head verification, and denial

Three fresh diagnostics were run only through public non-reportable mode:

| Seed / invocation | Raw semantic SHA-256 | Summary semantic SHA-256 | Verification |
|---|---|---|---|
| `424242` / `88b6d20deb1b418bbbbd2a467f02c908` | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` | semantic true; identity true; valid true; reportable false |
| `424242` / `95480b85d0214ae1a8bb281f16902220` | same | same | semantic true; identity true; valid true; reportable false |
| `424243` / `fb5d43db9d7446b2ad39657944d1b44b` | `7f7a0eb3d22387a74f4b8fb1dba56715406ef4da81a65e5aefd181f2675b0347` | `3228bda10bc24eb94be30fea5d6010a991996a672f7f4f082e9febfcf27deff6` | semantic true; identity true; valid true; reportable false |

Same-seed semantic hashes matched exactly; different-seed raw and summary hashes both differed. The same-seed runs received different invocation IDs and separate receipts.

An old-head diagnostic from `613bc658...` was rejected against the exact current checkout for code-commit mismatch and missing receipt. An exact byte copy of a current package remained semantically valid but received `execution_identity_assured=false` and overall non-success without its corresponding controlled receipt.

Public `--reportable` exited 3 with `DENIED` before invocation, receipt, or run creation. A final R-04 probe measured runs/receipts/invocations as `[30, 7, 7]` before and after. The controlled approval path remained absent.

## 6. Original F-01 through F-08 disposition

| Finding | Final re-challenge disposition | Evidence and qualification |
|---|---|---|
| F-01 — workspace/write authority | Corrected for public diagnostic paths | CLI, direct public run, and worker paths require the designated workspace, direct-child repository, and exact `var/runs` sink. Broader roots, alternate checkout placement, child/temp/sibling roots, traversal-equivalent canonical forms, ADS/device forms, and a real junction were denied. The new receipt/invocation control-store junction issue is separately recorded under R-02/R-03. |
| F-02 — forged governor authorization | Corrected in the harness; generic constructor seam remains | The 62-case independent authorization probe rejected forged/copied/stale/policy/context/action mutations and the public harness constructs the controlled governor. An arbitrary in-process caller can still construct the low-level broker with a permissive or duck-typed governor; that caller can execute the one supported synthetic transition. This is outside the public harness boundary and must not become an adapter injection point. |
| F-03 — incomplete action/state binding | Corrected for current harness semantics | Action ID/type/target/config/schema, policy/context/state digests, tick, and complete before/after state were bound. Cross-state replay and collateral assets/identities/sessions/credentials/services/missions/dependencies/config/schema mutations failed. A content-identical decision can be reused against the same immutable pre-state because there is no one-shot ledger; reuse after state change fails. |
| F-04 — refreshed evidence closure | Substantive closure corrected; hostile nested payload unresolved | Refreshed configuration, seed, action, decision, execution, verification, audit, ordering, run-ID clone, metrics, JSONL/CSV/Parquet, and checksum mutations were rejected semantically or by identity. The newly found nested-payload exception prevents a complete fail-closed disposition. |
| F-05 — strict parsing/resource bounds | Parquet corrected; retained nested JSON unresolved | Duplicate/extra/noncanonical/nonfinite/malformed/deep/oversized configuration and retained documents, exact schema/row/inventory checks, and bounded Parquet ingestion mostly held. A 1,500-level valid payload still escapes as `RecursionError` during later semantic normalization. |
| F-06 — timeout/failed transaction | Core parent transaction corrected; local anchor residuals unresolved | Parent-before-worker ownership, no receipt capability in the child, exact staging/final authority, sentinel preservation, EOF/malformed/start failure, timeout before/after raw, termination/no orphan, and failed evidence held. Post-hoc invocation-parent junction and control-record inode replacement still undermine local identity assurance. |
| F-07 — approval/interlock | Corrected for current bootstrap | Non-controlled hard-linked approval was rejected; opened/read/final path link count checks exist; duplicate/malformed/indirect/wrong binding paths fail closed; public reportable denial remains pre-output. |
| F-08 — prerelease policy | Corrected | Project metadata and exact command disallow prereleases; the offline/no-cache lock check passed and no unstable locked release was found. |

## 7. R-01 through R-04 disposition

### R-01 — terminal bounded Parquet ingestion: corrected in exercised scope

An independent 22-case probe was rerun under the newly reconstructed `env1` and passed all assertions. Structured result:

`...\parquet\probe-20260823T174358.013118Z\parquet_probe_results.json`  
SHA-256: `CA03974082759C3E30F89D208BE5897E07D5030A8D2A7175943B92035B06008B`

It instrumented the shared `pyarrow.parquet` module and every verifier-reachable `pq.read_table` and `ParquetFile.read` call. Results:

- both Parquet artifacts were preflight-opened before either was materialized; observed order was raw open, derived open, raw read, derived read; each was read once and `pq.read_table` was never called;
- raw, derived, and aggregate encoded/decoded-cap failures caused zero table materializations and zero downstream semantic/label/metric/receipt/checksum consumers;
- exact schema, row count, row groups, column chunks, footer metadata, Thrift strings, malformed footer, and missing-artifact/fallback challenges failed before materialization;
- compressed raw (`5,167` encoded / `536,614` decoded bytes) and derived (`4,358` / `524,854`) exceeded a safely reduced 64 KiB decoded cap and terminated without later reads;
- oversized payload/identifier strings were checked after the artifact's sole globally bounded materialization but before row conversion or downstream consumption.

Qualification: production-size limits were not exhausted, every codec/page grammar was not fuzzed, and no hand-crafted native Parquet with a deliberately lying footer was created. A metadata-underreporting proxy exercised the post-materialization guard. These are assurance limits, not demonstrated R-01 bypasses.

### R-02/R-03 — parent ownership and local receipts: materially improved but not closed

Positive independent results:

- core receipt suite: 11 passed;
- lifecycle/clone suite: 7 passed, 1 failed on the new junction finding, 1 real-file-symlink skip; excluding those two cases, 7 passed/2 deselected;
- worker-envelope/parent-before-start suite: 2 passed;
- direct worker call without `_ownership` failed with `TypeError` before any write;
- marker/capability/path/device/inode/run binding mutations, staging/final sentinels, siblings/prefix lookalikes, occupied final path, missing/duplicate/copied/altered/hard-linked receipts, run-directory inode replacement, wrong receipt capability, and child-selected receipt/run results failed closed;
- process-start failure, EOF, malformed/partial envelope, real reduced-deadline timeouts before and after raw creation, raw retention, and orphan prevention held;
- renamed and retimestamped refreshed clone remained semantic-only and did not gain identity;
- two same-seed deterministic runs received distinct invocation IDs and receipts;
- missing receipt produced semantic true, identity false, reportable false, valid false, and CLI exit 1.

The real NTFS parent-junction and byte-identical control-record replacement results in Section 9 keep R-02/R-03 unresolved.

### R-04 — approval hard links: corrected for the current bootstrap

A safe, non-controlled approval file with `st_nlink=2` was rejected. Source inspection found five link-count checks spanning the opened handle, repeated reads, and final identity comparison. Missing, malformed, duplicate-key, missing-key, extra-key, wrong-commit, dirty-tree, wrong configuration/seed-registry/baseline/metric hash, wrong protocol, lexical outside-path, parent junction/reparse, and in-place repeated-read mutation variants all failed closed through pure validation/current regressions. Public reportable mode created no invocation, receipt, or run. No controlled approval record was created. Real file-symlink creation and concurrent open-handle replacement remained physically blocked as listed in Section 16.

## 8. Adapted legacy and adversarial test disposition

The original authorization and adversarial scripts were copied byte-for-byte before execution:

- `authorization_rechallenge_original.py`: `9066492080E6E221A5F096F929C54C68CC4ED8BF9042AAE4108212403021E285`
- `adversarial_rechallenge_original.py`: `AAC7468223E25FD8D9CF781E4FB9B2307652D5BF28E9A55ED5DE6C2CA141BBD7`

The original authorization logic was run through a review-only current-checkout adapter and passed 62/62. It covered all decision and action fields; context/policy/state swaps; cross-state replay; non-reversible, unknown, unsupported, escalated, prohibited, and external action denial; complete collateral state; and alternate-governor behavior.

The pristine legacy adversarial run produced 19 passes, one host replacement/symlink-style skip, and 15 failures. Those are not classified as product failures without interface translation:

- one expected old hard-linked-approval acceptance is now intentionally false because R-04 rejects it;
- 14 reference removed private helpers, token-only ownership, or fake-parent assumptions replaced by the parent authority object.

Equivalent current interfaces were exercised by the current path/parser/R-04 probes, the 11-case receipt suite, 7-case lifecycle suite, 2-case worker-envelope suite, and complete/selected committed tests. They test the underlying security properties rather than awarding credit for removed APIs.

Additional independent results:

- path probe: canonical `repo/..` authority accepted; broader workspace and alternate non-direct-child checkout denied; ADS, device, child, temporary, sibling-lookalike, and real junction output roots denied; no count changed;
- hostile configuration probe: YAML 11/11 rejected (duplicate, explicit tag, 21 aliases, recursive alias, excessive depth, oversized, NaN, infinity, non-string key, nonmapping root, malformed); JSON 7/7 rejected (duplicate, NaN, infinity, deep, oversized, nonmapping root, malformed);
- an earlier current-control selection passed 100 with one real-symlink privilege skip; a final explicitly named control selection passed 129 with the same single skip;
- complete pytest additionally covered duplicate action IDs and approved actions absent from defender proposals;
- resource regressions covered event/action limits above 100, aggregate output limits, audit payload bounds, and timeout/termination paths; the independent compressed-Parquet and spawned-worker probes challenged the corresponding implementation paths outside the committed regressions.

## 9. Newly discovered findings

### N-01 — merge blocking — receipt/invocation parent junctions retain identity assurance

A real NTFS junction was placed at lexical `workspace/var/receipts` before a diagnostic and pointed to a sibling workspace directory. The parent wrote the genuine receipt through that junction into the sibling target. Verification returned:

`semantic_content_valid=true`, `execution_identity_assured=true`, `valid=true`, `reportable=false`, `errors=[]`.

Post-run replacement of `var/receipts` by a sibling junction produced the same result. Replacing `var/invocations` by a sibling junction also left identity and overall validity true. `fsutil reparsepoint query` confirmed mount-point tag `0xa0000003`, and `path_has_symlink_or_reparse` returned true when called on the lexical paths.

Root cause: `assert_write_path` resolves at `paths.py:161`. `receipt_path_for` resolves `var/receipts` at `receipts.py:128-129`; creation then checks the already-resolved path at `receipts.py:390-395`. Verification similarly obtains an already-resolved receipt path at `receipts.py:545`, and marker verification resolves at `receipts.py:607-610`. The lexical reparse walk therefore receives a path from which the junction has disappeared.

Impact is bounded to the PACD workspace and does not enable reportable mode or external execution. However, a pre-existing junction defeats ordinary cooperative exact controlled-location enforcement, and post-hoc junctions defeat the verifier's explicit indirect-path assurance. This is a current local-identity defect, not a demand for cryptographic attestation.

Evidence: `...\receipts\R02_R03_RECEIPT_CHALLENGE_NOTES.md`, SHA-256 `FA61B61B08CD716C56FD71EEE3B2C2A7375AE3A0256A1CE62521704AFCF3921B`.

### N-02 — merge blocking specification gap — inode-replaced local control records remain assured

A receipt was replaced before verification by a new singly linked file containing byte-identical canonical bytes at the same path. Its `st_ino` changed, yet identity and overall validity stayed true. Replacing the ownership marker in the same way also changed its inode while preserving identity assurance.

This requires control-store write access and cannot be elevated into author signing, trusted time, or malicious-same-user resistance; the project correctly disclaims those properties. Nevertheless, the final challenge explicitly required an inode-mismatched receipt to fail execution-instance assurance. Current stable reads bind the handle to the path during one read, but there is no persistent parent anchor against which a replacement inode is compared. The observed behavior must therefore be recorded as an unresolved local-anchor requirement, not silently subsumed under cryptographic limitations.

### N-03 — merge blocking — deeply nested retained payload escapes `verify_run`

A refreshed-closure raw event used valid, canonical `payload_json` containing 1,500 nested objects. The payload was 16,501 bytes; complete raw artifacts remained small (`events.parquet` 31,171 bytes; `events.jsonl` 35,174 bytes). The strict retained validator detected excessive nesting, but `verify_run` continued with retained rows and called `semantic_events_hash(raw_rows)` at `verify.py:638`. Recursive `_normalize_semantic` at `manifest.py:80-92` then raised an uncaught `RecursionError`; the exception clause at `verify.py:643` does not include it.

Direct API verification did not return a `VerificationResult`. The public CLI caught the escaped exception at its outer boundary, emitted `status=FAILED` with reason `RecursionError: maximum recursion depth exceeded`, and exited 1. No tampered package was accepted, but a correct invalid verdict and structured semantic/identity fields were not returned. This violates fail-closed verifier behavior for a bounded hostile retained artifact and shows that a strict-ingestion error is not terminal for every later consumer.

The independent evidence matrix totals were 113 cases: 111 semantic rejections, one coherent clone rejected by identity only, one exception, and zero invalid-package acceptances. The adapted legacy matrix was 68/68 expected; expanded additions were 41 rejections plus this exception; malformed-row addendum was 3/3 rejected.

Evidence:

- `...\evidence\expanded\results.json`, SHA-256 `73DBCCCF438E92036C58023A37F744AC4BC2E330FA4E10E7E762BE6F7DEE6535`
- adapted matrix, SHA-256 `E7D49EE30D2F6AEE7E1015E5CE38EDF27AE5D99E74415A5E24313D608BE5ECCA`
- malformed-row addendum, SHA-256 `2C56C3A5C12027803D1887243AC7ECB7ACA501272500EE8D6DAE5D6B27C9FA1F`
- identity/old-head results, SHA-256 `894A4F9AE3911B91E9BFF3CB9C25B5FF6DFA03C4465C7ACD96FF6F0FDC73E0C0`

## 10. Execution-authorization assessment

The supported harness reevaluates actions through its own governor, requires exact proposal membership, and binds decision, policy, context, configuration, schema, target, tick, and complete pre-state. All 15 decision fields and all action fields were independently altered one at a time and rejected. A decision from an alternate policy, later context, altered entity, later tick, changed state/configuration/schema, or resulting state failed before mutation. Only the supported reversible automatic `isolate_session` synthetic transition executed. Prohibited, escalated, unknown, unsupported, external, and non-reversible candidates never executed.

Complete after-state verification rejected collateral changes in state ID, tick, schema/configuration, assets, identities, sessions, credentials, services, mission functions, and dependencies. Duplicate action IDs and execution of a configured action absent from defender proposals failed closed.

The low-level `SimulatedExecutionBroker` constructor accepts an arbitrary `SafetyGovernor` or duck-typed permissive object, and the independent probe demonstrated that such an arbitrary in-process caller can execute the synthetic transition. The public harness does not expose that injection and constructs its controlled governor. This is an architectural seam, not a production adapter; it must remain unexposed.

## 11. Evidence-integrity and research-integrity assessment

Positive evidence:

- exact current-head baseline verified semantically and by local receipt;
- same-seed replay hashes matched and different-seed hashes differed;
- old-head evidence, current copies without receipts, and coherent renamed/retimestamped clones did not gain current identity;
- refreshed configuration, seed registry, candidate/action, decisions, executions, verification, audit, event meaning/order/count, derived metrics, execution count, JSONL/CSV/Parquet, schemas, manifests, checksums, missing/extra artifacts, duplicate/gapped sequences, and malformed/nonfinite/unknown rows were rejected;
- R-01 demonstrated terminal bounded Parquet behavior in the complete verifier;
- failed worker evidence and raw artifacts were retained only through parent-owned transaction paths in the exercised non-junction cases;
- all generated runs remained explicitly non-reportable.

Limitations/findings:

- N-03 permits hostile nested retained content to escape the structured verifier contract;
- N-01/N-02 mean local execution identity is not assured under the explicitly challenged parent-junction/inode substitutions;
- audit writing is append-oriented at the application boundary, not WORM, signed, hash-anchored externally, or independently timestamped;
- the verifier shares schemas and deterministic builders with the producer, leaving common-mode risk;
- no effect, benchmark, comparative, generalization, publication, or operational-readiness claim was produced or is supported.

## 12. Local receipt threat-model assessment

The source, CLI fields, and builder reports correctly distinguish `semantic_content_valid`, `execution_identity_assured`, `reportable`, and overall validity. Missing identity assurance returns non-success and cannot be mistaken for a fully verified package. The receipt binds invocation/run, exact commit and lock hash, configuration/seed hashes, raw/summary semantics, package digest, timestamps, final path, ownership digest, and run-directory device/inode. Creation is exclusive and same-seed runs receive separate anchors.

The documentation is appropriately explicit that this is a cooperative local bootstrap anchor—not author-signed, externally timestamped, WORM, cryptographic execution attestation, reportable evidence, or resistance to an arbitrary same-user writer. This review does not demand those deferred properties.

That disclaimer does not cure N-01: a pre-existing ordinary junction bypasses code that explicitly claims lexical controlled-location enforcement. It also does not satisfy the requested inode-mismatch test in N-02. These are narrower current local-anchor contract failures.

## 13. Host guardrails and external-capability inventory

No Desktop, Documents, Downloads, OneDrive-redirected equivalent, operating-system directory, registry setting, service, scheduled task, global PATH, firewall, endpoint protection, UAC, permission, or security policy was modified. Review writes were confined to the authorized PACD workspace: the direct-child review checkout, task environments/probes under `var/tmp`, and non-reportable runs/receipts under `var`. Only verified task-created scratch directories were removed for clean probe reruns.

Real junctions were safely created only inside task-controlled workspace paths and restored. Temporary `R:`/`Q:` SUBST aliases were removed; final `subst` output was empty. `var/receipts`, `var/invocations`, `var/runs`, and `var/tmp` were final ordinary directories, not reparse points. Both Git checkouts were clean.

Static inventory found:

- zero `.github/workflows` files;
- zero `APPROVAL.json` records, including the controlled path;
- only `SimulatedExecutionBroker`, with `adapter_name="simulated_only"`, `network_enabled=False`, and one in-memory action type;
- no socket/HTTP/cloud/endpoint/identity client import, production credential path, shell execution adapter, real target, external scan, or production adapter;
- fixed `subprocess.run(shell=False, timeout=10)` only for local Git provenance;
- bounded multiprocessing spawn only for the diagnostic worker;
- Windows FFI only for host-resource and protected-known-folder checks.

The `external_network_scan` string is a prohibited synthetic configuration token, not an implementation. Arbitrary Python or the operating system could of course be used outside this application; no PACD-exposed path invokes that capability. The public reportable flag exists only to reach a pre-output interlock that always raises after validation, so there is no enabled reportable execution path.

## 14. Architecture assessment

The bootstrap has credible structural separation for:

- an evaluation harness distinct from defender implementations;
- a typed defender interface;
- a separate safety governor;
- controlled, simulated-only execution;
- retained-artifact verification separated from execution;
- append-style audit capture and metrics derived from retained raw records;
- a fail-closed reportable interlock.

The following seams exist but are not substantive PACD implementation, and are not defects merely for remaining bootstrap placeholders:

- red-agent behavior is a fixed synthetic fixture and is not integrated into the harness;
- multi-agent orchestration is an unused coordinator seam;
- mission-aware governance performs structural/digest validation, not substantive mission tradeoff reasoning;
- uncertainty-aware autonomy is a deterministic toy probability/threshold path;
- polymorphism operators exist but are not selected by the harness;
- human oversight is simulated, not a live oversight/authorization participant;
- a null baseline exists, but there is no fair comparative baseline experiment or allocation analysis.

The low-level broker/governor constructor and shared verifier/producer modules remain trust/common-mode seams. They must not be described as production isolation or independent scientific validation.

## 15. Differences from builder reports

Independent results agree with the builder on:

- exact lock/tool identity, two offline frozen reconstructions, doctor, tests, 77% coverage, and security gates;
- deterministic exact-head replay, old-head denial, absent-approval denial, and status-only `cf2dae85..4cba657` delivery delta;
- R-01's single bounded ingestion path and terminal raw/derived/aggregate Parquet failures;
- parent creation before worker start, separation of the receipt capability, exact staging/final transaction behavior in non-junction cases, clone identity denial, and timeout/raw-retention behavior;
- R-04 hard-link rejection;
- explicit non-cryptographic local-receipt limitations and non-substantive architecture seams;
- absence of workflows, approvals, reportable execution, production adapters, and external capability.

Independent results differ materially in three places:

1. The builder broadly states that junction/reparse protections remain covered and that the receipt is under the controlled `var/receipts` location. Real parent-junction probes show that receipt creation and verification canonicalize before checking, and identity remains assured.
2. The builder states that directory/inode mismatches fail local assurance. A run-directory inode replacement did fail, but a byte-identical receipt or ownership-marker inode replacement did not.
3. The builder's strict retained-JSON and evidence claims did not identify the later semantic-normalization recursion path. The independent 1,500-level payload produces an unhandled API exception.

The builder did not claim an independent pass, signing, external time, WORM storage, or malicious-same-user resistance; this review does not attribute those claims to it.

## 16. Unexecuted or physically blocked tests

- Real Windows file/directory symlink creation was denied with `WinError 1314`. No elevation or policy change was requested. Real NTFS junction/reparse tests were executed and exposed N-01.
- Concurrent replacement while a control-record handle was open was not deterministically orchestrated; Windows open-handle replacement semantics blocked the prior form. In-place repeated-read mutation, hard links, pre-verification byte-identical replacement, and real parent junctions were executed.
- Production-size 64 MiB/4 MiB allocations, every codec/page encoding/Thrift grammar, and a hand-crafted native Parquet with a deliberately false footer were not attempted. Safely reduced caps, ZSTD expansion, malformed magic/footer, metadata bounds, and an underreporting proxy exercised the same Python control paths.
- No real protected/device/ADS write was performed; denial/canonicalization was exercised without writing to those targets.
- No real network, cloud, endpoint, identity, shell adapter, production credential, or external target was invoked because static/runtime inventory found no such application capability.
- No controlled approval or reportable experiment was run. Pure/private validation variants and public absent-approval denial were exercised without creating the forbidden file.
- A full five-minute hang was not awaited. A real spawned worker used a reduced deadline; deterministic process doubles exercised terminate, join, kill, EOF, malformed/partial envelope, start failure, and no-orphan behavior.
- Original old-head evidence scripts were not executed destructively in their original result directories. Byte-identical originals were preserved and review-only current-interface copies were executed. The six-case addendum was not separately invoked because all six cases were included in the adapted 68-case matrix.

## 17. Complete command ledger

Material commands are normalized below. Dynamic mutations are implemented in the named task-created scripts. Two ad hoc `python -c` bodies were preserved after execution as the named driver files and are shown in equivalent file form.

```powershell
$WS = 'C:\Users\mthie\PACD-Workspaces\PACD-Simulation'
$FEATURE = "$WS\repo\pacd-simulation"
$REVIEW = "$WS\repo\pacd-simulation-final-review-4cba657"
$TASK = "$WS\var\tmp\final-rechallenge-4cba657"
$UV = "$WS\var\cache\tools\uv\0.12.5\uv.exe"
$BASEPY = 'C:\Users\mthie\AppData\Roaming\uv\python\cpython-3.13.15-windows-x86_64-none\python.exe'
$PY = "$TASK\env1\Scripts\python.exe"
$GH = "$WS\var\cache\tools\gh\2.98.0\bin\gh.exe"

& $GH repo view mthiessmeier/pacd-simulation --json nameWithOwner,isPrivate,visibility,defaultBranchRef,url
& $GH pr view 1 --repo mthiessmeier/pacd-simulation --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,mergedAt,mergeStateStatus,url
& $GH api repos/mthiessmeier/pacd-simulation/issues/1/timeline --paginate -H 'Accept: application/vnd.github+json'

git clone --no-hardlinks $FEATURE $REVIEW
git -C $REVIEW switch -c independent-final-rechallenge-4cba657 4cba65779753a3096e2bd7551e7d4ff7321df4a2
git -C $REVIEW rev-parse HEAD
git -C $REVIEW status --porcelain=v1
git -C $REVIEW log --reverse --format='%H %P %s' 613bc658^..4cba657
git -C $REVIEW merge-base 613bc65861fb428e8df45f509e568421a8547273 4cba65779753a3096e2bd7551e7d4ff7321df4a2
git -C $REVIEW rev-list --merges 613bc65861fb428e8df45f509e568421a8547273..4cba65779753a3096e2bd7551e7d4ff7321df4a2
git -C $REVIEW diff --name-status cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff..4cba65779753a3096e2bd7551e7d4ff7321df4a2
foreach ($sha in @('c2b2272d898a8d2314871f85744c065d4cc8f84e','01451792ef28ad99c3be630a19f42d66cd6fa293','52328b904accfc46c711085b0862c0421aacc1e0','cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff','4cba65779753a3096e2bd7551e7d4ff7321df4a2')) { git -C $REVIEW show --format='%H%n%P%n%s' --name-status $sha }
Get-FileHash -Algorithm SHA256 $REVIEW\uv.lock
$env:PACD_REVIEW_SCAN = $REVIEW
& $BASEPY -c "import os,pathlib,subprocess; r=pathlib.Path(os.environ['PACD_REVIEW_SCAN']); fs=[r/p for p in subprocess.check_output(['git','-C',str(r),'ls-files'],text=True).splitlines() if (r/p).is_file()]; bad=[str(p) for p in fs if os.stat(p,follow_symlinks=False).st_nlink != 1]; print({'tracked_regular_files':len(fs),'non_single_linked':bad})"
Remove-Item Env:PACD_REVIEW_SCAN

& $UV lock --project $REVIEW --check --offline --no-cache --prerelease disallow
$env:UV_PROJECT_ENVIRONMENT = "$TASK\env1"
& $UV sync --project $REVIEW --frozen --offline --cache-dir "$WS\var\cache\uv" --python $BASEPY --prerelease disallow
# Offline refusal: locked SciPy wheel absent from that cache. Verified task env removed.
$env:UV_PROJECT_ENVIRONMENT = "$TASK\env1"
& $UV sync --project $REVIEW --frozen --offline --cache-dir "$WS\var\cache\uv-project" --python $BASEPY --prerelease disallow
$env:UV_PROJECT_ENVIRONMENT = "$TASK\env2"
& $UV sync --project $REVIEW --frozen --offline --cache-dir "$WS\var\cache\uv-project" --python $BASEPY --prerelease disallow
& $UV --version
& $PY --version

& "$TASK\env1\Scripts\pacd-sim.exe" doctor --repo-root $REVIEW --workspace-root $WS
& "$TASK\env1\Scripts\ruff.exe" format --check . --no-cache
& "$TASK\env1\Scripts\ruff.exe" check . --no-cache
& "$TASK\env1\Scripts\mypy.exe" src tests --no-incremental --cache-dir "$TASK\mypy-cache"
& $PY -m pytest -p no:cacheprovider --basetemp "$WS\var\tmp\fpr-pytest-001" -q
& $PY -m pytest -p no:cacheprovider --basetemp "$WS\t\fpr2" -q
& $PY -m pytest -p no:cacheprovider --basetemp "$WS\t\fprcov" --cov=pacd_sim --cov-branch --cov-report=term-missing --cov-report="json:$TASK\coverage.json" -q
& "$TASK\env1\Scripts\bandit.exe" -c pyproject.toml -r src
& "$TASK\env1\Scripts\detect-secrets.exe" scan --all-files
& "$TASK\env1\Scripts\pip-audit.exe" --local --skip-editable

& "$TASK\env1\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
& "$TASK\env1\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
& "$TASK\env1\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424243
& "$TASK\env1\Scripts\pacd-sim.exe" verify --workspace-root $WS "$WS\var\runs\diagnostic-20260823T173646.199584Z-seed-424242-88b6d20deb1b418bbbbd2a467f02c908"
& "$TASK\env1\Scripts\pacd-sim.exe" verify --workspace-root $WS "$WS\var\runs\diagnostic-20260823T173648.960271Z-seed-424242-95480b85d0214ae1a8bb281f16902220"
& "$TASK\env1\Scripts\pacd-sim.exe" verify --workspace-root $WS "$WS\var\runs\diagnostic-20260823T173651.856293Z-seed-424243-fb5d43db9d7446b2ad39657944d1b44b"
& "$TASK\env1\Scripts\pacd-sim.exe" verify --workspace-root $WS "$WS\var\runs\diagnostic-20260823T100919.674020Z-seed-424242-f3ff9a97c6304e73afb87b983922c4d1
& "$TASK\env1\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --reportable

& $PY "$TASK\controls\authorization_rechallenge_adapted.py"
subst R: $WS
& $PY -m pytest -q "$TASK\controls\adversarial_rechallenge_original.py" -ra
subst R: /D
& $PY "$TASK\controls\path_current_probe.py"
& $PY "$TASK\controls\parser_current_probe.py"
& $PY "$TASK\controls\r04_current_probe.py"
& $PY -m pytest -p no:cacheprovider -q tests\negative tests\property\test_authorization_binding.py tests\property\test_environment_invariants.py tests\property\test_governor_admissibility.py tests\property\test_path_jail_properties.py tests\property\test_schema_properties.py tests\reproducibility\test_parquet_bounded_ingestion.py tests\reproducibility\test_retained_json_bounds.py tests\unit\test_dependency_policy.py tests\unit\test_safety_governor.py tests\unit\test_schema_and_yaml.py tests\unit\test_simulated_execution.py --basetemp "$WS\t\fprctl2"

& $PY -m py_compile "$TASK\parquet\independent_parquet_probe.py"
& $PY "$TASK\parquet\independent_parquet_probe.py"

subst Q: "$TASK\receipts"
& $PY -m pytest -q "$TASK\receipts\independent_receipt_probes_v6.py" --basetemp Q:\p8 -ra
& $PY -m pytest -q "$TASK\receipts\independent_process_and_clone_probes.py" --basetemp Q:\p9 -ra
& $PY -m pytest -q "$TASK\receipts\independent_process_and_clone_probes.py" --basetemp Q:\p10 -k 'not junction and not symlink' -ra
& $PY -m pytest -q "$TASK\receipts\independent_worker_envelope_probes.py" --basetemp Q:\p11 -ra
& $PY "$TASK\receipts\preexisting_receipt_junction_probe.py"
& $PY "$TASK\receipts\byte_identical_control_record_replacement_probe.py"
& $PY -c "from pacd_sim.harness.run import _run_diagnostic_worker; _run_diagnostic_worker('a','b','c','d')"
subst Q: /D

& $PY -m py_compile "$TASK\evidence\adapted\rechallenge_current.py"
& $PY "$TASK\evidence\adapted\rechallenge_current.py"
& $PY -m py_compile "$TASK\evidence\expanded\integrity_expanded.py"
& $PY "$TASK\evidence\expanded\integrity_expanded.py"
# Semantically exact equivalents of the executed python -c bodies were preserved:
& $PY "$TASK\evidence\identity_verification_driver.py"
& $PY "$TASK\evidence\malformed_row_addendum_driver.py"
& "$TASK\env1\Scripts\pacd-sim.exe" verify --workspace-root $WS "$TASK\evidence\expanded\cases\payload_excessive_nesting\diagnostic-20260823T165838.242026Z-seed-424242-b9c89b71e4d642379b1adc0b5b614055

rg --files -g '.github/workflows/**'
rg -n '^\s*(from|import)\s+(socket|requests|httpx|urllib|aiohttp|boto3?|botocore|azure|google\.cloud|kubernetes|paramiko|fabric|winrm|ldap|msal|openai)\b' src
rg -n 'subprocess\.(run|Popen|call|check_output)|os\.system|shell\s*=|multiprocessing|ctypes' src
Test-Path configs\protocol\frozen\APPROVAL.json
subst
Get-Item "$WS\var\receipts","$WS\var\invocations","$WS\var\runs","$WS\var\tmp"
git -C $REVIEW status --porcelain=v1
git -C $FEATURE status --porcelain=v1
```

Two harmless command corrections are retained for transparency: a repeated parser/R-04 probe initially refused because its own task-created scratch root still existed; only those verified non-reparse task roots were removed and the probes reran successfully. One manual deep-payload CLI call first supplied unsupported `verify --repo-root` and exited usage status 2; the corrected public syntax reproduced the `RecursionError` failure with exit 1. Other no-effect shell attempts were one malformed `rg` quoting command, sandbox-denied external patch updates, one PowerShell here-string parse failure, and two result-formatting errors; none wrote repository or controlled evidence. Read-only `Get-Content`, `rg`, `Get-FileHash`, `Get-ChildItem`, Git, JSON extraction, help, and inventory commands were used throughout. `New-Item`/`Copy-Item` and exact text replacement were limited to task-created review directories and byte-preserved/adapted probe copies.

## 18. Required corrective actions and merge recommendation

Before another independent review:

1. Preserve and validate exact lexical `var/receipts` and `var/invocations` paths before any resolution; reject every parent reparse component during creation and verification; add real NTFS parent-junction regressions.
2. Define and implement the expressly required receipt/ownership inode-mismatch anchor within the stated cooperative local model, or narrow the assurance contract and challenge specification explicitly before claiming the property.
3. Make strict retained-payload failure terminal for the complete verifier and ensure every later semantic/label/metric consumer is skipped; catch recursion defensively so `verify_run` always returns a structured invalid result for bounded hostile inputs.
4. Rerun the complete independent challenge at the exact new additive head while PR #1 remains open and unmerged.

## 19. Final classification

**FAIL — bootstrap not acceptable for merge**

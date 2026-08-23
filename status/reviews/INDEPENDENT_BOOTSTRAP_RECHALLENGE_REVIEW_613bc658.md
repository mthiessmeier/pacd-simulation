# Independent PACD Bootstrap Re-Challenge Review — PR #1

Repository: `mthiessmeier/pacd-simulation`  
Pull request: PR #1, `Bootstrap bounded local PACD simulation environment`  
Exact reviewed PR head: `613bc65861fb428e8df45f509e568421a8547273`  
Base / head: `main` / `codex/environment-bootstrap-v1`  
Review date: 2026-08-23  
Posture: independent review and challenge only; no merge, commit, feature-branch modification, approval record, reportable experiment, production adapter, real target, or host-security change

## Final classification

**FAIL — bootstrap not acceptable for merge**

The locked bootstrap environment reconstructs offline at the exact head, doctor passes in the correctly placed clean review checkout, all 155 committed tests pass with one privilege-dependent skip, branch-aware coverage is 77%, the quality/security checks pass, fresh current-head diagnostics reproduce and verify, and most F-01 through F-08 remediations withstand challenge.

Merge is nevertheless blocked. A safely compressed Parquet probe demonstrated that the verifier's decoded-size rejection is not terminal: after rejecting oversized raw Parquet metadata, the complete `verify_run` call proceeds into later reads of that same artifact. The derived-summary Parquet path has no equivalent decoded-size preflight and is repeatedly materialized. This directly fails the newly required resource boundary and contradicts the remediation report's claim that retained Parquet materialization is bounded.

Two further integrity findings remain: a coherently retimestamped/renamed run is accepted after its self-consistency closure is refreshed, and parent failure retention can claim, modify, and move a pre-existing staging directory whose name ends in the invocation token. A hard-linked approval record is also accepted by the private loader, although the bootstrap's unconditional reportable denial makes that residual non-exploitable today.

PR #1 was confirmed open and unmerged after the review. It was not merged.

## Findings

### R-01 — High / merge blocking — rejected Parquet is later materialized

The strict raw-evidence preflight correctly inspected Parquet metadata without decoding and emitted `Raw Parquet decoded column data exceeds the 64 MiB cap`. It did not call `ParquetFile.read`. However, `verify_run` only appends the strict errors at `src/pacd_sim/reproducibility/verify.py:240-248` and continues. Later paths call `pq.read_table` at `verify.py:129,411,429,452`, reopen Parquet in `reproducibility/manifest.py:112`, and read raw data again in `metrics/summarize.py:54`.

Two independent reduced-cap probes reached the same conclusion:

| Probe | Encoded / decoded | Strict result | Subsequent target reads |
|---|---:|---|---:|
| Main raw probe | 5,167 B / 536,614 B; cap 65,536 B | decoded-size rejection; no strict full read | 4 guarded materialization attempts |
| Independent raw probe | 8,693 B / 2,008,413 B; cap 20,000 B | decoded-size rejection; no `ParquetFile.read` | 8 outer `pq.read_table` calls, including 4 full reads |
| Main derived probe | 4,323 B / 524,809 B; cap 65,536 B | no decoded-size cap exists | 2 guarded materialization attempts |
| Independent derived probe | 6,584 B / 2,001,569 B | no cap error | 3 reads, including 2 full approximately 2 MB tables |

The probes monkeypatched every subsequent module-wide `pq.read_table` and `ParquetFile.read`. The main guard raised before target materialization, proving the attempted control flow without allocating the hostile expansion. The independent probe allowed a safely bounded approximately 2 MB expansion and observed the actual later reads. Reducing the aggregate encoded-run cap below the physical run size did short-circuit with zero Parquet calls, so the defect is specifically the decoded-artifact boundary.

Required correction: make a failed Parquet preflight terminal before any later artifact consumer, add schema/row/decoded-size preflight for derived summary Parquet, and reuse bounded validated tables rather than reopening attacker-controlled files.

Evidence:

- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\evidence-main\resource_boundary_probe.py`, SHA-256 `A085D8AE92DEA512D227DA113FBF2DBF17BBD15144B7F7EDC52EB2A228FA3B11`
- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\evidence-agent\results.json`, SHA-256 `FB057E45F74FCCAC93DB49A481686EAF4204E9557D66CB12C3C6B135F56AB38A`
- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\evidence-agent\parquet-probe`

### R-02 — Medium / unresolved evidence-identity condition — coherent run relabel accepted

A copied valid diagnostic was shifted by one second: directory name/run ID, manifest run ID/start/end, and every raw row run ID were updated, then raw semantic, artifact, manifest, and checksum closure was refreshed. Verification returned `valid=true` with no errors.

This does not change reconstructed action semantics, code, configuration, or seed; it is not a semantic action forgery. It does show that the package authenticates internal consistency, not the original evidence-instance identity or time. A valid run can be cloned, misdated, and presented as a distinct run. That contradicts the builder's explicit claim that refreshed run-ID mutations are rejected and matters to the requested append-only/replay boundary.

Required condition: externally anchor run identity using a trusted append-only receipt/registry, signed receipt, or content-addressed identity before treating run IDs/timestamps as authenticated evidence.

### R-03 — Medium / conditional transaction-ownership defect — parent claims pre-existing staging

`_retain_interrupted_evidence` discovers a candidate solely by a directory name ending in `-<invocation_token>.staging` (`harness/run.py:1471-1488`), validates the name/token (`:1491-1500`), and passes it to `_retain_failed_run` (`:1501-1508`). It has no child-created ownership marker or handle.

A pre-existing matching task-only directory containing a sentinel was selected by `_retain_parent_failure`; `status.json` was added and the entire directory was moved from `var/tmp` into `var/runs`. The sentinel bytes survived, but the pre-existing directory was not left untouched. This conflicts with the child-side ownership invariant at `run.py:752-769`.

The public token is a fresh UUID (`run.py:1588`), so exploitation requires token knowledge or a local same-workspace race and cannot escape the workspace jail. Evidence sentinel SHA-256: `542832C5609B5B14657C28D2F54AAA318706B06F60AD92560329D3150464D9D6` under `...\paths\custom-r7\f06-sentinel\var\runs\diagnostic-preexisting-seed-424242-ffffffffffffffffffffffffffffffff`.

Required correction: retain only a staging directory proven to have been created by this worker invocation, using an unforgeable ownership channel/handle or an exclusive marker established by the parent before launch.

### R-04 — Low / future enablement — hard-linked approval accepted by loader

The private `_load_approval` stable-read logic binds path/file identity and content but does not reject a regular file with `st_nlink > 1`. A hard-linked non-controlled review probe was accepted. No controlled `APPROVAL.json` was created. Current reportable execution is unconditionally denied at `harness/run.py:928-939`, before run-directory creation, so this cannot enable a reportable bootstrap run.

Condition: reject multi-link approval files before any future removal of the unconditional reportable denial.

## Review isolation and established facts

The primary no-hardlink checkout was created at:

`C:\Users\mthie\PACD-Workspaces\PACD-Simulation\repo\pacd-simulation-review-613bc658`

It is on local review-only branch `independent-rechallenge-613bc658` at the exact reviewed SHA. The feature checkout remained clean on `codex/environment-bootstrap-v1` at the same SHA. A repeated `os.stat().st_nlink` scan found zero multi-link files among 218 regular checkout files outside `.git`.

An initial no-hardlink checkout at `...\review\pr1-613bc658-rechallenge-20260823` was intentionally challenged. Doctor rejected it because the repository was not a direct child of `<workspace>\repo`. It remained clean and was not used as proof of a successful environment.

GitHub was queried independently at the end of review:

| Fact | Result |
|---|---|
| Repository | `mthiessmeier/pacd-simulation` |
| Privacy | `PRIVATE`, `isPrivate=true` |
| Default branch | `main` |
| PR state | `OPEN`, non-draft, `mergedAt=null` |
| Base / head branch | `main` / `codex/environment-bootstrap-v1` |
| Remote PR head | `613bc65861fb428e8df45f509e568421a8547273` |
| `uv.lock` SHA-256 | `12372A81D459EC112417B7A76B7FC65A32F5E0DA865B39A466C443563A28F290` |
| Python | CPython `3.13.15` |
| uv | `0.12.5 (210d1f678 2026-08-14 x86_64-pc-windows-msvc)` |
| GitHub Actions workflows | absent |
| Frozen approval record | absent in Git tree and both checkouts |
| Production execution adapters | absent; one simulated-only broker |

The full additive commit graph was:

~~~text
613bc65 Record bootstrap remediation status
cfeb513 Bound retained Parquet materialization
47740cf Eliminate failed-retention alternate-link writes
c1d39d8 Harden interrupted evidence retention
1ec6a9e Remediate independent bootstrap challenge findings
35be713 Record private PR delivery evidence
f5776b0 Document bootstrap validation evidence
39cc2bc Build bounded PACD diagnostic environment
32a8345 Initial commit
~~~

`35be713..cfeb513` changed exactly 20 implementation/test/documentation paths: `README.md`, `pyproject.toml`, `src/pacd_sim/{cli.py,execution/broker.py,execution/verification.py,governance/governor.py,harness/run.py,reproducibility/evidence_validation.py,reproducibility/reportable.py,reproducibility/verify.py}`, and ten test/support files. It contained 2,608 insertions and 87 deletions.

`cfeb513..613bc658` added exactly two status records and no implementation/test/config/lock change:

- `status/CURRENT_STATUS.md`
- `status/REMEDIATION_REPORT_v1.0.md`

## External-execution capability assessment

No `.github/workflows` tree, approval record, executable/gitlink, production adapter, real scan, socket operation, HTTP client, packet library, external target adapter, cloud API, endpoint API, identity API, production credential lookup, or shell execution adapter exists in the tracked bootstrap.

The only broker is `SimulatedExecutionBroker`; it declares `network_enabled=False` and supports the immutable in-memory `isolate_session` transition. The only source imports of `subprocess` are fixed, bounded, shell-free, read-only local Git provenance queries in `doctor.py` and `reportable.py`. Multiprocessing launches only the fixed local diagnostic worker. Static negative tests also prohibit network/process imports in the execution package.

## Environment reconstruction and standard validation

Two absent, isolated environments were reconstructed from the exact current-head `uv.lock` using the cached locked artifacts only:

- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\env1`
- `C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\env2`

Both frozen offline synchronizations installed the 73 locked packages under CPython 3.13.15. The exact self-contained lock check `uv lock --check --offline --no-cache --prerelease disallow` passed and resolved 73 packages without network access. The lock contains zero prerelease/development versions and `pyproject.toml` explicitly sets `prerelease = "disallow"`.

| Check | Independent result |
|---|---|
| `pacd-sim doctor`, correctly placed clean review checkout | PASS; all 12 checks, exact head/branch, clean |
| doctor against checkout under `workspace\review` | expected DENIAL; outside explicit `workspace\repo` boundary |
| `uv lock --check --offline --no-cache --prerelease disallow` | PASS; 73 packages |
| frozen offline synchronization, environment 1 | PASS; 73 packages |
| frozen offline synchronization, environment 2 | PASS; 73 packages |
| Ruff format check | PASS; 105 files formatted |
| Ruff lint | PASS |
| strict mypy | PASS; 81 source/test files |
| complete pytest | PASS; 155 passed, 1 skipped in 42.86 s |
| complete branch-aware pytest | PASS; 155 passed, 1 skipped in 46.51 s |
| aggregate branch-aware coverage | 77%: 3,226 statements, 1,120 branches |
| Bandit | PASS; no findings |
| detect-secrets, every tracked file except `.git` | 14 candidates manually reviewed; no credential material |
| pip-audit | PASS; no known vulnerabilities; editable local project skipped |
| independent authorization probe | PASS; 62/62 assertions |
| independent evidence mutation matrix | 61/62 rejected; coherent run-ID shift accepted |
| six-case evidence addendum | PASS; 6/6 rejected |
| independent interlock/path/transaction probe | 34 passed, 1 host-dependent skip |
| selected committed safety/replay suites | 105 passed |

The detect-secrets candidates were fixed non-secret material: an example policy key in the guardrail document, immutable status/commit/archive hashes, and a fixed test alphabet.

The one committed-suite skip was the actual Windows directory-symlink creation case. The non-elevated host returned WinError 1314. No privilege or security control was changed. Mocked symlink/reparse variants and an actual junction were exercised. The independent approval replacement test also skipped its replacement branch because Windows refused replacement while the file handle was open; in-place repeated-read mutation was separately exercised and denied.

### Transparent procedural retries

Review setup failures were not treated as product failures and are recorded here:

1. The first `env2` synchronization command was launched from the wrong current directory before the environment existed; rerunning from the exact checkout succeeded.
2. The first full pytest attempt used a nonexistent `--basetemp` parent and produced 85 setup errors plus 71 passes. The next full and coverage attempts used overly long Windows temp paths and each produced five WinError 206 path failures. Unchanged code passed both complete suites from short roots `<workspace>\t\i61` and `<workspace>\t\i62`.
3. An initial selected-suite run encountered the same five path-length failures; the green selected run used short roots and recorded 105 passes.
4. A later duplicate invocation of the main Parquet probe refused to overwrite its task-created destinations, as designed; the authoritative earlier probe result was retained.
5. Final convenience invocations initially could not find `uv`/`gh` on that shell's PATH; absolute cached tool paths were then used. A stale restricted TEMP path caused one uv access denial; an absent task-only TEMP directory was created and the exact lock check passed. The first GitHub query was blocked by the review network sandbox and was rerun read-only with the required network permission.

No retry changed source, tests, configuration, lock state, host security, or the feature branch.

## Fresh diagnostic reproduction and exact-head binding

Three fresh runs were generated only under the authorized `<workspace>\var\runs` and were explicitly labelled `NON_REPORTABLE_DIAGNOSTIC`:

| Seed/run | Raw semantic SHA-256 | Summary semantic SHA-256 | Strict verification |
|---|---|---|---|
| 424242 A | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` | valid |
| 424242 B | `6657cb73aa85b7c6ff9ecb8e5284f9999fff727cb6330b46fcad715b04cdf4bf` | `9616e1edf0401f353625e3b35e714b14dc517b55bbe7d4c5db76c2b3565ecd76` | valid |
| 424243 | `7f7a0eb3d22387a74f4b8fb1dba56715406ef4da81a65e5aefd181f2675b0347` | `3228bda10bc24eb94be30fea5d6010a991996a672f7f4f082e9febfcf27deff6` | valid |

Each run had the exact 11-artifact allowlist and passed full retained-artifact verification. Same-seed semantics matched exactly; the different seed changed both raw and summary semantics.

A new non-reportable diagnostic was independently generated at historical head `35be713295b81ecf5ee22d26c851beff49983b42` in a separate no-hardlink checkout/environment. Verification of that package against the current clean `613bc658` checkout returned `valid=false`, including exact code-commit mismatch and reconstructed semantic mismatches. A fresh `613bc658` run verified against the same current checkout returned `valid=true`. This establishes exact-code-head binding for substantive evidence.

A requested reportable-mode denial attempt exited 3 with `DENIED` because approval was absent. The run-directory count was 18 before and after; `APPROVAL.json` remained absent. No reportable experiment ran.

## Original finding-by-finding disposition

| Original ID | Re-challenge disposition | Evidence/conclusion |
|---|---|---|
| F-01 | Corrected for public diagnostic path | CLI, direct `run_diagnostic` validation, and worker-side checks bind the designated workspace and direct-child repository. Broader roots, alternate placement, traversal, junction/reparse, ADS/device output spellings, and path-component substitution failed closed. Generic low-level contained ADS syntax remains accepted, but the diagnostic sink requires exact `workspace/var/runs`. |
| F-02 | Corrected in the harness; direct API seam documented | Forged/copied/stale/context-swapped/policy-swapped decisions and all 15 independently mutated decision fields were rejected before mutation. The harness constructs its trusted governor. An arbitrary in-process caller can still instantiate `SimulatedExecutionBroker` with a permissive duck-typed governor; this is outside the current harness trust boundary and must not become an adapter injection point. |
| F-03 | Corrected in the harness | Action ID/type/target/config/schema, decision/policy/context/state digests, configuration, tick, and exact before/after state are bound. Cross-state replay and collateral identity/session/service/mission/asset/config/schema mutations failed. Exact copied decisions can be reused against an identical immutable pre-state because no one-shot ledger exists; reuse after state change fails. |
| F-04 | Substantive semantic remediations corrected; run identity unresolved | Refreshed configuration, seed registry, action semantics, event order/count, decisions, verification, audit, execution count, JSONL/Parquet divergence, and metrics were rejected. R-02 shows coherent run-ID/timestamp relabel remains accepted. |
| F-05 | JSON/schema strictness corrected; resource claim unresolved | Duplicate/extra/noncanonical/nonfinite/malformed JSON, unknown fields/events, exact Parquet schema/row changes, missing/extra artifacts, and checksum/manifest tampering failed closed. R-01 shows decoded Parquet materialization is not actually bounded and derived Parquet has no decoded cap. |
| F-06 | Preemptive timeout corrected; ownership residual unresolved | Terminate/kill behavior, EOF/malformed envelopes, partial raw retention, hard-link-safe atomic status replacement, and failed evidence passed. R-03 shows parent retention can claim a pre-existing token-matching staging directory. |
| F-07 | Corrected for current bootstrap; future hard-link residual | Exact lexical path, every parent component, duplicate/malformed/extra/wrong approval bindings, junction/reparse, and repeated-read mutation fail closed. R-04 remains before future reportable enablement; current reportable mode is unconditionally denied. |
| F-08 | Corrected | Project/readme command explicitly disallows prereleases; exact offline/no-cache check passes and lock contains only stable releases. |

## Authorization, controlled execution, and collateral-state challenge

The independent authorization script executed 62 assertions at exact clean head. Script:

`C:\Users\mthie\PACD-Workspaces\PACD-Simulation\var\tmp\rechallenge-613bc658-20260823\auth\authorization_rechallenge.py`  
SHA-256: `9066492080E6E221A5F096F929C54C68CC4ED8BF9042AAE4108212403021E285`

Results:

- all 15 `PolicyDecision` fields, mutated one at a time, were rejected;
- all 13 action-field substitutions were rejected;
- five governance/context changes were rejected;
- forged APPROVE, copied decision, stale decision, alternate policy decision, context swap, policy swap, and cross-state replay were rejected before mutation;
- decisions reused after tick/schema/configuration/identity/session state changes were rejected or raised before mutation;
- forced approval of non-reversible, unsupported, escalated, prohibited, and external actions did not execute;
- a governor-approved configured action absent from the defender's proposals caused harness failure and no `simulated_execution` event;
- complete post-state comparison rejected collateral mutations to ID, tick, schema, configuration, source, assets, identities, sessions, credentials, services, mission functions, and dependencies.

Two direct-Python seams are distinguished from harness behavior:

1. The broker constructor accepts any governor-like object. A caller deliberately bypassing the harness can supply a permissive governor and execute the sole supported reversible simulated isolation. The production-free harness never accepts such injection.
2. There is no one-shot authorization ledger, so the exact trusted decision may execute repeatedly against the exact same immutable pre-state. Duplicate IDs and the single-pass harness prevent this in the diagnostic; a future stateful adapter must add nonce/consumption semantics.

## Adversarial test inventory

### Workspace authority, canonicalization, hard links, transactions, and interlock

The independent custom probe recorded 34 passes, one host-dependent skip, zero failures/errors. Its executed cases were:

- public authority at the direct-child checkout; broader caller root; alternate checkout under `workspace/review`; default-workspace junction alias;
- SUBST device alias canonicalization without authority widening;
- sibling, prefix-lookalike, `..` traversal, ADS spelling, `\\.\NUL` device path, contained alternate spelling, exact output-root enforcement;
- actual junction/reparse component detection;
- exact prerelease policy/readme/lock stability;
- unknown action and non-reversible automatic action denial;
- missing approval and outside lexical approval path;
- missing/extra approval keys; wrong commit; dirty repository; wrong protocol/config/seed/baseline/metric hashes;
- duplicate/malformed approval JSON; mocked indirect approval; actual junction parent;
- repeated-read in-place mutation; replacement while open; hard-linked approval loader probe;
- timeout termination and evidence retention; unresponsive terminate/kill path; poll false; pipe EOF; list envelope; non-boolean `ok`; worker error envelope; success envelope missing a result;
- pre-existing token-matching sentinel; timeout partial-raw retention; already-finalized partial evidence; hard-linked `status.json` against an external sentinel;
- final assertion that no controlled approval record existed.

Evidence:

- script `...\paths\adversarial_rechallenge.py`, SHA-256 `AAC7468223E25FD8D9CF781E4FB9B2307652D5BF28E9A55ED5DE6C2CA141BBD7`
- JUnit `...\paths\adversarial-rechallenge-final.xml`, SHA-256 `A17FC33F7EDAA3339EB1D71ACC2931EB03F4486B23C4510C85A5832E40FC1ECC`
- selected-suite JUnit `...\paths\pytest-selected-green.xml`, SHA-256 `01C8FB73B042427DE02C49BEC82D040688018CC76EE0B6ACBF0BDBC59BDAEE44`

### Hostile configuration/parser inputs

The complete and selected current-head suites reran the strict configuration attacks. All failed closed before diagnostic output:

- YAML duplicate keys and JSON duplicate keys;
- explicit YAML tags;
- ordinary aliases over the allowed count and recursive aliases;
- excessive nesting and expanded node count;
- input exceeding 1 MiB;
- YAML/JSON NaN and positive/negative infinity;
- malformed YAML and malformed JSON;
- unknown scenario/configuration fields;
- duplicate action IDs.

### Evidence/replay mutation matrix

The authoritative independent matrix executed 62 cases with zero setup exceptions. The baseline was valid. Sixty-one expected-invalid cases were rejected; only `coherent_run_id_shift` was accepted as R-02.

Executed case names:

- provenance/digests: `manifest_code_commit`, `manifest_dirty_state`, `manifest_python_version`, `manifest_lockfile_hash`, `manifest_config_hash_start`, `manifest_config_hash_end`, `manifest_seed_registry_hash`, `manifest_baseline_definition_hash`, `manifest_metric_definition_hash`, `manifest_protocol_version`, `manifest_raw_semantic_hash`, `manifest_summary_semantic_hash`;
- refreshed controlled inputs: `refreshed_config_closure`, `refreshed_seed_registry`;
- candidate/action chain: `candidate_action_id`, `candidate_action_type`, `candidate_configuration`, `candidate_target`;
- decision chain: `decision_action_digest`, `decision_disposition`, `decision_governance_digest`, `decision_policy_digest`, `decision_state_digest`;
- execution chain: `execution_action_type`, `execution_authorized_action`, `execution_authorized_state`, `execution_config`, `execution_decision_digest`, `execution_decision_id`, `execution_policy_digest`, `execution_state_before`, `execution_target`;
- verification/audit/safety: `verification_execution_id`, `verification_outcome`, `audit_payload`, `unknown_action_type`, `nonreversible_approved`, `execute_escalated`, `execute_prohibited`;
- raw order/count/type/numeric: `raw_reordered_resequenced`, `raw_missing_row`, `raw_duplicate_row`, `raw_extra_row`, `raw_unknown_event`, `raw_nonfinite_tick`;
- payload/peer/schema: `payload_duplicate_key`, `payload_extra_key`, `payload_noncanonical`, `payload_nonfinite`, `payload_malformed`, `jsonl_only_mutation`, `parquet_only_mutation`, `raw_extra_column`;
- retained JSON: `manifest_duplicate_key`, `manifest_extra_key`, `manifest_noncanonical`, `status_nonfinite`;
- derived: `derived_refreshed_meaning`, `derived_duplicate_row`, `derived_missing_row`, `derived_extra_column`;
- identity: `coherent_run_id_shift`.

The six-case addendum separately rejected:

- top-level JSONL duplicate key;
- noncanonical top-level JSONL row;
- extra JSONL field/row divergence;
- malformed raw Parquet;
- malformed derived Parquet;
- refreshed derived `simulated_execution_count`.

Addendum results: `...\evidence-agent\addendum-results.json`, SHA-256 `5B27723335E1059891B1300F01459E8FFD35C2B0CE34D5BE55C60FA1F1044827`. The original 62-case result remained byte-for-byte unchanged.

### Artifact inventory and resource boundaries

Independent and committed probes also exercised:

- missing required artifact;
- extra undeclared regular/reparse artifact;
- incomplete/empty manifest allowlist;
- unrefreshed checksum mismatch;
- refreshed configuration/seed/provenance closure;
- JSONL/Parquet disagreement;
- raw and derived schema change;
- duplicate/missing/extra rows and sequences;
- event-chain mutation, prohibited/escalated execution, and missing verification;
- aggregate output cap without creating a large file;
- event limit above 100, action limit above 100, audit payload above 64 KiB, input/depth/node/alias caps;
- compressed raw and derived Parquet decoded-size behavior, including R-01.

### Approval/reportable matrix

Without ever creating `configs/protocol/frozen/APPROVAL.json`, the review challenged missing, malformed, duplicate-key, missing-key, extra-key, wrong commit, dirty repository, wrong configuration hash, wrong seed-registry hash, wrong baseline hash, wrong metric hash, wrong protocol version, final-file indirection, parent junction/reparse, outside lexical location, in-place repeated-read substitution, attempted file replacement, and a non-controlled hard-link probe.

All executable reportable paths remained denied before output creation. The open-handle replacement could not be performed because Windows rejected replacement of the open file; no security setting was weakened to force it. R-04 records the hard-link loader residual.

## Command ledger

The following are the material commands/checks executed. Paths are written exactly or with the declared review variables for readability:

~~~powershell
$WS = 'C:\Users\mthie\PACD-Workspaces\PACD-Simulation'
$REVIEW = "$WS\repo\pacd-simulation-review-613bc658"
$OLD = "$WS\repo\pacd-simulation-oldhead-review-35be713"
$TASK = "$WS\var\tmp\rechallenge-613bc658-20260823"
$PY = "$TASK\env2\Scripts\python.exe"
$UV = "$WS\var\cache\tools\uv\0.12.5\uv.exe"
$GH = "$WS\var\cache\tools\gh\2.98.0\bin\gh.exe"

& $GH repo view mthiessmeier/pacd-simulation --json nameWithOwner,isPrivate,visibility,defaultBranchRef,url
& $GH pr view 1 --repo mthiessmeier/pacd-simulation --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,mergedAt,url

git clone --no-hardlinks https://github.com/mthiessmeier/pacd-simulation.git <review-checkout>
git switch --detach 613bc65861fb428e8df45f509e568421a8547273
git switch -c independent-rechallenge-613bc658
git clone --no-hardlinks https://github.com/mthiessmeier/pacd-simulation.git $OLD
git switch --detach 35be713295b81ecf5ee22d26c851beff49983b42
git switch -c independent-oldhead-35be
git status --porcelain=v1
git rev-parse HEAD
git branch --show-current
git log --graph --decorate --oneline --all --boundary
git diff --stat 35be713295b81ecf5ee22d26c851beff49983b42..cfeb5137a397294a310199f93b165b25bc5a03d6
git diff --name-status 35be713295b81ecf5ee22d26c851beff49983b42..cfeb5137a397294a310199f93b165b25bc5a03d6
git diff --name-status cfeb5137a397294a310199f93b165b25bc5a03d6..613bc65861fb428e8df45f509e568421a8547273
Get-FileHash -Algorithm SHA256 uv.lock

$env:UV_PROJECT_ENVIRONMENT = "$TASK\env1"
& $UV sync --frozen --offline
$env:UV_PROJECT_ENVIRONMENT = "$TASK\env2"
& $UV sync --frozen --offline
& $UV lock --check --offline --no-cache --prerelease disallow
& $UV --version
& $PY --version

& "$TASK\env2\Scripts\pacd-sim.exe" doctor --workspace-root $WS --repo-root $REVIEW
& "$TASK\env1\Scripts\pacd-sim.exe" doctor --workspace-root $WS --repo-root "$WS\review\pr1-613bc658-rechallenge-20260823"
& "$TASK\env2\Scripts\ruff.exe" format --check . --no-cache
& "$TASK\env2\Scripts\ruff.exe" check . --no-cache
& "$TASK\env2\Scripts\mypy.exe" src tests --no-incremental --cache-dir "$TASK\cache\mypy"
& $PY -m pytest -p no:cacheprovider --basetemp "$WS\t\i61" -q
& $PY -m pytest -p no:cacheprovider --basetemp "$WS\t\i62" --cov=pacd_sim --cov-branch --cov-report=term-missing -q
& "$TASK\env2\Scripts\bandit.exe" -c pyproject.toml -r src
& "$TASK\env2\Scripts\detect-secrets.exe" scan --all-files
& "$TASK\env2\Scripts\pip-audit.exe" --local --skip-editable

& "$TASK\env2\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
& "$TASK\env2\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
& "$TASK\env2\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424243
& "$TASK\env2\Scripts\pacd-sim.exe" verify <fresh-run-A> --workspace-root $WS --repo-root $REVIEW
& "$TASK\env2\Scripts\pacd-sim.exe" verify <fresh-run-B> --workspace-root $WS --repo-root $REVIEW
& "$TASK\env2\Scripts\pacd-sim.exe" verify <fresh-run-C> --workspace-root $WS --repo-root $REVIEW
& "$TASK\env2\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --reportable

& "$TASK\oldenv\Scripts\pacd-sim.exe" diagnostic --workspace-root $WS --output-root "$WS\var\runs" --scenario configs/scenarios/diagnostic_identity_smoke.yaml --seed 424242
& "$TASK\env2\Scripts\pacd-sim.exe" verify <old-head-run> --workspace-root $WS --repo-root $REVIEW

& $PY "$TASK\auth\authorization_rechallenge.py"
& $PY "$TASK\paths\adversarial_rechallenge.py"
& $PY "$TASK\evidence-agent\rechallenge.py"
& $PY "$TASK\evidence-agent\addendum_six_cases.py"
& $PY "$TASK\evidence-main\resource_boundary_probe.py"

& $PY -m pytest -q "$TASK\paths\adversarial_rechallenge.py" --junitxml="$TASK\paths\adversarial-rechallenge-final.xml"
& $PY -m pytest -q <selected CLI/path/governor/execution/transaction/replay/dependency modules> --junitxml="$TASK\paths\pytest-selected-green.xml"

rg --files -g '.github/workflows/**'
rg -n -i '<network/socket/http/cloud/endpoint/identity/credential/shell/process patterns>' src tests pyproject.toml
Test-Path 'configs\protocol\frozen\APPROVAL.json'
~~~

The complete pytest commands were first attempted with longer task temp roots; their Windows path-length-only failures and the final unchanged-code short-root passes are recorded above. The authorization probe had one intentional intermediate Pydantic-invalid-state abort while developing the task-created probe; its authoritative rerun treated the pre-mutation validation error as fail-closed and completed 62/62 assertions.

## Architecture assessment

The bootstrap now has credible structural separation for the required PACD boundaries:

- an evaluation harness separate from the defender implementation;
- a common typed defender interface;
- a safety governor separate from defenders and execution;
- a simulated-only execution broker with no network/process/API facility;
- post-transition verification and rollback checks;
- an independent retained-artifact verifier that reconstructs the expected diagnostic chain from the controlled checkout;
- an application-level append writer for raw evidence;
- metrics regenerated from retained raw events;
- an unconditional fail-closed reportable interlock.

The authorization remediations are substantive inside the harness: the trusted governor is re-evaluated, proposal membership is checked, decisions bind current action/policy/context/pre-state, and verification compares complete state. The verifier is also materially stronger than at `35be713`: it anchors controlled code/configuration/seed inputs and rejects the substantive refreshed-closure attacks listed above.

Important architectural limitations remain:

- the verifier shares schemas, deterministic builders, and some implementation modules with the producer, leaving common-mode risk;
- the audit writer is append-oriented at application runtime but is not WORM storage, hash chained, signed, or externally timestamped;
- R-02 demonstrates that evidence-instance identity/time is self-asserted rather than externally anchored;
- the broker's constructor is an in-process trust boundary, not a cryptographic or process-isolated governor boundary;
- authorizations are not one-shot capabilities.

The following seams exist but are **not substantive PACD implementation**. These expected bootstrap limitations are not classified as defects merely for being placeholders:

- **Red-agent behavior:** a fixed synthetic diagnostic fixture; the red-agent module had 0% branch-aware test coverage and is not integrated into the main harness.
- **Multi-agent orchestration:** a coordinator seam exists, had 0% coverage, and is unused by the diagnostic.
- **Mission-aware governance:** mission objects/snapshots are structurally validated and bound, but the governor does not perform substantive mission tradeoff reasoning.
- **Uncertainty-aware autonomy:** a deterministic toy probability update/threshold path, not general uncertainty-aware autonomy.
- **Polymorphism selection:** standalone operators exist, had 0% coverage, and are not selected by the harness.
- **Human oversight:** simulated oversight records exist, had 0% coverage, and do not provide a live human authorization path in the main diagnostic.
- **Fair comparative baselines:** a null baseline definition/interface exists, but no comparative baseline experiment, allocation, or fairness analysis is executed.

## Host-guardrail assessment

The review did not write to Desktop, Documents, Downloads, OneDrive-redirected equivalents, protected operating-system locations, or any external target. It did not change software, registry, services, tasks, global PATH, firewall, endpoint protection, permissions, UAC, or security policy. It did not create a real socket/scan/API call, production credential path, workflow, approval record, or reportable experiment.

All persistent review material is in the designated PACD workspace: no-hardlink checkouts under `repo`, environments/probes under `var/tmp`, non-reportable diagnostics under `var/runs`, and this report under `bootstrap-status`. Task-created SUBST aliases were removed; `subst` was empty at final hygiene. Both the review and feature checkouts were clean at the exact head. No existing repository file was modified.

Repository controls successfully rejected a broader authority root, non-direct-child repository, sibling/common-prefix path, traversal, junction/reparse component, device path, and diagnostic ADS/alternate output root. A SUBST alias resolving to the same canonical workspace was accepted without widening authority. The low-level generic jail accepts an ADS spelling contained inside its root, but no diagnostic writer accepts such a root and no ADS write was performed.

Host protections are not historical proof. The committed host logs and builder reports are claims about earlier activity; this review independently establishes only the state and actions it observed.

## Evidence-integrity and research-integrity assessment

Positive controls:

- all generated runs were explicitly `NON_REPORTABLE_DIAGNOSTIC`;
- each fresh run had the exact 11-file set: marker, canonical config, seed registry, status, manifest, JSONL, raw Parquet, summary CSV, summary Parquet, run log, and SHA256SUMS;
- fresh same-seed semantic hashes matched and different-seed hashes differed;
- substantive action/configuration/seed/provenance/event/metric tampering failed closed;
- old-code evidence was rejected against the exact current checkout;
- derived metrics were reproduced from retained raw records;
- failed-run evidence and hard-link-safe atomic status replacement were exercised;
- missing approval produced no run directory;
- no effect, comparison, safety, operational-readiness, publication, or generalization claim was produced.

Limitations:

- R-01 permits a compressed hostile retained artifact to consume memory after already failing its bound;
- R-02 means a self-consistent evidence package is not proof of original run identity/time or uniqueness;
- R-03 weakens provenance of interrupted evidence because parent retention does not prove child ownership;
- audit evidence is not externally anchored or cryptographically append-only;
- fair comparative baselines and substantive PACD research capability do not yet exist.

The bootstrap remains appropriate only as a bounded non-reportable diagnostic scaffold. Its artifacts must not support reportable claims.

## Differences from the builder's remediation/status reports

The independent review agrees with the builder on:

- exact additive commit history and the status-only `cfeb513..613bc658` delta;
- unchanged lock hash, Python/uv compatibility, offline reconstruction, quality/security checks, and current-head deterministic hashes;
- corrected public workspace authority and strengthened action/governor/state binding;
- rejection of substantive refreshed configuration/action/event/metric mutations;
- preemptive worker deadline, termination/kill paths, and preservation of task-created partial evidence;
- junction/reparse and stable-read approval hardening;
- explicit stable-only uv policy;
- absence of workflows, approval, reportable execution, production adapters, and external capability;
- the non-substantive architecture seams.

It differs materially in four places:

1. The remediation report says retained Parquet has bounded encoded and decoded size before materialization. That is true only inside the strict raw preflight; the complete verifier continues into later raw reads, and derived summary has no decoded-size preflight. R-01 disproves the complete-call claim.
2. The remediation report says refreshed run-ID mutations are rejected. A coherent run-ID/timestamp/closure shift verified valid. R-02 narrows the claim to substantive semantics, not evidence-instance identity.
3. The remediation report does not identify that parent interruption handling can claim and move a pre-existing token-matching staging directory. R-03 is a new transaction-ownership finding.
4. The remediation report discusses future approval authenticity/substitution generally but does not state that the loader accepts hard-linked regular files. R-04 makes that future-enablement condition explicit.

The builder's main validation table was recorded at implementation head `cfeb513` and some replay evidence at `47740cf`; this review reconstructed and tested the exact delivery head `613bc658`. The two later files were indeed status-only, but they were treated as claims rather than proof.

## Unexecuted or physically blocked tests

- **Real Windows directory symlink:** not created because the non-elevated host returned WinError 1314. An actual junction plus mocked symlink/reparse cases passed. No privilege was requested to bypass host policy.
- **Approval path replacement while its handle was open:** Windows denied replacement. In-place mutation between repeated reads was executed and rejected.
- **Controlled approval hard link:** not created because the review was explicitly forbidden to create `configs/protocol/frozen/APPROVAL.json`. The private loader behavior was safely demonstrated at a non-controlled task path, and the public reportable path remained unconditionally denied.
- **Real protected-path/device/ADS write:** intentionally not performed. Canonicalization and sink-denial paths were exercised without writing to a protected/device/alternate stream.
- **Real network, cloud, endpoint, identity, shell adapter, or external target:** intentionally not executed; static inventory and negative tests establish that no such implementation exists.
- **Five-minute wall-clock hang:** not waited out. The real spawned-worker test reduced the deadline to zero and completed in under ten seconds; deterministic process doubles exercised terminate, join, kill, EOF, malformed envelope, and no-retention-on-unkillable behavior.
- **Reportable experiment with any approval variant:** intentionally not run. Pure validation paths and absent-approval public denial were exercised without creating the forbidden record.

These exclusions do not excuse R-01; both reduced-cap resource probes were fully executed and directly failed the required complete-call behavior.

## Merge conditions

Before another merge classification:

1. Make raw/derived decoded Parquet preflight terminal for every later verifier consumer and independently repeat the instrumented complete-call challenge.
2. Define and enforce the evidence-instance identity contract. If run ID/time/uniqueness is claimed, externally anchor it and reject coherent relabel/replay.
3. Bind interrupted-evidence retention to a directory proven to be created by the current invocation, then repeat the pre-existing sentinel/race challenge.
4. Reject hard-linked approval files before any future reportable enablement.
5. Rerun the full independent challenge at the exact new additive head while PR #1 remains open and unmerged.

## Final decision

The remediation substantially improves the bootstrap and closes the original governor, action-binding, most verifier, public workspace, timeout, reparse, and prerelease-policy defects. It does not satisfy the explicit complete-call resource boundary, and it retains evidence-identity and interrupted-transaction ownership gaps.

**FAIL — bootstrap not acceptable for merge**

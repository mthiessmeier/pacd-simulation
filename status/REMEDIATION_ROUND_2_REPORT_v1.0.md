# PACD Bootstrap Remediation Round 2 Report v1.0

## 1. Scope and controlling classification

This is the versioned builder remediation record following acceptance of the August 23, 2026
Independent PACD Bootstrap Re-Challenge Review.

- Repository: `mthiessmeier/pacd-simulation`, private
- PR: #1, `codex/environment-bootstrap-v1` into `main`
- Exact independently reviewed head: `613bc65861fb428e8df45f509e568421a8547273`
- Exact round-two implementation-validation head:
  `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff`
- Controlling classification: **FAIL — bootstrap not acceptable for merge**
- Current disposition: locally remediated candidate requiring a complete independent re-challenge

This report does not claim an independent PASS and does not authorize merge. PR #1 remains open
and unmerged.

## 2. Preserved evidence and additive history

The exact accepted review is preserved byte-for-byte at
`status/reviews/INDEPENDENT_BOOTSTRAP_RECHALLENGE_REVIEW_613bc658.md`, length 43,881 bytes,
SHA-256:

`6D1F4756DA2EA427FA601DC3215C1586C9A07057C92F1780C019FE8E5FDB253B`

No prior report, review evidence, `CURRENT_STATUS.md`, or
`REMEDIATION_REPORT_v1.0.md` was overwritten, deleted, or silently revised.

Round-two history is additive:

| Commit | Purpose |
|---|---|
| `c2b2272d898a8d2314871f85744c065d4cc8f84e` | Preserve the exact independent re-challenge report. |
| `01451792ef28ad99c3be630a19f42d66cd6fa293` | Reject hard-linked approval records. |
| `52328b904accfc46c711085b0862c0421aacc1e0` | Bind bounded evidence to parent-owned invocation records and local execution receipts. |
| `cf2dae85cfc7f0da467a85d2f1cf3e31ef1176ff` | Remove an optimization-sensitive production assertion from receipt-authority denial. |

No force push, amend, rebase, reset, history rewrite, merge, visibility change, license selection,
workflow addition, controlled approval record, reportable execution, production adapter, real
target, cloud/network action, or external integration was performed.

## 3. Accepted finding disposition

### R-01 — terminal bounded Parquet handling

Raw and derived Parquet enter one bounded ingestion stage before any table is exposed. That stage:

- opens stable, singly linked regular files and checks encoded per-file and aggregate limits;
- bounds footer metadata, row groups, column chunks, Thrift strings/containers, decoded
  per-artifact and aggregate size, exact Arrow schema, and exact row count;
- bounds relevant string and payload cells after the sole materialization;
- preflights both artifacts before materializing either;
- returns terminally on any preflight or materialization failure;
- materializes each accepted artifact once through `ParquetFile.read`;
- passes cached tables and rows to labels, semantic hashes, summary derivation, and all later
  verifier consumers; and
- rechecks stable file identity/digest without reopening a rejected Parquet artifact.

Instrumented tests monkeypatch module-wide `pq.read_table` and `ParquetFile.read`. They prove
zero materialization after raw decoded-cap, derived decoded-cap, and aggregate encoded-cap
failures, and at most one materialization for each accepted raw/derived artifact.

### R-02 and R-03 — parent-owned invocation and local evidence identity

Before worker launch, the parent exclusively creates the exact invocation ownership directory,
staging directory, bounded ownership marker, worker capability, and separate parent-only receipt
capability. The worker receives the exact authority object with the receipt capability removed and
may write only to that parent-authorized staging directory.

Retention and finalization operate on the exact authority object. They validate the marker
identity, capability digests, canonical paths, staging device/inode, run identity, and expected
final path. They do not scan names, suffixes, siblings, or prefix lookalikes. Finalization uses a
non-overwriting rename. Pre-existing matching staging/final sentinels remain untouched.

After successful finalization, the parent exclusively creates a receipt under
`var/receipts/<invocation-id>.json`. The receipt binds:

- invocation ID and run ID;
- exact Git commit and lockfile hash;
- canonical configuration hash;
- seed and seed-registry hash;
- raw and summary semantic hashes;
- complete evidence-package digest;
- parent start/completion and manifest start/end timestamps;
- exact final path;
- ownership-marker digest; and
- owned final-directory device/inode.

Verification now reports three separate properties:

1. semantic-content validity;
2. execution-instance identity assurance from the local receipt; and
3. reportable status, which remains false.

A missing, duplicate, copied, mismatched, renamed, retimestamped, or directory-replaced package
does not gain a distinct authenticated execution identity. Deterministic same-content reruns
receive separate invocation IDs and receipts. EOF, malformed-envelope, process-start failure, and
timeouts before/after raw evidence use only the exact parent-owned transaction.

### R-04 — approval hard links

Approval stable reads require `st_nlink == 1` on the opened handle, after each bounded read, and
during final path-identity comparison. A safe non-controlled hard-link regression is rejected.
Bootstrap reportable execution remains unconditionally denied; no controlled
`configs/protocol/frozen/APPROVAL.json` was created.

## 4. Maintained earlier protections

The complete test suite retained the previously corrected F-01 through F-08 and inline-review
boundaries:

- checkout-derived workspace authority and exact `var/runs` output jail;
- traversal, alternate placement, symlink/junction/reparse, ADS/device, and protected-path denial;
- broker reevaluation through the harness-owned governor;
- complete action, proposal, policy, context, configuration, schema, and pre-state binding;
- fail-closed prohibited, escalated, unknown, and non-reversible automatic actions;
- exact state-transition verification with collateral-state rejection;
- strict duplicate/unknown/noncanonical/nonfinite/oversized JSON/YAML/evidence handling;
- manifest, checksum, event-chain, replay, metric, JSONL, and Parquet closure checks;
- duplicate action-ID denial;
- preemptive timeout/termination, raw-evidence preservation, and outside-sentinel protection;
- strict reportable-approval matrix with unconditional pre-output denial; and
- explicit stable-only offline lock policy.

## 5. Trust boundary and unresolved limitations

The new receipt satisfies the requested bootstrap local-control contract, but it is cooperative
bookkeeping rather than cryptographic provenance. It is not signed, protected by a platform key,
stored in WORM/external append-only storage, or externally timestamped. An arbitrary same-user
in-process or filesystem caller that can write both ownership and receipt stores can forge
canonical-looking local records. Private parent helper calls are likewise not a security boundary.
Consequently:

- `execution_identity_assured=true` means the package matches the current local controlled
  anchor under the cooperative harness threat model;
- it does not prove author identity, independent time, unique physical execution, or resistance to
  a malicious same-user process; and
- it never changes `reportable=false`.

This scope is explicit in the receipt module and must remain explicit in any external claim.
A failed exclusive setup can leave a newly created empty task-owned invocation directory after a
collision; no pre-existing file or directory is claimed or modified. This residue is bounded to
the workspace and is not treated as retained evidence.

The generic low-level broker remains callable by an arbitrary in-process Python caller with an
alternate governor. The supported public harness constructs its trusted governor and prevents
that injection. This seam must not be exposed as a production adapter.

## 6. Architecture assessment

The bootstrap still has separate seams for the evaluation harness, defender interface, safety
governor, controlled simulated execution broker, independent verifier, append-style audit writer,
raw-derived metrics, and fail-closed reportable interlock. Round two strengthens evidence
ingestion and local invocation identity without adding real-world execution.

The following remain intentionally non-substantive bootstrap seams and are not claimed as PACD
research capability:

- red-agent behavior is a fixed synthetic fixture;
- multi-agent orchestration is an unused coordinator seam;
- mission-aware governance validates structure rather than substantive mission reasoning;
- uncertainty-aware autonomy is a toy diagnostic probability/threshold path;
- polymorphism selection is not integrated into the harness;
- human oversight is simulated and not a substantive governor participant; and
- a null baseline exists, but no fair comparative baseline experiment is implemented.

Independent verification still shares schemas and deterministic builders with the harness,
creating ordinary common-mode risk. Audit evidence is append-style at the application boundary,
not WORM, externally anchored, or author-signed.

## 7. Host guardrails and research integrity

All implementation, test, environment, receipt, and diagnostic output remained inside the
designated PACD workspace. No protected Desktop, Documents, Downloads, OneDrive-redirected path,
unrelated content, registry setting, service, scheduled task, global PATH, firewall, endpoint
protection, or host guardrail was changed.

Static and runtime inventory found no GitHub Actions workflow, production adapter, real scan,
socket/packet operation, external target, cloud API, endpoint API, identity API, shell-based
execution adapter, production credential path, or external integration. Fixed subprocess use is
limited to local Git provenance queries and the bounded diagnostic worker process.

Every generated run is `NON_REPORTABLE_DIAGNOSTIC`. No effect, safety, benchmark,
generalization, publication, or operational-readiness claim is made.

## 8. Required next step

The exact pushed delivery head must receive a new complete independent PACD bootstrap
re-challenge. Until that reviewer issues a superseding classification:

1. the accepted FAIL remains controlling;
2. PR #1 remains open and unmerged;
3. no reportable execution or approval record may be created; and
4. the local receipt limitation and bootstrap-only architecture seams must not be overstated.

Validation details are in `status/REMEDIATION_ROUND_2_VALIDATION_v1.0.md`.

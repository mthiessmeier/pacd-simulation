# PACD Bootstrap Remediation Round 3 Report v1.0

## 1. Scope and controlling classification

This is the versioned builder remediation record following acceptance of the August 23, 2026
Independent PACD Bootstrap Final Re-Challenge Review.

- Repository: `mthiessmeier/pacd-simulation`, private
- PR: #1, `codex/environment-bootstrap-v1` into `main`
- Exact independently reviewed head: `4cba65779753a3096e2bd7551e7d4ff7321df4a2`
- Exact round-three implementation-validation head:
  `edd016cdca8a182d7014adf3ef47c8648b9f9e5d`
- Controlling classification: **FAIL — bootstrap not acceptable for merge**
- Disposition: locally remediated candidate requiring a complete independent re-challenge

This report does not claim an independent PASS and does not authorize merge. PR #1 remains open
and unmerged.

## 2. Preserved review and additive history

The exact accepted final re-challenge review is preserved byte-for-byte at
`status/reviews/INDEPENDENT_BOOTSTRAP_FINAL_RECHALLENGE_REVIEW_4cba657.md`:

- byte count: `45,534`;
- SHA-256: `23610FA16D66818E433D0DE0695A4AD30F9B8695ACE73EC7E4AB76BC4755276B`.

No earlier report, review, status file, or remediation record was overwritten, deleted, or
silently revised. Round-three history is additive:

| Commit | Purpose |
|---|---|
| `7a8180293c1a890d8fd5c79abbe2e34c3f40ec48` | Preserve the exact accepted final re-challenge review. |
| `edd016cdca8a182d7014adf3ef47c8648b9f9e5d` | Harden lexical control stores, cooperative assurance output, and terminal retained-evidence verification. |

The final report-bearing commit is recorded in the PR description and handoff comment because a
commit cannot embed its own final SHA.

No force push, amend, rebase, reset, squash, history rewrite, merge, visibility change, license
selection, workflow addition, controlled approval record, reportable execution, production
adapter, real target, cloud/network action, external integration, or new credential was created.

## 3. Governing local-receipt assurance decision

`execution_identity_assured` means cooperative local content, lexical-path, run, and
configuration binding at verification time. Structured output now states:

```text
identity_assurance_scope = LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING
historical_control_file_inode_continuity_assured = false
reportable = false
```

A byte-identical, singly linked replacement at the same correctly validated lexical path is not,
by itself, an assurance failure. Altered content, binding, path, link count, reparse state,
run-directory identity, configuration, seed, semantic hash, or package relationship still fails.

The receipt is not author-signed, externally timestamped, stored in WORM media, resistant to an
arbitrary malicious same-user writer, or a cryptographic execution attestation. No local inode
registry was added and historical control-file inode continuity is not claimed.

## 4. N-01 — exact lexical control-store enforcement

`var/receipts` and `var/invocations` now retain their exact lexical paths separately from resolved
paths. The shared control-path guard:

- constructs only the fixed canonical workspace-relative store path;
- rejects traversal components, ADS spellings, device namespaces, and reserved-device names;
- walks the lexical path and every existing component for symlinks, junctions, and reparses before
  resolution;
- requires the lexical normalized path to equal the fixed expected path;
- resolves only after the lexical check and requires the resolved path to remain identical; and
- is repeated around store creation, receipt creation/read/verification, ownership creation/read,
  interrupted evidence retention, finalization, and local identity evaluation.

Public diagnostic failures now return a structured non-success envelope with `valid=false`,
`semantic_content_valid=false`, `execution_identity_assured=false`, the exact cooperative scope,
historical continuity false, and reportable false.

Real non-elevated NTFS junction regressions cover pre-existing and post-run receipt/invocation
roots, nested invocation paths, sibling targets, and prefix lookalikes. The fixture restores the
ordinary control directory in an outer `finally` even after partial setup failure, removes only
its task-created target, and snapshots files, bytes, directories, and entry types so an empty
directory write is detected. Target sentinels and genuine copied records remain unchanged.

## 5. N-03 — terminal strict-evidence failure

One documented maximum retained JSON/payload container depth, `64`, now applies to every
independently decoded retained JSON document and embedded payload. Iterative, string-aware syntax
preflight rejects excessive depth before the recursive JSON decoder. Iterative decoded-value
preflight runs before recursive semantic normalization, and `RecursionError` remains only a final
defensive structured-invalid boundary.

Any strict retained-document, artifact-inventory, schema, row, JSONL, payload, or bounded-Parquet
error returns immediately from complete verification. Rejected evidence does not reach semantic
hashes, normalization, labels, summary reconstruction, metrics, receipt verification, checksum
semantic consumers, or later Parquet materialization.

The exact 1,500-level review payload returns `VerificationResult(valid=false)` and CLI
`status=INVALID`; it does not raise. Object, array, and mixed nesting immediately below, at, and
above the limit are covered. Semantic hashing measures an independently decoded payload at its
own root, avoiding an event-envelope off-by-one: exact depth 64 is accepted and depth 65 is
rejected. A complete-verifier plumbing regression confirms exact-depth semantic validity before
the intentionally stale copied-run receipt binding fails.

## 6. N-02 — assurance-contract clarification

The receipt module, verification result, CLI failure output, README, and
`docs/EXECUTION_IDENTITY_ASSURANCE.md` now distinguish semantic validity, cooperative local
identity binding, historical inode continuity, and reportability.

Tests confirm:

- byte-identical singly linked same-path receipt and marker replacement preserves semantic and
  cooperative binding;
- changed bytes, changed path, hard links, reparses, run-directory inode replacement, and
  receipt/run/configuration/seed/hash mismatches fail;
- valid and early-invalid API/CLI output carries the exact fixed scope and false historical/
  reportable flags; and
- no output claims signing, external timestamping, WORM storage, malicious-same-user resistance,
  cryptographic attestation, or reportable status.

## 7. Maintained prior protections

The full suite retained R-01 terminal bounded Parquet ingestion and R-04 approval hard-link
denial, together with earlier F-01 through F-08 protections:

- checkout-derived workspace authority and exact `var/runs` write jail;
- traversal, alternate placement, symlink/junction/reparse, ADS/device, and protected-path denial;
- harness-owned governor reevaluation and complete authorization binding;
- fail-closed prohibited, escalated, unknown, and non-reversible automatic actions;
- exact state-transition and collateral-state verification;
- strict duplicate, unknown, noncanonical, nonfinite, malformed, oversized, and nested data
  handling;
- manifest, checksum, event-chain, replay, metric, JSONL, and Parquet closure;
- duplicate action-ID denial;
- bounded process timeout/termination and failed-evidence preservation; and
- unconditional absent-approval reportable denial before output creation.

## 8. Architecture, trust boundary, and research integrity

The bootstrap retains separate seams for the evaluation harness, defender interface, safety
governor, simulated execution broker, independent verifier, append-style audit writer,
raw-derived metrics, and fail-closed reportable interlock. It adds no real-world execution path.

The following remain intentionally non-substantive bootstrap seams, not PACD research claims:

- red-agent behavior is a fixed synthetic fixture;
- multi-agent orchestration is an unused coordinator seam;
- mission-aware governance validates structure rather than substantive mission reasoning;
- uncertainty-aware autonomy is a toy diagnostic threshold path;
- polymorphism selection is not integrated;
- human oversight is simulated rather than an operational participant; and
- a null baseline exists without a fair comparative experiment.

Audit records remain local append-style application evidence, not externally anchored WORM
records. Independent verification still shares schemas and deterministic builders with the
harness, leaving ordinary common-mode risk. The generic low-level broker is callable by an
arbitrary in-process caller, but the supported harness owns and reconstructs its governor; this
seam is not exposed as a production adapter.

Static and runtime checks found no GitHub Actions workflow, `APPROVAL.json`, production adapter,
real scan, socket/packet operation, external target, cloud/endpoint/identity API, shell execution
adapter, production credential path, or external integration. Fixed subprocess use remains
limited to local Git provenance and the bounded diagnostic worker. Every created run is
`NON_REPORTABLE_DIAGNOSTIC`.

## 9. Required next step

A new independent reviewer must rerun the complete PACD bootstrap challenge against the exact
pushed report-bearing head. Until a reviewer issues a superseding classification:

1. **FAIL — bootstrap not acceptable for merge** remains controlling;
2. PR #1 remains open and unmerged;
3. no reportable execution or approval record may be created; and
4. cooperative local assurance and bootstrap-only architecture seams must not be overstated.

Exact builder validation is recorded in `status/REMEDIATION_ROUND_3_VALIDATION_v1.0.md`.

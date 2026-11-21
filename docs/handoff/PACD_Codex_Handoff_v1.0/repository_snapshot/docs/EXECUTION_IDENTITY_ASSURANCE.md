# Local Execution Identity Assurance

## Status and scope

This document defines the execution-identity assurance contract for the non-reportable PACD
bootstrap. The local receipt and ownership marker are controlled cooperative anchors. They are not
reportable-evidence anchors and must not be interpreted as such.

Every structured verification result exposes the following assurance scope without removing the
existing `execution_identity_assured` field:

| Field | Bootstrap value or meaning |
| --- | --- |
| `identity_assurance_scope` | `LOCAL_COOPERATIVE_CONTENT_PATH_AND_RUN_BINDING` |
| `execution_identity_assured` | Whether current local content, path, run, configuration, receipt, and ownership-marker bindings all pass |
| `historical_control_file_inode_continuity_assured` | Always `false` |
| `reportable` | Always `false` |

## What a successful local binding establishes

`execution_identity_assured=true` establishes only that verification found a consistent local
relationship at verification time among:

- the exact validated lexical and resolved receipt and invocation control-store paths;
- the control files' canonical content and single-link, non-reparse state;
- the final run path and the current run-directory identity;
- the invocation and run identifiers;
- the exact code commit and lockfile hash;
- the configuration, seed, and seed-registry bindings;
- the raw and summary semantic hashes; and
- the retained evidence-package digest and receipt/ownership-marker relationship.

This field is separate from `semantic_content_valid`. Overall `valid=true` for a bootstrap package
means that both semantic-content validation and the cooperative local identity binding succeeded.
It does not mean `reportable=true`.

## Control-file replacement rule

The verifier does not claim historical inode continuity for the receipt or ownership-marker file.
A byte-identical, singly linked replacement of either control file at the same correctly validated
lexical path does not, by itself, change semantic validity or the cooperative local binding result.
Consequently, `historical_control_file_inode_continuity_assured` remains `false` even when
`execution_identity_assured=true`.

This rule does not relax current-path or binding checks and does not extend to replacement of the
bound run directory. Assurance must fail for any of the following:

- altered control-file bytes or a noncanonical control record;
- a changed or uncontrolled control-file path;
- a hard-linked control file or any unexpected link count;
- a symlink, junction, reparse point, alternate data stream, device spelling, or indirect control
  path;
- replacement of the bound run directory or a mismatch in its identity;
- a renamed or retimestamped clone without its corresponding controlled local records; or
- any receipt/run/configuration/seed/hash/package/ownership mismatch.

## Explicitly excluded assurances

Neither a local control record nor a successful bootstrap verification establishes:

- historical control-file or receipt inode continuity;
- author identity or an author signature;
- a trustworthy external timestamp;
- WORM or other immutable storage;
- resistance to a malicious process running as the same user;
- cryptographic execution attestation; or
- reportable evidence or authorization to perform a reportable run.

The SHA-256 digests used by the bootstrap bind local content; they are not digital signatures.
Control-record timestamps are locally recorded values checked for content and chronological
consistency, not externally trusted time. No additional replaceable local registry can convert
these properties into historical continuity, signing, trusted time, WORM storage,
malicious-same-user resistance, attestation, or reportability.

## Consumer interpretation

Consumers must evaluate `semantic_content_valid`, `execution_identity_assured`,
`identity_assurance_scope`, `historical_control_file_inode_continuity_assured`, and `reportable`
together. They must not relabel a locally valid `NON_REPORTABLE_DIAGNOSTIC` as an experiment,
reportable result, external attestation, or author-authenticated evidence.

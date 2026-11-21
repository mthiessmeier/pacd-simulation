# Immediate Codex work order

**Status:** Concrete continuation instructions and proposed first technical scope. Check live authority before implementation.  
**Program scope:** Completion of the original broader PACD implementation agenda, with all retained requirements preserved.  
**First deliverable:** WP00 reconciliation and a complete, reviewable next work order.  
**First proposed technical increment:** WP01 development comparison-plan binding and attempt accounting.

## 1. Start from verified current evidence

Inspect the existing repository, worktree and PR state read-only. Record repository identity, current branch, full HEAD, merge base, dirty/untracked work, current remote head, latest accepted implementation, PR #9/#11 and any newer work. Inspect before running scripts.

Use the repository's existing clean-checkout or isolated-branch procedure. Preserve local work and concurrent changes. Never reset to a packaged SHA, re-run bootstrap installation, force-push, silently merge, overwrite untracked files, or adopt historical source commands merely because they are in the archive.

Read live AGENTS.md, owner decisions, current architecture, package/build configuration, CLI, implementation, tests, acceptance records and scope crosswalk. The existing toolchain and locked environment are the starting point. Record actual versions; do not upgrade for convenience.

PR #9 and PR #11 may still be drafts. Read their source material with that status and continue unaffected reconciliation. The package contains the relevant originals, so missing publication files should not block work that does not depend on them.

## 2. WP00: finish requirement-level reconciliation

### Inputs

- repository_snapshot/docs/PHASE2_SCOPE_CONTINUITY.md: eighteen workstreams.
- repository_snapshot/docs/PHASE2_ORIGINAL_SCOPE_INVENTORY.csv: immutable source identities and original text.
- 08_SOURCE_UNIT_RECONCILIATION.csv: working copy with additional evidence/mapping columns.
- Five original documents: WO, TM, EC, FM and MD.
- Live accepted code, tests, PR reviews, decisions and limitations.

### Required procedure

1. Classify every retained source unit: implementation requirement; acceptance/control requirement; draft methodological definition; source-explicitly deferred item; historical instruction; explanatory material; table header; or duplicate/cross-reference.
2. Preserve original unit IDs and text. Assign stable requirement IDs to actual requirements. Compound requirements may have child IDs; duplicates may map to the same requirement. Keep every parent and source link.
3. Map requirements to SC-01 through SC-18 and one or more WP IDs. Include work beyond the immediate next increment.
4. Inspect actual source, tests and accepted review scope. Separate implemented behavior from helpers, schemas, comments, retrospective-only tools and proposals. Distinguish builder-reported tests, accepted evidence and checks independently reproduced in this session.
5. Classify requirements as accepted complete, partial, open, not yet evidenced, source-explicitly deferred, or draft methodology. A missing citation alone does not prove absence. A passing narrow fixture or module name does not prove completion of a broader behavior.
6. Record precise residual behavior and discriminating acceptance criteria. Keep the original criterion or cite a later explicit author-approved equivalent.
7. Identify conflicts rather than silently resolve them. The Increment 1 equivalence decision applies to its stated scope. The six accepted bounded increments do not automatically close every original completion criterion.
8. Allocate every open or partial requirement to a delivery package. Record dependencies and the smallest coherent next increment. Existing accepted capability may satisfy a dependency; do not rebuild it.
9. Preserve all original draft scenarios, conditions, ablations and metric IDs even when not selected for the first experiment or implementation slice. Their source draft status stays visible.

### Concrete outputs

Use existing project conventions where equivalent files already exist; do not create competing authoritative tables.

- A completed first-pass reconciliation table, such as status/REMAINING_SCOPE_RECONCILIATION.csv, preserving all source IDs and identifying every residual requirement.
- A full remaining implementation plan, such as docs/REMAINING_IMPLEMENTATION_PLAN.md, with all WP allocations and dependency/acceptance criteria.
- A concrete next work order, such as docs/work_orders/DEVELOPMENT_COMPARISON_PLAN_v1.0.md, with the current authority, exact modules/files, behavior, interfaces, tests and exclusions.
- Current limitations and a source-conflict/decision note where needed. Do not fabricate author approvals or mark a proposed disposition approved.
- A real status/SESSION_HANDOFF.md or the current approved equivalent, populated from observed state rather than a blank template.
- Additive feature-branch commits and a reviewable unmerged PR under the applicable workflow.

### WP00 acceptance

- Every original source unit remains accounted for; non-requirement and duplicate classification is explicit.
- All eighteen workstreams, six classes, eight conditions, sixteen fairness dimensions, ten draft ablations and 47 metric IDs survive.
- Accepted-complete requirements cite applicable code, tests, accepted commit/review and any limitations.
- All partial/open/not-evidenced requirements have a concrete remaining acceptance need, dependency and work-package allocation.
- Source-explicitly deferred items, especially H6, retain their boundary.
- No requirement is removed or newly deferred by omission, milestone selection or phase renaming.
- The first work order is implementation-ready, with its authority status stated.
- Do not finish with the entire table still labeled unreconciled. Genuine evidence gaps may remain, but must name the gap, its consequence and the task that resolves it.
- For this documentation step, validate references and classifications. Do not run the full simulator suite solely to claim a documentation check; run code checks when necessary to resolve a specific capability question or when required by the implementation gate.

## 3. WP01: proposed first technical increment

### Problem

The accepted attempt register records attempt ID, invocation ID and seed. It retains unsuccessful outcomes honestly, but does not prospectively identify each planned comparison cell's scenario, defender condition, configuration and code revision.

The next bounded improvement is a **versioned development comparison plan** or compatible extension. It is a development control, not an author-approved frozen protocol, trusted timestamp, formal preregistration or reportable-run authorization.

### Inspect and reuse

Start with:

- src/pacd_sim/metrics/registered.py and dispositions.py;
- src/pacd_sim/configuration.py and schema.py;
- src/pacd_sim/cli.py and harness/run.py;
- reproducibility/manifest.py, receipts.py, verify.py and evidence_validation.py;
- existing registered-metrics, episode-metrics, configuration, identity, replay and reportability tests.

Discover actual signatures, invariants and CLI options. The package does not claim a new command or schema already exists. Use a new explicit format/version when adding strict fields; do not silently reinterpret existing v1 records.

### Required behavior

1. Define a bounded plan and comparison-cell contract with stable IDs, development-only classification and canonical serialization.
2. Bind each planned attempt to its invocation and development seed; planned scenario and defender-condition identity; governed configuration identity; exact code revision; comparison mode; and applicable seed/stream or exogenous-event identity.
3. Prefer the existing canonical aggregate configuration hash and governed component hashes. If multiple identities are retained, validate their consistency. A caller-supplied hash must not substitute for reading and validating the actual inputs.
4. Freeze plan membership for that diagnostic batch through its canonical digest. Do not imply external attestation or immutable trusted time.
5. Preserve current v1 register parsing, output meanings and accepted diagnostics. Choose an explicit compatible extension or separate plan version.
6. If the plan controls launch, reject configuration, seed, invocation, condition or code substitutions before allocation wherever the existing transaction boundary permits it.
7. On read, verify retained evidence first and compare expected with observed identities before releasing cell metrics. Contradictions must remain visible and withhold inappropriate counts. Do not rewrite the original terminal evidence to make it fit the plan.
8. Preserve every declared slot: completed, failed, timed out, incomplete and invalid. A retry has a new identity and its own accounted-for slot. Do not silently change membership or hide the earlier failure.
9. Keep expected and observed identities separate. Use explicit null/unavailable values when trustworthy outcome measurements are absent.
10. Preserve zero-denominator behavior and existing completed-only metric semantics. Identify remaining MD section 11 safety/failure-accounting work; retaining a failed row does not establish its unmeasured safety outcomes.
11. Keep reports and replay read-only. Preserve path bounds, file-size/depth controls, receipt ownership and invocation-collision safeguards.
12. Do not let plans change the governor, scenario, metric implementation, seed registry or harness from inside a defender run.

### Meaningful acceptance cases

- A matching planned cell produces a verified result with expected and observed identities.
- Scenario, condition, configuration, code-revision and seed substitutions are caught.
- A valid completed episode cannot silently be assigned to the wrong planned cell.
- Formatting-only JSON changes preserve the canonical digest; substantive membership/order/identity changes alter it according to the documented contract.
- Duplicate/conflicting IDs, oversized/deep/unknown-field plans and occupied invocation identities fail through the existing bounded paths.
- Completed, failed, timeout, incomplete and invalid slots all remain visible.
- A late failure with completed-looking artifacts does not release successful measurements.
- Expected/observed mismatch never becomes a fabricated zero.
- Re-reading unchanged evidence reproduces the report without changing retained stores.
- Accepted v1 outputs and replay semantics remain compatible.
- Existing simulation-only and reportability-denial controls hold through their approved negative-test route.
- Independent review challenges the exact candidate commit and confirms the change does not grant new execution authority.

### Deliverable and review

Provide implementation, focused tests that challenge those failure modes, required project quality/security gates, updated schema/CLI documentation, traceability IDs, explicit limitations and a clean candidate PR. Follow existing incremental review rules. Do not self-issue independent acceptance or merge.

If the current live author instruction already authorizes this scope, proceed after the bounded preflight. If it requires a new decision, finish the concrete work-order PR with the exact proposed change and stop only at that decision. Do not request confirmation for ordinary file/module choices.

## 4. Next behavioral milestone after WP01

Stage WP05/WP06 into a small guarded review-to-action-to-mission loop using accepted environment and fixture capabilities where sufficient:

- A review package identifies one concrete reversible simulated action, its exact target, evidence, policy, pre-state and validity conditions.
- Define the simulated review lifecycle, capacity, latency, terminal decision and timeout/expiry.
- Review approval is recorded separately from governor authorization. Re-evaluate current authority and state before dispatch. Do not convert a generic review request into authority for an arbitrary action.
- The in-memory broker performs the allowed transition; verification checks the complete allowed after-state and collateral effects.
- Record pending, denied, expired, unauthorized, execution-failed, verification-failed and rollback outcomes.
- Derive mission consequences and relevant time measures from retained state transitions and explicit clock semantics.
- Use matched benign/adverse cases and a baseline that does not confound corroboration with duplicate suppression.

That first loop does not require every eventual 30–100-identity scenario or every adversary policy to be finished. It also does not close those broader requirements. Full action classes, six-class polymorphism, policy portfolios, multi-agent arbitration, all conditions and the full evaluation program retain their separate WP allocations.

## 5. Source, research and host controls

Preserve all live project guardrails, source provenance and exact-head review requirements. No real targets, network attack behavior, production data or external-action adapter; no global software/security changes; no history rewriting, direct main commits, self-merges or release publication.

All outputs remain NON_REPORTABLE_DIAGNOSTIC. Preserve draft status, calibration exposure and negative outcomes. No hypothesis verdict, claim of lower analyst burden from referral counts alone, final reportable seed range, human-participant study, or approval record is created by this work order.


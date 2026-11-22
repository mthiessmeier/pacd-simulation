# Operator review brief at admission

TM-019 calls for a rationale, uncertainty and impact preview at human review. TM-037 requires an evidence-backed proposal and fresh execution authority. The accepted GOV-002 evaluator already follows the bound request to its review outcome (MD-039). This WP06 increment makes a prospective brief available to the simulated reviewer at admission for the two implemented actions. R-TM-019 maps to WP05/WP06 and SC-10/11/12. R-TM-037 also maps to WP08. The owner authorized a public development draft from the approved PR #20 merge.

## Contract

The evaluator may select `guarded_review.decision_brief: operator-preview-v1` in a governed scenario. On successful queue admission, retain the operator brief inside the concrete request binding. The request digest covers it and follows the same request through review. Keep the original contract for configurations that omit this setting. A full queue, an ineligible request or a brief too large for the existing audit payload limit records an admission failure. No partial package enters the queue.

Give the reviewer the governor's reason, the concrete proposed change and its synthetic target, the delivered signal and its age, and the limitations of the available evidence. The sensor model generates one reading per event from one source. Use opaque observation and source keys and the acquisition and delivery clock. The normalized evidence category, class-derived confidence, hidden event label, future measurements, configured review response and eventual dispatch outcome are outside the reviewer’s information set.

Project the immediate mission effect conditional on the proposed action receiving fresh authority while the submitted state still holds. Use the current dependency graph and immutable in-memory transition for isolation or sensing. Identify which missions would change availability. Distinguish this conditional preview from actual mission observations and elapsed outage. Preserve dispatch policy, capacity, expiry, denial, rollback and failure accounting.

## Acceptance

1. Produce a brief on the ordinary diagnostic path before any simulated approval or execution. Independently reconstruct the binding from the verified scenario, delivered observation, governor decision and submitted state. A genuine receipt for an altered brief must fail semantic verification even when the producer recomputes the request digest.
2. Compare an isolation fixture with core and auxiliary missions against its existing equivalent, and a sensing fixture against its original. Expect only the core mission to lose availability under the isolation projection. Expect no availability change from the sensing switch. Compare static and corroborated isolation, contextual sensing and a condition with no eligible referral. Use development seeds 424242 and 424243 and retain an unlaunched plan slot.
3. Challenge visible-input equivalence under changed hidden labels and future outcomes, delivery age, missing or mismatched observations and rejection paths. Check the fresh governor decision and unchanged execution path after review. Verify GOV-002 reconciles both binding versions and prior defaults, pinned plans and registers still reproduce.
4. Run the frozen suite and separate exact-revision reviews. Record command, configuration, seed, invocation, revision and evidence identities. Keep results classified `NON_REPORTABLE_DIAGNOSTIC`.

Inspect a retained diagnostic using `pacd-sim verify RUN_DIR`. In the verified `raw/events.jsonl`, the `guarded_review` row with outcome `pending` carries a JSON-encoded `payload_json` field. Decode this field and read `binding.operator_brief`. The outer binding carries the evaluator's provenance. A simulated decision remains subject to the governor and the dispatch pre-state check.

## Remaining work

Operator modification and override, richer uncertainty models, authority beyond the two synthetic actions, calibrated evidence thresholds, operator-burden and human-trust measurements retain their existing allocations. H6 requires a separate human study. [Source reconciliation](../../status/REMAINING_SCOPE_RECONCILIATION.csv) · [Full implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

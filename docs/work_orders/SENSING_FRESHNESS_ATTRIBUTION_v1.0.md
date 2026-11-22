# WP03/WP12 work order · Freshness at referral and execution

CAL-006 asks whether a candidate or executed action relied on evidence older than the applicable policy allows. Source unit MD-049, requirement R-MD-049, assigns this question to SC-03, SC-04 and SC-17. The [reconciliation](../../status/REMAINING_SCOPE_RECONCILIATION.csv) retains the definition as draft. This slice measures the two prospective sensing conditions introduced in [PR #17](https://github.com/mthiessmeier/pacd-simulation/pull/17). The source measurement clock and inclusive three-tick development window come from [WP03](VERIFIED_EVIDENCE_CONTEXT_v1.0.md). Both conditions' reliance rules come from [WP08](PROSPECTIVE_SENSING_SELECTION_v1.0.md).

## Measurement

Use the existing authenticated evidence and independent replay. For a real `candidate_action` row, evaluate the supporting measurements at the referral candidate's tick. For a guarded `executed` row, use the original referral's evidence at the actual execution tick. Count each stage once. Denied, expired, pending and pre-execution failures can contribute a candidate. A rollback after an execution retains the execution in its denominator. A recommendation to keep the default contributes neither stage.

The scheduled policy relies on the current measurement alone. The contextual policy also relies on its selected prior measurement tick. All references tied at that tick have the same age. A later observation cannot refresh either input retrospectively. Identify the referral and supporting evidence in each action record. Preserve the distinct concrete action identity at execution.

At each stage, age equals the stage tick minus the measurement tick. An action with complete attribution is stale when any required age exceeds three, and fresh otherwise. Classify incomplete attribution as unknown. Report the total and the fresh, stale and unknown counts separately for each stage. Divide stale by fresh plus stale. A zero denominator yields null. Each rate describes one fully verified episode. The existing attempt ledger preserves failed, invalid, timed-out and incomplete attempts separately with null episode metrics.

## Public entry points

From the pinned, clean checkout, use the existing metrics command with an optional extension.

```text
pacd-sim metrics RUN_DIR --sensing-freshness
pacd-sim metrics --plan PLAN_FILE --plan-sha256 PLAN_DIGEST --sensing-freshness
pacd-sim metrics --register REGISTER_FILE --register-sha256 REGISTER_DIGEST --sensing-freshness
```

The extension appears under `metrics.guarded_review.sensing_freshness` for an eligible completion. The same object is included in the per-attempt metric hash. Default metrics retain their accepted representation and hashes. An out-of-scope condition omits the extension. Only the evaluator reads these records. The governor and broker retain their existing decision and dispatch rules.

## Acceptance and limits

1. Register the nominal, costly and delayed fixtures with both sensing conditions and the two development seeds 424242 and 424243 before launch. Retain one unlaunched slot. A clean replay must reproduce plan identity, stage counts, denominators and report hashes.
2. On the nominal fixture, ticks 2 and 1 supply current and prior support. At candidate tick 3, both conditions are fresh. At execution tick 5, the scheduled input is exactly three ticks old. The contextual reference is four ticks old. Challenge a new delivery with a later clock and verify that the original support stays bound.
3. Check the costly contextual fallback and delayed pair, missing support, review denial, rollback and invalid producer evidence. Confirm that an unsupported condition preserves its existing metrics and that opt-in reads leave retained run records untouched.
4. Run the frozen full suite and static checks and compare the public per-run, registered and planned results. A separate session reviews the exact candidate. Preserve the command, environment, commit, configuration, seed and invocation records.

This is a development application of CAL-006 to two synthetic policies. Cross-condition attribution, failed-episode safety evidence, broader calibration and all other work packages remain in the [implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md). H6 retains its separate human-study authority. Classification `NON_REPORTABLE_DIAGNOSTIC`.

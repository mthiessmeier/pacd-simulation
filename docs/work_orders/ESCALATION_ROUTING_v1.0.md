# GOV-002 · Escalation routing completeness

Implement the draft GOV-002 definition for the two current guarded review contracts. WP06 owns the review lifecycle, WP05 the bound action and WP12 the measurement. R-MD-039 maps to SC-10, SC-11 and SC-17. Dependencies are the accepted governed review queue, verifier replay, release rules and registered development plans. The owner authorized the next public development PR from the approved #19 merge. D-017 and DEC-038 apply.

## Measurement contract

For a completed, verified guarded episode, count every original governor decision with disposition `ESCALATE` once. A complete guarded package binds that referral and governor decision to the proposed action, subject, delivered evidence, policy, pre-state and validity interval. Count the referral as routed when a verified admission has such a package and its matching request has a terminal review outcome. Use the actual referral and request identities throughout.

| Outcome for one escalation | Contribution to numerator |
|---|---|
| Approved, denied or expired with a complete matched package | 1, with each outcome counted separately |
| Capacity exhausted or admission refused | 0 |
| Admitted and still pending at the episode horizon | 0 |
| No matching admission or terminal outcome | 0 |

Publish the numerator, denominator, fraction, admitted package count and outcome breakdown. An empty denominator has a null fraction. Approval followed by a failed authorization, execution or rollback still has one review outcome. A review timeout appears as an expiry. A timed-out *attempt* has no publishable episode measurement.

## Entry points and acceptance

Extend the existing `pacd-sim metrics` command with `--review-routing` for run, pinned plan and pinned register reads. Use the existing verifier's checked events and canonical metrics hashing. Default output and historical digests must reproduce. Compose the option with sensing freshness and mission impact. Omit the extension outside guarded episodes. Preserve null measurements and receipts for incomplete, failed, timed-out and invalid attempts.

Prespecify a synthetic two-subject same-tick fixture with review capacity one. A static condition should produce two governor escalations, one complete approved package, one capacity failure and a fraction of 1/2. Run the corroborated comparison on the same inputs and development seeds 424242 and 424243. Use an ordinary admitted guarded referral as a positive control, an unguarded baseline for scope and an unlaunched slot for missingness. Challenge explicit denial, late or absent response, pending at the horizon, mismatched or tampered records, and downstream outcomes. Compare per-run, pinned-plan and pinned-register digests. Retain exact revision, configuration, stream and invocation identities with the results.

Independent reviewers should reconstruct the denominator from governor decisions and the numerator from matched admissions and terminal review records. Check the unchanged default reports and failure accounting on the exact candidate before a merge decision.

## Residual scope

MD-039 describes the metric over escalation packages generally. This development measurement covers the machine-verifiable package in the implemented guarded contracts. TM-019 and TM-037 retain operator-facing rationale, uncertainty and impact previews, modification, overrides and future action contracts. Calibration, cross-condition fairness, failed-episode safety and tail metrics, and the separate H6 human study retain their original allocations. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Requirement ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv) · [Full implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

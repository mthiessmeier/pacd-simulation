# Simulated approval burden

OPS-003 asks for approval requests, wait time, timeout and override count. R-MD-058 maps this to WP06/WP12 and SC-11/17. TM-019 covers queue behavior and TM-060 covers operational burden. The owner authorized another public development draft after the PR #21 merge. D-017, DEC-038 and the existing independent verification and release rules apply.

## Units and population

Report this optional measure for a verified, completed, guarded synthetic episode. An escalation is a governor decision to refer. A request begins when the queue admits its bound package. Count queue-capacity and other admission refusals separately. An admission does not establish approval, dispatch or action execution.

Account for each admitted request from submission until its matching approval, denial or expiry. A request still pending at the verified episode horizon contributes the observed wait through that tick. Label it pending and leave its terminal tick null. Its final duration is unknown. Match by originating referral, subject and request digest across both existing binding versions.

Count elapsed simulation ticks over the half-open interval from admission to closure or horizon. A same-tick resolution has zero wait. Sum individual waits in **request-ticks** so simultaneous waiting by different requests contributes separately. Publish the admitted-request rows, observed totals by outcome, and the mean and denominator for resolved requests. A zero denominator yields a null mean. Keep expired reviews separate from timed-out diagnostic attempts. No current guarded contract emits a simulated override. Report override count as null with its unsupported status.

## Controlled diagnostic

A governed two-subject fixture admits requests at ticks 2 and 5 under static review. Capacity is two, delay and validity are four ticks, and the horizon is tick 8. The first request reaches approval at tick 6. The other remains pending. The predicted observations are four resolved ticks, three censored ticks and seven request-ticks. Under corroborated review the same inputs yield zero admissions. Prespecify both conditions and development seeds 424242 and 424243. Use existing capacity-one, sensing, historic v1 and unguarded fixtures as controls and preserve an unlaunched plan slot.

## Acceptance

1. Independently reconcile admissions, per-request waits, expiries and censored rows to the raw governed events. Compare total request-ticks with the area under the number of open reviews. Exercise overlap, same-tick closure, denial, expiry after the last valid tick, horizon censoring, refusal and downstream dispatch outcomes.
2. Release the extension at `metrics.guarded_review.approval_burden` through the existing `pacd-sim metrics --approval-burden` run, pinned plan and pinned register paths. Their episode digests must agree. Preserve default hashes, historical binding behavior and composition with GOV-002, CAL-006 and MIS-002.
3. Invalid, failed, timed-out and incomplete attempts keep their status and null episode measurements. A verified unguarded episode omits the extension. Retest the reportable interlock, frozen environments, source reconciliation and independent exact-head review.

## Residual scope

An observed request-tick measures elapsed queue time. Staff effort, calibrated cost and human-subject burden require other evidence. The source’s preferred direction assumes equivalent safety and outcomes. Simulated override and modification, GOV-003, fair cross-condition interpretation, failed-episode safety, calibration and the separate H6 study retain their original acceptance criteria. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Source ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv) · [Remaining implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

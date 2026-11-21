# Guarded review of a synthetic session isolation

**WP05/WP06 development increment Â· NON_REPORTABLE_DIAGNOSTIC**

The owner authorized this slice after approving [PR #12](https://github.com/mthiessmeier/pacd-simulation/pull/12) at `d70510d8abb27d6d9729c402f06b0e69bc33c9f3`. Its merge into main at `f881f6553e9210d84e8f009a9700c0ce65eceabd` is the implementation base. The decision applies to one reversible in-memory handler and a simulated reviewer. The independent-review candidate has its own commit and PR.

## Scope and source traceability

| Retained units | Slice acceptance evidence | Residual scope |
|---|---|---|
| WO-063, TM-015, TM-018, TM-050, TM-051 | A concrete target, immutable action and policy binding, fresh dispatch decision, independently checked complete transition and restoration | Further action types, costs, contextual authority levels and broader partial-failure handlers in WP05 |
| TM-019, TM-049, TM-058, EC-027, EC-087 | Capacity, simulated delay, inclusive validity, one-shot resolution, preserved outcomes and accountability | Modification, overrides, richer human-routing and mission-command decisions in WP06 |
| TM-020, TM-036, EC-063, EC-082, EC-097 | In-memory broker, collateral checks, retained rollback success or failure and a failed-attempt receipt boundary | Additional recovery mechanisms, safe degradation and failed-episode safety/tail measures |
| FM-021, TM-060 | Identical reviewer, sensors and suppression rules for two prospective conditions, measured review waits and mission availability | Eight-condition design, sixteen fairness dimensions, all draft ablations, control-plane costs and calibration |
| EC-016, EC-017, TM-062, TM-073 | Simulator-only scope | H6 human-subject research retains separate authority |

The [source-unit ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv) records the earlier accepted baseline. The [remaining plan](../REMAINING_IMPLEMENTATION_PLAN.md) retains all 18 workstreams, six variation classes, portfolios, arbitration, comparisons and 47 metric IDs. This increment provides diagnostic measures and closes no broader work package.

## Runtime contract

A governed scenario opts in with `guarded_review` and supplies capacity, response delay, validity, end tick, response, rollback and matched sensor mean. Use `diagnostic_guarded_benign.yaml` or `diagnostic_guarded_adverse.yaml` with either `static_review.yaml` or `pacd_corroborated_review.yaml`. The evaluator owns configuration, seed, clock and synthetic truth. Both conditions receive the same tick, subject and sensor signal. Eligibility and suppression are visible separately in prospective decision rows. The shared gate admits the first eligible proposal in an elevated same-subject episode. The earlier comparison fixtures retain their original referral policies.

1. The existing independent governor evaluates a human-review referral. A queue request needs a matching escalation, delivered evidence and one eligible synthetic session. Admission records the exact reviewed isolation action, subject, evidence, state, policy and validity window under a request digest.
2. Ticks are integer simulation time. The queue advances to due work before the next delivered observation, resolves simultaneous requests in admission order, and advances through the configured horizon. Zero-delay review resolves after admission on the same tick. The expiry tick is inclusive. A missing response remains pending through that tick and expires on the next tick if reached.
3. Simulated approval consumes the request. The independent governor evaluates the concrete action against the **current** policy and snapshot. Apart from deterministic clock advancement, the dispatch pre-state must match the reviewed state. A new or stale decision cannot override a prohibition. Only the existing local broker can apply the reversible isolation.
4. Verification reconstructs the entire expected state and checks for collateral changes. A requested or necessary rollback checks the restored snapshot. The audit binds each lifecycle row to the original referral and request digest. Each stage reaches the audit before the next fallible operation starts. An ordinary operation failure retains the observed stage, error and recovery evidence in the failed attempt. The queue consumes both evidence IDs and their underlying observation IDs.
5. The read-only verifier reconstructs the governed schedule and expected transitions against retained rows. A verified completion releases the episode measures through the existing single-run and registered/plan interfaces. The original receipt, Git/configuration binding and reportability interlock apply.

## Measures and fixture oracle

Count each independently evaluated concrete candidate and the original referral in the action denominator. Reviewer approval alone contributes no governor approval or execution. Guarded metrics identify the clock unit, horizon, outcome counts and unresolved requests. Mean wait covers requests with an observed review resolution. Verification uses executed reviewed actions as its denominator. Rollback success uses attempted rollbacks. Canonical state digests distinguish wire values that compare equal in Python. A zero denominator yields `null`. A failed, timed-out, incomplete or invalid attempt contributes to attempt status and withholds its episode measurements.

Mission exposure accumulates the number of unavailable missions over half-open intervals between verified transitions from tick zero through the horizon. The denominator is mission count times horizon length in simulation ticks. A verified interruption and restoration in the same tick yields an observed zero-duration interruption. A failed episode has no completed exposure measurement.

| Default fixture property | Static | Corroborated |
|---|---:|---:|
| Delivery ticks in either truth condition | 2, 2, 3, 5 | 2, 2, 3, 5 |
| Eligible proposals before shared suppression | 4 | 2 |
| Admitted request tick | 2 | 3 |
| Governor-approved dispatch tick | 4 | 5 |
| Unavailable mission ticks through tick 8 | 4 of 8 | 3 of 8 |

These figures are deterministic fixture assertions. Same-tick duplicate readings cannot establish the first corroboration. When rollback is enabled the final availability projection must identify the restored mission. A missing response, capacity denial or failed authorization must never generate a broker dispatch.

## Reproduction

In a clean checkout under the dedicated workspace, use the locked environment and the existing interfaces. The diagnostic prints the invocation, manifest and run directory. Use that run directory for the read-only commands.

```powershell
uv sync --frozen --offline --python 3.13.15
uv run --frozen --no-sync pacd-sim doctor
uv run --frozen --no-sync pacd-sim diagnostic --scenario configs/scenarios/diagnostic_guarded_benign.yaml --baseline configs/defenders/static_review.yaml --seed 424242
uv run --frozen --no-sync pacd-sim verify <run-directory> --show-event-sequence
uv run --frozen --no-sync pacd-sim metrics <run-directory>
uv run --frozen --no-sync pytest -q tests/scenario/test_guarded_episode.py tests/unit/test_guarded_review.py
```

The WP01 comparison plan binds scenario, condition, revision, development seed, event/configuration digests and invocation before launch. Use a distinct cell for each seed and a fresh invocation ID per attempted run. The [WP01 work order](DEVELOPMENT_COMPARISON_PLAN_v1.0.md) gives the complete schema. `baseline` and `defender-trace` still compute retrospective proposals from verified observations. The guarded lifecycle itself is available in verified event order and measured by `metrics`.

## Review and limits

Challenge timing ties, replay, policy or state drift, denied/expired/pending requests, capacity exhaustion, unauthorized dispatch, collateral mutation and failed recovery. Check redigested forged rows, exact restoration, unmeasured denominators, stable legacy outputs, the locked suite and the reportability interlock. The [session handoff](../../status/SESSION_HANDOFF.md) identifies the actual branch, evidence, outstanding review and next action. The simulation tick has no calibrated physical-time equivalent. The fixtures supply identical observations across truth labels and establish no estimate of effectiveness or human performance.

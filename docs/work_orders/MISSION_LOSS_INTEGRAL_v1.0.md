# WP02/WP12 work order · Criticality-weighted mission loss

Draft metric MIS-002 asks for the integral of weighted mission degradation below nominal. Source MD-018 / R-MD-018 assigns the requirement to SC-02 and SC-17. The development acceptance criterion calls for hand integration and a change of weights. The prior verified report sums unavailable mission ticks across functions. The new opt-in view identifies which functions were unavailable and applies the weights from the checked-out scenario. [Requirement ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

## Measurement contract

For guarded episodes under `required_dependencies_v1`, nominal means that every configured mission is operational. Binary availability comes from the independent replay's dependency model. Let `D_i` be the number of simulated ticks during which mission `i` is unavailable in the half-open interval from zero to the verified episode horizon `H`. Its configured criticality `w_i` is a development weight.

- **Weighted loss** is the sum of `w_i × D_i`, in criticality-weighted mission ticks.
- **Possible weighted ticks** are `H × sum(w_i)`. The loss fraction is weighted loss divided by this exposure. A zero exposure yields a null fraction. Observed outage ticks remain available even for a mission assigned zero weight.
- The initial state applies from tick zero. An execution or restoration changes membership from its own tick forward. Simultaneous transitions have zero elapsed time between them. The last state persists to the horizon, including outages still unresolved then.
- Keep a mission-ID-ordered row for every mission, including its weight, unavailable ticks and contribution. Compute with exact ratios of the canonical decimal weights before producing numeric displays. The reduced `loss_fraction_exact` string preserves ratios below floating-point display resolution and is null when the fraction is undefined.

Use the independent replay's checked state and the existing receipt and artifact verification path. Only eligible verified completions receive `metrics.guarded_review.mission_impact`. Ineligible conditions omit the extension. Failed, timed-out, incomplete and invalid attempts retain their existing dispositions and null episode metrics. Failed-episode safety accounting has a separate work order.

## Development comparison

The two governed benign fixtures have one service-backed core mission that depends on the isolated session, and an auxiliary mission with independent service. The high-weight fixture assigns criticalities 0.8 and 0.2 to core and auxiliary respectively. The low-weight fixture reverses the assignment. The clock, dependencies, telemetry, event sequence and review policy match. The checked-out scenario and configuration hashes identify each weight assignment.

Prespecify the two fixtures with static review and corroborated review on development seeds 424242 and 424243. At horizon 8 the expected core outage is four ticks after static review or three after corroborated review. The auxiliary stays operational. The resulting weighted losses for the high and low fixtures are 3.2 and 0.8 under static review, and 2.4 and 0.6 under corroborated review. Keep an unlaunched comparison slot with null measurements. Use a sensing-only change as a zero-loss control and a legacy unguarded episode to check omission.

## Acceptance

1. Reproduce the four hand-integrated values, per-mission exposures and exact ratios. Challenge initial outages, nonuniform intervals, restoration at the horizon, same-tick rollback, tiny and zero weights, and zero exposure.
2. Require identical per-episode measurements and hashes from the run, pinned-plan and registered readers. Check the opt-in together with CAL-006 and the default wire representation. Substitute incorrect mission membership evidence under a genuine receipt. Verification must withhold the invalid measurements.
3. Check the clean merge base, run the frozen suite and static checks, and obtain independent review on the exact candidate. Preserve source, fixture, seed, plan, invocation and command identities.

```text
pacd-sim metrics RUN_DIR --mission-impact
pacd-sim metrics --plan PLAN_FILE --plan-sha256 PLAN_DIGEST --mission-impact
pacd-sim metrics --register REGISTER_FILE --register-sha256 REGISTER_DIGEST --mission-impact
```

The weights and binary nominal reference are development assumptions. Graded mission states, frozen weights, harm calibration, attribution of particular causes and cross-condition reportable analysis retain their separate criteria. MIS-005, failed-episode safety and H6 remain open. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Full implementation plan](../REMAINING_IMPLEMENTATION_PLAN.md)

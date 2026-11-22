# WP07 - One governed sensing-profile operator

**Evidence class** `NON_REPORTABLE_DIAGNOSTIC`

The owner authorized the next development increment after approving PR #14 at `18f3364775ad379b73b4b1ea958b125e4ace31cf`. The accepted [remaining plan](../REMAINING_IMPLEMENTATION_PLAN.md) places WP07 after the first guarded action and review slice. This work order selects the sensing class in TM-015/TM-016. The integration reuses the guarded request, independent governor, local broker, verification, rollback, receipt, comparison plan and failed-attempt accounting from [PR #14](https://github.com/mthiessmeier/pacd-simulation/pull/14).

## Decision and scope

At the first delivered observation the defender may request one reversible change to the synthetic subject's unique eligible session. The action changes the session's sensing profile from default to alternate. Its concrete effect is to retain two decimal places in subsequent delivered signals instead of one. Latent samples, event times, subject, review rules, budget and random stream are evaluator-owned. The initial reading and cost information available to the fixed and adaptive choices match. The defender has no access to subsequent latent samples or evaluator knowledge measures.

| Condition | Decision rule |
|---|---|
| Fixed | Request the switch at the decision opportunity if it is admissible and affordable. |
| Adaptive | Compare the observed signal with the declared switch cost and retain the default on a tie or when cost exceeds benefit. Apply the same eligibility and budget checks. |
| Disabled | Retain the default profile. Use the same observations, opportunity, evaluator configuration and budget. |

Selected requests remain subject to review capacity, delay, expiry and fresh authority at dispatch. Isolation and sensing have distinct action types and allowlists. Switching must change exactly one profile, preserve session availability and every collateral field, and verify against the independently projected complete state. Rollback restores the exact dispatch pre-state. A restored switch still incurs its verified switching cost. A failed or unverified attempt withholds completed episode measurements.

## Declared evaluator assumptions

The passive observer initially knows the default profile. While the alternate profile is active, the modeled probability the observer knows it equals the configured detectability. Integrate that probability over half-open simulation-tick intervals through the horizon. This model supplies an explicit diagnostic knowledge effect. The model contains no attacker decision or learning mechanism. The normalized switch cost and detectability are fixture inputs.

Both shipped scenarios use latent signal 0.86, the same live opportunity, capacity and response schedule, a one-unit budget, detectability 0.25, and horizon 8. Only cost and the scenario identifier differ across the nominal and costly inputs. The projected first reading is 0.9. The prospective request can arrive at tick 2 and dispatch at tick 4. The tick-5 reading is 0.86 in the alternate profile and 0.9 in the default profile.

| Fixture and condition | Verified switches | Charged cost | Alternate ticks | Expected known-profile ticks out of 8 |
|---|---:|---:|---:|---:|
| Nominal fixed or adaptive | 1 | 0.25 | 4 | 5 |
| Costly fixed | 1 | 0.95 | 4 | 5 |
| Costly adaptive or either disabled | 0 | 0 | 0 | 8 |

These numbers are deterministic acceptance oracles. A zero-duration verified switch and rollback has an observed cost and zero alternate ticks. Missing measurements remain null. Operators cannot change the evaluator, scenario, seeds, budget, authority, or metric calculation.

## Verification and reproduction

For a clean checkout inside the dedicated workspace, the following commands use registered development seeds and the frozen environment. Supply the run directory printed by the diagnostic to `verify` and `metrics`.

```powershell
uv sync --frozen --offline --python 3.13.15
uv run --frozen --no-sync pacd-sim doctor
uv run --frozen --no-sync pacd-sim diagnostic --scenario configs/scenarios/diagnostic_sensing_nominal.yaml --baseline configs/defenders/sensing_adaptive.yaml --seed 424242
uv run --frozen --no-sync pacd-sim verify <run-directory> --show-event-sequence
uv run --frozen --no-sync pacd-sim metrics <run-directory>
uv run --frozen --no-sync pytest -q tests/scenario/test_sensing_episode.py
```

Exercise all six scenario/condition pairs, refusal, budget exhaustion, same-tick restoration, delayed dispatch and adverse cost. Check that suppression of the operator preserves unrelated inputs. Challenge action substitution, collateral state changes, wrong policy, forged precision and cost/duration measures, and release through single-run and planned reports. Check legacy artifacts, missing-attempt denominators, reportability denial, exact code/configuration/seed identity and independent review on the candidate commit.

## Retained source obligations

WO-063/079 and TM-015/016/033/044/065/066 define the action and six-class architecture. EC-059 and the POL metric family remain in the [source-unit reconciliation](../../status/REMAINING_SCOPE_RECONCILIATION.csv). This increment supplies one operator, a controlled cost, duration and assumption-bound knowledge measure for SC-06/07/10/12/17. WP08/WP09 retain full six-class selection, portfolios and coordination. WP11-WP15 retain broader conditions, metrics, failure populations, calibration and reproduction. H6 retains separate human-subject authority.

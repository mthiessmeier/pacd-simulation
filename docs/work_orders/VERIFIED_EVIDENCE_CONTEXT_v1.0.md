# WP03 work order · Verified evidence age and source context

**Development scope.** Give a future WP08 selector a reproducible account of what a synthetic defender could have known at each delivery. This increment implements the retrospective input contract. WP08 still needs a prospective consumer, contextual utility, admissible portfolios and fallback. The owner authorized this increment after PR #15. The merged plan lists WP03 among WP08's start dependencies.

## Input and clock

Use the public `pacd-sim evidence-trace RUN_DIR` command on one completed diagnostic. The existing verifier authenticates the run, replays its governed inputs and checks the receipt before releasing the context. Derive every reading from that same snapshot. Join each delivered observation to its configured measurement tick. The v1 sensor has a fixed delay. Its script tick models an acquisition timestamp available with that delivery, with no clock error. Keep the actual delivered signal, including any applied sensing precision. Expose the shared nullable subject and opaque per-episode observation and sensor keys. Assign keys on first appearance in verified delivery order. Source labels, event IDs, script kinds, latent values, hypotheses and actions stay on the evaluator side.

For `evidence_context_v1`, fix a development window of three ticks inclusive. At each delivery, age equals the current delivery clock minus the measurement tick. Age three is fresh and age four is stale. Record the reading, decision clock, age, freshness, source relation and number of distinct eligible sensors for that subject. Eligibility means a fresh reading with an attributable subject. Both low and high signals provide source presence. A missing subject has zero attributable sources. A sensor with several readings supplies one distinct source. Two distinct sensors establish source diversity only. The built-in episodes use one sensor.

A repeated observation with identical contents cannot refresh its support. A conflicting reuse of a key, a new out-of-order delivery or a measurement later than its delivery invalidates the input. A delayed reading cannot displace more recent evidence from its sensor. Reset all state between traces. Include the input count and a digest over the versioned trace content. Equal visible streams share that digest across runs. The enclosing verifier supplies the episode identity. An empty input to the domain function has zero decisions. The current governed diagnostic requires at least one event. An invalid run supplies no trace or denominator.

## Acceptance

1. Check strict field bounds, the inclusive freshness boundary, equal-tick readings, delayed readings, independent subjects, source expiry, duplicates after expiry, conflicting key reuse and reset.
2. Discriminate repeated readings from distinct sources using synthetic unit inputs. Show that the production replay uses the governed measurement clock and delivered signal. Challenge the receipt boundary and retain invalid attempts.
3. Read matched benign/adverse episodes with the same visible signals and compare trace digests. Read switched and disabled sensing episodes, including their differing delivered follow-up. Verify that repeated reads are byte-identical and leave retained stores unchanged.
4. Reconstruct from the frozen environment, run existing compatibility and reportable-denial tests, and hand an exact unmerged commit to a separate review-only session. Record development seed, configuration, invocation and command evidence.

## Traceability and remaining behavior

| Original source | Contribution and open behavior |
|---|---|
| WO-064, TM-011, TM-012 | Measurement time, delivery time, source continuity and freshness advance the evidence schema. Source reliability, provenance across relays, integrity degradation, dropout and contradiction adjudication remain open. |
| FM-016, FM-017 | A single projection defines shared observable fields. Preserve future controls for sensor access, hidden information and fairness across conditions. |
| MD-048 / CAL-005, MD-049 / CAL-006 | Retain both definitions as draft. Distinct-source counts do not measure contradiction. Candidate and dispatch reliance on stale evidence require additional decision bindings and separate denominators. |

Full WP03 also requires broader telemetry, competing beliefs and calibration. WP08/WP09 retain all six variation classes, portfolios and coordination. The [remaining plan](../REMAINING_IMPLEMENTATION_PLAN.md) and [source ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv) carry every residual. The output remains `NON_REPORTABLE_DIAGNOSTIC`. H6 retains its separate human-study requirement.

## Reproduction

Use the frozen environment from a clean checkout in the PACD workspace. Replace `RUN_DIR` with the directory printed by the diagnostic.

```powershell
uv sync --frozen --offline --python 3.13.15
uv run --frozen --no-sync pacd-sim doctor
uv run --frozen --no-sync pacd-sim diagnostic --scenario configs/scenarios/diagnostic_sensing_nominal.yaml --baseline configs/defenders/sensing_adaptive.yaml --seed 424242
uv run --frozen --no-sync pacd-sim evidence-trace RUN_DIR
```

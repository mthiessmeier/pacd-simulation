# WP08 work order · Prospective sensing selection and fallback

**Development question.** Can the simulator use only the evidence already delivered, choose a sensing mode, explain a default choice and send a selected change through independent review and authorization? This slice compares two policies for one reversible sensing action on the same delivery schedule. Owner authority covers synthetic, local CPU diagnostics on the approved WP03 base.

## Conditions and clock

Use `sensing_contextual_v1` and `sensing_scheduled_v1` on the nominal, costly and delayed sensing fixtures. Both have one opportunity, the third delivery in an episode, and the same two possible choices, default precision or referral for alternate precision. Before and after the opportunity the selected profile is null. A default choice at the opportunity consumes it. There is no later retry. A selected alternate profile takes effect only after the guarded action is reviewed, freshly authorized, dispatched and verified. A denied referral can therefore have an alternate recommendation and zero realized switch cost.

Build the ordered `evidence_context_v1` prefix at each delivery. The prefix digest binds the inputs, ages and source relations visible to both policies. The shared fields are the opaque observation and sensor keys, nullable subject, acquisition tick, delivery tick and delivered signal. Treat the event tick as the acquisition tick under the fixed-delay sensor model. Preserve the original delivery order at ties. The simulator's hidden event kind, latent signal and future deliveries stay outside the policy input.

An unknown subject, age above three ticks, an unaffordable switch or an exact duplicate at the opportunity yields the default. On admissible evidence the scheduled policy always requests the switch. The contextual policy looks for an earlier measurement of the same subject still fresh at the current delivery. Choose the latest eligible measurement tick and the minimum delivered signal at that tick. An absent reference yields the default. Multiple readings from the same sensor establish temporal persistence only.

## Development utility

Default has zero incremental utility. Let `age` be the age of the current reading, and let `q` be the smaller of its delivered signal and the reference signal. For the contextual choice at an admissible opportunity with history,

```text
benefit = q × (4 − age) / 4
utility = benefit − switch_cost
```

The weights on benefit and cost are both one. Only strictly positive utility requests alternate precision. Ties select default. The benefit is a development proxy for prioritizing sustained signals while they are fresh. The cost is the configured switching burden. Unscored decisions have null reference/score fields as applicable. The existing governor, queue, denial, failure and rollback paths determine the actual outcome. Reliability, conflict between sources, measured information gain and broader security/mission utility require additional mechanics.

## Acceptance

1. Compare the digest in each prospective decision with the retrospective evidence trace of the same delivered prefix. Check subject isolation, order, ties, reference age, short prefixes, resets, duplicate handling, hostile costs and the inclusive three-tick boundary. Changing a future input cannot alter a preceding choice.
2. On nominal and costly fixtures both policies see `0.9` at the opportunity with age one. The contextual benefit is `0.675`. Costs of `0.25` and `0.95` discriminate selection from fallback. The scheduled comparison requests both. The delayed fixture has age four, and both policies abstain. Replay must distinguish selected, pending, denied, expired, failed, rolled back and verified effects using the existing event chain.
3. Require independent replay of the clock, decision, utility, prefix binding and subsequent state. An authentic local receipt for inconsistent output must withhold episode metrics and traces. Preserve the existing WP03 and WP07 wire outputs.
4. Register exact development comparisons before launch. Record configuration, event, seed, invocation and commit identity. Retain incomplete and invalid attempts with null measurements. Challenge reporting interlocks, run the frozen suite and submit an unmerged candidate to independent review.

## Reproduction

From the clean checkout inside the dedicated workspace:

```powershell
uv sync --frozen --offline --python 3.13.15
uv run --frozen --no-sync pacd-sim doctor
uv run --frozen --no-sync pacd-sim diagnostic --scenario configs/scenarios/diagnostic_sensing_nominal.yaml --baseline configs/defenders/sensing_contextual.yaml --seed 424242
uv run --frozen --no-sync pacd-sim verify RUN_DIR
uv run --frozen --no-sync pacd-sim evidence-trace RUN_DIR
uv run --frozen --no-sync pacd-sim metrics RUN_DIR
```

The retained decision events in `raw/events.jsonl` contain the prospective choice and prefix binding. Use the run directory printed by the diagnostic.

## Residual scope

WO-079, TM-016/034/035/044–046/067 and FM-016/017/037/044 motivate this bounded selection and matched control. TM-017 coordination remains with WP09. The opportunity and utility definition are development assumptions. WP08 retains its six classes, contextual modes, multi-objective terms, diversity, transition and fallback requirements. The remaining plan retains all 47 draft metrics and separate failed-episode safety evidence. H6 requires separate human-study authority. This increment is `NON_REPORTABLE_DIAGNOSTIC`. [Full plan](../REMAINING_IMPLEMENTATION_PLAN.md) · [Source ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

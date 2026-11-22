# Session handoff · CAL-006 sensing freshness

[PR #18](https://github.com/mthiessmeier/pacd-simulation/pull/18) is the public draft for this WP03/WP12 increment. The branch is `codex/wp12-sensing-freshness`. The [work order](../docs/work_orders/SENSING_FRESHNESS_ATTRIBUTION_v1.0.md) records the measurement definition, scope, controls, reproduction commands and acceptance checks. The PR records the exact final candidate and review disposition.

| Record | Verified identity |
|---|---|
| [PR #17](https://github.com/mthiessmeier/pacd-simulation/pull/17) | Owner approved `8111df4de98e976f9d19d619145e913a723b2e13`. The GitHub PR and remote pull ref matched. Two independent review-only sessions passed that head. |
| Merge on main | `61eb93e96369fc78decd03f9b8a2d846633bc314`. Parents in order were `74ac0b9a2a4deb10e77cab31db248eee19a7794a` and the approved PR head. Tree `69f8afe519be2eb516532989fe41a5c0ae85d50a` matched the approved tree. |
| Development branch | Fresh ordinary clone from the merge. Work order `18e1eed57e5902b8f25c8a197354ec34fe5f8c5a`. Implementation `470f95f1828b2c3abc23ba2bd9f3aede59dc5546`. |
| Authority | The owner's exact-head merge instruction authorizes the next public draft. Live AGENTS.md, D-017 and DEC-038 govern non-reportable local work. Public delivery follows the owner's current instruction. Documentation drafts #9 and #11 were open during preflight. |
| Sources | MD-049 / R-MD-049, draft CAL-006, mapped to SC-03/04/17. [Source reconciliation](REMAINING_SCOPE_RECONCILIATION.csv) and [remaining implementation plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). |

The optional metrics view joins the proposed decision to the actual emitted candidate. It then follows the referral, request digest and concrete action to the executed event. Both stages use the original evidence prefix and report their own clocks, counts and known denominators. On the nominal fixture the contextual reference reaches age four at execution, one tick beyond the development freshness window. The scheduled condition's only required input reaches exactly three ticks. A stale executed action in this diagnostic is a measurement. Changes to execution authority would require a separate work order.

Before the candidate handoff, 15 unit tests, eight public-interface scenario tests and 21 existing metrics tests passed. One earlier test assertion expected a semantic rejection to expose the receipt-only identity flag. Its correction verifies the independent receipt and then checks that public measurements are withheld. The original attempt is retained. The [PR](https://github.com/mthiessmeier/pacd-simulation/pull/18) and dedicated workspace evidence index `review/pr18/final-evidence.json` carry the full exact-head test results, independent review, plan, configuration, invocation and command records. Runtime is CPython 3.13.15 with uv 0.12.5. The lock SHA-256 is `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. Development seeds are 424242 and 424243.

Independent review should challenge the original evidence binding across later deliveries, inclusive freshness at age three, the executed versus verified or rolled-back populations, missing support, default output compatibility and the withholding of metrics for invalid or unlaunched attempts. Merge requires a separate owner decision on the reviewed head. Broader CAL-006 attribution, safety evidence for failed episodes, policy portfolios, specialist arbitration and the separate H6 human study remain open in the full plan. Classification `NON_REPORTABLE_DIAGNOSTIC`.

[Previous WP08 handoff](https://github.com/mthiessmeier/pacd-simulation/blob/8111df4de98e976f9d19d619145e913a723b2e13/status/SESSION_HANDOFF.md)

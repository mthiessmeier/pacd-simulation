# WP02 work order · Configured asset and credential dependencies

The original charter calls for synthetic endpoints and service dependencies (EC-022), and for sessions and credentials in the enterprise model (EC-023). WO-076 and architecture layer TM-013 tie those entities to deterministic reset, mission continuity and rollback. The state already represents an asset's availability and an opaque credential's active state. This increment makes those inputs available to governed scenarios under SC-01, SC-02 and SC-15. [Source ledger](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

## Scenario contract

An optional `assets` array holds rows with `id`, `kind` and Boolean `available`. An optional `credentials` array holds rows with `id`, an owning `identity_id` and Boolean `active`. Each array accepts zero to 100 rows. Every field in a supplied row is required. Unknown fields, non-Boolean states and explicit null arrays are invalid. Omitted arrays retain the historical canonical representation. An explicit empty array records the author's choice in the configuration hash and creates an empty population in state.

Use the same immutable entity records, global ID and owner checks, dependency evaluator and verified readers as the rest of the simulator. A positive dependency propagates unavailability from upstream to downstream. Ownership alone has no availability effect. The credential record carries an identifier and simulated status only.

## Matched diagnostics

In all three fixtures session A supports an endpoint asset, which supports service A. An opaque credential owned by identity B and session B separately support service B. Each service backs its own mission. Both missions have the same weight. The fixtures share the two benign events, review schedule, graph, and horizon of eight ticks. The adverse cases each change a single initial Boolean and the scenario name.

| Initial state | Static review, A and B available ticks | Corroborated review, A and B available ticks |
|---|---|---|
| Asset available and credential active | 6, 8 | 8, 8 |
| Asset unavailable | 0, 8 | 0, 8 |
| Credential inactive | 6, 0 | 8, 0 |

Static review isolates session A at tick six. When the asset was initially unavailable, mission A already had an outage at tick zero. The separate initial and transition records must preserve that distinction. The fractions use each mission's full eight-tick observation period.

## Acceptance

1. Check omitted, empty, populated, malformed and over-limit inputs through the canonical loader and both schema modes. Preserve prior scenario hashes. Reject dangling owners and dependencies, cross-type ID collisions and extraneous credential fields.
2. Hand-check the initial, isolated and restored memberships in each fixture. Verify acquisition of the correct initial state on reset and the original state digest after restoration. Exercise an ownership-only reference and a zero-weight edge.
3. Pin each fixture and guard on development seeds 424242 and 424243. Enroll a distinct same-seed replay, an unguarded control and an unlaunched attempt. The verified episode, pinned plan and pinned register must agree. An observed zero remains distinct from the absent measurement on the unlaunched attempt.
4. Run frozen tests, compatibility and quality checks and obtain separate independent review at the exact candidate. Retain commands, config and code hashes, seed, invocation, outcome and review identities. The owner authorized the PR #28 merge and this public development draft under AGENTS.md, DEC-038 and D-017.

The fixtures exercise binary availability and one endpoint kind. Provider-specific behavior, credential lifecycle and privileges, trust paths, graded degradation, estimated mission cost and the separate H6 study retain their existing requirements. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Remaining plan](../REMAINING_IMPLEMENTATION_PLAN.md)

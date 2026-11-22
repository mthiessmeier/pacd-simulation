# WP02 work order · Enterprise population endpoints

The experimental charter sets a development target of 30–100 synthetic identities (EC-020). The original work order asks for configuration-driven populations and bounded tests (WO-076). Architecture layer 3 links that population to reset determinism, session and service references, mission dependencies and verification of state transitions (TM-013). This increment exercises the two endpoints under SC-01, SC-02 and SC-15. [Source reconciliation](../../status/REMAINING_SCOPE_RECONCILIATION.csv)

## Governed inputs

Ship `diagnostic_enterprise_30.yaml` and `diagnostic_enterprise_100.yaml` as explicit configurations through the existing guarded scenario loader. Each identity owns one session. Its session has one corresponding service and a mandatory dependency from that session to that service. The last numbered identity's service supplies `mission-target`. All other services supply `mission-reference`. Both missions start operational and have equal criticality. Stable IDs identify every graph member, including the unobserved population.

The two benign events reference the last identity at tick 1 and the first at tick 4. Reuse the retained-approval review clock and horizon 8. Exercise static review and corroborated review at each size. The source fixes the population range. The graph, event schedule, relative subject positions and weights in these fixtures are development choices.

## Acceptance

1. Load both complete populations through the existing governed configuration path. Check unique IDs, session ownership, service-to-mission membership, dependency direction, and rejection of broken references. Reset the state and check that its canonical identity and memberships reproduce.
2. Verify the exact subject and session in the simulated review. Under static review, isolating the last session at tick 6 interrupts its single-service mission for two ticks. The reference mission stays operational. Under corroborated review, the two distinct subjects leave both missions available through tick 8. Read mission state using the existing verified MIS-001 reader.
3. Run pinned development cells for both sizes, conditions and seeds 424242 and 424243. Enroll a separately identified same-seed replay for each size. Check the deterministic evidence against its original, retaining distinct invocation/attempt IDs. Keep an unguarded control and one unlaunched slot. Direct, pinned plan and pinned register readers must agree on released measurements and retain missing data.
4. Run the frozen suite and quality gates and obtain independent review on the exact branch head. Record canonical hashes, invocation identities and commands. Use the accepted configuration schema, safety policy, broker, verifier and readers throughout.

This work addresses the population-endpoint criterion of R-EC-020 and part of R-WO-076 and R-TM-013. Additional identity roles, privileges, trust paths, richer services, graded degradation and collateral-cost calibration retain their original criteria. These deterministic cases support simulator development. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Full plan](../REMAINING_IMPLEMENTATION_PLAN.md)

# Remaining original PACD implementation work

**Version:** 1.0 · **Status:** Proposed delivery sequence · **Evidence:** NON_REPORTABLE_DIAGNOSTIC

## Purpose and interpretation

Preserve the accepted diagnostic milestone while completing the original agenda. A first loop, one operator or a phase rename cannot replace the full program.

Refresh the November 21 checkpoint against live source. “Partial” and “not established” describe evidence limits, not automatic absence. Reuse accepted behavior; require exact source, tests, commit and review evidence for closure.

Read the [scope crosswalk](repository_snapshot/docs/PHASE2_SCOPE_CONTINUITY.md) and [original sources](repository_snapshot/docs/reference/phase2-original-2026-08-23/README.md): WO (work order), TM (traceability), EC (experimental charter), FM (fairness), MD (metrics). Draft sources remain draft.

The [register](07_WORK_PACKAGE_REGISTER.json) provides implementation areas and criteria; the [reconciliation table](08_SOURCE_UNIT_RECONCILIATION.csv) connects source units to requirements and packages. Its 558 paragraphs, list items and table rows include duplicates and historical material; they are not 558 unique engineering tasks.

## Recommended execution order

Start with WP00 and the concrete [immediate work order](04_IMMEDIATE_WORK_ORDER.md). WP01 is the first proposed technical PR: strengthen development comparison-plan binding and accounting while preserving v1 behavior. WP05 and WP06 then deliver the first guarded review-to-action-to-mission loop using accepted environment and scenario capabilities wherever sufficient. WP07 establishes one integrated operator; WP08 and WP09 retain the full six-class, portfolio and coordination agenda.

Advance environment, adversary, baseline, metric and scenario packages incrementally. Build failure accounting alongside behavior. WP11 completes comparison modes; WP14 expands analysis; WP15 prepares independent protocol review.

Dependency IDs denote capabilities needed to start useful work; accepted equivalents can satisfy them. Separate completion_requires and closure_gate fields prevent early starts from being mistaken for full acceptance. Split packages into reviewable PRs without dropping residual scope. This document grants no new implementation authority: execute already-authorized increments; otherwise complete their concrete work order and identify the outstanding decision.

## WP00 — Reconcile original scope and establish the next work order

**Scope:** SC-01, SC-02, SC-03, SC-04, SC-05, SC-06, SC-07, SC-08, SC-09, SC-10, SC-11, SC-12, SC-13, SC-14, SC-15, SC-16, SC-17, SC-18. **Dependencies:** Live-state verification. **Sources:** WO 2,4,5,11–14; TM 2–10; EC 16; FM 7; MD 12.

**Current evidence.** The six bounded diagnostic increments are accepted. The preserved inventory contains 558 source units; detailed implementation evidence mapping remains pending.

**Remaining work.** Classify every original source unit as requirement, draft methodological definition, standing control, historical instruction, explanation or duplicate linked to a retained requirement. Preserve all IDs and parent-child relationships. Map actual requirements to SC workstreams and delivery packages, current source/tests/reviews, accepted commit, status, remaining behavior, acceptance criteria and dependencies. Produce a complete residual implementation plan, current session handoff and exact first work order; resolve source conflicts through recorded author decisions without reopening accepted work unnecessarily.

**Completion evidence.** No original ID disappears; every actual requirement is mapped to evidence or an open delivery item. Accepted-complete status cites exact implementation and acceptance evidence; not-evidenced status is not silently converted to absent. All original named inventories and separate H6/reportability boundaries remain accounted for.

## WP01 — Bind development comparison plans to attempted runs

**Scope:** SC-01, SC-14, SC-15, SC-17, SC-18. **Dependencies:** WP00. **Sources:** TM 4; FM 3; MD 8–11; WO 6.5,7.

**Current evidence.** The current attempt register binds attempt ID, invocation ID and seed. Verified completions expose configuration identity retrospectively.

**Remaining work.** Define a versioned development comparison plan identifying cells, scenario, defender condition, code revision, governed configuration, development seed/stream identity, comparison mode and canonical digest. Reuse existing bounded loaders, launch ownership, verification and accounting; preserve current v1 behavior and explicit expected-versus-observed identities. Retain every failed, timed-out, incomplete or invalid attempt and separately identify retries; avoid implying trusted preregistration time or a frozen experimental protocol.

**Completion evidence.** Condition/configuration/code/seed substitution cannot silently release measurements for the wrong planned cell. Formatting-only changes preserve canonical identity; substantive changes, collisions and stale bindings are detected. Existing replay and reportability-denial behavior remain intact; exact-head independent review precedes acceptance.

## WP02 — Complete enterprise, mission and simulated-time semantics

**Scope:** SC-01, SC-02, SC-15, SC-16, SC-17. **Dependencies:** WP00. **Sources:** WO 6.1; TM layer 3 and 4–5; EC 4; MD 3.

**Current evidence.** Immutable graphs, directed dependencies and binary availability/continuity are accepted for bounded fixtures; broader temporal and entity semantics require reconciliation.

**Remaining work.** Extend configured identities, accounts, credentials, sessions, privileges, trust paths, endpoints and synthetic SaaS/cloud services to the original 30–100-identity target while keeping tests small. Define mission criticality, dependencies, time-weighted availability, degradation, recovery and defensive collateral effects using explicit synthetic assumptions. Complete deterministic reset, snapshots, propagation and resource-bounded lifecycle semantics; reuse existing capabilities for early integration slices.

**Completion evidence.** State and dependency invariants hold across reset, isolation, restoration and failed recovery. Time-dependent mission outcomes regenerate from retained state transitions and distinguish attack-caused from defense-caused effects. Scale and duration assumptions are documented; no claim of real-world calibration follows from synthetic parameters.

## WP03 — Complete telemetry, evidence and competing beliefs

**Scope:** SC-01, SC-03, SC-04, SC-15, SC-17. **Dependencies:** WP00. **Sources:** TM layers 1,2,4 and 5–6; EC 4,8; MD 6.

**Current evidence.** The accepted planner consumes observation-only tick, subject and signal inputs. Repeated-reading corroboration is a narrow rule within the broader evidence architecture.

**Remaining work.** Add configured identity, endpoint, SaaS, cloud-service, deception and mission observations with coverage, delay, noise, loss, integrity, detector reliability and provenance. Implement bounded normalization, freshness, source reliability, contradiction and chain of custody; preserve evaluator-only ground truth and distinguish repeated or correlated evidence from independent corroboration. Add competing hypotheses, provenance-weighted uncertainty updates and development calibration records, with explicit reset and stale-evidence rules.

**Completion evidence.** Malformed, duplicate, stale and conflicting inputs have defined bounded behavior without hidden ground-truth leakage. Sensor/event streams reproduce while documenting permitted causal divergence between defender conditions. Calibration measures have defined outcomes/timing and adversarial or misleading evidence can worsen decisions visibly.

## WP04 — Implement bounded adaptive adversary and scenario state machines

**Scope:** SC-05, SC-15, SC-16, SC-17. **Dependencies:** WP00. **Sources:** WO 6.2; TM layer 4 and 5–6; EC 5,8; MD 2.

**Current evidence.** The accepted scenarios use scripted synthetic events. Substantive adaptive state-machine behavior has not been established by that acceptance.

**Remaining work.** Model abstract reconnaissance, credential acquisition, session reuse, discovery, escalation, lateral movement, resource access and persistence as synthetic state transitions. Add defensive-change adaptation and stealth, speed, mission-focus and deception-sensitive policies with controlled drift. Define objective states, feasible actions, transition preconditions and timing without operational exploit commands, real credentials or external capabilities.

**Completion evidence.** Impossible transitions are rejected and policy variants affect retained synthetic trajectories. Fixed exogenous streams are separable from endogenous responses to defense; same numeric seeds alone are not treated as pairing proof. Benign and hostile regimes remain retained, including regimes where static defense performs well.

## WP05 — Expand guarded action, authorization, execution and recovery contracts

**Scope:** SC-01, SC-06, SC-10, SC-12, SC-17. **Dependencies:** WP00. **Sources:** WO 5.2,6.1,6.4; TM layers 5,8,10 and 5–6; MD 5.

**Current evidence.** The independent governor, in-memory broker and exact-state verification support narrow isolation and review pathways; broader handler semantics remain open.

**Remaining work.** Define versioned action contracts with target, preconditions, expected effects, cost, authority, reversibility, verification and rollback, retaining all six action classes in the wider catalog. Implement contextual authority envelopes, evidence levels and autonomy tiers 0–5, independent reevaluation and policy/state/action bindings; separate evidence level from confidence. Add one-shot authorization for stateful actions, allowlisted simulated handlers, independent expected-state reconstruction, collateral checks, partial failure, failed rollback and safe degradation.

**Completion evidence.** Stale, replayed, mismatched, prohibited or unauthorized non-reversible actions cannot dispatch. Expected and actual effects, unintended mutations and failed recovery remain separately auditable. The first accepted handler is a bounded slice; unimplemented action classes and contextual governance requirements stay open.

## WP06 — Integrate human oversight and the first guarded decision-to-outcome loop

**Scope:** SC-02, SC-06, SC-10, SC-11, SC-12, SC-17. **Dependencies:** WP00, WP01, WP05. **Sources:** TM layers 3,8–11 and 5–6; EC 4; MD MIS,SAF,GOV,OPS.

**Current evidence.** Prospective policies currently stop at review referral. A standalone approval helper does not establish an integrated queue or completed intervention.

**Remaining work.** Model review arrivals, capacity, delay, approval/denial/modification/override, timeout and expiry, with rationale, uncertainty/impact package and mission-command envelope. Reevaluate authority after relevant state or policy changes; connect one reversible simulated action to actual execution, verification and mission consequences. Demonstrate the complete observation-to-outcome chain on existing accepted fixtures where sufficient; capture pending, denied, expired, failed and successful outcomes and a matched comparator.

**Completion evidence.** Late/missing approval, queue overload, policy drift and state drift cannot silently authorize execution. Delay, legitimate completion, unnecessary intervention and mission effect derive from events rather than referral count alone. This simulation produces no human-trust claim; H6 remains separately deferred.

## WP07 — Integrate the first substantive polymorphic operator

**Scope:** SC-06, SC-07, SC-10, SC-12, SC-17. **Dependencies:** WP00, WP05, WP06. **Sources:** WO 6.4; TM layers 5–6; EC 10; MD 4.

**Current evidence.** Polymorphism helpers exist, but integrated polymorphic state-changing behavior is identified as future work in the reviewed architecture.

**Remaining work.** Select one operator within the canonical six-class taxonomy and specify its state transition, observation needs, cost, duration, detectability and reversibility. Route selection, authorization, execution and verification through canonical interfaces; expose a modeled adversary-knowledge effect with explicit assumptions. Compare a fixed choice and an adaptive choice under matched budget and information, retaining no-op and adverse-cost cases.

**Completion evidence.** The operator changes simulated state with a complete decision/effect trail and meaningful rollback behavior. Removing the operator in an ablation does not alter unrelated evaluation conditions. Acceptance closes only this operator slice; full six-class and coordinated requirements remain assigned to WP08/WP09.

## WP08 — Complete six-class portfolios and contextual multi-objective policy selection

**Scope:** SC-06, SC-07, SC-08, SC-10, SC-17. **Dependencies:** WP00, WP03, WP05, WP07. **Sources:** WO 6.4; TM 3 (layers 5–6),5–6; FM 5; MD 4.

**Current evidence.** An accepted threshold rule or one operator would not establish full candidate portfolios, six-class capability or contextual policy selection.

**Remaining work.** Retain substantive sensing, deception, infrastructure/network, identity/access, response and coordination variation; define portfolio metadata and admissibility. Implement contextual policy modes and fallback with explicit security benefit, information gain, attacker cost, mission effect, burden, reversibility, uncertainty and safety components. Represent diversity, switching cost, detectability and attacker-knowledge reliability/decay without rewarding unnecessary churn or hiding utility weights.

**Completion evidence.** Each class has implemented, traceable behavior and discriminating tests or an explicit author disposition; no class vanishes through scheduling. Component isolation, extreme values, hostile costs and policy transitions have defined behavior. Observed coordinated benefits remain development observations until separate reportable evaluation.

## WP09 — Integrate specialist proposals and multi-agent arbitration

**Scope:** SC-09, SC-08, SC-10, SC-17. **Dependencies:** WP00, WP05, WP08. **Sources:** WO 6.4; TM layer 7 and 6; FM 5; MD OPS-002,POL-007.

**Current evidence.** A proposal coordinator seam exists; its presence does not establish tested integrated multi-agent behavior.

**Remaining work.** Implement typed specialist proposals, conflict detection, precedence and sequencing with explicit role and information boundaries. Retain arbitration rationale, duplicate-action denial, order-independence requirements, deadlock handling and safe fallback. Expose coordinated and matched uncoordinated variants, including proposal-processing burden and contested-action outcomes.

**Completion evidence.** Conflict matrices and ordering challenges discriminate incorrect arbitration. No specialist can modify policies, metrics, evaluation state or another role’s authority. Arbitration and fallback decisions are reproducible and auditable, including negative outcomes.

## WP10 — Implement the complete defender and reference-condition suite

**Scope:** SC-13, SC-14, SC-17. **Dependencies:** WP00, WP01. **Sources:** WO 6.3; EC 6; FM 2,6.

**Current evidence.** The static review comparator and corroborated review planner support a narrow contrast; the full planned suite remains to be reconciled.

**Remaining work.** Retain static defense, deterministic SOAR-style automation, delayed human response, random polymorphism, single-layer adaptive defense, full PACD, oracle reference and internal unbounded simulated diagnostic. Give each condition a substantive versioned definition, authentic information/action access, resource accounting and compatible controlled form. Use matched duplicate suppression and a corroboration ablation when isolating the current planner’s mechanisms; do not substitute those refinements for the original full suite.

**Completion evidence.** Every condition has source-linked behavior and exact configuration/test evidence, rather than a placeholder name. Oracle privileges are explicit; oracle and unbounded conditions remain reference-only with no real tools. Applicable safety-policy variation preserves host isolation, simulation boundaries, audit integrity and reportability controls. Full-suite acceptance also requires the applicable WP05/WP06/WP08/WP09 capabilities and other original behavior dependencies to be complete or explicitly author-dispositioned; WP00/WP01 alone satisfy only the start gate.

## WP11 — Complete authentic and equalized comparison modes

**Scope:** SC-14, SC-15, SC-17, SC-18. **Dependencies:** WP00, WP01, WP10. **Sources:** WO 11; EC 7; FM 1–4,6; MD 1,10–11.

**Current evidence.** Shared observation/governor paths and attempt accounting are useful foundations, but do not establish the complete fairness design.

**Remaining work.** Implement both system-level comparisons of authentic complete systems and controlled comparisons that isolate policy or coordination. Account for all sixteen dimensions: scenario allocation, telemetry, state knowledge, mission knowledge, action catalog, safety rules, oversight, compute, retry/timeout, rollback, randomness, failure handling, metrics, tuning, negative controls and missing data. Declare intrinsic asymmetries, equalize appropriate budgets and semantics, separate exogenous paired streams from endogenous divergence and retain comparable calibration exposure.

**Completion evidence.** A reviewer can identify exactly what differs and reproduce each intended comparison cell. Swapped conditions, asymmetric inputs, hidden resource advantages and mismatched failure rules are detected. System-level differences are not attributed to one algorithmic mechanism without suitable isolation.

## WP12 — Implement the complete metric, data-contract and failure-outcome program

**Scope:** SC-17, SC-18, SC-01. **Dependencies:** WP00. **Sources:** WO 6.5; TM layer 11 and 7; EC 10–11; MD 1–12.

**Current evidence.** Verified disposition metrics, registered completion accounting and raw-to-derived regeneration are accepted. Forty-seven broader metric definitions remain individually tracked.

**Remaining work.** Preserve SEC-001–007, MIS-001–006, POL-001–007, SAF-001–006, GOV-001–005, CAL-001–006, GEN-001–005 and OPS-001–005, implementing each as its required mechanics become available. Complete raw-event, episode and manifest contracts; define numerator, denominator, unit, eligibility, timing/censoring, aggregation, missingness, exclusions, provenance and applicable distribution/tail reporting. Distinguish verified completed-episode measurements from failed/invalid-episode safety evidence. Develop attributable hard-failure accounting without inventing missing measurements or treating null as zero.

**Completion evidence.** Every implemented value regenerates from the appropriate retained evidence using a single condition-independent definition. Prohibited/catastrophic events and rollback failures remain visible by identity, including explicitly unresolved observations in invalid attempts. Metric IDs stay draft where assumptions remain unresolved; no metric becomes primary or frozen merely through implementation.

## WP13 — Complete scenario, control-plane and adverse-regime coverage

**Scope:** SC-16, SC-04, SC-05, SC-10, SC-12, SC-17. **Dependencies:** WP00. **Sources:** WO 6.2,6.5,11; TM 7; EC 8,11; MD 5–7.

**Current evidence.** Identity, maintenance and repeated-reading fixtures are accepted; they do not cover all planned scenario and failure families.

**Remaining work.** Retain all sixteen EC section 8 families: credential/session abuse, lateral movement, privilege misuse, SaaS/token persistence, deception sensing, mission disruption, degraded telemetry, inaccurate mission models, unreliable rollback, policy failure, evidence manipulation, strong static controls, low attacker adaptability, rapid humans, costly polymorphism and poor calibration. Individually test benign administration, prohibited candidates, non-reversible automatic actions, corrupted mission data, policy failure, failed rollback, telemetry outage, stale/duplicate authorization, unseen topology and denied external-action attempts. Add adverse/no-benefit cases as supported mechanics arrive; preserve failed, negative and inconclusive outcomes without tuning scenarios for PACD success.

**Completion evidence.** Each named family has a defined synthetic setup, expected invariant or measurement and linked retained outcome. Control-plane corruption cannot silently change evaluator truth or authorize prohibited actions. Unimplemented dependencies are explicit; missing evidence cannot be converted to a favorable score.

## WP14 — Complete calibration, ten ablations, sensitivity and analysis tooling

**Scope:** SC-18, SC-04, SC-07, SC-08, SC-09, SC-14, SC-17. **Dependencies:** WP00, WP11, WP12. **Sources:** WO 6.5,7,11; EC 9,12–13; FM 5–6; MD 6–7.

**Current evidence.** Development seeds and deterministic replay exist. Broader calibration, ablation and sensitivity tooling requires requirement-level reconciliation.

**Remaining work.** Retain ablations without mission model, uncertainty, reversibility, orchestration, policy portfolio or oversight delay; one polymorphism class; degraded governor; inaccurate dependencies; unreliable rollback. Record every tuned parameter, rationale and exposure; separate unit/property/development/calibration/holdout-development roles and treat inspected holdouts as exposed. Implement sensitivity grids, unseen topology/drift/degradation analyses and draft statistical/exclusion/multiplicity choices with a justified sampling unit, keeping reportable choices unfrozen.

**Completion evidence.** Each ablation changes its named mechanism and documents unavoidable coupled changes. Analysis retains adverse/tail outcomes and can be regenerated without hand-edited result tables. Repeated deterministic cases are not treated as independent sample size, and favorable development outcomes cannot select future reportable seeds.

## WP15 — Complete independent reconstruction and protocol-readiness review

**Scope:** SC-18, SC-14, SC-17, SC-10. **Dependencies:** WP00, WP11, WP12, WP13, WP14. **Sources:** WO 4,8–13; TM 7–10; EC 14–16; FM 6; MD 10–12.

**Current evidence.** The bounded diagnostic milestone has recorded independent review. Acceptance of the expanded original program remains a separate evidence requirement.

**Remaining work.** Reconstruct accepted increments from exact commits with complete source/config/seed/runtime/lock identities, retained failures, limitations and one-command table/figure regeneration. Audit closure of all actual original requirements and the WO section 11 criteria, including substantive components, fair modes, adverse cases, sensitivity/ablations and draft-protocol readiness. Prepare a concrete independent freeze-review packet covering baselines, metrics, distributions, seed/exclusion controls and analysis assumptions; retain reportable interlock denial.

**Completion evidence.** Every closure cites exact implementation, tests and independent acceptance; remaining items have explicit owner dispositions. Program closure requires every WP01–WP14 and every original substantive requirement to be accepted complete or explicitly author-dispositioned; no package may be skipped by following start dependencies alone. An independent session can reproduce the expanded development package and challenge assumptions and boundaries. Protocol readiness does not create approval, reportable seeds or empirical conclusions; H6 remains outside simulation-only acceptance.

## Scope preservation and completion discipline

The following inventories must survive every plan revision: 18 workstreams; all 558 original source-unit IDs; eight defender/reference conditions; sixteen fairness dimensions; ten draft ablations; all 47 metric IDs; and the six polymorphism classes with their coordinated use. Requirements may be split or linked as duplicates without losing their source identities. Removal, narrowing or new deferral requires an explicit author disposition identifying affected IDs.

Each PR records affected IDs, changed behavior, exact source/configuration/test evidence, independent review, limitations and open items. Helpers and narrow fixtures cannot close broader behavior requirements; favorable development aggregates cannot establish PACD effectiveness.

Retain every failed, timed-out, incomplete and invalid attempt. Missing measurements stay unavailable rather than becoming zeros. Preserve separately attributable prohibited, catastrophic and rollback outcomes even when ordinary completed-episode metrics cannot be released; document evidentiary uncertainty instead of inventing measurements. Claims about lower operational burden require modeled work and delays, not merely fewer referrals.

All simulated adversary activity, actions and controls remain synthetic, local and CPU-only. Keep the harness outside the system under test, preserve observation/ground-truth boundaries, and retain independent governance, simulation-only execution, evidence integrity and reportability controls. Oracle and unbounded conditions remain internal references. H1–H5 remain unclassified during development; H6 requires a separate human-participant protocol and is not included in simulation-only completion.

The original completion criteria remain the scope reference, subject to explicit author decisions and accepted equivalents. Preserve the accepted milestone and allocate all residual work. A new phase changes delivery order without silently shrinking the agenda.

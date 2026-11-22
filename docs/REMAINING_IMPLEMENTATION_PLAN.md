# Remaining Phase 2 implementation plan

This plan retains the full original requirements through WP15 and records the merged implementation checkpoint at **PR #22**, commit [`31c1645ee28a7bbd2488dfb2d354be1fdea3fd25`](https://github.com/mthiessmeier/pacd-simulation/tree/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25). WP01 development-plan binding, the first guarded decision-to-outcome loop, one sensing operator, evidence-aware selection, four optional metric extensions and the operator review brief have merged. They are bounded slices, not closure of the broader original scope. [Current progress and evidence](../status/CURRENT_PROGRESS.md) distinguish these slices from residual work. The row-level source and original acceptance criteria in [the reconciliation](../status/REMAINING_SCOPE_RECONCILIATION.csv) control coverage. Filter work_package_ids, then read original_text, current evidence and remaining_behavior alongside the unchanged acceptance_criteria.

## Sources and disposition

The original five exports and the SC-01–SC-18 crosswalk are pinned at [scope preservation c4e2005](https://github.com/mthiessmeier/pacd-simulation/tree/c4e200595377cf64c6129dec61712d04412d1ec2/docs). Resolve the CSV source_file and export line against that tree. Resolve package_source_file against the [handoff directory at 2191b41](https://github.com/mthiessmeier/pacd-simulation/tree/2191b41304aa3c079641d76caf92d7d209d72476/docs/handoff/PACD_Codex_Handoff_v1.0). Implementation/test paths refer to the accepted code unless identified as proposed. The immutable input inventory and completed assessment have distinct roles. Source aliases are WO (work order), TM (traceability), EC (charter), FM (fairness) and MD (metric dictionary).

- **Decision precedence.** Use live AGENTS.md, Michael's latest continuation and DEC-038 for local non-reportable Phase 2 work. Earlier handoff and sequencing proposals remain historical context. Current owner instructions authorize the documentation refresh; they do not freeze a reportable protocol or silently remove an original requirement.
- **Scope conflict.** WO §§5–6 retain broader original criteria. The [owner decision for Increment 1](../status/PHASE2_INCREMENT1.md) accepts five governed inputs and specified equivalents for that increment. Later config families remain within scope. The historical bootstrap tag, six-branch sequence and historical status columns cannot establish current implementation status.
- **Evidence.** The [PR #8 acceptance](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861) remains the six-increment historical baseline. PR #12 and PR #14–#22 add the bounded slices recorded in [current progress](../status/CURRENT_PROGRESS.md), including exact merge/candidate identities and reported verification. Private raw review packets are not republished by this documentation update. Refreshed ledger rows cite current code/test evidence; PR8_BASELINE_RETAINED rows retain explicitly historical assessments. A helper or accepted slice can remain partial against broader original criteria.
- **Closure.** A change removing, deferring or narrowing scope needs an explicit author disposition listing affected source and requirement IDs, rationale and residual consequences. H6 requires a separate human-participant study. Development work may preserve interface data and simulated latency. H1–H5, RQ4, publication decisions, reportable seed selection and protocol approval keep their source gates.
- **Safety and custody.** The evaluator controls scenario allocation, seeds and metric measurement. The harness schedules and records episodes. The independent governor decides action authorization, and the in-memory broker enforces it. Keep all future scenario and adversary behavior abstract and local to synthetic state. Keep every failure visible and segregate unknown outcome measurements from true zeros. Never average away prohibited executions or catastrophic outcomes.

## Coverage and evidence limits

There are 558 original source units across WO (160), TM (81), EC (140), FM (59) and MD (118). Multiple units can point to one requirement. The ledger retains source order, parents, original metric IDs and exact text. An accepted-complete row applies only to the criterion in that row. Standing controls still apply on every increment.

| Inventory | Where to inspect it | Closure owner |
|---|---|---|
| Six classes and coordinated use | WO §6.4, TM §3 layers 5–7, SC-06–SC-09 | WP05–WP09 |
| Eight defender/reference conditions and two modes | FM-005–013 and EC-041–053 | WP10–WP11 |
| Sixteen fairness dimensions and ten draft ablations | FM-014–030 and FM-038–049 | WP11 and WP14 |
| Sixteen scenario families and ten control/failure cases | EC-054–071 and EC-091–102 | WP04 and WP13, with WP12 for safety evidence |
| Forty-seven draft metric IDs | Filter original_metric_id in MD; SEC 7, MIS 6, POL 7, SAF 6, GOV 5, CAL 6, GEN 5, OPS 5 | WP12 with WP14 |
| Human-participant boundary | EC-016–017, TM-062 and TM-073 | Separate human-study authority; WP06 only develops simulation interfaces |

MD-076 requests a raw field named `configuration_hash`. The accepted writer and verifier bind the same digest under `config_hash`. WP12 must resolve the wire contract while keeping v1 replay compatible. There is no recorded MD §8 equivalence. For failed or invalid episodes, the retained terminal status establishes the attempt disposition. Any independently attributable safety or tail observation still needs its own verified evidence and denominator.

Run `python docs/work_orders/check_reconciliation.py <handoff-directory>` in this checkout to verify the ledger against the pinned template, source lines and cited Git trees. The validator checks IDs, mappings, states and paths. Evidence interpretation requires reading the source and tests.

## Review sequence

WP01 merged in PR #12. PR #14 implemented the first guarded isolation/review/verification/recovery loop; PR #15 integrated sensing. PR #16–#22 added verified evidence context, prospective selection, CAL-006, MIS-002, GOV-002, the bound operator brief and OPS-003 request-time accounting. Do not restart these as wholly future increments. Their action-specific acceptance does not close the full mapped packages.

At this checkpoint, modification/override and its downstream accounting remain a concrete WP06 increment; any open PR #23 proposal requires separate review and acceptance. Preserve the exact reversible action, target, policy, evidence, pre-state and validity interval through every extension. Reevaluate authority and current state before dispatch, independently verify the complete post-state and collateral effects, and retain pending, denied, expired, unauthorized, execution-failed, verification-failed and rollback outcomes. Review each slice before advancing. Broader authority, evidence, class, adversary and metric increments may proceed when their bounded start dependencies are available.

WP07 already has one substantive sensing operator; WP08 has a bounded prospective sensing choice. WP08 and WP09 still carry the full six classes, multi-objective portfolios and coordinated use through their original closure tests. A start dependency can be satisfied by a bounded accepted equivalent. Full-package closure also requires every mapped residual and any stronger completion gate below. Every runtime increment needs an unmerged candidate, exact source/config/seed identity, failure ledger, meaningful tests and a fresh review-only session.


## WP00 · Reconcile the source and select the next increment

The PR #12 baseline reconciliation covered all 558 units, workstream/package allocations and preserved source references. The current refresh retains that exact assessment in [history](../status/history/REMAINING_SCOPE_RECONCILIATION_PR8.csv) and updates current evidence/residuals through PR #22. Continue checking every cited path and source identity; independent review should sample evidence semantics as well as assess ID coverage. Keep this plan, the ledger, [WP01 work order](work_orders/DEVELOPMENT_COMPARISON_PLAN_v1.0.md) and [session handoff](../status/SESSION_HANDOFF.md) aligned without rewriting original source or acceptance criteria.

## WP01 · Bind development comparison plans to attempted runs

Start dependencies: WP00. Workstreams: SC-01, SC-14, SC-15, SC-17, SC-18. Sources: TM 4, FM 3, MD 8–11, WO 6.5,7.

[PR #12](https://github.com/mthiessmeier/pacd-simulation/pull/12) merged the bounded development-plan contract: cells bind intended mode, expected scenario/condition, code/configuration, seed registry, exogenous script and invocation before launch. Expected/observed checks gate measurement release and retain all planned attempts and retries. V1 registers remain available. This content binding is not trusted preregistration or evidence that either fairness mode is complete. The original contract and acceptance requirements below remain controls for subsequent extensions.

- Define a versioned development comparison plan identifying cells, scenario, defender condition, code revision, governed configuration, development seed/stream identity, comparison mode and canonical digest.
- Reuse existing bounded loaders, launch ownership, verification and accounting; preserve current v1 behavior and explicit expected-versus-observed identities.
- Retain every failed, timed-out, incomplete or invalid attempt and separately identify retries; avoid implying trusted preregistration time or a frozen experimental protocol.

**Acceptance**

- Condition/configuration/code/seed substitution cannot silently release measurements for the wrong planned cell.
- Formatting-only changes preserve canonical identity; substantive changes, collisions and stale bindings are detected.
- Existing replay and reportability-denial behavior remain intact; exact-head independent review precedes acceptance.

## WP02 · Complete enterprise, mission and simulated-time semantics

Start dependencies: WP00. Workstreams: SC-01, SC-02, SC-15, SC-16, SC-17. Sources: WO 6.1, TM layer 3 and 4–5, EC 4, MD 3.

Immutable graphs, directed dependencies and binary availability/continuity support bounded fixtures. PR #19 merged the [MIS-002 work order](work_orders/MISSION_LOSS_INTEGRAL_v1.0.md): weighted binary mission loss over verified simulated time with matched criticality variations. Broader entity/scale and temporal semantics, graded degradation, causal attribution and calibrated/frozen harm weights remain open.

- Extend configured identities, accounts, credentials, sessions, privileges, trust paths, endpoints and synthetic SaaS/cloud services to the original 30–100-identity target while keeping tests small.
- Define mission criticality, dependencies, time-weighted availability, degradation, recovery and defensive collateral effects using explicit synthetic assumptions.
- Complete deterministic reset, snapshots, propagation and resource-bounded lifecycle semantics; reuse existing capabilities for early integration slices.

**Acceptance**

- State and dependency invariants hold across reset, isolation, restoration and failed recovery.
- Time-dependent mission outcomes regenerate from retained state transitions and distinguish attack-caused from defense-caused effects.
- Scale and duration assumptions are documented; no claim of real-world calibration follows from synthetic parameters.

## WP03 · Complete telemetry, evidence and competing beliefs

Start dependencies: WP00. Workstreams: SC-01, SC-03, SC-04, SC-15, SC-17. Sources: TM layers 1,2,4 and 5–6, EC 4,8, MD 6.

PR #16 added verified evidence age and source context; PR #17 consumes the delivered prefix prospectively for one sensing decision. Built-in episodes still use one sensor. Repeated-reading temporal persistence is a narrow rule within the broader evidence architecture; it does not establish independent corroboration or calibrated beliefs.

- Add configured identity, endpoint, SaaS, cloud-service, deception and mission observations with coverage, delay, noise, loss, integrity, detector reliability and provenance.
- Implement bounded normalization, freshness, source reliability, contradiction and chain of custody; preserve evaluator-only ground truth and distinguish repeated or correlated evidence from independent corroboration.
- Add competing hypotheses, provenance-weighted uncertainty updates and development calibration records, with explicit reset and stale-evidence rules.

**Acceptance**

- Malformed, duplicate, stale and conflicting inputs have defined bounded behavior without hidden ground-truth leakage.
- Sensor/event streams reproduce while documenting permitted causal divergence between defender conditions.
- Calibration measures have defined outcomes/timing and adversarial or misleading evidence can worsen decisions visibly.

The merged [verified evidence context work order](work_orders/VERIFIED_EVIDENCE_CONTEXT_v1.0.md) supplies the same measurement-age/source-prefix contract used by the [prospective sensing selector](work_orders/PROSPECTIVE_SENSING_SELECTION_v1.0.md). PR #18 adds original-support attribution at referral and execution. Broader prospective policies, source reliability, contradiction, competing beliefs and calibration remain open.

## WP04 · Implement bounded adaptive adversary and scenario state machines

Start dependencies: WP00. Workstreams: SC-05, SC-15, SC-16, SC-17. Sources: WO 6.2, TM layer 4 and 5–6, EC 5,8, MD 2.

The accepted scenarios use scripted synthetic events. Substantive adaptive state-machine behavior has not been established by that acceptance.

- Model abstract reconnaissance, credential acquisition, session reuse, discovery, escalation, lateral movement, resource access and persistence as synthetic state transitions.
- Add defensive-change adaptation and stealth, speed, mission-focus and deception-sensitive policies with controlled drift.
- Define objective states, feasible actions, transition preconditions and timing without operational exploit commands, real credentials or external capabilities.

**Acceptance**

- Impossible transitions are rejected and policy variants affect retained synthetic trajectories.
- Fixed exogenous streams are separable from endogenous responses to defense; same numeric seeds alone are not treated as pairing proof.
- Benign and hostile regimes remain retained, including regimes where static defense performs well.

## WP05 · Expand guarded action, authorization, execution and recovery contracts

Start dependencies: WP00. Workstreams: SC-01, SC-06, SC-10, SC-12, SC-17. Sources: WO 5.2,6.1,6.4, TM layers 5,8,10 and 5–6, MD 5.

The independent governor, in-memory broker and independently reconstructed exact-state verification support two reviewed handlers: isolate_session and switch_sensing_profile. Bound review, fresh dispatch authorization and recovery are integrated. Broader handler, evidence-level, contextual authority and autonomy-tier semantics remain open.

- Define versioned action contracts with target, preconditions, expected effects, cost, authority, reversibility, verification and rollback, retaining all six action classes in the wider catalog.
- Implement contextual authority envelopes, evidence levels and autonomy tiers 0–5, independent reevaluation and policy/state/action bindings; separate evidence level from confidence.
- Add one-shot authorization for stateful actions, allowlisted simulated handlers, independent expected-state reconstruction, collateral checks, partial failure, failed rollback and safe degradation.

**Acceptance**

- Stale, replayed, mismatched, prohibited or unauthorized non-reversible actions cannot dispatch.
- Expected and actual effects, unintended mutations and failed recovery remain separately auditable.
- The first accepted handler is a bounded slice; unimplemented action classes and contextual governance requirements stay open.

## WP06 · Integrate human oversight and the first guarded decision-to-outcome loop

Start dependencies: WP00, WP01, WP05. Workstreams: SC-02, SC-06, SC-10, SC-11, SC-12, SC-17. Sources: TM layers 3,8–11 and 5–6, EC 4, MD MIS,SAF,GOV,OPS.

The merged guarded queue binds review to a concrete simulated action and rechecks dispatch authority. PR #20 added [GOV-002 routing](work_orders/ESCALATION_ROUTING_v1.0.md), PR #21 the [operator review brief](work_orders/OPERATOR_REVIEW_BRIEF_v1.0.md), and PR #22 [OPS-003 approval burden](work_orders/APPROVAL_BURDEN_v1.0.md). The brief carries a rationale and conditional immediate binary mission preview; compromise probability is null. OPS-003 measures resolved and horizon-censored queue time, with override count null/unsupported. Modifications, overrides, broader mission-command envelopes and richer uncertainty remain open; queue time is not staff effort or H6 evidence.

- Model review arrivals, capacity, delay, approval/denial/modification/override, timeout and expiry, with rationale, uncertainty/impact package and mission-command envelope.
- Reevaluate authority after relevant state or policy changes; connect one reversible simulated action to actual execution, verification and mission consequences.
- Demonstrate the complete observation-to-outcome chain on existing accepted fixtures where sufficient; capture pending, denied, expired, failed and successful outcomes and a matched comparator.

**Acceptance**

- Late/missing approval, queue overload, policy drift and state drift cannot silently authorize execution.
- Delay, legitimate completion, unnecessary intervention and mission effect derive from events rather than referral count alone.
- This simulation produces no human-trust claim; H6 remains separately deferred.

## WP07 · Integrate the first substantive polymorphic operator

Start dependencies: WP00, WP05, WP06. Workstreams: SC-06, SC-07, SC-10, SC-12, SC-17. Sources: WO 6.4, TM layers 5–6, EC 10, MD 4.

[PR #15](https://github.com/mthiessmeier/pacd-simulation/pull/15) merged the first substantive operator: a reversible sensing-profile change affects subsequent delivered precision, passes through the guarded execution path and retains verified cost/duration plus an assumption-bound observer-knowledge proxy. Fixed/adaptive/disabled comparisons include adverse-cost and no-op cases. PR #17 adds a bounded evidence-aware contextual choice. The original requirements below remain the contract for this slice and later operators; broader classes, multi-objective selection, adaptive attacker knowledge and coordination remain open.

- Select one operator within the canonical six-class taxonomy and specify its state transition, observation needs, cost, duration, detectability and reversibility.
- Route selection, authorization, execution and verification through canonical interfaces; expose a modeled adversary-knowledge effect with explicit assumptions.
- Compare a fixed choice and an adaptive choice under matched budget and information, retaining no-op and adverse-cost cases.

**Acceptance**

- The operator changes simulated state with a complete decision/effect trail and meaningful rollback behavior.
- Removing the operator in an ablation does not alter unrelated evaluation conditions.
- Acceptance closes only this operator slice; full six-class and coordinated requirements remain assigned to WP08/WP09.

## WP08 · Complete six-class portfolios and contextual multi-objective policy selection

Start dependencies: WP00, WP03, WP05, WP07. Workstreams: SC-06, SC-07, SC-08, SC-10, SC-17. Sources: WO 6.4, TM 3 (layers 5–6),5–6, FM 5, MD 4.

PR #17 merged one prospective contextual-versus-scheduled sensing choice with exact benefit/cost arithmetic and fallback. One sensing operator and that bounded context rule do not establish full candidate portfolios, six-class capability or the original multi-objective policy model.

- Retain substantive sensing, deception, infrastructure/network, identity/access, response and coordination variation; define portfolio metadata and admissibility.
- Implement contextual policy modes and fallback with explicit security benefit, information gain, attacker cost, mission effect, burden, reversibility, uncertainty and safety components.
- Represent diversity, switching cost, detectability and attacker-knowledge reliability/decay without rewarding unnecessary churn or hiding utility weights.

**Acceptance**

- Each class has implemented, traceable behavior and discriminating tests or an explicit author disposition; no class vanishes through scheduling.
- Component isolation, extreme values, hostile costs and policy transitions have defined behavior.
- Observed coordinated benefits remain development observations until separate reportable evaluation.

The [prospective sensing selection work order](work_orders/PROSPECTIVE_SENSING_SELECTION_v1.0.md) binds the WP03 evidence prefix to one governed sensing choice and a default fallback. The six-class portfolio, broader utility components and coordination remain open.

## WP09 · Integrate specialist proposals and multi-agent arbitration

Start dependencies: WP00, WP05, WP08. Workstreams: SC-09, SC-08, SC-10, SC-17. Sources: WO 6.4, TM layer 7 and 6, FM 5, MD OPS-002,POL-007.

A proposal coordinator seam exists; its presence does not establish tested integrated multi-agent behavior.

- Implement typed specialist proposals, conflict detection, precedence and sequencing with explicit role and information boundaries.
- Retain arbitration rationale, duplicate-action denial, order-independence requirements, deadlock handling and safe fallback.
- Expose coordinated and matched uncoordinated variants, including proposal-processing burden and contested-action outcomes.

**Acceptance**

- Conflict matrices and ordering challenges discriminate incorrect arbitration.
- No specialist can modify policies, metrics, evaluation state or another role’s authority.
- Arbitration and fallback decisions are reproducible and auditable, including negative outcomes.

## WP10 · Implement the complete defender and reference-condition suite

Start dependencies: WP00, WP01. Workstreams: SC-13, SC-14, SC-17. Sources: WO 6.3, EC 6, FM 2,6.

Static and corroborated review now have guarded consequences; fixed/adaptive/disabled and contextual/scheduled sensing supply additional bounded comparisons. These implementations do not complete or replace the eight original defender/reference conditions and their authentic/controlled forms.

- Retain static defense, deterministic SOAR-style automation, delayed human response, random polymorphism, single-layer adaptive defense, full PACD, oracle reference and internal unbounded simulated diagnostic.
- Give each condition a substantive versioned definition, authentic information/action access, resource accounting and compatible controlled form.
- Use matched duplicate suppression and a corroboration ablation when isolating the current planner’s mechanisms; do not substitute those refinements for the original full suite.

**Acceptance**

- Every condition has source-linked behavior and exact configuration/test evidence, rather than a placeholder name.
- Oracle privileges are explicit; oracle and unbounded conditions remain reference-only with no real tools.
- Applicable safety-policy variation preserves host isolation, simulation boundaries, audit integrity and reportability controls.

**Full closure** (WP05, WP06, WP08, WP09). Full-suite acceptance requires complete applicable action, oversight, six-class polymorphism, policy-portfolio, multi-agent arbitration and full-PACD behavior, or an explicit author disposition for each residual requirement. Applicable enterprise, telemetry, adversary, metric and scenario dependencies must also be evidenced; the start dependency list alone cannot establish full-suite completion.

## WP11 · Complete authentic and equalized comparison modes

Start dependencies: WP00, WP01, WP10. Workstreams: SC-14, SC-15, SC-17, SC-18. Sources: WO 11, EC 7, FM 1–4,6, MD 1,10–11.

PR #12 binds intended comparison mode and expected inputs to planned attempts; later review/sensing conditions share defined observation, action and budget interfaces. These mechanics do not establish the complete fairness design or replace independent assessment of all sixteen dimensions.

- Implement both system-level comparisons of authentic complete systems and controlled comparisons that isolate policy or coordination.
- Account for all sixteen dimensions: scenario allocation, telemetry, state knowledge, mission knowledge, action catalog, safety rules, oversight, compute, retry/timeout, rollback, randomness, failure handling, metrics, tuning, negative controls and missing data.
- Declare intrinsic asymmetries, equalize appropriate budgets and semantics, separate exogenous paired streams from endogenous divergence and retain comparable calibration exposure.

**Acceptance**

- A reviewer can identify exactly what differs and reproduce each intended comparison cell.
- Swapped conditions, asymmetric inputs, hidden resource advantages and mismatched failure rules are detected.
- System-level differences are not attributed to one algorithmic mechanism without suitable isolation.

## WP12 · Implement the complete metric, data-contract and failure-outcome program

Start dependencies: WP00. Workstreams: SC-17, SC-18, SC-01. Sources: WO 6.5, TM layer 11 and 7, EC 10–11, MD 1–12.

Verified disposition metrics, planned/registered completion accounting and raw-to-derived regeneration are implemented. PR #18–#22 add four optional extensions: [CAL-006 freshness](work_orders/SENSING_FRESHNESS_ATTRIBUTION_v1.0.md), [MIS-002 mission loss](work_orders/MISSION_LOSS_INTEGRAL_v1.0.md), [GOV-002 routing](work_orders/ESCALATION_ROUTING_v1.0.md) and [OPS-003 approval burden](work_orders/APPROVAL_BURDEN_v1.0.md). Their individual-run, pinned-plan and pinned-register paths share verified evidence and retain null for unavailable values. All 47 metric IDs remain draft methodology. Broader definitions, common raw/summary schema requirements, calibrated thresholds and independently attributable failed-episode safety remain open.

- Preserve SEC-001–007, MIS-001–006, POL-001–007, SAF-001–006, GOV-001–005, CAL-001–006, GEN-001–005 and OPS-001–005, implementing each as its required mechanics become available.
- Complete raw-event, episode and manifest contracts; define numerator, denominator, unit, eligibility, timing/censoring, aggregation, missingness, exclusions, provenance and applicable distribution/tail reporting.
- Distinguish verified completed-episode measurements from failed/invalid-episode safety evidence. Develop attributable hard-failure accounting without inventing missing measurements or treating null as zero.

**Acceptance**

- Every implemented value regenerates from the appropriate retained evidence using a single condition-independent definition.
- Prohibited/catastrophic events and rollback failures remain visible by identity, including explicitly unresolved observations in invalid attempts.
- Metric IDs stay draft where assumptions remain unresolved; no metric becomes primary or frozen merely through implementation.

## WP13 · Complete scenario, control-plane and adverse-regime coverage

Start dependencies: WP00. Workstreams: SC-16, SC-04, SC-05, SC-10, SC-12, SC-17. Sources: WO 6.2,6.5,11, TM 7, EC 8,11, MD 5–7.

Identity, maintenance and repeated-reading fixtures are joined by bounded guarded isolation/recovery, sensing cost/delay, mission-criticality, review-contention, bound-brief and pending-burden diagnostics. They do not cover all sixteen planned scenario families or the ten control/failure cases.

- Retain all sixteen EC section 8 families: credential/session abuse, lateral movement, privilege misuse, SaaS/token persistence, deception sensing, mission disruption, degraded telemetry, inaccurate mission models, unreliable rollback, policy failure, evidence manipulation, strong static controls, low attacker adaptability, rapid humans, costly polymorphism and poor calibration.
- Individually test benign administration, prohibited candidates, non-reversible automatic actions, corrupted mission data, policy failure, failed rollback, telemetry outage, stale/duplicate authorization, unseen topology and denied external-action attempts.
- Add adverse/no-benefit cases as supported mechanics arrive; preserve failed, negative and inconclusive outcomes without tuning scenarios for PACD success.

**Acceptance**

- Each named family has a defined synthetic setup, expected invariant or measurement and linked retained outcome.
- Control-plane corruption cannot silently change evaluator truth or authorize prohibited actions.
- Unimplemented dependencies are explicit; missing evidence cannot be converted to a favorable score.

## WP14 · Complete calibration, ten ablations, sensitivity and analysis tooling

Start dependencies: WP00, WP11, WP12. Workstreams: SC-18, SC-04, SC-07, SC-08, SC-09, SC-14, SC-17. Sources: WO 6.5,7,11, EC 9,12–13, FM 5–6, MD 6–7.

Development seeds, deterministic replay, bounded sensing no-op/adverse-cost comparisons and mission-criticality variations exist. These diagnostics do not complete the original ten ablations, calibrated exposure program, sensitivity/generalization tooling or a frozen statistical analysis.

- Retain ablations without mission model, uncertainty, reversibility, orchestration, policy portfolio or oversight delay; one polymorphism class; degraded governor; inaccurate dependencies; unreliable rollback.
- Record every tuned parameter, rationale and exposure; separate unit/property/development/calibration/holdout-development roles and treat inspected holdouts as exposed.
- Implement sensitivity grids, unseen topology/drift/degradation analyses and draft statistical/exclusion/multiplicity choices with a justified sampling unit, keeping reportable choices unfrozen.

**Acceptance**

- Each ablation changes its named mechanism and documents unavoidable coupled changes.
- Analysis retains adverse/tail outcomes and can be regenerated without hand-edited result tables.
- Repeated deterministic cases are not treated as independent sample size, and favorable development outcomes cannot select future reportable seeds.

## WP15 · Complete independent reconstruction and protocol-readiness review

Start dependencies: WP00, WP11, WP12, WP13, WP14. Workstreams: SC-18, SC-14, SC-17, SC-10. Sources: WO 4,8–13, TM 7–10, EC 14–16, FM 6, MD 10–12.

Public PR records report scoped independent review for the merged diagnostic slices through PR #22; current progress distinguishes reported verification from newly reproduced evidence. Acceptance and independent reconstruction of the entire expanded original program remain separate requirements.

- Reconstruct accepted increments from exact commits with complete source/config/seed/runtime/lock identities, retained failures, limitations and one-command table/figure regeneration.
- Audit closure of all actual original requirements and the WO section 11 criteria, including substantive components, fair modes, adverse cases, sensitivity/ablations and draft-protocol readiness.
- Prepare a concrete independent freeze-review packet covering baselines, metrics, distributions, seed/exclusion controls and analysis assumptions; retain reportable interlock denial.

**Acceptance**

- Every closure cites exact implementation, tests and independent acceptance; remaining items have explicit owner dispositions.
- An independent session can reproduce the expanded development package and challenge assumptions and boundaries.
- Protocol readiness does not create approval, reportable seeds or empirical conclusions; H6 remains outside simulation-only acceptance.

**Full closure** (WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP11, WP12, WP13, WP14). Program closure requires every WP01–WP14 and every original substantive requirement to be accepted complete or explicitly author-dispositioned with affected source IDs and residual scope recorded. Reportable execution and H6 retain their separate gates; no package may disappear through dependency scheduling.

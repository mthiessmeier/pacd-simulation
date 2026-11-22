# Remaining Phase 2 implementation plan

The accepted engineering milestone covers six bounded increments. This plan schedules the remaining original requirements through WP15. The row-level source and acceptance criteria in [the reconciliation](../status/REMAINING_SCOPE_RECONCILIATION.csv) control coverage. Filter its work_package_ids column to obtain each package's scope, then read original_text and acceptance_criteria together. The table reports the accepted baseline. WP01 is a candidate until its separate review concludes.

## Sources and disposition

The original five exports and the SC-01–SC-18 crosswalk are pinned at [scope preservation c4e2005](https://github.com/mthiessmeier/pacd-simulation/tree/c4e200595377cf64c6129dec61712d04412d1ec2/docs). Resolve the CSV source_file and export line against that tree. Resolve package_source_file against the [handoff directory at 2191b41](https://github.com/mthiessmeier/pacd-simulation/tree/2191b41304aa3c079641d76caf92d7d209d72476/docs/handoff/PACD_Codex_Handoff_v1.0). Implementation/test paths refer to the accepted code unless identified as proposed. The immutable input inventory and completed assessment have distinct roles. Source aliases are WO (work order), TM (traceability), EC (charter), FM (fairness) and MD (metric dictionary).

- **Decision precedence.** Use live AGENTS.md, Michael's latest continuation and DEC-038 for local non-reportable Phase 2 work. PR #9 proposes an additional handoff convention. The current task independently requests the handoff. PR #11 preserves sources and proposes sequencing. Neither draft must merge to start this work.
- **Scope conflict.** WO §§5–6 retain broader original criteria. The [owner decision for Increment 1](../status/PHASE2_INCREMENT1.md) accepts five governed inputs and specified equivalents for that increment. Later config families remain within scope. The historical bootstrap tag, six-branch sequence and historical status columns cannot establish current implementation status.
- **Evidence.** The [PR #8 acceptance](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861) identifies an 86-test independent challenge and two frozen 389-pass suites, each with one skip. PR #10 updates the walkthrough only. Row evidence cites accepted behavior where applicable. Open or not yet evidenced rows specify the behavioral demonstration required. A helper can be partial even when all of its unit tests pass.
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

First verify WP01 against the accepted register and its failure accounting. Next split WP05/WP06 into an action contract, a simulated review lifecycle and one integrated transition. A pending request carries the exact reversible action, target, policy, evidence, pre-state and validity interval. Record the decision, re-evaluate authority and current state before dispatch, then let the in-memory broker apply the allowed transition. Verify the complete post-state and collateral effects. Cover pending, denied, expired, unauthorized, execution-failed, verification-failed and rollback outcomes on matched benign/adverse fixtures. Record mission effects against explicit clock semantics and isolate duplicate suppression from corroboration. Review each slice before advancing.

WP07 then integrates one operator. WP08 and WP09 carry the six classes, portfolio selection and coordinated use through their own closure tests. Start environment, evidence, abstract scenario, condition and metric slices when their listed input capabilities exist. A start dependency can be satisfied by a bounded accepted equivalent. Full-package closure also requires every mapped residual and any stronger completion gate below. Every runtime increment needs an unmerged candidate, exact source/config/seed identity, failure ledger, meaningful tests and a fresh review-only session.


## WP00 · Reconcile the source and select the next increment

Verify all 558 units against the five pinned exports, assign each actual requirement to its workstreams and packages, check every cited path and resolve duplicate references. Deliver the ledger, this plan, the [WP01 work order](work_orders/DEVELOPMENT_COMPARISON_PLAN_v1.0.md) and [session handoff](../status/SESSION_HANDOFF.md). Independent review should sample evidence semantics as well as assess ID coverage.

## WP01 · Bind development comparison plans to attempted runs

Start dependencies: WP00. Workstreams: SC-01, SC-14, SC-15, SC-17, SC-18. Sources: TM 4, FM 3, MD 8–11, WO 6.5,7.

The current attempt register binds attempt ID, invocation ID and seed. Verified completions expose configuration identity retrospectively.

- Define a versioned development comparison plan identifying cells, scenario, defender condition, code revision, governed configuration, development seed/stream identity, comparison mode and canonical digest.
- Reuse existing bounded loaders, launch ownership, verification and accounting; preserve current v1 behavior and explicit expected-versus-observed identities.
- Retain every failed, timed-out, incomplete or invalid attempt and separately identify retries; avoid implying trusted preregistration time or a frozen experimental protocol.

**Acceptance**

- Condition/configuration/code/seed substitution cannot silently release measurements for the wrong planned cell.
- Formatting-only changes preserve canonical identity; substantive changes, collisions and stale bindings are detected.
- Existing replay and reportability-denial behavior remain intact; exact-head independent review precedes acceptance.

## WP02 · Complete enterprise, mission and simulated-time semantics

Start dependencies: WP00. Workstreams: SC-01, SC-02, SC-15, SC-16, SC-17. Sources: WO 6.1, TM layer 3 and 4–5, EC 4, MD 3.

Immutable graphs, directed dependencies and binary availability/continuity are accepted for bounded fixtures; broader temporal and entity semantics require reconciliation.

- Extend configured identities, accounts, credentials, sessions, privileges, trust paths, endpoints and synthetic SaaS/cloud services to the original 30–100-identity target while keeping tests small.
- Define mission criticality, dependencies, time-weighted availability, degradation, recovery and defensive collateral effects using explicit synthetic assumptions.
- Complete deterministic reset, snapshots, propagation and resource-bounded lifecycle semantics; reuse existing capabilities for early integration slices.

**Acceptance**

- State and dependency invariants hold across reset, isolation, restoration and failed recovery.
- Time-dependent mission outcomes regenerate from retained state transitions and distinguish attack-caused from defense-caused effects.
- Scale and duration assumptions are documented; no claim of real-world calibration follows from synthetic parameters.

## WP03 · Complete telemetry, evidence and competing beliefs

Start dependencies: WP00. Workstreams: SC-01, SC-03, SC-04, SC-15, SC-17. Sources: TM layers 1,2,4 and 5–6, EC 4,8, MD 6.

The accepted planner consumes observation-only tick, subject and signal inputs. Repeated-reading corroboration is a narrow rule within the broader evidence architecture.

- Add configured identity, endpoint, SaaS, cloud-service, deception and mission observations with coverage, delay, noise, loss, integrity, detector reliability and provenance.
- Implement bounded normalization, freshness, source reliability, contradiction and chain of custody; preserve evaluator-only ground truth and distinguish repeated or correlated evidence from independent corroboration.
- Add competing hypotheses, provenance-weighted uncertainty updates and development calibration records, with explicit reset and stale-evidence rules.

**Acceptance**

- Malformed, duplicate, stale and conflicting inputs have defined bounded behavior without hidden ground-truth leakage.
- Sensor/event streams reproduce while documenting permitted causal divergence between defender conditions.
- Calibration measures have defined outcomes/timing and adversarial or misleading evidence can worsen decisions visibly.

The [verified evidence context work order](work_orders/VERIFIED_EVIDENCE_CONTEXT_v1.0.md) covers measurement age and distinct sensor presence for a retrospective WP08 input. Reliability, contradiction, competing beliefs, prospective decisions and calibration remain open.

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

The independent governor, in-memory broker and exact-state verification support narrow isolation and review pathways; broader handler semantics remain open.

- Define versioned action contracts with target, preconditions, expected effects, cost, authority, reversibility, verification and rollback, retaining all six action classes in the wider catalog.
- Implement contextual authority envelopes, evidence levels and autonomy tiers 0–5, independent reevaluation and policy/state/action bindings; separate evidence level from confidence.
- Add one-shot authorization for stateful actions, allowlisted simulated handlers, independent expected-state reconstruction, collateral checks, partial failure, failed rollback and safe degradation.

**Acceptance**

- Stale, replayed, mismatched, prohibited or unauthorized non-reversible actions cannot dispatch.
- Expected and actual effects, unintended mutations and failed recovery remain separately auditable.
- The first accepted handler is a bounded slice; unimplemented action classes and contextual governance requirements stay open.

## WP06 · Integrate human oversight and the first guarded decision-to-outcome loop

Start dependencies: WP00, WP01, WP05. Workstreams: SC-02, SC-06, SC-10, SC-11, SC-12, SC-17. Sources: TM layers 3,8–11 and 5–6, EC 4, MD MIS,SAF,GOV,OPS.

Prospective policies currently stop at review referral. A standalone approval helper does not establish an integrated queue or completed intervention.

- Model review arrivals, capacity, delay, approval/denial/modification/override, timeout and expiry, with rationale, uncertainty/impact package and mission-command envelope.
- Reevaluate authority after relevant state or policy changes; connect one reversible simulated action to actual execution, verification and mission consequences.
- Demonstrate the complete observation-to-outcome chain on existing accepted fixtures where sufficient; capture pending, denied, expired, failed and successful outcomes and a matched comparator.

**Acceptance**

- Late/missing approval, queue overload, policy drift and state drift cannot silently authorize execution.
- Delay, legitimate completion, unnecessary intervention and mission effect derive from events rather than referral count alone.
- This simulation produces no human-trust claim; H6 remains separately deferred.

## WP07 · Integrate the first substantive polymorphic operator

Start dependencies: WP00, WP05, WP06. Workstreams: SC-06, SC-07, SC-10, SC-12, SC-17. Sources: WO 6.4, TM layers 5–6, EC 10, MD 4.

Polymorphism helpers exist, but integrated polymorphic state-changing behavior is identified as future work in the reviewed architecture.

- Select one operator within the canonical six-class taxonomy and specify its state transition, observation needs, cost, duration, detectability and reversibility.
- Route selection, authorization, execution and verification through canonical interfaces; expose a modeled adversary-knowledge effect with explicit assumptions.
- Compare a fixed choice and an adaptive choice under matched budget and information, retaining no-op and adverse-cost cases.

**Acceptance**

- The operator changes simulated state with a complete decision/effect trail and meaningful rollback behavior.
- Removing the operator in an ablation does not alter unrelated evaluation conditions.
- Acceptance closes only this operator slice; full six-class and coordinated requirements remain assigned to WP08/WP09.

## WP08 · Complete six-class portfolios and contextual multi-objective policy selection

Start dependencies: WP00, WP03, WP05, WP07. Workstreams: SC-06, SC-07, SC-08, SC-10, SC-17. Sources: WO 6.4, TM 3 (layers 5–6),5–6, FM 5, MD 4.

An accepted threshold rule or one operator would not establish full candidate portfolios, six-class capability or contextual policy selection.

- Retain substantive sensing, deception, infrastructure/network, identity/access, response and coordination variation; define portfolio metadata and admissibility.
- Implement contextual policy modes and fallback with explicit security benefit, information gain, attacker cost, mission effect, burden, reversibility, uncertainty and safety components.
- Represent diversity, switching cost, detectability and attacker-knowledge reliability/decay without rewarding unnecessary churn or hiding utility weights.

**Acceptance**

- Each class has implemented, traceable behavior and discriminating tests or an explicit author disposition; no class vanishes through scheduling.
- Component isolation, extreme values, hostile costs and policy transitions have defined behavior.
- Observed coordinated benefits remain development observations until separate reportable evaluation.

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

The static review comparator and corroborated review planner support a narrow contrast; the full planned suite remains to be reconciled.

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

Shared observation/governor paths and attempt accounting are useful foundations, but do not establish the complete fairness design.

- Implement both system-level comparisons of authentic complete systems and controlled comparisons that isolate policy or coordination.
- Account for all sixteen dimensions: scenario allocation, telemetry, state knowledge, mission knowledge, action catalog, safety rules, oversight, compute, retry/timeout, rollback, randomness, failure handling, metrics, tuning, negative controls and missing data.
- Declare intrinsic asymmetries, equalize appropriate budgets and semantics, separate exogenous paired streams from endogenous divergence and retain comparable calibration exposure.

**Acceptance**

- A reviewer can identify exactly what differs and reproduce each intended comparison cell.
- Swapped conditions, asymmetric inputs, hidden resource advantages and mismatched failure rules are detected.
- System-level differences are not attributed to one algorithmic mechanism without suitable isolation.

## WP12 · Implement the complete metric, data-contract and failure-outcome program

Start dependencies: WP00. Workstreams: SC-17, SC-18, SC-01. Sources: WO 6.5, TM layer 11 and 7, EC 10–11, MD 1–12.

Verified disposition metrics, registered completion accounting and raw-to-derived regeneration are accepted. Forty-seven broader metric definitions remain individually tracked.

- Preserve SEC-001–007, MIS-001–006, POL-001–007, SAF-001–006, GOV-001–005, CAL-001–006, GEN-001–005 and OPS-001–005, implementing each as its required mechanics become available.
- Complete raw-event, episode and manifest contracts; define numerator, denominator, unit, eligibility, timing/censoring, aggregation, missingness, exclusions, provenance and applicable distribution/tail reporting.
- Distinguish verified completed-episode measurements from failed/invalid-episode safety evidence. Develop attributable hard-failure accounting without inventing missing measurements or treating null as zero.

**Acceptance**

- Every implemented value regenerates from the appropriate retained evidence using a single condition-independent definition.
- Prohibited/catastrophic events and rollback failures remain visible by identity, including explicitly unresolved observations in invalid attempts.
- Metric IDs stay draft where assumptions remain unresolved; no metric becomes primary or frozen merely through implementation.

## WP13 · Complete scenario, control-plane and adverse-regime coverage

Start dependencies: WP00. Workstreams: SC-16, SC-04, SC-05, SC-10, SC-12, SC-17. Sources: WO 6.2,6.5,11, TM 7, EC 8,11, MD 5–7.

Identity, maintenance and repeated-reading fixtures are accepted; they do not cover all planned scenario and failure families.

- Retain all sixteen EC section 8 families: credential/session abuse, lateral movement, privilege misuse, SaaS/token persistence, deception sensing, mission disruption, degraded telemetry, inaccurate mission models, unreliable rollback, policy failure, evidence manipulation, strong static controls, low attacker adaptability, rapid humans, costly polymorphism and poor calibration.
- Individually test benign administration, prohibited candidates, non-reversible automatic actions, corrupted mission data, policy failure, failed rollback, telemetry outage, stale/duplicate authorization, unseen topology and denied external-action attempts.
- Add adverse/no-benefit cases as supported mechanics arrive; preserve failed, negative and inconclusive outcomes without tuning scenarios for PACD success.

**Acceptance**

- Each named family has a defined synthetic setup, expected invariant or measurement and linked retained outcome.
- Control-plane corruption cannot silently change evaluator truth or authorize prohibited actions.
- Unimplemented dependencies are explicit; missing evidence cannot be converted to a favorable score.

## WP14 · Complete calibration, ten ablations, sensitivity and analysis tooling

Start dependencies: WP00, WP11, WP12. Workstreams: SC-18, SC-04, SC-07, SC-08, SC-09, SC-14, SC-17. Sources: WO 6.5,7,11, EC 9,12–13, FM 5–6, MD 6–7.

Development seeds and deterministic replay exist. Broader calibration, ablation and sensitivity tooling requires requirement-level reconciliation.

- Retain ablations without mission model, uncertainty, reversibility, orchestration, policy portfolio or oversight delay; one polymorphism class; degraded governor; inaccurate dependencies; unreliable rollback.
- Record every tuned parameter, rationale and exposure; separate unit/property/development/calibration/holdout-development roles and treat inspected holdouts as exposed.
- Implement sensitivity grids, unseen topology/drift/degradation analyses and draft statistical/exclusion/multiplicity choices with a justified sampling unit, keeping reportable choices unfrozen.

**Acceptance**

- Each ablation changes its named mechanism and documents unavoidable coupled changes.
- Analysis retains adverse/tail outcomes and can be regenerated without hand-edited result tables.
- Repeated deterministic cases are not treated as independent sample size, and favorable development outcomes cannot select future reportable seeds.

## WP15 · Complete independent reconstruction and protocol-readiness review

Start dependencies: WP00, WP11, WP12, WP13, WP14. Workstreams: SC-18, SC-14, SC-17, SC-10. Sources: WO 4,8–13, TM 7–10, EC 14–16, FM 6, MD 10–12.

The bounded diagnostic milestone has recorded independent review. Acceptance of the expanded original program remains a separate evidence requirement.

- Reconstruct accepted increments from exact commits with complete source/config/seed/runtime/lock identities, retained failures, limitations and one-command table/figure regeneration.
- Audit closure of all actual original requirements and the WO section 11 criteria, including substantive components, fair modes, adverse cases, sensitivity/ablations and draft-protocol readiness.
- Prepare a concrete independent freeze-review packet covering baselines, metrics, distributions, seed/exclusion controls and analysis assumptions; retain reportable interlock denial.

**Acceptance**

- Every closure cites exact implementation, tests and independent acceptance; remaining items have explicit owner dispositions.
- An independent session can reproduce the expanded development package and challenge assumptions and boundaries.
- Protocol readiness does not create approval, reportable seeds or empirical conclusions; H6 remains outside simulation-only acceptance.

**Full closure** (WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP11, WP12, WP13, WP14). Program closure requires every WP01–WP14 and every original substantive requirement to be accepted complete or explicitly author-dispositioned with affected source IDs and residual scope recorded. Reportable execution and H6 retain their separate gates; no package may disappear through dependency scheduling.

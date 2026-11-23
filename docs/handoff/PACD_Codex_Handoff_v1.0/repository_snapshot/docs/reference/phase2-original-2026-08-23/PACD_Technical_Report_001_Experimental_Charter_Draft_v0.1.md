# PACD Technical Report 001 Experimental Charter Draft

**Document ID:** PACD-TR001-CHARTER-001  
**Version:** 0.1  
**Status:** Draft for Phase 2 implementation; not approved, preregistered, or frozen  
**Date:** 2026-08-23  
**Governing decisions:** PACD-DEC-006, PACD-DEC-008, PACD-DEC-038  
**Permitted evidence:** Non-reportable development and calibration only

## 1. Purpose

This draft defines the intended research structure for:

*PACD Technical Report 001: Experimental Evaluation of Bounded Polymorphic Agentic Cyberdefense in an Identity-Centric Enterprise Simulation.*

It guides implementation but does not authorize reportable runs. Any value, distribution, sample size, seed range, exclusion rule, statistical method, or primary comparison in this draft remains changeable until an author-approved freeze.

## 2. Research Questions

- **RQ1:** How should defender-side polymorphism be defined and classified in cyberdefense systems?
- **RQ2:** What architecture can support bounded polymorphic agentic cyberdefense under partial observability, adversarial adaptation, and mission constraints?
- **RQ3:** How can agentic defenders select polymorphic defensive actions while balancing security benefit, operational cost, uncertainty, reversibility, and mission impact?
- **RQ4:** Does coordinated polymorphism across sensing, deception, configuration, access, and response improve cyber-resilience outcomes compared with static defense or isolated adaptive mechanisms?
- **RQ5:** How should Polymorphic Agentic Cyberdefense be evaluated for robustness, generalization, safety, mission impact, and calibrated trust?
- **RQ6:** What governance and oversight model is required for responsible deployment of polymorphic agentic cyberdefense?

Phase 2 implements structures relevant to all six questions. It may generate implementation and diagnostic evidence for RQ1–RQ3 and the methodological aspects of RQ5/RQ6. It may not answer RQ4, the measured portion of RQ5, or the operational validity of RQ6.

## 3. Future-Testable Hypotheses

- **H1:** Governed defender-side polymorphism reduces attacker effectiveness more than static defense under conditions of reconnaissance, lateral movement, and adaptive adversary behavior.
- **H2:** Coordinated polymorphism across multiple defensive layers produces stronger resilience outcomes than isolated adaptive mechanisms at a single layer.
- **H3:** A bounded agentic architecture can improve defensive responsiveness without producing unacceptable levels of collateral operational impact.
- **H4:** Safety constraints, authorization tiers, reversibility checks, and human oversight mechanisms can reduce harmful autonomous actions while preserving the performance benefits of adaptive defense.
- **H5:** Evaluation methods that include adversarial drift, unseen topologies, mission-impact metrics, and safety testing will reveal weaknesses not visible in static benchmark evaluation.
- **H6:** Human trust in agentic cyberdefense improves when the system provides action rationale, uncertainty estimates, expected impact, reversibility information, and audit trails.

No Phase 2 development result may classify any hypothesis as supported, rejected, confirmed, or falsified. H6 requires human participants and is outside simulation-only testing.

## 4. Initial Simulation Scope

The first integrated environment should model identity-centric enterprise compromise and mission-aware containment without attempting to simulate all cyber operations.

Target scale and entities:

- 30–100 synthetic identities;
- normal users, privileged users, service accounts, and vendor identities;
- endpoints, SaaS systems, cloud services, and mission-critical applications;
- active sessions, credentials, privileges, trust paths, and service dependencies;
- one or more mission functions with explicit dependency graphs;
- synthetic identity, endpoint, SaaS, deception, and mission telemetry;
- reversible and irreversible simulated defensive actions;
- approval delay, telemetry degradation, rollback success/failure, and benign administrative activity.

No real network, production data, customer data, credentials, or external security control may be used.

## 5. Adversary Behavior Families

Draft state-machine behaviors:

1. reconnaissance;
2. credential acquisition;
3. session reuse;
4. resource and privilege discovery;
5. privilege escalation;
6. lateral movement;
7. data or mission-resource access;
8. persistence;
9. adaptation to observed defensive changes;
10. policy variants for stealth, speed, mission focus, and deception sensitivity.

Phase 2 may calibrate reachability, timing, and plausibility. It may not tune adversary parameters to produce a preferred PACD result.

## 6. Defender Conditions

Planned conditions:

- static defense;
- deterministic SOAR-style automation;
- delayed human-centered response;
- random polymorphism;
- single-layer adaptive defense;
- full PACD;
- unbounded agentic control as an internal diagnostic condition with simulated tools only;
- oracle defense as an upper-bound reference.

Each condition requires a versioned definition and fairness classification. The oracle and unbounded conditions are references, not deployable recommendations.

## 7. Comparison Modes

### 7.1 System-level comparison

Each defender receives the information, mission model, actions, execution reliability, and approval structure intrinsic to its authentic design. Results describe complete systems, not isolated algorithms.

### 7.2 Controlled comparison

Telemetry, state information, mission information, action set, execution reliability, compute/resource accounting, and scenario allocation are equalized where methodologically appropriate. Differences should isolate policy and coordination effects.

Both modes are required before reportable claims. A baseline may not be intentionally blinded merely to advantage PACD.

## 8. Scenario Families

Draft families:

- credential compromise and session abuse;
- identity-driven lateral movement;
- privileged-account misuse;
- SaaS access and token/session persistence;
- deception-assisted sensing;
- mission-critical dependency disruption;
- telemetry delay, noise, loss, and corruption;
- inaccurate mission/dependency models;
- unreliable rollback;
- policy-service failure;
- adversarial evidence manipulation;
- highly effective static controls;
- low attacker adaptability;
- rapid human response;
- high polymorphism cost;
- poor detector calibration.

At least one benign negative-control scenario and one regime in which PACD may underperform are mandatory.

## 9. Development and Reportable Seeds

Phase 2 uses a versioned **development seed registry** only. It is used for unit tests, debugging, calibration, and scenario plausibility checks.

Future reportable seed ranges must be generated and frozen after implementation and fairness review. Development seeds must not silently become the reportable sample. The frozen protocol must record the relationship between development, calibration, holdout, and reportable seeds.

No exact reportable seed range is established by this draft.

## 10. Outcome Families

Draft primary families:

- attacker objective completion;
- attack progression and time;
- defender responsiveness;
- mission continuity and degradation;
- defensive collateral impact;
- prohibited and catastrophic actions;
- rollback and recovery;
- polymorphism diversity and switching cost;
- attacker-knowledge reliability/decay;
- uncertainty calibration;
- governance compliance;
- approval and human-oversight burden;
- resource and compute cost;
- generalization under unseen topologies and drift.

The Metric Dictionary governs definitions. No primary outcome or multiplicity policy is frozen.

## 11. Negative Controls and Hard Failures

Mandatory visible controls include:

- benign administrative activity;
- prohibited action candidate;
- non-reversible automatic action;
- corrupted mission data;
- policy-service failure;
- failed rollback;
- telemetry outage/degradation;
- duplicate or stale authorization;
- out-of-distribution topology;
- external-action attempt denied by the simulation boundary.

Hard failures may never disappear into an average score. Counts, rates, tail outcomes, and episode identifiers must remain available.

## 12. Calibration and Author-Model Bias Controls

Before reportable freeze:

- calibrate environment mechanics without examining final reportable outcomes;
- document every tuned parameter and rationale;
- retain scenarios where static or human defense performs strongly;
- include regimes unfavorable to polymorphism;
- review baseline information/action parity;
- separate development, calibration, and holdout scenario sets;
- freeze metric formulas and exclusions before reportable execution;
- require independent challenge of the frozen protocol.

## 13. Draft Analysis Plan

Not established in this version:

- sample size;
- reportable seed range;
- primary comparison;
- confidence interval method;
- multiplicity control;
- exclusion criteria;
- missing/corrupt episode handling;
- catastrophic-tail threshold;
- equivalence or noninferiority margins;
- sensitivity grid.

These items require a later protocol version, explicit author approval, and a freeze hash. Phase 2 may implement analysis tooling without selecting favorable methods after observing reportable outcomes.

## 14. Reproducibility Requirements

A reportable candidate must satisfy:

1. every reported number is generated from retained raw records;
2. every table and figure regenerates with one command;
3. code, configuration, seed registry, baseline definitions, metrics, interpreter, and lockfile are hashed;
4. failed and prohibited outcomes are retained;
5. summaries are reproducible from raw event records;
6. the exact report matches generated artifacts;
7. a person other than the primary implementation author can reproduce the results.

## 15. Freeze Gate

Reportable mode remains unavailable until:

- this charter advances to an approved frozen version;
- the baseline fairness matrix is approved;
- metric definitions and schemas are frozen;
- scenario and adversary distributions are frozen;
- reportable seed and exclusion controls are frozen;
- independent protocol challenge is complete;
- the author issues an exact `APPROVAL.json` or successor record tied to the commit and governed hashes.

## 16. Current Disposition

This draft authorizes architecture, implementation, tests, calibration, and protocol refinement only under PACD-DEC-038. It is not a preregistration, not a final protocol, and not empirical evidence.

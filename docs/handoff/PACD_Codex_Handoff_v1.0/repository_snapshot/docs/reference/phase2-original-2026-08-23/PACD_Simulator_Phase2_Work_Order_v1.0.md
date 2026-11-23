# PACD Simulator Phase 2 Work Order

**Document ID:** PACD-SIM-WORKORDER-002  
**Version:** 1.0  
**Status:** Authorized implementation work order  
**Date:** 2026-08-23  
**Authorizing decision:** PACD-DEC-038  
**Starting baseline:** `pacd-bootstrap-v1.0` / `a09991a3a6ed6ff3889138a787c61c8c545c1cd0`  
**Evidence boundary:** Non-reportable development only

## 1. Mission

Develop the PACD simulator from the independently accepted bootstrap scaffold through small, reviewable, testable increments while preserving host safety, research integrity, exact provenance, fair-comparison design, and the reportable-mode interlock.

Phase 2 may implement and calibrate mechanics. It may not produce or imply empirical PACD findings.

## 2. Governing Sources

Apply in order:

1. latest explicit author decision;
2. Decision Register v1.0;
3. Canonical Artifact Manifest v1.0 and tag `pacd-bootstrap-v1.0`;
4. Project Charter v1.0;
5. Phase 2 Architecture-to-Code Traceability Matrix v0.1;
6. this work order;
7. Experimental Charter Draft v0.1, Fairness Matrix v0.1, and Metric Dictionary v0.1;
8. repository `AGENTS.md`;
9. retained earlier sources for provenance.

Never silently reconcile conflicts. Stop and escalate if a required change would weaken a governing control.

## 3. Hard Guardrails

All bootstrap host and repository guardrails remain mandatory.

- Do not modify, move, rename, overwrite, or delete content in Desktop, Documents, Downloads, or redirected equivalents.
- Do not uninstall, repair, replace, upgrade, downgrade, or reconfigure pre-existing software.
- Do not weaken antivirus, EDR, firewall, UAC, encryption, backup, browser, or enterprise controls.
- Do not elevate, reboot, edit the registry, create services/tasks, alter global PATH, or install Docker/WSL/GPU/cloud tooling.
- Do not use real network scanning, packet activity, exploitation, credential testing, malware, persistence, command-and-control, hack-back, production APIs, real customer data, or real targets.
- Do not create `configs/protocol/frozen/APPROVAL.json`.
- Do not run `--reportable`.
- Do not change repository visibility, add a public license, publish a package/release, create paid CI, or delete branches/tags/history.
- Do not commit directly to `main`.
- Do not modify the monograph or publication artifacts.
- Do not use prior draft results as evidence.
- Do not label a development run as an experiment, result, finding, benchmark, or hypothesis test.

If any prohibited activity appears necessary, stop and escalate with exact action, path/account, risk, alternative, rollback, and minimum required decision.

## 4. Branch and Review Model

Begin from exact tag `pacd-bootstrap-v1.0`, not from a mutable local checkout.

Use six increments:

1. `codex/phase2-model-and-schemas-v1`
2. `codex/phase2-core-environment-v1`
3. `codex/phase2-red-agent-and-scenarios-v1`
4. `codex/phase2-baselines-v1`
5. `codex/phase2-pacd-defender-v1`
6. `codex/phase2-metrics-and-reproducibility-v1`

Each increment requires:

- a clean no-hardlink checkout or ordinary clean clone under `<workspace>\repo`;
- a branch from the exact accepted merge/tag or latest accepted Phase 2 merge;
- additive commits only;
- a pull request that remains unmerged during review;
- versioned change log, validation report, known limitations, and traceability update;
- separated reviewer session that did not write the implementation;
- exact-head acceptance before merge.

Do not bundle all increments into one pull request.

## 5. Immediate Authorized Increment — Models and Schemas

The first Codex task must implement only Increment 1.

### 5.1 Deliverables

Create or refine:

- core domain models for identity, session, credential, asset, service, mission function, dependency, telemetry, evidence, hypothesis, belief state, action, policy, oversight request, execution, verification, audit, episode, and run;
- strict configuration schemas for scenario, topology, mission, adversary, defender, safety policy, metric registry, and development seed registry;
- schema versions and exact-key validation;
- bounded size, depth, alias, nonfinite, unknown-key, and duplicate-key handling;
- immutable identifiers and configuration-version bindings;
- JSON Schema or equivalent controlled schema artifacts under `schemas/`;
- `docs/SCHEMA_CATALOG.md`;
- `docs/PHASE2_IMPLEMENTATION_BOUNDARY.md`;
- updated `docs/ARCHITECTURE.md`;
- updated traceability matrix.

### 5.2 Required Model Properties

- immutable or explicitly versioned state;
- deterministic canonical serialization and hashing;
- finite numeric values only;
- explicit optionality; no ambiguous `Any`-style payloads in controlled interfaces;
- distinct identifiers for entity, run, episode, action, decision, policy, and configuration;
- explicit mission and governance context;
- explicit action target, precondition, expected effect, cost, reversibility, authority, verification, and rollback fields;
- explicit provenance, reliability, freshness, integrity, and contradiction fields for evidence;
- explicit development-seed classification;
- no production credentials, URLs, endpoints, commands, or executable payloads.

### 5.3 Tests

At minimum:

- unit tests for every schema;
- property tests for round-trip canonicalization and hashing;
- negative tests for duplicate/unknown keys, nonfinite values, excessive depth/size, invalid IDs, inconsistent versions, and forbidden external fields;
- invariants for unique IDs, mission dependency references, action targets, state immutability, and seed classification;
- compatibility tests proving the existing non-reportable diagnostic still passes;
- reportable-denial regression proving no output is created;
- static scan proving no external action capability was added.

### 5.4 Increment 1 Non-Goals

Do not implement the full environment, adaptive red agent, baselines, PACD planner, comparative metrics, reportable protocol, or empirical analysis in Increment 1.

## 6. Subsequent Increment Requirements

### 6.1 Core Environment

Implement deterministic enterprise/mission graph, reset, state transitions, sessions, credentials, privileges, services, mission dependencies, degradation, recovery, and rollback mechanics. Target 30–100 synthetic identities through configuration, but keep tests small and bounded.

### 6.2 Red Agent and Scenarios

Implement bounded abstract adversary state machines and scenario families. No real exploit details, commands, tools, network operations, or external targets. Include benign administrative negative controls and hostile parameter regimes.

### 6.3 Baselines

Implement substantive static, deterministic automation, delayed human, random polymorphism, single-layer adaptive, oracle, and unbounded diagnostic conditions. Enforce the Fairness Matrix and resource accounting.

### 6.4 PACD Defender

Implement evidence-to-belief update, candidate generation, six-class polymorphism management, policy portfolio, multi-agent arbitration, safety-governor inputs, oversight routing, and simulated execution. Keep safety and authorization independent.

### 6.5 Metrics and Reproducibility

Implement the Metric Dictionary, raw event/episode/run schemas, one-command regeneration, sensitivity tooling, ablations, calibration, negative controls, and complete manifests. Preserve all failed episodes and hard failures.

## 7. Development Seed Policy

- Create a versioned development seed registry.
- Label seeds as unit, property, development, calibration, or holdout-development.
- Do not define final reportable seeds.
- Do not reuse development outcomes to select a favorable reportable range.
- Retain seed and stream assignment in every run manifest.
- A later author-approved frozen protocol must create the reportable registry.

## 8. Evidence and Output Policy

Until a later decision, retain the existing evidence label:

`NON_REPORTABLE_DIAGNOSTIC`

Every Phase 2 run and report must state:

- development-only;
- not reportable;
- not hypothesis evidence;
- exact commit/config/seed identity;
- known limitations;
- whether evidence is builder-generated or independently reviewed.

Raw outputs remain outside Git under the bounded workspace. Do not commit local runs, receipts, capabilities, host identifiers, or unsanitized paths.

## 9. Quality and Security Gates for Every Increment

Run from a clean exact-head checkout:

- offline lock check with prereleases disallowed;
- frozen environment reconstruction;
- doctor;
- Ruff format and lint;
- strict mypy;
- complete pytest;
- branch-aware coverage;
- Bandit;
- detect-secrets;
- pip-audit;
- targeted unit/property/negative/scenario/reproducibility suites;
- same-seed replay where behavior exists;
- reportable-mode denial and unchanged run/receipt/invocation counts;
- static external-capability scan;
- clean worktree and exact PR head.

Coverage is a diagnostic, not a manufactured threshold. Uncovered safety-critical paths must be identified and dispositioned.

## 10. Review Requirements

The builder may not self-issue final acceptance.

A fresh review-only session must:

- reconstruct from the exact PR head;
- treat builder reports as claims;
- rerun standard and targeted gates;
- challenge schemas, path boundaries, authorization, transaction ownership, evidence integrity, and new behavior;
- record unexecuted tests;
- issue PASS, PASS WITH CONDITIONS, or FAIL;
- leave the PR unmerged.

A PASS WITH CONDITIONS is acceptable only when no current host-safety, execution-control, evidence-integrity, reproducibility, or non-reportable boundary condition remains.

## 11. Phase 2 Completion Definition

Phase 2 is not complete merely because the simulator produces charts.

Completion requires:

1. substantive implementations for the environment, adversary, baselines, PACD defender, mission model, governance, and metrics;
2. fair system-level and controlled-comparison modes;
3. every reported development number regenerates from raw records;
4. negative controls and hostile regimes behave plausibly;
5. sensitivity and ablation tooling exists;
6. known limitations are current;
7. the draft protocol is ready for independent freeze review;
8. no reportable run has occurred;
9. no hypothesis is classified;
10. an independent reviewer can reconstruct and run the development suite.

## 12. Required Increment Reports

For each pull request produce:

- preflight;
- work log;
- command log;
- decision log;
- escalation log;
- change log;
- validation report;
- known limitations;
- updated traceability;
- installed/dependency delta;
- source/download hashes;
- exact-head final report.

Sanitize hostnames, usernames, tokens, capabilities, serial numbers, and unrelated software details.

## 13. Stop Conditions

Stop before proceeding when:

- the baseline tag or expected commit does not resolve exactly;
- repository privacy or branch identity differs;
- a source/configuration conflict cannot be governed;
- a change requires real system integration;
- a metric, seed, baseline, or outcome is being selected because it favors a conclusion;
- a reportable approval or frozen protocol would be needed;
- a host guardrail blocks the work;
- a test failure cannot be corrected without weakening controls;
- a protected file or pre-existing software would need modification.

## 14. Current First Action

Create Increment 1 from `pacd-bootstrap-v1.0`, read all governing controls, write a preflight, and present the exact planned file/module changes before implementation. No Phase 2 code may be merged until its exact-head independent review passes.

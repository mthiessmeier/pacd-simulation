# PACD Simulation

PACD is a public, open-source Python research simulator for studying governed
cyberdefense in synthetic environments. It separates defender proposals, independent
authorization, simulated execution, state verification, recovery, and measurement.

**Start with the [current public demonstration](docs/current_demo/README.md).**
The walkthrough is pinned to merged **PR #22**, commit
[`31c1645`](https://github.com/mthiessmeier/pacd-simulation/commit/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25),
and exercises four bounded scenarios using the existing command-line interface.
It shows guarded execution, a sensing change, mission loss, escalation routing,
an operator decision brief, and simulated approval waiting time. A fifth declared
attempt remains unlaunched so that missing outcomes stay visible.

## What is implemented at this checkpoint

| Capability | Observable behavior |
|---|---|
| Guarded action lifecycle | A proposal can enter a capacity-limited simulated review queue. Approval, denial, expiry, refusal, and pending review remain distinguishable. The governor checks authority and state again before dispatch. |
| Two state-changing actions | The in-memory broker supports session isolation and a reversible sensing-profile switch. The switch changes the precision of subsequent observations of the same synthetic signal. |
| Prospective sensing policies | Fixed, adaptive, disabled, contextual, and scheduled conditions use bounded evidence, switching costs, and governed fallback rules. |
| Verified evidence context | Acquisition and delivery clocks, freshness, duplicate handling, and source identity are reconstructed without exposing evaluator-only truth to the policy. |
| Operator decision brief | Opted-in review packages bind rationale, action and target, delivered evidence, and a conditional immediate mission-availability preview. Compromise probability is explicitly unknown. |
| Consequence and oversight measurements | Optional views report evidence age at referral and execution (CAL-006), weighted mission unavailability (MIS-002), escalation routing (GOV-002), and simulated approval waits (OPS-003). |
| Reproduction and failure accounting | Verification reconstructs retained behavior. Registered attempts preserve completed, failed, timed-out, invalid, and incomplete outcomes; missing measurements remain null. |

See the [current progress record](status/CURRENT_PROGRESS.md) for merged increments,
evidence links, and residual scope, and the [architecture](docs/ARCHITECTURE.md) for
component boundaries. The [full remaining implementation plan](docs/REMAINING_IMPLEMENTATION_PLAN.md)
retains the original broader agenda.

## Reproduce the demonstration

The [step-by-step guide](docs/current_demo/README.md) provides PowerShell and POSIX
setup instructions for a fresh, clean producer checkout at the exact implementation
revision. It uses the committed dependency lock and the required CPython 3.13.15
runtime. The demonstration helper lives in the documentation checkout and calls the
unmodified public CLI in the pinned producer environment.

The guide includes expected synthetic observations, their interpretation, and the
retained outputs to inspect. Its [validation record](docs/current_demo/VALIDATION.md)
distinguishes passed source and unit checks from the four-case public CLI walkthrough,
which stopped at this documentation environment's free-space check before any case
was launched. Follow the guide's workspace and setup steps before running the helper.
Existing checkouts, runtimes, and retained run records do not need to be replaced.

## Evidence and scope

All current outputs are labeled `NON_REPORTABLE_DIAGNOSTIC`. They demonstrate
implemented contracts and reproducible synthetic behavior; they do not establish
PACD effectiveness, real-world safety, generalization, or operational readiness.
Reportable mode remains denied without a separately approved frozen protocol.

The runtime is local, CPU-only, and simulation-only. Current defenders are coded
policies, the adversary is scripted, and human review is simulated. There is one
integrated sensing-class variation. Adaptive adversaries, the remaining polymorphism
classes, substantive multi-agent coordination, broader baselines, calibrated metrics,
and the complete evaluation program remain in scope. Live model inference and real
security-control APIs are not part of this checkpoint. The H6 human-participant
study retains its separate requirements.

Local execution identity assurance binds retained content, paths, runs, code, and
configuration within the cooperative local threat model. Its limits are described
in [Execution identity assurance](docs/EXECUTION_IDENTITY_ASSURANCE.md).

## Progress and historical records

- [Current merged capability and work-package status](status/CURRENT_PROGRESS.md).
- [Requirement-level scope and evidence ledger](status/REMAINING_SCOPE_RECONCILIATION.csv).
- [Preserved original ledger baseline](status/history/REMAINING_SCOPE_RECONCILIATION_PR8.csv).
- [Remaining implementation plan and unchanged acceptance criteria](docs/REMAINING_IMPLEMENTATION_PLAN.md).
- [Current session handoff](status/SESSION_HANDOFF.md).
- [Historical Phase 2 demonstration at accepted `d5a2969`](https://github.com/mthiessmeier/pacd-simulation/blob/d5a29699e14409bfd54d30c51117c81077639ee6/docs/application_demo/README.md).
- [Historical Phase 2 top-level walkthrough](https://github.com/mthiessmeier/pacd-simulation/blob/546005be5ee0fb2289ef639b58d7d8102e16ae70/README.md), including its earlier proposal-and-escalation example.

The historical walkthroughs retain their original revision, assumptions, and
observations. Use the current demonstration above to inspect the later guarded
execution and sensing capabilities.

## License

Copyright 2026 Michael Thiessmeier. The simulator software and associated technical
documentation identified in [LICENSING.md](LICENSING.md) are licensed under the
[Apache License 2.0](LICENSE). [NOTICE](NOTICE) records attribution, and
[CITATION.cff](CITATION.cff) supplies software citation metadata. Separate research,
book, commercial-architecture, and internal workflow materials retain their
separate status as described in the licensing scope.

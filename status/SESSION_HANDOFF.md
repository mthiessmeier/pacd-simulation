# Session handoff · Public demonstration and progress refresh

## Current accepted implementation

The verified public `main` checkpoint is merged [PR #22](https://github.com/mthiessmeier/pacd-simulation/pull/22),
commit `31c1645ee28a7bbd2488dfb2d354be1fdea3fd25`, tree
`4eed4ef988d7ddd9647c40ed4f5c35d5bb21fa67`. Its feature head was
`52d8278a77614459d20773b372a11651a3edbec8`. PR #21's operator brief and PR #22's
simulated approval-wait accounting are merged capabilities.

The previous [PR #22 development handoff](https://github.com/mthiessmeier/pacd-simulation/blob/31c1645ee28a7bbd2488dfb2d354be1fdea3fd25/status/SESSION_HANDOFF.md)
is preserved byte for byte in [the history directory](history/README.md).
It describes the earlier candidate stage; it does not
establish the current merge status. Refresh GitHub state at the beginning of the
next session. At this refresh, [PR #23](https://github.com/mthiessmeier/pacd-simulation/pull/23)
remained an open draft on `codex/wp06-review-veto`, head
`f4e945e4ed31faa3004c936e2784bdcc8d1a162d`. Its proposed veto and GOV-003 behavior
are excluded from this merged checkpoint. Existing draft PRs #9 and #11 are
separate work; this documentation refresh does not merge or supersede them.

## This documentation increment

Michael requested a public introduction and progress record through the latest
merged PR, including a commit-pinned guarded-execution, sensing, mission-loss and
review-routing walkthrough while retaining the historical example and original
scope. Changes are prepared on `codex/docs-public-progress-pr22`.

- The [README](../README.md) now describes the public repository and points to the
  [current walkthrough](../docs/current_demo/README.md).
- The walkthrough uses a helper outside a clean PR #22 producer checkout. Four
  existing fixtures cover execution, sensing, mission impact, routing, operator
  briefs and approval waiting; a fifth declared slot is intentionally unlaunched.
- [CURRENT_PROGRESS.md](CURRENT_PROGRESS.md) maps merged increments and work-package
  residuals. The [ledger](REMAINING_SCOPE_RECONCILIATION.csv) preserves all 558 source
  units, original text, acceptance criteria and allocations. Its
  [original assessment](history/REMAINING_SCOPE_RECONCILIATION_PR8.csv) is retained.
- The [architecture](../docs/ARCHITECTURE.md) and
  [remaining plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) describe the current
  bounded behavior and the broader unfinished work. Historical Phase 2 demo files,
  runtime code, tests, governed configurations and dependency declarations are unchanged.

## Verification and outstanding issue

See [the validation record](../docs/current_demo/VALIDATION.md). The existing
source-reconciliation validator passed; 49 focused existing unit tests passed;
helper syntax, lint and formatting passed. Independent review found no blocking
documentation issue.

**The full public CLI walkthrough is unexecuted here.** The final helper called the
unmodified doctor, which passed 11 of 12 checks but rejected the native workspace's
roughly 4.2 GiB of free space against its 20 GiB minimum. It retained the failure
before register creation or diagnostic launch. Expected fixture results are not
published as new observed results. No guard was bypassed and no protocol approval
was created.

## Immediate next steps

1. Refresh `main` and all relevant PR heads. If a later implementation PR has merged,
   update the progress checkpoint and review whether the demonstration needs a new
   producer pin. Preserve previous records and distinguish merged from proposed work.
2. Review the documentation diff. On a native PACD workspace with at least 20 GiB
   free, run the guide against its exact producer pin and retain all outputs. Add
   the verified observation record after checking the run identities, null attempt,
   repeated report, evidence immutability and reportable-mode denial.
3. Keep this increment unmerged until its separate review and owner merge decision.
   Do not change guards, rewrite earlier evidence or claim a passed walkthrough to
   satisfy the documentation task. No default-branch or repository-setting change
   is part of this increment.
4. Continue implementation from the live accepted state and the
   [remaining plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md). Inspect existing PR #23
   work before starting overlapping oversight changes. Acceptance of a bounded
   slice does not close its full work package, calibrate a metric, or authorize the
   separate H6 human-participant study.

All outputs retain `NON_REPORTABLE_DIAGNOSTIC`. The original scope and acceptance
gates remain in force; this refresh introduces no new scope closure or experimental
authorization.

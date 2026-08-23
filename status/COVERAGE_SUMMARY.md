# PACD Diagnostic Coverage Summary

**Evidence label:** `NON_REPORTABLE_DIAGNOSTIC`

**Generated:** 2026-08-23T01:34:39-04:00
**Command result:** 108 tests passed on CPython 3.13.15; 74% aggregate branch-aware coverage.

No arbitrary coverage minimum was imposed. The retained local reports are `coverage.xml` and
`htmlcov/`; both are ignored diagnostic artifacts and are not committed.

## Safety-critical coverage review

| Module or boundary | Coverage | Disposition |
|---|---:|---|
| Safety governor | 97% | Approval, escalation, prohibition, and admissibility properties are exercised. |
| Execution verification and rollback | 84% | Action/config/hash binding, corrupt nonexecution, mismatch, and rollback denial paths are exercised. |
| Simulated execution broker | 84% | Approved execution, full authorization-digest binding, and nonexecution for escalated/prohibited actions are exercised. |
| Environment model | 82% | Global-ID uniqueness, reference/config invariants, isolation, and exact-context restoration are exercised. |
| Diagnostic harness | 77% | Event chain, transactional failure, collision preservation, raw retention, summaries, prohibited action, negative control, and output jail are exercised. |
| Run verifier | 76% | Exact closed-world manifest allowlists, canonical config, component hashes, seed/protocol/label/disposition, reparse, nonreportable/simulated-only state, same-action verification, budget, and tamper checks are exercised. |
| Reportable interlock | 64% | Missing, malformed, mismatched, extra-key, and dirty-tree denial paths are exercised. The valid-approval execution path is intentionally unexecuted because bootstrap may not create an author approval record. |

The CLI dispatch was not exercised by the coverage suite; it is covered by the retained manual
doctor, diagnostic, verifier, and reportable-denial gates. Diagnostic red-agent, orchestration,
oversight, and polymorphism modules are architectural seams not invoked by this minimal smoke
scenario; they make no reportable claim and remain candidates for a separately approved future
protocol. Rare operating-system I/O failure branches remain partially uncovered, while the
fail-closed transactional finalization path is directly regression-tested.

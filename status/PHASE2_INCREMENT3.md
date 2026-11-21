# Phase 2 Increment 3 acceptance · 21 November 2026

Michael Thiessmeier approved PR #5 at `f35051a873cf50628284861c7259a460616126e3`. It merged into main as `d48e950e72482a4daa027385039432fc4e766593`, with first parent `80773db7446a6ce44dc2845fd065e345da2df9ec` and second parent equal to the approved head. Both the merge and the approved head have tree `dc59cff482cfae7b81ced686bf0c6748716e75a1`. [Owner approval and main verification](https://github.com/mthiessmeier/pacd-simulation/pull/5#issuecomment-7067475971)

Each of the two clean frozen, offline test runs passed 341 tests and skipped the Windows directory-symlink privilege case. Five verified CLI runs across the smoke and maintenance fixtures matched the reviewed script, raw and summary hashes. Both sets of regenerated CSV and Parquet files matched the original bytes. The maintenance fixture preserved the benign administrator session through the user-session isolation.

This acceptance covers the bounded scripted scenarios and the verifier's event-sequence view. Evidence classification is `NON_REPORTABLE_DIAGNOSTIC`.

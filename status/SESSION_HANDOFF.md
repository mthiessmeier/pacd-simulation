# PACD continuation · WP00 and WP01

**Evidence class** `NON_REPORTABLE_DIAGNOSTIC`. This is the builder’s checkpoint for the documentation commit that follows `13dd59d54ab6c6b93a143bd2c8d9248daff6ea6d`. The pull request records the resulting SHA, exact-head gate results, separate review dispositions and any later corrections. [Candidate PR #12](https://github.com/mthiessmeier/pacd-simulation/pull/12)

## Git, provenance and authority

| Item | Observed state |
|---|---|
| Repository and branch | Private `mthiessmeier/pacd-simulation`, default `main`, working branch `codex/wp00-reconciliation-wp01-order`. Fresh ordinary clone under the dedicated workspace’s `repo` directory. |
| Accepted implementation | `d5a29699e14409bfd54d30c51117c81077639ee6`, approved PR #8 head `9f58a43021eb1efe159a55b4540e0e872b963349`. Two historical 389-pass/one-skip suites, 80.35% coverage and an independent 86-test challenge. [Accepted scope](https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861) |
| Starting base and merge base | Both `df33295469094a5ed9aa26fcc4b1fa1d019d3e5c`, 0 ahead/0 behind at preflight. PR #10 changes only README.md relative to the accepted merge. |
| Existing checkout | Clean bootstrap branch at `d3d63bc213c386a7839bb7a2f05cfdafa3ca5eb3`, its own merge base with live main, 0 ahead/27 behind. It stayed in place. |
| Live controls | Root AGENTS.md blob `92678b83f5cf21342811b1cbaaa84846b7a4b66e`, status/DECISIONS.md and the DEC-037/038 and owner-equivalence record in status/PHASE2_INCREMENT1.md. The owner’s November 21 continuation names WP01; DEC-038 permits development and calibration in the original broader Phase 2 scope. |
| PR #9 | Open draft handoff policy at `148b2cdb92a2046574b56201cfa9ee9510589a49`. The owner explicitly requested this handoff. |
| PR #11 | Open draft preserving the five exports and crosswalk at `c4e200595377cf64c6129dec61712d04412d1ec2`. Current package head `2191b41304aa3c079641d76caf92d7d209d72476`. No newer PR was present at preflight. |
| This branch | Preflight/work order `e69a61e`; first runtime candidate `42c6746230796fa3631d427df4720e7491fc5489` pushed to draft PR #12; selected-pair preparation and two-condition test `13dd59d54ab6c6b93a143bd2c8d9248daff6ea6d`. Final ledger, plan and this checkpoint are staged for the next additive commit. Target remains main. |

The explicitly identified archive was copied into dedicated workspace evidence with SHA-256 `6638f07a881856f528a1c1ec728fa040b9a42352c96547e0285671ae9a256126`. Thirty checksum entries matched the extracted package, copied archive members and Git blobs at the package head. The private copy receipt records actual paths, sizes and hashes under `var/tmp/wp00-20261121/inputs`. No dependency pins changed. The frozen local toolchain is uv 0.12.5 / CPython 3.13.15, lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`.

## What to inspect

- [Completed assessment](REMAINING_SCOPE_RECONCILIATION.csv) preserves all 558 units, 47 metric IDs and all source text. Rows describe accepted implementation evidence or assign residual work. They include duplicates, draft methods and controls.
- [Remaining plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) covers all 18 workstreams, WP00–WP15, full-package closure and the next guarded review stages. [WP01 work order](../docs/work_orders/DEVELOPMENT_COMPARISON_PLAN_v1.0.md) specifies CLI, plan schema, acceptance and operating limits.
- The earlier acceptance ends at referral for both prospective review defenders. Approval helpers supply no dispatch authority. Pending reviews, durable reauthorization, physical-time mission harm, six-class portfolios, specialist arbitration, full fairness and failed-episode safety/tail measures remain allocated.
- The candidate binds a pinned ordered plan to an exclusively claimed invocation and verifies the actual scenario, condition, script, registry, seed, configuration and revision. Only receipt-verified matches release measurements. A changed plan or an old unplanned completion yields an invalid cell with withheld counts. Distinct slots retain failures and retries. The plan’s mode is metadata pending WP11 controls.
- PR #9 and #11 remain separate drafts. The August initial branch instructions/historical status and Increment 1 equivalence have the limits described in the plan. MD-076 still needs a versioned wire-name decision or implementation. H6 remains separate human-subject work. No protocol approval, research result or merge decision was created.

## Verification and reproducibility

In the dedicated workspace, the builder used `git ls-remote origin refs/heads/main 'refs/pull/*/head'`, `git merge-base HEAD origin/main`, `git rev-list --left-right --count HEAD...origin/main`, `gh pr list --state all`, `gh pr view` and the PR #8 acceptance-comment API. Current source evidence and historical PR results have distinct identities.

At runtime commit `42c6746230796fa3631d427df4720e7491fc5489`, the separate clean gate checkout passed the offline frozen sync/lock, doctor, Ruff lint, mypy, Bandit and 41 focused tests. The first Ruff format check found the Python example in the work order; it was formatted in the subsequent commit. The direct CLI fixture produced two verified completions and one incomplete slot with seed 424242. Plan `32f042589f0286fb34d1791149c76402c552f26a689557f7c1e1e6449fcf1c98`, aggregate configuration `54e7a429b27bf94deeefe22f79ba22fff7ce36ae35dc6647b02784008ef10364`, report `d3398114a866be0cfc14a307e0ba50670a28aa168ad8b20f6019da47c41f5c09`. The condition substitution and nine approved expected-denial requests left the shared stores unchanged. The v1 eight-slot compatibility fixture reported three completions in 19 CLI calls. The two-condition addition passed all three targeted plan tests. No reportable run occurred.

Builder command lines, exits, logs and output fingerprints live under `review/wp01-code1`, `review/wp01-code1-cli` and the final `review/wp01-candidate1` packet when complete. The local orchestration and plan files under `var/tmp/wp00-20261121` and `review` stay outside Git. To reproduce the core checks in a clean candidate checkout:

```powershell
uv sync --frozen --offline --python 3.13.15
uv lock --check --offline --no-cache --prerelease disallow
uv run --frozen --no-sync pacd-sim doctor
uv run --frozen --no-sync ruff format --check .
uv run --frozen --no-sync ruff check .
uv run --frozen --no-sync mypy src tests docs/application_demo/regenerate.py
uv run --frozen --no-sync pytest -q --cov=pacd_sim --cov-branch
uv run --frozen --no-sync bandit -c pyproject.toml -r src
uv run --frozen --no-sync detect-secrets scan --no-verify .
uv run --frozen --no-sync pip-audit --local --skip-editable
python docs/work_orders/check_reconciliation.py <handoff-directory>
```

Use the locked workspace cache and a new workspace-local temp directory. The command receipts include the exact per-gate paths. Reportable-denial tests use the established expected-refusal route only. The historical full suites and independent review on PR #8 do not accept this PR.

## Next authorized action

Read the current PR #12 body for the latest tested SHA and review results, compare it with `git rev-parse HEAD`, and inspect outstanding findings. Review-only sessions must reconstruct on the exact candidate, challenge plan substitution/late failure/null outcomes, and check source fidelity and acceptance evidence. Address findings additively, rerun affected gates and leave the PR unmerged for Michael. After acceptance, the next behavioral slice is WP05/WP06: bind one synthetic reversible action and its exact target/state to a review, re-evaluate authority before dispatch, and retain each terminal and rollback outcome. The remaining allocations in the ledger continue to govern.

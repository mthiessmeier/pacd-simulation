# Session handoff · Configured asset and credential dependencies

[PR #29](https://github.com/mthiessmeier/pacd-simulation/pull/29) is the public development draft on `codex/wp02-asset-credential-dependencies`. Its description records the exact candidate, checks and independent review results. A separate owner decision controls merge. [WP02 work order](../docs/work_orders/ASSET_CREDENTIAL_DEPENDENCIES_v1.0.md)

| Record | Identity or evidence |
|---|---|
| Approved PR #28 | `fea51acb104d13ba9d20208d9e0b47f0b5e84bb0`. The local checkout, public branch, pull ref and PR head matched. Both independent reviews passed this head. The private evidence index matched SHA-256 `e781a7aff3912d6b1f315301e97b3972add3ea4fbfeba598016072aecdaae4f4`. |
| Verified main | Merge `c9b3620db74a40cbd5bdd917acae7fa8d051beaa`, parents `8cda05df92c180a4c3c32e038534d061b55822bb` and `fea51acb104d13ba9d20208d9e0b47f0b5e84bb0` in that order. The approved head and merge have the same file tree, `9c506b4f449bc395b8c3eec5872100e85657dd15`. |
| Feature history | Work order `b85cc93146ea18cf79c209bb8c16148904b52637`, configuration and state loading `e4bd5003a3f567a12dca8259a9581ce718697a37`, matched fixtures and regression tests `474792866450922e5c054ecd6431a2732bde952d`. |
| Source and authority | WP02, R-EC-022, R-EC-023, R-WO-076, R-TM-013, SC-01/02/15. The latest owner instruction authorizes the #28 merge and this public development draft under AGENTS.md, DEC-038 and D-017. Documentation drafts #9, #11 and #24 were open at preflight. |
| Frozen environment | CPython 3.13.15, uv 0.12.5 and lock SHA-256 `2ed6b7134df13ce28adaed91bbed4198251fb98e46618f98608cfb8db6047b69`. The dedicated workspace has the offline cache `var/cache/uv-project`. |

Use the existing `diagnostic` and `metrics --function-availability` readers. A scenario can name synthetic assets and opaque credential records, each with an explicit initial Boolean state. In the three matched fixtures, loss of the endpoint interrupts mission A and loss of the credential interrupts B. The ordinary static-review isolation can interrupt A independently at tick six. Initially unavailable missions contribute eight observed outage ticks over the full eight-tick horizon. An unlaunched attempt has null metrics.

Fifteen focused fixture tests passed. The candidate loader reproduced canonical configuration and initial-state hashes for all 21 earlier scenarios. The private index `review/pr29/final-evidence.json` records exact commands, checks, review digests and the pinned comparison on development seeds 424242 and 424243.

These fixtures exercise binary availability for one endpoint kind and synthetic credential activity. Other asset and service classes, credential lifecycle, privileges, trust paths, graded degradation, calibration and failed-episode safety retain their existing acceptance criteria. H6 retains its separate human-study requirement. Classification `NON_REPORTABLE_DIAGNOSTIC`. [Full plan](../docs/REMAINING_IMPLEMENTATION_PLAN.md) · [Previous handoff](https://github.com/mthiessmeier/pacd-simulation/blob/fea51acb104d13ba9d20208d9e0b47f0b5e84bb0/status/SESSION_HANDOFF.md)

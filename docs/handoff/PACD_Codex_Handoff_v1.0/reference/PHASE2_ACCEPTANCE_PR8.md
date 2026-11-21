# Retained acceptance record: PR #8

Source: https://github.com/mthiessmeier/pacd-simulation/pull/8#issuecomment-7068565861

Created: 2026-11-21T20:11:03Z

Record copied for handoff provenance; verify current source before relying on it.

## Increment 6 accepted · Phase 2 diagnostic work sample

Michael Thiessmeier approved Increment 6 and authorized merging PR #8 at `9f58a43021eb1efe159a55b4540e0e872b963349`. Accepted main is `d5a29699e14409bfd54d30c51117c81077639ee6`. Its first parent is `9c9dfcec659870c41aa7cc95846d6760d9c31df7`, its second parent is the approved head, and its tree `b8f84815f15aee2473ea2150820497777eb541b6` matches the approved tree.

All 32 local gates passed on the merge. Each of two fresh frozen environments passed 389 tests with one Windows directory-symlink privilege skip. Branch-aware coverage was 80.35%. The fresh dependency audit found zero known advisories across 72 packages. All 28 secret-scan fingerprints matched the approved head. Nine reportable requests were denied with the retained run, receipt and invocation stores unchanged.

The 114 compatibility CLI calls reproduced all 19 reference episodes, verified raw and summary semantics and regenerated CSV and Parquet byte-for-byte. The registered-set replay returned the expected exits for all 19 calls, including four deliberate refusals. It accounted for 3 verified completions in 8 attempts. The verified raw events supplied 5 escalations among 7 candidate actions, 1 simulated execution and 0 prohibited executions. The remaining rows reported a failure, a timeout, two incomplete attempts and an invalid binding.

The independent challenge on this main commit passed 86 focused tests. Its ten-slot register produced 4 completions, 2 retained failures, 1 timeout, 2 incomplete attempts and 1 invalid attempt. An independent action-ID calculation recovered 6 escalations among 8 observed candidates. No blocking findings remain. The timeout challenge exercised the production exception and retention path.

Acceptance covers the six bounded Phase 2 engineering increments and their synthetic reproducibility package. All output is `NON_REPORTABLE_DIAGNOSTIC`. The evaluator walkthrough was run in a fresh named checkout of the accepted merge, and its retained manifest recorded this exact SHA. The checked-in README’s implementation pin `5eb554c` was exercised separately. [Accepted source](https://github.com/mthiessmeier/pacd-simulation/tree/d5a29699e14409bfd54d30c51117c81077639ee6) · [Diagnostic and registered-set commands](https://github.com/mthiessmeier/pacd-simulation/blob/d5a29699e14409bfd54d30c51117c81077639ee6/docs/application_demo/README.md#account-for-a-registered-set-of-attempts)

Accepted-main SHA-256 evidence fingerprints:

- Gate ledger `95fdaf0df73fb4984737c8a43b461c9d161821a135659b27c73cab3ec58eeb9c`
- CLI compatibility matrix `505b7ae57c724d394ac6c4a4193de4038c33639e3a56dd9d520a6ba8b37061a6`
- Registered-attempt replay `555570e63cae750ddd8e55fe5cd7ecd4a01b3f0f8adc76ec17a275477ab2a836`
- Independent review receipt `b856872746178cc3690b3ccff18df57455d870b633f9cb48888750a966958981`


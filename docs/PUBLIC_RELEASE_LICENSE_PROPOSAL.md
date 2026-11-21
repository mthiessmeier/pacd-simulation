# PACD licensing and public work-sample proposal

**Status:** PROPOSAL ONLY — no license grant, publication approval or visibility change.  
**Prepared:** 2026-11-21  
**Reviewed private repository:** mthiessmeier/pacd-simulation  
**Reviewed main:** f881f6553e9210d84e8f009a9700c0ce65eceabd

## Recommended decision

Use the unmodified **Apache License 2.0** for a deliberately scoped public research edition of the simulator, subject to confirmation of the licensor's rights and acceptance of the license's commercial-reuse and contributor-patent terms.

Retain the existing repository as the private development and audit record. Prepare a separate public companion from a pinned accepted snapshot. This recommendation addresses actual historical host-path records and the broader internal source/handoff branches; it does not imply that the simulator code is confidential or unsuitable for publication.

This proposal does not select a license for the owner, replace LICENSE_PENDING.md, or authorize creating a public repository. The code, tests and metadata are unchanged.

## Application requirement

The US residency form asks for links showcasing notable work and a short explanation of the applicant's involvement. It does not specify a public GitHub repository or an open-source license. The listed deadline is November 22, 2026, 11:59 p.m. Pacific (November 23, 2:59 a.m. Eastern).

An accessible work sample is useful, but the application deadline does not require making an unresolved intellectual-property grant. If publication authority remains unresolved, submit already-public work and accurately describe the simulator's availability without presenting a private link as anonymously accessible.

Source: https://job-boards.greenhouse.io/anthropic/jobs/5438311008

## License choices

| Choice | Main consequence | Proposed use |
|---|---|---|
| Apache-2.0 | Commercial/proprietary reuse with notice obligations and express contributor patent terms | Preferred if broad research and industry reuse is intended |
| MIT | Broad reuse under a short notice-based license; no express Apache-style patent clause | Simplicity-first alternative; not an assured patent-preservation strategy |
| MPL-2.0 | Distributed covered-file modifications remain under MPL; larger proprietary combinations are possible | Alternative if file-level reciprocity is the objective |
| AGPL-3.0 | Strong copyleft plus source-offer requirements for qualifying remotely used modified versions | Select only if network-use reciprocity is a deliberate objective |
| Public with no OSS license | Public inspection/forking under platform terms, with default copyright restrictions otherwise | Distinct publication choice; not an open-source release or confidentiality protection |

All listed standard open-source licenses permit commercial use. A research-only, noncommercial, or no-training restriction would require a different source-available strategy; do not insert it into Apache and continue labeling the result Apache-2.0.

Apache's patent grant is limited to the contributor-licensable claims described in its section 3. It is not a blanket grant of every patent held by the licensor. Its grants are consequential and cannot be treated as a reversible repository setting.

Public disclosure is a separate decision from licensing. Publishing technical material can affect patent rights even if the repository has no open-source license. Any relevant filing and disclosure position therefore needs to be resolved for the selected public contents; this proposal makes no determination of ownership, filing status, or patentability.

## Proposed public scope

Include only reviewed, authorized content:

- Simulator source and tests.
- Synthetic diagnostic configurations, schemas, dependency lock and build metadata.
- Purpose-written public architecture, execution-assurance and reproduction documentation.
- A compact diagnostic verification summary tied to the source and public-export revisions.
- Citation metadata, the chosen license, relevant attribution and third-party notices.
- Transparent provenance identifying the exported development revision and documentation omissions.

Keep the following outside the proposed public edition unless specifically authorized:

- Book manuscripts, unpublished architectural drafts, Interregnum and commercial product architecture.
- Internal Codex handoff archives/templates and private Library resource identifiers.
- Historical installation, remediation and host-path records.
- Private ownership, assignment or patent-preparation material.
- Any real credentials, personal/customer data, unapproved third-party material or reportable approval record.

The accompanying PUBLIC_EXPORT_CANDIDATES_2026-11-21.json identifies paths at the reviewed main revision for further release review. It is a candidate manifest, not a secret-scan result, copyright clearance, final allowlist or runnable export.

## Verified repository-specific preparation needs

1. LICENSE_PENDING.md states that no project license is selected; pyproject.toml still says license pending/private.
2. status/SANITIZATION_CORRECTION_A01_v1.0.md records two historical local-profile paths retained through additive history. These were classified low severity, not a credential leak. Current-tip sanitization does not remove them from history.
3. Open draft PR11 includes the full original planning exports and handoff ZIP with private source identifiers. A whole-repository visibility change includes branch/PR content, not only main.
4. README.md assumes authenticated private access, a workspace-local uv installation and a prepopulated offline package cache. Public reproduction needs a verified fresh-environment route and a separately described later offline-replay route.
5. The recorded dependency inventory is older than the current lock. Refresh it for the exact release and distinguish direct/runtime dependencies, development tools and any bundled third-party content.
6. PR12 merged at the reviewed main revision and includes WP00/WP01 work. Do not restart those tasks from the older handoff checkpoint.
7. This focused review did not establish an exhaustive full-history secret scan or a copyright/patent chain of title. No simulator tests were rerun for this proposal.

## Exact implementation sequence after the decisions

1. Record the approved license, actual copyright holder/licensor, rights-cleared publication scope and selected public-repository approach. Existing grants by third parties remain their own.
2. Build a private release candidate from the approved accepted revision using an explicit file allowlist. Preserve the original private history. Do not use a public fork or mirror that unintentionally transfers all internal branches/history.
3. Add the canonical unmodified Apache-2.0 LICENSE text if that choice is approved. Add accurate copyright/attribution notices. Include NOTICE only where needed or useful; do not use it to add restrictions to the license.
4. Update package metadata using the supported build-backend format and ensure the license is included in the built distribution. Resolve the pending-license marker through an explicit supersession record; do not leave contradictory metadata.
5. Add CITATION.cff with verified author, title, version and the actual public URL. Do not invent a DOI, ORCID, release date or affiliation. Requested scholarly citation is distinct from license obligations.
6. Prepare a public README describing the guarded-agency research question, actual implemented behavior, development limitations, applicant's contribution and AI-assisted implementation/review process. Include working local installation and diagnostic commands, expected artifact types, and a clearly bounded verification summary.
7. Review the actual export and included binary/archive contents for private material, secrets, third-party notices and rights scope. Refresh dependency notices against the pinned lock. Confirm that documentation exclusions do not remove required code/test fixtures or controls.
8. Test the export in an authorized clean isolated environment with the required gates and one small diagnostic. Record results for the exact exported revision; prior private-repo test counts do not automatically validate a modified export. Preserve NON_REPORTABLE_DIAGNOSTIC and all simulation-only controls.
9. Present the concrete release candidate and exact publication target. Change audience only after the owner's actual publication decision. Respect any already-recorded approval; do not request it repeatedly.
10. Verify the final repository and reproduction instructions without a signed-in session before inserting its real URL in the application. Submit before the application deadline even if a separate broader open-source release is postponed.

## Decisions still required

- **Licensor:** Who owns or is authorized to license the released simulator code and included documentation? The author field is not a substitute for resolving this.
- **Reuse policy:** Is commercial/proprietary reuse under Apache-2.0, including its defined patent grant, intended?
- **Disclosure scope:** Are relevant patent/disclosure and third-party rights cleared for the selected contents?
- **Publication target:** Approve the proposed curated public companion, or explicitly choose publication of the existing repository after reviewing its full exposed scope.

AGENTS.md section 6 and LICENSE_PENDING.md reserve license selection and public release to Michael Thiessmeier. This proposal completes preparatory analysis and identifies the concrete decisions; it supplies none of those approvals.

## Primary references

- Apache license: https://www.apache.org/licenses/LICENSE-2.0
- MIT license: https://opensource.org/license/mit
- MPL FAQ: https://www.mozilla.org/en-US/MPL/2.0/FAQ/
- AGPL text: https://opensource.org/license/agpl-3-0
- Open Source Definition: https://opensource.org/osd
- GitHub licensing: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- GitHub visibility: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- Rights and dependencies: https://opensource.guide/legal/
- USPTO disclosure guidance: https://www.uspto.gov/patents/basics/international-protection/filing-patents-abroad
- EPO internet disclosures: https://www.epo.org/en/legal/guidelines-epc/2026/g_iv_7_5.html


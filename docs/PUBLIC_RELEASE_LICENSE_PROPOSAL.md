# Approved PACD license and public work-sample preparation

**License decision:** APPROVED — Apache License 2.0  
**Licensor:** Michael Thiessmeier  
**Decision date:** November 21, 2026 (America/New_York)  
**Publication work:** Preparation remains open; repository visibility is unchanged.  
**Reviewed implementation base:** f881f6553e9210d84e8f009a9700c0ce65eceabd

## Owner decision

Michael Thiessmeier confirmed his authority as licensor and selected Apache 2.0.
The copyright/licensor and software-license questions raised by the earlier
proposal are resolved for this implementation. Do not ask for those decisions
again. The current grant and its scope are recorded in [LICENSE](../LICENSE),
[NOTICE](../NOTICE), [LICENSING.md](../LICENSING.md), and decision D-017.

The original proposal is retained in Git history. Its conditional language does
not override the owner's subsequent decision. This file retains its existing
path so earlier links continue to resolve.

## Scope implemented

The first-party simulator source, tests, synthetic configurations, schemas, build
support and identified technical documentation use Apache-2.0. The package
metadata identifies that license and includes the license, attribution and scope
files in built distributions. CITATION.cff records the software author and actual
repository URL without inventing a public release, DOI or affiliation.

The books, commercial architecture, original research exports, internal handoff
archives and private provenance/status records remain separate works outside this
grant, as specified by LICENSING.md. Existing dependency and third-party notices
remain applicable. Project simulation and evidence controls are not additional
restrictions on Apache-covered downstream use.

## Application and publication objective

The US Anthropic residency form asks for links showcasing notable work and a
description of the applicant's involvement. It does not require an open-source
repository. The listed deadline is November 22, 2026, 11:59 p.m. Pacific
(November 23, 2:59 a.m. Eastern).

Source: https://job-boards.greenhouse.io/anthropic/jobs/5438311008

The proposed public companion remains a publication approach, not an audience
change already performed. The current development/audit repository is private.
Its URL is not yet an anonymously accessible application work sample.

## Current publication preparation needs

1. Refresh the live implementation and accepted-review state. PR12 delivered the
   comparison-plan work; newer work may supersede this checkpoint.
2. Prepare a curated public candidate from an accepted pinned revision, preserving
   private development history. The existing candidate inventory covers 185 files
   at the earlier main checkpoint and is a starting inventory, not a final allowlist
   or a clearance record. Add the newly approved license/notice/scope/citation files.
3. Preserve all required source, fixtures, tests and development controls. Review
   actual export contents, including any archives, rather than assuming that a path
   name establishes publication suitability.
4. Keep historical host paths and internal source/handoff packets outside the
   initial public edition. The repository documents an additive historical
   host-path correction; current-tip cleanup did not remove historical objects.
5. Adapt the README for a reviewer with a fresh environment. The existing commands
   assume authenticated access, a prepared workspace and a populated offline cache.
   Verify an initial installation route and a separate subsequent replay route.
6. Refresh dependency license/notice inventory against the exact release lock and
   inspect any bundled third-party content. Do not infer incompatibility from the
   existence of a dependency, or claim that its own license was replaced.
7. Describe actual implemented behavior, limitations, the applicant's contribution,
   and AI-assisted implementation/review accurately. Keep development output
   NON_REPORTABLE_DIAGNOSTIC and distinguish recorded prior tests from export tests.
8. Run the applicable isolated export checks and a bounded diagnostic, recording
   exact source/export identities and observed results. This licensing change does
   not itself establish a tested public edition.
9. Publish only the exact reviewed contents to the owner-authorized target and
   verify access without a signed-in session before using that URL in the application.
   Honor an existing publication decision if one has subsequently been recorded.

## Remaining publication choices

The owner has settled the license and licensor. The separate remaining publication
choice is whether to use a curated public companion or expose the existing
repository after reviewing its full history, branches and PR contents. Release
review of the exact selected files and an accessible final URL are also still needed.
Do not turn those publication tasks into another request to approve Apache 2.0.

## Primary references

- Apache license: https://www.apache.org/licenses/LICENSE-2.0
- Apache licensing FAQ: https://www.apache.org/foundation/license-faq.html
- GitHub licensing: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- GitHub visibility: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- Python build-backend inclusion rules: https://docs.astral.sh/uv/concepts/build-backend/

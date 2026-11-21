# Scope preservation documentation record — 2026-11-21

## Instruction and preflight

Michael Thiessmeier asked to preserve the work items in the original broader Phase 2 scope after questioning whether the proposed Phase 3 was already included.

Read-only GitHub inspection confirmed main df33295469094a5ed9aa26fcc4b1fa1d019d3e5c, accepted Phase 2 implementation d5a29699e14409bfd54d30c51117c81077639ee6, and the existing AGENTS.md. PR #9 remained open/draft. The recursive tree was complete and contained no Actions workflow and no existing paths overwritten by these new scope documents. The existing README receives an appended navigation section only.

## Changes

- Preserved complete retrieved texts of five August planning sources as explicitly labeled normalized exports with identity and SHA-256 metadata.
- Added an 18-workstream crosswalk preserving the complete original scope.
- Added 558 stable source-unit inventory entries, including all 47 original metric IDs.
- Preserved eight defender/reference conditions, ten proposed ablations, sixteen fairness dimensions, scenario and hard-failure inventories, six-class polymorphism, policy portfolios and multi-agent arbitration.
- Added a README pointer so later sessions can discover the scope record.

The inventory contains paragraphs, list items and table rows, including overlap and historical controls; its count is not a count of unique requirements. No original requirement is declared complete, dropped or newly deferred by this documentation. Requirement-level evidence reconciliation remains open.

## Documentation verification

- PASS: all five reads were complete (has_more=false).
- PASS: every inventory original_text matches its specified export line after CSV readback.
- PASS: all source-unit IDs are unique.
- PASS: all 47 expected metric IDs are present exactly once in the MD source inventory.
- PASS: the crosswalk contains SC-01 through SC-18.
- PASS: retained source exports have recorded UTF-8 byte counts and SHA-256 fingerprints.
- Simulator tests, diagnostic runs and implementation acceptance: UNEXECUTED in this documentation task.
- Remote tree/commit/file readback: to be verified after creating the documentation commit; final verified result belongs in the PR description.

## Remaining work

Complete item-level evidence mapping against accepted implementation and reviews. Adopt a full work order that schedules all remaining original requirements; phase numbering and proposed delivery groups are not an authorization to reduce scope. Preserve H6's separate human-subject boundary and all reportability controls. Review this documentation PR without treating it as independent simulator acceptance. Leave it unmerged under AGENTS.md.

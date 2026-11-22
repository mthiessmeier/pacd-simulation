# PACD simulator licensing

**License:** Apache License, Version 2.0 (`Apache-2.0`)  
**Licensor:** Michael Thiessmeier  
**Copyright:** Copyright 2026 Michael Thiessmeier  
**Owner decision:** November 21, 2026 (America/New_York)

Michael Thiessmeier authorized Apache 2.0 for the simulator work identified below.
The complete, unmodified license is in [LICENSE](LICENSE), with attribution in
[NOTICE](NOTICE). The terms of that license govern the covered work.

## Covered simulator work

The Apache-2.0 grant covers the first-party contents of:

- `src/`, `tests/`, `configs/`, and `schemas/`;
- `pyproject.toml`, `uv.lock`, `.python-version`, `.editorconfig`, `.gitattributes`,
  `.gitignore`, and `.pre-commit-config.yaml`;
- `README.md`, `AGENTS.md`, `CITATION.cff`, and this `LICENSING.md`;
- `docs/ARCHITECTURE.md`, `docs/EXECUTION_IDENTITY_ASSURANCE.md`, and
  `docs/application_demo/`;
- Python implementation/validation utilities directly in `docs/work_orders/`
  (files matching `docs/work_orders/*.py`).

This identifies the licensed software, tests, synthetic configurations, build
support and associated technical documentation. New material outside these paths
must have an explicit license designation before it is represented as Apache-2.0.
Existing third-party licenses and ownership notices continue to apply to any
third-party material within these paths.

## Separate works outside this grant

Internal research, provenance and workflow records are distinct works and are not
included in this Apache-2.0 grant merely because they are stored in this repository.
This includes `status/`, `docs/reference/`, `docs/handoff/`, `docs/governance/`,
Markdown work orders in `docs/work_orders/`, `docs/REMAINING_IMPLEMENTATION_PLAN.md`,
and `docs/PUBLIC_RELEASE_LICENSE_PROPOSAL.md`, including embedded source exports
and archives. Their existing rights and any separate notices remain applicable;
no new redistribution permission for those separate works is granted here.

The separately held PACD books, Guarded Agency material, Interregnum, and Cyber
Eagle commercial architecture are also outside this grant. A reference to one of
those works is not a license to reproduce that work. Third-party dependencies
retain their own licenses; this file does not relicense them.

These boundaries identify separate material outside the licensed work. They do
not add noncommercial, research-only, no-training or other use restrictions to
the Apache-covered simulator. Simulation-only and NON_REPORTABLE_DIAGNOSTIC
requirements are project development and evidence controls, not modifications of
the Apache License or restrictions on downstream fields of use.

## Distribution and citation

Distributions of the covered work must comply with Apache 2.0, including its
applicable license and notice obligations. The Python build metadata includes
`LICENSE`, `NOTICE`, and this scope statement as license files. Check any bundled
third-party materials for their own redistribution requirements.

`CITATION.cff` supplies software citation metadata. Scholarly citation is requested
and is not an additional condition added to Apache 2.0. No public release date,
DOI or public-access claim is asserted by the citation record.

## Publication status and historical instructions

License selection is resolved. `LICENSE_PENDING.md` is retained only as a
superseded historical pointer. Older statements that no license has been chosen
do not override this decision for the covered work in this revision.

Repository visibility and publication of separate research/provenance records
remain separate decisions. The repository is private at this licensing revision;
adding a software license does not make a private URL accessible to reviewers.
This decision creates no empirical approval, reportable result or release tag.

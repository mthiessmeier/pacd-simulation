# PACD Environment Bootstrap — Escalation Log

| ID | Timestamp | Blocker | Proposed action | Affected path/system/account | Risk | Alternatives | Cost | Author decision | Status |
|---|---|---|---|---|---|---|---|---|---|
| E-001 | 2026-08-23T00:05:32.1675239-04:00 | Official uv 0.12.5 archive checksum passed, but the extracted executable was not Authenticode-signed and the provenance fetch required GitHub authentication | After E-002 approval, fetch and verify the official uv attestation; execute uv only after successful verification | `%WORKSPACE_ROOT%\var\downloads\uv-x86_64-pc-windows-msvc-0.12.5.zip`; `%WORKSPACE_ROOT%\var\cache\tools\uv\0.12.5\uv.exe`; public GitHub attestation API | Executing an unattested unsigned binary could violate provenance and host-safety controls | Provide an offline signed bundle/signed build; explicitly accept official checksum only; or stop blocked | $0; no paid service | Michael Thiessmeier approved the OAuth prerequisite; exact SLSA attestation then passed | RESOLVED |
| E-002 | 2026-08-23T00:05:32.1675239-04:00 | No existing GitHub CLI authentication; repository search/delivery and uv attestation retrieval could not continue | Authorize the official HTTPS web-device OAuth flow without an SSH key; verify secure storage and active account without exposing the token | Authorized GitHub account; Windows credential store; task-local GitHub CLI configuration | Persistent OAuth grant with default `repo`, `read:org`, and `gist` scopes; potential plaintext fallback; recorded HTTPS preference | Authenticate independently; supply an approved authenticated environment; or stop blocked | $0; no Actions or cloud spend | Michael Thiessmeier explicitly approved; keyring storage verified and persistent Git helper declined | RESOLVED |

## E-001 detail

- **Necessity:** `uv` was required for TC-03 through TC-06, the isolated Python 3.13 runtime, lockfile, tests, and reconstruction. It was executed only after provenance verification.
- **Rollback plan:** No rollback action is taken now. All task-created files are isolated under the workspace; actual deletion remains an author action unless separately approved. The failed empty bundle is retained as evidence.
- **Disposition:** Resolved through the approved E-002 OAuth flow and exact official SLSA attestation verification; no checksum-only exception was used.

## E-002 detail

- **Necessity:** Required to identify/create the correct private repository, clone/push/open the unmerged PR, pass TC-02/GH gates, and retrieve the uv attestation.
- **Security/data risk:** The official device flow granted a persistent OAuth token. GitHub CLI reported secure OS keyring storage; no PAT or SSH key was created and the token was never displayed.
- **Rollback plan:** No automatic logout or credential deletion is authorized. If later requested, the exact credential/config target would be inventoried and a separate approval obtained before removal.
- **Disposition:** Explicitly authorized by Michael Thiessmeier; completed through the official flow with secure storage verification and no persistent Git credential helper.

## Resolution evidence (2026-08-23T00:11:11.7241065-04:00)

- E-002: OAuth device flow completed for the expected personal account. GitHub CLI reports secure keyring storage; boolean inspection found no plaintext token field. The prompt to configure Git credentials was declined; no persistent Git credential helper was added.
- E-001: gh attestation verify --repo astral-sh/uv --format json passed for SHA-256 4c4d49d8738847d9b71ba319e49a5688c93eac0fe6204b1df24e98528dddf39a with SLSA provenance. Full verification is retained privately. uv remained unexecuted until this resolution was recorded.

## 2026-11-21 · Frozen dependency audit

The unchanged accepted lock reports 83 advisory entries across six distributions in a fresh audit. The builder retained all IDs and fix-version lists, including repeats, in the local reviewer packet. Dependency updates fall outside the continuation's locked-toolchain scope. Before merge, the owner and reviewer must disposition the findings under the project dependency policy. A separate reviewed lock change can be built and tested inside a new environment. The existing environment can be retained throughout. No host software change, paid resource or cleanup is required.

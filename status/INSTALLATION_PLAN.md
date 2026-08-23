# PACD Bootstrap Installation Plan

**Recorded before download/install:** 2026-08-23T00:00:49.3529527-04:00

| Product | Version | Official source | Publisher | License | Scope | Expected disk use | Reason |
|---|---|---|---|---|---|---|---|
| GitHub CLI | 2.98.0 stable | `https://github.com/cli/cli/releases/tag/v2.98.0` and versioned Windows amd64 ZIP/checksum assets | GitHub | MIT | Workspace-local portable under `var/cache/tools/gh/2.98.0`; no persistent PATH change | Under 150 MB including archive/extraction | Required for authenticated repository selection, branch delivery, and PR gate |
| uv | 0.12.5 stable | `https://github.com/astral-sh/uv/releases/tag/0.12.5` and versioned Windows x86_64 MSVC ZIP/checksum assets | Astral Software, Inc. | Apache-2.0 OR MIT | Workspace-local portable under `var/cache/tools/uv/0.12.5`; no persistent PATH change | Under 150 MB including archive/extraction | Required for isolated Python, lock, sync, and reconstruction gates |

Archives will be saved only under `var/downloads`, hashes will be checked against official release checksums or release metadata, and extraction will occur only into new versioned directories. No installer, elevation, registry change, service, reboot, global/user PATH change, or pre-existing software modification is planned.

A stable Python 3.13 runtime will be planned separately after uv is verified and its install behavior can be inspected. No prerelease runtime is authorized.

**Official release API confirmation (2026-08-23T00:01:37.7847911-04:00):** GitHub CLI v2.98.0 and uv 0.12.5 are stable (prerelease=false). Declared archive sizes are 15,035,669 bytes and 20,329,591 bytes respectively. The uv plan was corrected from the stale indexed 0.12.1 result before download.

| CPython managed runtime | 3.13.15 stable (cpython-3.13.15-windows-x86_64-none) | astral-sh/python-build-standalone release 20260814; uv official catalog/mirror | Python Software Foundation / Astral managed distribution | Python-2.0 plus bundled component licenses; legal sufficiency not asserted | uv-managed default per-user runtime directory; --no-bin --no-registry; download cache under workspace | 21,936,392-byte archive; under 250 MB installed/cache estimate | Required pinned interpreter; existing Python 3.12 remains unchanged |

Published archive SHA-256: 07c977bbe4abad07e3bbc314608633e6c74eab482a7bae81f4361cda970b45e6. Exact archive and GitHub/Sigstore attestation will be verified before uv python install; installation will not use --upgrade, --reinstall, --force, --default, or a registry/bin shim.

## Project-local dependency environment

**Recorded before lock/sync:** 2026-08-23T00:23:31.6670537-04:00

| Component set | Requested constraints | Official source | Scope | Expected disk use | Reason |
|---|---|---|---|---|---|
| PACD simulation runtime | matplotlib>=3.10; networkx>=3.4; numpy>=2.2; pandas>=2.2; pyarrow>=19; pydantic>=2.10; PyYAML>=6.0.2; scipy>=1.15; simpy>=4.1 | Python Package Index (`https://pypi.org/simple`) through uv | New repository-local `.venv` and workspace-local uv cache only | Under 2 GB combined | Deterministic synthetic simulation, validation, metrics, and artifact serialization |
| PACD development and acceptance tooling | bandit>=1.8; detect-secrets>=1.5; hypothesis>=6.130; mypy>=1.15; pip-audit>=2.8; pre-commit>=4.2; pytest>=8.3; pytest-cov>=6.0; ruff>=0.11 | Python Package Index (`https://pypi.org/simple`) through uv | Same new `.venv`; no global installation or persistent PATH change | Included in the under-2-GB estimate | Required quality, security, type, reconstruction, and acceptance gates |

uv will resolve and pin exact transitive versions in `uv.lock` using the verified CPython 3.13.15 runtime, then perform a frozen sync into the new `.venv`. Existing Python installations and environments will not be inspected for packages or modified. Package metadata will be exported after sync for exact version, source, and declared-license inventory; the inventory is informational and does not assert legal sufficiency.

## Clean reconstruction acceptance environment

**Recorded before sync:** 2026-08-23T01:38:28.9037259-04:00

The same exact `uv.lock`, verified CPython 3.13.15 runtime, official-PyPI artifact cache, declared licenses, and dependency purposes above will be synchronized offline into the new task-only `%WORKSPACE_ROOT%\var\tmp\reconstruction-venv-final` environment. Expected additional disk use is under 500 MB. This separate environment exists only to establish TC-05 from a clean target without deleting or altering the primary `.venv`, any global package state, or any pre-existing environment. It will be retained as ignored local acceptance evidence; no persistent PATH or registry change is authorized.

## Completion reconciliation

The plan was executed without scope expansion. GitHub CLI 2.98.0 and uv 0.12.5 remained workspace-local; CPython 3.13.15 remained a separate uv-managed runtime with no bin shim or registry registration; the primary `.venv` and clean reconstruction environment each installed the same 73 locked packages. The reconstruction ran offline and passed all 108 tests. No administrator elevation, reboot, service, scheduled task, persistent PATH change, global package mutation, paid service, container, GPU, or cloud resource was used.

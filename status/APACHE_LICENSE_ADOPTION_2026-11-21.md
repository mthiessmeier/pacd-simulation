# Apache 2.0 adoption — November 21, 2026

## Authority and scope

Michael Thiessmeier confirmed his authority as licensor and explicitly selected Apache 2.0. Decision D-017 records the approved choice. This change implements that instruction; no further license/authority confirmation is required.

The grant covers the simulator work identified in LICENSING.md. Separate books, commercial material, original research exports, handoff archives and status/provenance records retain their separate status. Software simulation/evidence controls are not added as downstream license restrictions.

Source for the change: PR13 head ebcf8fd6af87c5c5ed7f83ce6359c9a09a0a2109, based on accepted main f881f6553e9210d84e8f009a9700c0ce65eceabd. No runtime file or dependency requirement is modified.

## License provenance

- Canonical source: https://www.apache.org/licenses/LICENSE-2.0.txt
- ASF website source mirror: https://github.com/apache/www-site/blob/main/content/licenses/LICENSE-2.0.txt
- Retrieved Git blob: d645695673349e3947e8e5ae42332d0ac3164cd7
- LICENSE bytes: 11358
- LICENSE SHA-256: cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30
- The added LICENSE is byte-identical to the retrieved canonical text and the installed standard Apache-2.0 reference. Copyright attribution is recorded separately in NOTICE; the canonical text is unmodified.

## Validation environment

Packaging validation used an isolated task-only virtual environment with CPython 3.13.5 and uv_build 0.12.5, satisfying the existing build requirement >=0.11.32,<0.13. No simulator runtime dependencies were installed or changed. Existing host tools were not upgraded or reconfigured.

The official PyPI uv_build wheel was independently downloaded and checked against its published SHA-256; the installed shim and binary match that verified wheel:

- Distribution: uv_build-0.12.5-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
- Source metadata: https://pypi.org/pypi/uv_build/0.12.5/json
- Download bytes: 1597895
- SHA-256: 1e0bf8d15464358a093165b342f0c3ceddf4c3f8d9eea9d3e4d7d4c506e72f80

## Observed checks

- PASS: pyproject.toml parses; its only changes are the SPDX license expression and the three declared license files. All dependency requirements and other metadata remain unchanged.
- PASS: CITATION.cff parses as YAML and agrees with the author, project version and license; it invents no DOI or release date.
- PASS: LICENSE_PENDING.md, AGENTS.md and the prior proposal consistently recognize the completed owner decision.
- PASS: standard PEP 517 build_sdist and build_wheel hooks completed with uv_build 0.12.5.
- PASS: both artifacts report License-Expression: Apache-2.0 and License-File entries for LICENSE, NOTICE and LICENSING.md.
- PASS: both artifacts contain those three files byte-identically; the wheel identifies Michael Thiessmeier as author.
- PASS: all 63 packaged Python module files match the pinned source bytes; wheel CRC validation passes.
- PASS: a separate read-only reviewer inspected the changed files and independently reopened both artifacts, confirming the metadata, included licensing files and unchanged module contents. No material finding remained.

The first direct backend invocation failed because the task-local executable directory was not on that process's PATH. Supplying the virtual environment's bin directory in the build process environment resolved it. No project or global PATH setting was changed. The successful checks above follow that corrected invocation.

## Artifact identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| pacd_simulation-0.1.0.tar.gz | 109636 | d8871abb0119fc12b7c53b661223647e13fb2cf020ed8b96347d894048bfef5b |
| pacd_simulation-0.1.0-py3-none-any.whl | 134071 | 4c776a272e3a7747707948723f292a833fdea8ebbe03ca9b7b58d781cb995bd7 |

The source distribution and wheel were built to validate licensing metadata and packaging. They are not a public release or a complete evaluator work-sample export. The current README still documents the earlier accepted evaluation route; fresh public reproduction remains separate preparation.

## Limits and delivery

Simulator runtime tests, full dependency-license review, public-export tests and publication clearance: UNEXECUTED / NOT ISSUED in this licensing task. No empirical approval or effectiveness claim is created.

The change is delivered through an additive update to PR13 with an expected-head lease. The final commit and verified remote hashes belong in the PR metadata after publication of the private branch. Leave the PR unmerged under the repository workflow; the repository remains private.

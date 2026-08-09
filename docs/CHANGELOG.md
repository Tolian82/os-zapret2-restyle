# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

## [Unreleased]

### Added

- Added immutable normalized Python `CandidateSpec` evidence for every automated
  candidate attempt, including stable identity, ordered Lua actions and arguments,
  protocol/L3/L7/payload/range data, resource classes, provenance, cost/complexity and
  exact rendered runtime arguments.
- Added one job-scoped `ResourceInventory` snapshot of installed Zapret2 Lua and fake-file
  resources, built-in BLOBs and inline capability at job initialization.
- Added a validated native Zapret2 TLS 1.3 DAG with seven reconnaissance seeds, sixteen
  expansion nodes, stable graph evidence and exact built-in/external golden candidates.
- Added validated job-scoped search-epoch evidence and locked atomic timing telemetry for
  DNS, stages, candidates, stability attempts and job execution through mandatory
  restoration.

### Changed

- Began the adaptive-search implementation with `_28`: Stage-50 `accepted` evidence now
  prioritizes matching Stage-60 catalog families but no longer excludes the remaining
  families. An all-rejected Stage-50 result therefore still enters bounded Stage-60
  candidate testing instead of reporting zero candidates solely because no family was
  accepted.
- Continued the adaptive-search implementation with `_29`: Python now selects only the
  candidate's declared Lua/resources/ranges and renders the exact dvtws2 argument file;
  active shell candidate adapters retain FreeBSD/IPFW/dvtws2 lifecycle mutations but no
  longer choose Lua, BLOB, range or search policy.
- Continued the adaptive-search implementation with `_30`: active Stage 50/60 now plans
  from the native DAG instead of flat TSV policy, semantically skips only candidates with
  missing declared resources, and preserves candidate-defined `-d8`, `-d10` or absent
  ranges through runtime, stability and final profile output.
- Continued the adaptive-search implementation with `_31`: every Stage-60 PASS/FAIL now
  selects the next reachable graph neighbor, Stage 40 pins one endpoint set for all
  candidate/final replay, and normal discovery/publication stops at three winners while
  preserving truthful smaller results.

### Verification

- Published and owner-tested `v0.4.0_2` on OPNsense. Standard job `job.2HVQqr` against
  `discord.com` produced `accepted=[]` at Stage 50, still attempted all 14 current
  Stage-60 catalog candidates, and passed Stage-90 restoration with no temporary IPFW
  rule from `19100–19131`. Truthful `NO_CANDIDATE` does not invalidate the `_28`
  reachability/restoration PASS.
- `_29` adds focused CandidateSpec/ResourceInventory, adapter-boundary and package-content
  regressions. It makes no new owner-live PASS claim; `v0.4.0_2` remains the latest
  published and owner-tested testing candidate.
- `_30` adds focused graph/golden/resource/range coverage on Linux and FreeBSD 15 plus
  package inspection for `search_graph.py`. It makes no new publication or owner-live
  claim; `v0.4.0_2` remains the latest published and owner-tested testing candidate.
- `_31` adds focused live-planner/search-epoch/three-winner/timing coverage, verifies
  candidate DNS removal and bound Stage-40 requests, and inspects both new modules in the
  FreeBSD package. It changes no timeout or owner-live claim; `v0.4.0_2` remains the
  latest published and owner-tested testing candidate.

## [0.4.0] - 2026-08-09

### Added

- Added Strategy Lab as an asynchronous Diagnostics workflow with start/status/cancel/
  result handling, persisted progress/events, bounded stages, candidate isolation,
  stability/replay validation, shortlist output, circular testing, and exact service
  restoration.
- Added Standard and Extended protocol evidence for TLS 1.3, TLS 1.2, HTTP, fixed QUIC
  capability and validated generic UDP paths, with target normalization and IPv4/IPv6
  capability handling.
- Added Python 3.13 as the packaged automated Strategy Lab orchestration runtime while
  retaining audited FreeBSD system mutations and private circular-session state behind
  narrow shell boundaries.
- Added comprehensive corrective, integration, repository-hygiene, FreeBSD 15 package,
  migration-continuity, and live-regression contracts.

### Changed

- Migrated automated Strategy Lab ownership from the first-generation shell worker to
  structured Python state, stage orchestration, request/probe execution, candidate
  search, replay, result construction, and Diagnostics status reconciliation.
- Hardened cancellation, stage/terminal semantics, deadline containment, restoration,
  candidate ownership, eligibility, persisted reload, retention, progress localization,
  Settings coordination, and package/repository CI.
- Approved the next native-Zapret2 adaptive-search architecture and A/B/C cold/warm
  measurement plan without changing the v0.4.0 executable search behavior.
- Replaced the blanket all-row stable-release live gate with release-specific risk-based
  row selection while retaining the complete 18-row matrix as regression inventory.

### Fixed

- Corrected the post-migration Stage-50 aggregator so a candidate-local structured
  failure rejects that candidate instead of aborting the family screen.
- Increased the DNS request deadline and enclosing Stage-40 envelope so real FreeBSD
  resolver latency no longer causes the observed false timeout at two seconds.

### Verification

- Source, focused regression, complete corrective-matrix and FreeBSD 15 package checks
  qualify the `_27` source used for this release.
- Owner live Scenario 1 on `v0.3.3_27` passed Stages 40, 50, 60, 70 and exact Stage-90
  restoration; terminal `NO_CANDIDATE` was truthful.
- Scenario 1 is the risk-selected mandatory live row for v0.4.0. Matrix rows 2–18 remain
  pending regression coverage and are not claimed as PASS.

### Distribution

- Advanced `VERSION` from the `0.3.3` testing line to `0.4.0` and reset
  `PLUGIN_REVISION` from `27` to `1`.
- Published immutable release tag `v0.4.0` and package
  `os-zapret2-restyle-0.4.0_1.pkg` for `FreeBSD:15:amd64` with the matching checksum and
  Pages/pkg repository.
- The owner installed `0.4.0_1` on OPNsense after publication.

## [0.3.2] - 2026-08-03

### Changed

- Added `docs/GITHUB_PUBLICATION.md` to the mandatory documentation reading order and
  made it the final specialist authority before GitHub mutation.
- Replaced the normal Draft → Ready publication path with one ready pull request and one
  complete check set for the unchanged final commit.
- Required the exact package-candidate pull-request title to be computed before the PR
  is opened.
- Distinguished the PR title `v<VERSION>_<PLUGIN_REVISION>: ...` from the release
  squash subject `release: prepare v<VERSION>`.
- Required multi-file GitHub/API publication through one set of blobs, one tree, and one
  atomic commit instead of sequential contents-API commits.
- Required failed delivery cycles to be closed and replaced with a new clean cycle
  rather than repaired through commits, title edits, Ready transitions, repeated
  retriggers, or force-push.
- Added explicit delivery-stage and release-authorization gates.
- Made release progression forward-only: published tags, releases, assets, and versions
  remain immutable and are never rolled back, replaced, or reused.
- Required complete tag, workflow, package, checksum, Pages, and pkg-repository
  verification before installation commands are provided.

### Verification

- Recorded the project owner's successful live verification of release/package
  `v0.3.1` / `os-zapret2-restyle-0.3.1_1.pkg`.
- Closed DIAG-002 as resolved and live verified.
- Confirmed that v0.3.2 changes governance and documentation only; runtime behavior
  remains the accepted v0.3.1 implementation.

### Distribution

- Advanced `VERSION` from `0.3.1` to `0.3.2`.
- Kept/reset `PLUGIN_REVISION` at `1` for the new version.
- Expected immutable tag: `v0.3.2`.
- Expected package: `os-zapret2-restyle-0.3.2_1.pkg`.

## [0.3.1] - 2026-08-03

### Fixed

- Fixed Test Domain Connectivity clearing its result field when curl reported a
  timeout, connection reset, TLS failure, DNS failure, connection refusal, or another
  non-zero connectivity result.
- Preserved the existing complete DNS, HTTPS, timing, and final-classification report
  for both positive and negative probes.
- Added an explicit API error when configd returns no diagnostic output instead of
  reporting an empty string as successful data.

### Verification

- Added a focused mocked diagnostic contract test for timeout, connection reset,
  generic curl failure, invalid input, and the MVC empty-response guard.
- Added the focused test to CI alongside shell syntax, PHP syntax, and FreeBSD package
  build validation.
- Project-owner live verification of package `0.3.1_1` completed successfully on
  2026-08-03; everything in the release was reported working correctly.

### Distribution

- Advanced `VERSION` from `0.3.0` to `0.3.1`.
- Reset `PLUGIN_REVISION` from `2` to `1`.
- Published immutable tag `v0.3.1` and package
  `os-zapret2-restyle-0.3.1_1.pkg` through the GitHub Release and Pages/pkg pipeline.

## [0.3.0] - 2026-08-03

### Added

- Added a native collapsible **Zapret2 Service** section to the Settings page with:
  - Started, Stopped, and Error state;
  - active bol-van/zapret2 stable tag;
  - Start/Stop control;
  - the four latest stable upstream releases;
  - Apply for install, reinstall, upgrade, and downgrade;
  - asynchronous setup polling and failure notification.
- Added `setup.sh show` to return up to the four latest published stable releases.
- Added `setup.sh install VERSION` for exact stable-release installation,
  reinstallation, upgrade, and downgrade.
- Added latest-stable behavior for setup without an explicit version.
- Added a validated stable-release cache at
  `/var/db/zapret2-restyle/releases.cache` with one-hour freshness, locked refresh,
  atomic replacement, stale fallback, and malformed-response protection.
- Added the active-release marker
  `/var/db/zapret2-restyle/runtime.release` so candidate Git HEAD cannot be displayed
  as installed before activation succeeds.
- Added `setup_transaction.sh` as the managed GUI transaction boundary around the
  existing setup backend.
- Added focused behavioral coverage for successful selected-release activation and
  rollback of Git commit, binaries, active tag, permissions, and service state.

### Changed

- Kept `setup.sh` as the authoritative release discovery, dependency, checkout,
  compilation, and service-refresh backend.
- Routed GUI-selected release operations through
  `setup_launcher.sh → setup_transaction.sh → setup.sh → zapret_service.sh`.
- Made the active release marker authoritative during a running setup operation.
- Imposed `umask 022` for managed release checkout and build operations.
- Normalized Lua/blob data to `0644`, runtime directories to `0755`, and compiled
  runtime executables to `0755`.
- Preserved Started/Stopped state through package replacement and selected upstream
  release operations.

### Fixed

- Fixed configd parameter mismatch for selected setup releases.
- Fixed false GUI launch success before setup completion.
- Fixed operation polling, release-cache handling, passive discovery errors, cold-start
  firewall preparation, forced package replacement, runtime Lua permissions, candidate
  tag display, and failed candidate activation rollback.

### Live verification

- Verified release-cache reuse, cold reboot, forced package replacement while Started
  and Stopped, stopped selected-release installation, and running GUI downgrade.
- Verified active tag markers, required file permissions, and no requirement for a
  reboot or manual service restart after successful operations.

### Distribution

- Advanced `VERSION` to `0.3.0` and reset `PLUGIN_REVISION` to `1`.
- Published package `os-zapret2-restyle-0.3.0_1.pkg` and the matching repository.

## [0.2.5] - 2026-08-01

### Fixed

- Added a replacement `+PRE_INSTALL` hook so package upgrade stops and verifies the
  installed service before file replacement and restores only a previously running
  service.
- Made `setup.sh install` refresh replacement runtime code before reporting ready.

### Engineering workflow

- Automated the release tag handoff after a canonical release-preparation merge.
- Added repository-root `AGENTS.md`, mandatory documentation recovery, and csh command
  preflight.

### Distribution

- Published tag `v0.2.5`, package `0.2.5_1`, checksums, and the matching Pages/pkg
  repository.

## [0.2.4] - 2026-08-01

### Fixed

- Closed lifecycle-lock descriptor 9 before launching long-lived dvtws2 and supervisor
  daemons, preventing later lifecycle operations from remaining blocked.

### Distribution

- Published tag `v0.2.4`, package `0.2.4_1`, checksums, and the matching Pages/pkg
  repository.

## [0.2.3] - 2026-07-31

### Fixed

- Required exact configd `OK` for Settings Apply and service reconfigure.
- Made service lifecycle regenerate configuration before start and reconfigure.
- Preserved persistent model, template, and runtime state on failed Apply.

### Changed

- Closed Milestone 7 while retaining unperformed checks as regression backlog.
- Opened Milestone 8 for upstream runtime management.
- Standardized OPNsense instructions on root csh.

### Distribution

- Published tag `v0.2.3`, package `0.2.3_1`, checksums, and the matching Pages/pkg
  repository.

## [0.2.2] - 2026-07-30

### Fixed

- Replaced obsolete split HTTP/HTTPS strategy guidance with unified Traffic Strategy
  guidance.
- Marked `scripts/verify-release-package.sh` executable.

### Changed

- Added `docs/GITHUB_WORKFLOW.md` and made `docs/INDEX.md` the documentation recovery
  entry point.

### Release validation

- Published tag `v0.2.2`, package `0.2.2_1`, and the updated Pages/pkg repository.

## [0.2.1] - 2026-07-29

### Fixed

- Corrected the pkg repository URL from `pkg+https://` to ordinary `https://`.
- Preserved the approved unsigned repository configuration.

## [0.2.0] - 2026-07-29

### Added

- Added normalized expansion of strategy profiles containing multiple HOSTLIST/IPSET
  placeholders.
- Added one generated runtime profile per unique target while preserving shared
  strategy parameters.
- Added project-owned OPNsense pkg repository updates.

### Changed

- Unified strategy normalization and runtime profile generation.
- Preserved user-authored `--new` boundaries.

### Distribution

- Published tag `v0.2.0` and package `0.2.0_1`.

## [0.1.0] - 2026-07-28

### Added

- Independent project identity and versioning.
- Modular Backend v2, unified Traffic Strategy, HOSTLIST/IPSET target registry,
  validation, blob resolution, port extraction, generated dvtws2 arguments,
  transactional activation, launcher/supervisor separation, firewall lifecycle,
  execution stages, and field-level GUI errors.
- Project requirements, architecture, roadmap, development state, and release
  infrastructure.

### Infrastructure

- Added GitHub Release package/checksum publication and the GitHub Pages
  FreeBSD:15:amd64 pkg repository.
- Updated GitHub Actions to Node.js 24-capable versions.

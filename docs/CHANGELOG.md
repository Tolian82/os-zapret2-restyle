# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

## [Unreleased]

### Added

- Added the asynchronous Strategy Lab start/status/cancel/result job framework.
- Added detached worker launch, one-active-job state, atomic `status.json`, ordered
  `events.ndjson`, per-job logs, PID files, and cancellation markers.
- Added four configd actions and four Diagnostics API actions.
- Added a dormant Diagnostics progress/Stop shell while preserving the current
  synchronous Blockcheck user path.
- Added focused mocked contract coverage for job lifecycle, busy handling, cancellation,
  bilingual skipped messages, state cleanup, and legacy-path preservation.

### Changed

- Advanced Strategy Lab implementation from documentation-only planning to the first
  package code patch.
- Preserved exact cancellation output `SKIPPED — отменено` and
  `SKIPPED — canseled`.
- Kept network tests, Zapret2 lifecycle mutation, temporary candidate runtime, and
  firewall changes outside Patch 2.

### Distribution

- Kept `VERSION=0.3.2` and advanced `PLUGIN_REVISION` from `3` to `4`.
- Package candidate: `os-zapret2-restyle-0.3.2_4.pkg`.
- This patch does not create a project release or publish package assets.

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

# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

## [Unreleased]

### Fixed

- Added a replacement `+PRE_INSTALL` hook so package upgrade stops and verifies the
  installed service before the old package hook and file replacement, aborts on stop
  failure, and restarts only a service that was running before the upgrade.
- Made `setup.sh install` refresh the service through configd after verifying dvtws2
  and before recording setup state as ready.
- Added focused CI coverage for package-upgrade state transfer and setup activation.

### Changed

- Incremented package revision to `0.2.4_2` without changing project VERSION.

### Engineering workflow

- Automated the normal release tag handoff after a verified release-preparation merge
  that changes VERSION and uses the canonical release subject.
- Added an idempotent GitHub Actions trigger that creates the immutable annotated tag
  and explicitly dispatches the existing Release workflow without an owner-side Git
  command.
- Retained direct tag push only as an emergency fallback and added focused CI contract
  coverage for the automated path.
- Added repository-root `AGENTS.md` so repository-aware agents encounter the
  mandatory documentation preflight before normal project work.
- Required explicit reading of the approved methodology and principles in
  DECISIONS.md, WORKING_CONVENTIONS.md, and DEVELOPMENT_GUIDE.md rather than relying
  on chat context, memory, or summaries.
- Made documentation recovery a blocking response preflight rather than an advisory
  reminder.
- Added an explicit csh dialect check for every OPNsense command block.
- Added an authorized-release runbook that preserves one-time release approval across
  transport fallback and supplies a canonical csh-safe tag trigger when an external
  credential boundary genuinely remains.

## [0.2.4] - 2026-08-01

### Fixed

- Closed lifecycle-lock descriptor 9 before launching the long-lived dvtws2 and
  supervisor daemons, preventing a completed start from permanently blocking later
  Apply and service operations with status 75.
- Added a focused regression test for both daemon launch sites and child-process
  descriptor isolation.

### Changed

- Made publication capability discovery and transport fallback mandatory: GitHub
  integration/API first, authenticated ordinary Git second, and GitHub CLI when
  available.
- Explicitly prohibited treating missing `gh` as a blocker while another approved
  authenticated publication path is available.
- Defined local preparation as incomplete until branch, PR, CI, merge, and `main`
  verification finish; release assets still require explicit release authority.

### Distribution

- Advanced `VERSION` to `0.2.4` and reset `PLUGIN_REVISION` to `1` for the immutable
  prerelease tag and package `os-zapret2-restyle-0.2.4_1.pkg`.
- Published tag `v0.2.4`, the verified package and SHA256SUMS release assets, and the
  matching FreeBSD:15:amd64 Pages/pkg repository.

## [0.2.3] - 2026-07-31

### Fixed

- Required the exact configd `OK` response so `Error (N)` can no longer be
  reported as a successful Settings Apply or service reconfigure.
- Made the service lifecycle regenerate zapret.conf from saved OPNsense settings
  before start as well as reconfigure, preventing stale boot configuration.
- Kept failed Apply transactional by restoring the previous persistent model and
  generated template while preserving the previous live runtime.
- Added a focused configuration-activation regression test.

### Changed

- Made working branch → one atomic commit → Draft PR → CI → Ready → squash merge
  the standing default for ordinary requested development changes, without repeated
  publication or merge confirmations.
- Defined explicit analysis-only, patch-only, branch-only, and PR-only requests as
  narrower stopping points that override the default delivery cycle.
- Made one explicit release request sufficient authority for the complete verified
  release pipeline while retaining stop boundaries for ambiguity, unpublished local
  state, failed gates, new authority, destructive work, and history rewriting.
- Allowed automatic cleanup only of the temporary branch created for the completed
  task; pre-existing owner branches and other remote objects remain protected.
- Defined deterministic package-revision handling and one consolidated blocking
  question only when repository, GitHub, CI, documentation, and diagnostics cannot
  supply the required answer.
- Kept package metadata unchanged for governance-only documentation changes outside
  package contents while using standard CI, including its package job, as the build
  and verification stage.
- Made the exact current GitHub commit the authoritative baseline for normal
  development.
- Removed the mandatory owner-supplied archive for repository state already
  committed and pushed to GitHub.
- Retained archives and unified patches only for explicitly transferred
  unpublished local state or when that delivery mode is requested.
- Defined one atomic multi-file commit per logical change and explicit
  fast-forward approval for direct publication to `main`.
- Made working branches and pull requests optional and removed GitHub CLI as a
  mandatory workflow dependency.
- Closed Milestone 7 by project-owner decision while retaining unperformed lifecycle, reboot, controlled-failure, timeout-chain, and GUI/API checks as a regression backlog.
- Opened Milestone 8 with GUI management of bol-van/zapret2 stable releases through the existing setup.sh backend as the first priority.
- Added the later GUI task for an additional BLOB repository without inventing its repository or technical contract.
- Standardized OPNsense console instructions on csh, with explicit `sh` and `exit` boundaries when POSIX shell is required.
- Standardized normal Git verification on `git status --short`, `git diff --check`, and `git diff --stat`.
- Updated release-facing version, repository-signing, package-version-source, and
  maintained-version documentation for the v0.2.3 prerelease.

### Distribution

- Advanced `VERSION` to `0.2.3` and reset `PLUGIN_REVISION` to `1`.
- Published package name: `os-zapret2-restyle-0.2.3_1.pkg`.
- Published annotated tag `v0.2.3` at commit `da3d8e7`.
- Completed the release workflow successfully, including validation, FreeBSD package
  and repository build, GitHub Release publication, and GitHub Pages deployment.
- Published `os-zapret2-restyle-0.2.3_1.pkg` and `SHA256SUMS` as GitHub Release assets
  and updated the FreeBSD:15:amd64 pkg repository with the same package.
- Kept this release as a prerelease until focused invalid Apply, valid Apply, and
  reboot verification is completed on OPNsense.
- Preserved immutable release `v0.2.2` and its verified `0.2.2_1` package.

## [0.2.2] - 2026-07-30

### Fixed

- Replaced obsolete Settings and Diagnostics guidance that referenced removed HTTP/HTTPS Strategy fields.
- Directed blockcheck results to the unified Traffic Strategy field and warned against blindly replacing existing multi-profile strategies.
- Marked `scripts/verify-release-package.sh` executable so release verification can be invoked directly.

### Changed

- Reset the package revision to `1` for project version `0.2.2`.
- Established unified Git `.patch` files, `git apply --check`, full diff review, and Git-based application as the default remote change-delivery workflow.
- Prohibited direct console editing of tracked project files during normal remote development.
- Added `docs/GITHUB_WORKFLOW.md` for commit, push, release asset, pkg repository, and publication procedures.
- Made `docs/INDEX.md` the mandatory documentation recovery entry point.
- Established owner-supplied `os-zapret2-restyle-<short_commit_sha>.tar.gz` archives as the authoritative baseline for multi-file patch preparation.

### Release validation

- Published `main` and annotated tag `v0.2.2` at commit `fc6b208`.
- Built and verified `os-zapret2-restyle-0.2.2_1.pkg`.
- Confirmed package installation and working runtime on OPNsense.
- Rebuilt and updated the GitHub Pages pkg repository for `0.2.2_1`.
- Removed inherited upstream tags `v1.6.1` through `v1.7.2` from `origin`.
- Confirmed that no source changes were made after publication and verification of the release baseline.

### Documentation

- Synchronized project state, roadmap, audit trail, devlog, and changelog with the released `v0.2.2` baseline.
- Kept the public README strategy example unchanged by explicit project-owner instruction.

## [0.2.1] - 2026-07-29

### Fixed

- Corrected the pkg repository URL from `pkg+https://` to ordinary
  `https://`.
- Fixed repository catalogue updates on OPNsense.
- Preserved `signature_type: "none"` and the `FreeBSD:15:amd64`
  repository target.

## [0.2.0] - 2026-07-29

### Added

- Added normalized expansion of strategy profiles containing multiple
  `<HOSTLIST:name>` and/or `<IPSET:name>` placeholders.
- Added one generated runtime profile per unique target while preserving the
  remaining parameters of the user-authored profile.
- Added release preparation for installation and updates through the
  project-owned OPNsense pkg repository.

### Changed

- Unified the strategy normalization and runtime profile generation pipeline.
- Preserved user-authored standalone `--new` profile boundaries while removing
  the need to add extra boundaries solely for multiple target placeholders.
- Updated the project version to `0.2.0` and reset the package revision to `1`.
- Retained the explicitly unsigned repository configuration with
  `signature_type: "none"` as the approved project distribution model.

### Distribution

- The release tag is `v0.2.0`.
- The expected package version is `0.2.0_1`.
- The expected package filename is
  `os-zapret2-restyle-0.2.0_1.pkg`.
- The repository target remains `FreeBSD:15:amd64`.
- GitHub Release and GitHub Pages must be generated from the same validated tag.

## [0.1.0] - 2026-07-28

### Added

- Independent `os-zapret2-restyle` project identity and versioning.
- Modular Backend v2.
- Unified multiline Traffic Strategy.
- Multiple strategy profiles separated by `--new`.
- Generic `<TYPE:name>` placeholder parser.
- HOSTLIST and IPSET target registry.
- Built-in targets for YouTube domains, Telegram IPv4 networks, and user domains.
- Target Mode for profiles without explicit placeholders.
- Strict domain and IPv4/CIDR validation.
- Domain wildcard normalization.
- Duplicate removal and canonical target storage.
- Global Exclude Domains handling.
- Blob resolver.
- Automatic TCP and UDP port extraction from Traffic Strategy.
- Generated dvtws2 argument file.
- Staged release validation.
- Atomic runtime activation and restoration.
- Separate launcher and supervisor responsibilities.
- ipfw divert-rule generation from extracted ports.
- Machine-readable execution-stage reporting.
- Transactional Apply with field-level GUI errors.
- Safe reconfigure that preserves the active service on candidate failure.
- Explicit native-looking Apply button in the OPNsense GUI.
- Project requirements, architecture, development-state, roadmap, and community files.

### Changed

- Replaced separate HTTP and HTTPS strategy fields with Traffic Strategy.
- Removed the separate GUI Ports field from Backend v2.
- Replaced service-specific strategy handling with generic target placeholders.
- Reworked service lifecycle around candidate build, validation, activation, and rollback.
- Started independent package metadata with:
  - `PLUGIN_NAME=zapret2-restyle`
  - `PLUGIN_VERSION=0.1.0`

### Infrastructure

- Approved a project-owned FreeBSD pkg repository on GitHub Pages for GUI installation and updates.
- Defined GitHub Release assets and checksums for the first FreeBSD:15:amd64 test release.
- Standardized user-facing command instructions into separate validation and installation blocks.

- Established `VERSION` as the single project-version source.
- Standardized project and package identity as `os-zapret2-restyle`.
- Retained `zapret` as the stable internal OPNsense service name.
- Reworked package build metadata for the independent repository.
- Reworked CI and release automation for the `main` branch and independent
  GitHub releases.
- Updated package lifecycle messages and package description.

### Fixed

- Removed the manual SSH runtime-setup requirement. This initial first-Start/Apply
  implementation was later superseded by automatic package post-install bootstrap.
- Added lifecycle action timeouts sufficient for the original one-time bootstrap path.

- Supervisor monitoring now verifies that the live PID still identifies the configured dvtws2 binary before treating the runtime as healthy.
- Removed disconnected inherited watchdog scripts so supervisor_loop.sh is the only runtime failure detector.
- Hardened launcher and supervisor PID handling so stale or reused PIDs are not treated as plugin-owned processes and cannot receive TERM or KILL.
- Made supervisor SIGKILL escalation conditional on the expected supervisor process still being present after the grace period.
- Removed the duplicate `firewall_rules_present()` declaration so firewall runtime-state checks have one canonical implementation.
- Serialized mutating lifecycle operations with a FreeBSD lockf-backed mutex and prevented stale supervisor callbacks from tearing down replacement runtime state.
- Invalid target data no longer stops a working dvtws2 service.
- Failed target preparation now reports `failed` instead of remaining `running`.
- Invalid values are no longer persisted before backend validation.
- GUI domain fields accept wildcard input.
- Normalized target values are written back to the GUI.
- Apply button text no longer depends on standard hidden JavaScript initialization.

### Release validation

- Added archive-level preflight validation of the generated package name, version,
  and project URL before GitHub Release and pkg-repository publication.


Release infrastructure preflight:
- corrected pkg catalogue output validation for current `pkg repo`;
- updated GitHub Pages artifact upload action;
- documented repository registration and GUI installation;
- explicitly marked the v0.1.0 prerelease repository as unsigned.

- Fixed the first-release CI failure caused by passing `FreeBSD:15:amd64` through
  the generic GitHub Actions artifact uploader.
- Preserved the native pkg ABI path while staging GitHub Release assets separately.
- Updated checkout and generic artifact actions to Node.js 24-capable versions.

### Project direction

- Closed Milestone 6 after the successful first official v0.1.0 release.
- Recorded the permanent split between native GitHub Pages pkg paths and flat GitHub
  Release asset staging.
- Opened Milestone 7 with priority on completing and verifying already approved
  functionality.
- Deferred general UX and design audits; interface work remains tied to actual
  functionality or demonstrated usability blockers.
- Planned migration of internal documentation into `docs/` and focused verification of
  strategy application to named HOSTLIST and IPSET targets.

## Documentation layout — 2026-07-29

- Moved engineering documentation into the `docs/` directory.
- Updated the root README documentation entry point and reading order.
- Updated CI required-file checks for the new documentation paths.
- No runtime or user-visible plugin behavior changed.
- Corrected automatic runtime bootstrap to clone bol-van/zapret2 instead of the legacy bol-van/zapret repository.

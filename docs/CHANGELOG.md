# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

## [Unreleased]

No unreleased changes.

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
  `/var/db/zapret2-restyle/releases.cache` with:
  - one-hour freshness;
  - `lockf` refresh serialization;
  - atomic replacement;
  - stale-cache fallback;
  - protection against empty or malformed API responses.
- Added the active-release marker
  `/var/db/zapret2-restyle/runtime.release` so candidate Git HEAD cannot be displayed
  as installed before activation succeeds.
- Added `setup_transaction.sh` as the managed GUI transaction boundary around the
  existing setup backend.
- Added focused behavioral coverage for successful selected-release activation and
  rollback of Git commit, binaries, active tag, permissions, and service state.
- Added architecture, audit evidence, development log, decision record, and release
  notes for the completed Zapret2 Service work package.

### Changed

- Kept `setup.sh` as the authoritative release discovery, dependency, checkout,
  compilation, and service-refresh backend.
- Routed GUI-selected release operations through:

  ```text
  setup_launcher.sh → setup_transaction.sh → setup.sh → zapret_service.sh
  ```

- Made the active release marker authoritative during a running setup operation.
- Imposed `umask 022` for managed release checkout and build operations.
- Normalized Lua/blob data to `0644`, runtime directories to `0755`, and compiled
  runtime executables to `0755`.
- Preserved Started/Stopped state through ordinary package upgrade, `pkg add -f`,
  `pkg install -f`, and selected upstream release operations.
- Preserved the existing configd watcher and replaced only its worker while new
  plugin actions were loaded.
- Reset `PLUGIN_REVISION` to `1` for project version `0.3.0`.

### Fixed

- Fixed configd `Parameter mismatch` caused by passing `install` and VERSION as two
  parameters to an action containing one `%s` placeholder.
- Fixed false API success caused by treating detached configd request acceptance as
  completed setup success.
- Fixed operation polling that could lose the setup state before `busy=1` appeared.
- Fixed repeated and fragile GitHub Releases API reads.
- Fixed passive temporary release-list failure producing a global red error modal.
- Fixed dvtws2 cold start attempting to create DIVERT4 before `ipdivert` and `ipfw`
  were prepared.
- Fixed forced package replacement leaving a previously Started service Stopped.
- Fixed selected Git checkout creating `0640 root:wheel` Lua files that became
  unreadable after dvtws2 dropped to UID/GID 65534.
- Fixed transient display of a candidate Git tag as the installed release while the
  previous process was still running.
- Fixed failed selected-release activation leaving the host stopped on the candidate
  checkout.
- Added automatic restoration of the previous upstream commit, compiled binaries,
  active tag, and complete service state after a failed candidate activation.

### Live verification

- Verified stable-release cache reuse by unchanged mtime across repeated fresh reads.
- Verified cold reboot automatically loaded ipdivert/ipfw, installed rule 19000,
  started dvtws2 and supervisor, and reached `13|13|ready|ok` without manual kldload.
- Verified `pkg add -f` while Started replaced dvtws2 and supervisor PIDs, preserved
  the configd watcher, and returned to Started before pkg completed.
- Verified `pkg add -f` while Stopped remained Stopped with no runtime processes or
  plugin-owned ipfw rules.
- Verified Stopped v1.0.3 → GUI Apply v1.0.4 produced Stopped v1.0.4.
- Verified Started v1.0.4 → GUI Apply v1.0.3 produced Started v1.0.3.
- Verified Git HEAD and `runtime.release` matched the selected tag.
- Verified required Lua files remained `0644 root:wheel`.
- Verified successful managed operations required no OPNsense reboot, manual configd
  restart, Web GUI restart, or manual Zapret restart.

### Distribution

- Advanced `VERSION` to `0.3.0`.
- Reset `PLUGIN_REVISION` from `13` to `1`.
- Expected immutable tag: `v0.3.0`.
- Expected package: `os-zapret2-restyle-0.3.0_1.pkg`.
- GitHub Release and FreeBSD:15:amd64 Pages/pkg repository are generated from the same
  validated tag.
- The existing workflow publishes the GitHub Release as a prerelease under the wider
  project release policy.

## [0.2.5] - 2026-08-01

### Fixed

- Added a replacement `+PRE_INSTALL` hook so package upgrade stops and verifies the
  installed service before the old package hook and file replacement, aborts on stop
  failure, and restarts only a service that was running before the upgrade.
- Made `setup.sh install` refresh the service through configd after verifying dvtws2
  and before recording setup state as ready.
- Added focused CI coverage for package-upgrade state transfer and setup activation.

### Distribution

- Advanced `VERSION` to `0.2.5` and reset `PLUGIN_REVISION` to `1` for the immutable
  prerelease tag and package `os-zapret2-restyle-0.2.5_1.pkg`.
- Published annotated tag `v0.2.5`, the verified package and SHA256SUMS assets, and
  the matching FreeBSD:15:amd64 Pages/pkg repository.

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
- Required explicit reading of approved methodology and principles instead of relying
  on chat context, memory, or summaries.
- Added an explicit csh dialect check for OPNsense command blocks.

## [0.2.4] - 2026-08-01

### Fixed

- Closed lifecycle-lock descriptor 9 before launching long-lived dvtws2 and supervisor
  daemons, preventing a completed start from permanently blocking later Apply and
  service operations with status 75.
- Added focused regression coverage for both daemon launch sites and child-process
  descriptor isolation.

### Distribution

- Advanced `VERSION` to `0.2.4` and reset `PLUGIN_REVISION` to `1`.
- Published tag `v0.2.4`, package `0.2.4_1`, SHA256SUMS, and the matching Pages/pkg
  repository.

## [0.2.3] - 2026-07-31

### Fixed

- Required exact configd `OK` so `Error (N)` could no longer be reported as successful
  Settings Apply or service reconfigure.
- Made the service lifecycle regenerate zapret.conf from saved OPNsense settings before
  start and reconfigure.
- Kept failed Apply transactional by restoring the previous persistent model and
  generated template while preserving the previous live runtime.
- Added focused configuration-activation regression coverage.

### Changed

- Established working branch → Draft PR → CI → Ready → squash merge as the standard
  delivery cycle.
- Closed Milestone 7 by project-owner decision while retaining unperformed checks as a
  regression backlog.
- Opened Milestone 8 with GUI management of bol-van/zapret2 stable releases through the
  existing setup backend.
- Standardized OPNsense console instructions on the default root csh shell.

### Distribution

- Advanced `VERSION` to `0.2.3` and reset `PLUGIN_REVISION` to `1`.
- Published tag `v0.2.3`, package `os-zapret2-restyle-0.2.3_1.pkg`, SHA256SUMS, and
  the matching Pages/pkg repository.

## [0.2.2] - 2026-07-30

### Fixed

- Replaced obsolete Settings and Diagnostics guidance that referenced removed
  HTTP/HTTPS Strategy fields.
- Directed blockcheck results to the unified Traffic Strategy field.
- Marked `scripts/verify-release-package.sh` executable.

### Changed

- Added `docs/GITHUB_WORKFLOW.md`.
- Made `docs/INDEX.md` the mandatory documentation recovery entry point.
- Established Git-based patch review and application conventions.

### Release validation

- Published `main` and annotated tag `v0.2.2` at commit `fc6b208`.
- Built and verified `os-zapret2-restyle-0.2.2_1.pkg`.
- Confirmed package installation and working runtime on OPNsense.
- Updated the GitHub Pages pkg repository.

## [0.2.1] - 2026-07-29

### Fixed

- Corrected the pkg repository URL from `pkg+https://` to ordinary `https://`.
- Fixed repository catalogue updates on OPNsense.
- Preserved `signature_type: "none"` and the `FreeBSD:15:amd64` target.

## [0.2.0] - 2026-07-29

### Added

- Added normalized expansion of strategy profiles containing multiple
  `<HOSTLIST:name>` and/or `<IPSET:name>` placeholders.
- Added one generated runtime profile per unique target while preserving the remaining
  parameters of the user-authored profile.
- Added release preparation for installation and updates through the project-owned
  OPNsense pkg repository.

### Changed

- Unified the strategy normalization and runtime profile generation pipeline.
- Preserved user-authored standalone `--new` profile boundaries.
- Updated the project version to `0.2.0` and reset package revision to `1`.
- Retained the approved unsigned repository configuration.

### Distribution

- Tag: `v0.2.0`.
- Package: `os-zapret2-restyle-0.2.0_1.pkg`.
- Repository target: `FreeBSD:15:amd64`.

## [0.1.0] - 2026-07-28

### Added

- Independent `os-zapret2-restyle` identity and versioning.
- Modular Backend v2.
- Unified multiline Traffic Strategy.
- HOSTLIST and IPSET target registry.
- Target Mode, strict validation, wildcard normalization, duplicate removal, and
  canonical target storage.
- Blob resolution and automatic TCP/UDP port extraction.
- Generated dvtws2 argument file and staged validation.
- Atomic runtime activation and restoration.
- Separate launcher and supervisor responsibilities.
- ipfw divert-rule generation and machine-readable execution stages.
- Transactional Apply with field-level GUI errors.
- Project requirements, architecture, roadmap, development state, and release
  infrastructure.

### Changed

- Replaced separate HTTP and HTTPS strategy fields with unified Traffic Strategy.
- Removed the separate GUI Ports field from Backend v2.
- Retained `zapret` as the stable internal OPNsense service name.
- Established `VERSION` as the single project-version source.
- Reworked CI and release automation for the independent repository.

### Fixed

- Hardened launcher, supervisor, PID identity, lifecycle locking, runtime cleanup, and
  firewall state handling.
- Prevented invalid target data and candidate generation failures from replacing a
  working runtime.
- Added wildcard GUI input, normalized GUI reload, and visible Apply behavior.

### Infrastructure

- Approved a project-owned GitHub Pages pkg repository.
- Added GitHub Release package and checksum publication.
- Preserved native FreeBSD:15:amd64 repository layout while staging flat release
  assets separately.
- Updated GitHub Actions to Node.js 24-capable versions.

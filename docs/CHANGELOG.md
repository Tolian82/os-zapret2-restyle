# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

## [Unreleased]

### Fixed

- Marked `setup_launcher.sh` executable so the `configd` setup action can launch the automatic runtime bootstrap.

### Changed

- Package revision increased to `3` for the executable launcher correction.
- Package revision increased to `2` for the package-managed lifecycle change.
- Runtime bootstrap now starts automatically from package post-install instead of the
  first Start or Apply.
- `setup.sh` is now an internal install/remove lifecycle backend.
- Real package removal automatically cleans the downloaded engine, compiled runtime,
  generated state, logs, locks, PID files, and safely removable managed dependencies.
- Upgrade/reinstallation preserves the runtime until the new package post-install runs.

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

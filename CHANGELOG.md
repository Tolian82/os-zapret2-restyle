# Changelog

Project: **os-zapret2-restyle**

All notable changes to this project are documented in this file.

The project starts its own version history at `0.1.0`.

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

- Established `VERSION` as the single project-version source.
- Standardized project and package identity as `os-zapret2-restyle`.
- Retained `zapret` as the stable internal OPNsense service name.
- Reworked package build metadata for the independent repository.
- Reworked CI and release automation for the `main` branch and independent
  GitHub releases.
- Updated package lifecycle messages and package description.

### Fixed

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

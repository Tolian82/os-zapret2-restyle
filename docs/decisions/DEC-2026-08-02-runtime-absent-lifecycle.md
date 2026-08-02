# DEC-2026-08-02 — Plugin lifecycle is valid without an installed zapret2 runtime

Status: Approved and implemented; post-install integration paragraph superseded by
`DEC-2026-08-02-safe-post-install-action-reload.md`
Date: 2026-08-02

## Decision

Installing `os-zapret2-restyle` and installing the external bol-van/zapret2 runtime
are separate states. A clean plugin installation is successful when
`/usr/local/etc/zapret2/binaries/my/dvtws2` does not yet exist.

The executable dvtws2 file is the lifecycle gate for automatic service exposure and
boot startup. When it is absent:

- the boot syshook exits successfully without invoking `configctl zapret start`;
- the OPNsense service registry does not publish Zapret as a startable service;
- dvtws2, supervisor_loop.sh, PID files, and plugin-owned ipfw rules are not created;
- package installation, configd, the Web GUI, and release discovery remain healthy.

Package upgrade continues to preserve only a complete prior runtime state. A running
runtime is restored, a stopped runtime remains stopped, and an absent runtime remains
absent.

The earlier implementation also required an unconditional final Web GUI restart from
`+POST_INSTALL`. Live package `0.2.8_7` evidence proved that requirement unsafe and it
is superseded. The canonical configd action reload and the prohibition on package-owned
Web GUI restart are now defined by the separate safe post-install decision.

## Reason

Live package `0.2.8_5` evidence showed that replacement action files were present on
disk but unavailable until configd was restarted. A clean installation may also have
no runtime tree by design; treating that normal state as a boot or supervisor failure
would make plugin installation noisy and could affect unrelated OPNsense services.

## Consequences

- Plugin-installed and runtime-installed remain distinct states.
- Runtime absence is not a package installation error.
- Manual or GUI runtime installation remains owned exclusively by `setup.sh install`.
- Direct Start still fails clearly when no executable runtime exists, but automatic
  boot and service registration do not offer that invalid operation.
- Focused tests cover clean boot without dvtws2, service registration, service runtime
  guards, supervisor guards, and upgrade state preservation.
- Post-install action loading follows the superseding safe lifecycle decision.

## Affected files and documentation

- `src/etc/rc.syshook.d/start/20-zapret`
- `src/etc/inc/plugins.inc.d/zapret.inc`
- `scripts/test-package-lifecycle-restart.sh`
- this decision record
- `docs/decisions/DEC-2026-08-02-safe-post-install-action-reload.md`

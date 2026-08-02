# DEC-2026-08-02 — Plugin lifecycle is valid without an installed zapret2 runtime

Status: Approved and implemented
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

After replacement action files are installed, `+POST_INSTALL` restarts configd before
using the new actions. It then renders the Zapret template, restores a marked running
runtime during upgrade, and refreshes the Web GUI last.

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
- Focused tests cover configd action loading, clean boot without dvtws2, service
  registration, service runtime guards, supervisor guards, and upgrade ordering.
- Package candidate advances to `0.2.8_6`.

## Affected files and documentation

- `Makefile`
- `pkg/+POST_INSTALL`
- `src/etc/rc.syshook.d/start/20-zapret`
- `src/etc/inc/plugins.inc.d/zapret.inc`
- `scripts/test-package-lifecycle-restart.sh`
- this decision record

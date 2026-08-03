# DEC-2026-08-03 — Package replacement preserves complete service state without reboot

Status: Approved and implemented
Date: 2026-08-03

## Decision

Every replacement installation of `os-zapret2-restyle` must preserve the canonical
pre-transaction Zapret service state without requiring an OPNsense reboot, manual
service restart, or any other operator recovery action.

This contract applies to ordinary version upgrades and to forced replacement paths
such as `pkg add -f` and `pkg install -f`, even when pkg does not export
`PKG_UPGRADE` to package scripts.

The incoming package's `+PRE_INSTALL` is the earliest replacement hook. When the
installed service script exists, it must classify the complete service state before
old files are removed:

- running: create `/var/run/zapret2-restyle/pkg-replacement.restart`, stop the service,
  and verify the canonical stopped state;
- stopped: preserve an existing replacement marker from an interrupted retry and do
  not create a new one;
- incomplete: remove restart intent, clean the runtime through the normal Stop path,
  and do not promote it to running;
- unknown or failed Stop: abort the package operation visibly.

The replacement marker name is intentionally different from the historical
`pkg-upgrade.restart`. Older installed `+PRE_DEINSTALL` hooks do not know the new name,
so the marker survives the first forced replacement from package `0.2.8_11` even when
`PKG_UPGRADE` is absent.

The incoming `+POST_INSTALL` restores service only when the replacement marker exists.
It reloads configd actions through the existing watcher, renders the Zapret template,
starts through `configctl zapret start`, requires exact `OK`, verifies complete running
state, and only then removes both replacement and legacy markers. A true upgrade with
an interrupted historical `pkg-upgrade.restart` marker remains supported as a
compatibility fallback.

`+POST_DEINSTALL` remains service-free and does not erase an active replacement handoff.
A stale marker from an interrupted removal is harmless: successful replacement consumes
it, while a later fresh pre-install clears it when no installed service script exists.

## Reason

Live `pkg add -f` installation of package `0.2.8_10` over a running runtime left Zapret
stopped. The existing implementation depended on `PKG_UPGRADE` in all three handoff
stages:

1. incoming `+PRE_INSTALL` exited immediately because `PKG_UPGRADE` was absent;
2. installed `+PRE_DEINSTALL` removed the historical marker and stopped Zapret;
3. incoming `+POST_INSTALL` required `PKG_UPGRADE` and therefore did not restore it.

A later reboot started Zapret through the boot syshook, but rebooting the firewall is
not an acceptable package-installation requirement. The package transaction itself
must preserve service state.

FreeBSD pkg defines the replacement ordering as incoming pre-install, installed
pre-deinstall, file replacement, and incoming post-install. The incoming pre-install
therefore provides the required state-capture boundary independently of the optional
`PKG_UPGRADE` environment variable.

## Consequences

- Package candidate advances to `0.2.8_12`.
- A running service is stopped before replacement files are installed and is started
  again with replacement code before `pkg` reports success.
- A stopped service remains stopped.
- Incomplete or unknown state is never silently promoted.
- Stop and post-install Start failures abort visibly; restart intent remains available
  for a safe retry when Start fails.
- The first forced replacement from `0.2.8_11` is backward-compatible because the old
  hook cannot erase the new marker.
- No configd watcher restart, Web GUI restart, system reboot, or manual service command
  is part of the success path.
- Focused CI executes running, stopped, incomplete, failed-stop, fresh-install,
  interrupted-retry, and legacy-hook-transition scenarios.
- Live acceptance requires `pkg add -f` over a running service to finish with new
  dvtws2/supervisor PIDs, `service=started`, `ready|ok`, configd healthy, and no reboot.

## Affected files and documentation

- `Makefile`
- `pkg/+PRE_INSTALL`
- `pkg/+PRE_DEINSTALL`
- `pkg/+POST_INSTALL`
- `pkg/+POST_DEINSTALL`
- `scripts/test-package-lifecycle-restart.sh`
- `docs/PROJECT_STATE.md`
- this decision record

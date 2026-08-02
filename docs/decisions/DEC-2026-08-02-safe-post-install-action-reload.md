# DEC-2026-08-02 — Package post-install reloads actions without restarting the Web GUI

Status: Superseded by `DEC-2026-08-02-configd-worker-action-reload.md`
Date: 2026-08-02

## Historical decision

Package candidate `0.2.8_8` attempted to reload replacement configd actions by running:

`/usr/local/etc/rc.d/configd restart`

from `+POST_INSTALL`, waiting for `configctl system status`, then continuing with
plugin cache refresh, Zapret template rendering, and running-state restoration. The
package-owned Web GUI restart from the earlier implementation was removed.

## Supersession evidence

Live installation of `0.2.8_8` on OPNsense 26.7.1_1 proved that readiness during the
package script was not sufficient. The replacement watcher and worker accepted the
readiness request, rendered Syslog and Zapret templates, and allowed `pkg add` to finish
successfully. Immediately after the package transaction ended, both replacement
configd processes were gone while stale pid/socket files remained. Lighttpd, dvtws2,
and the Zapret supervisor remained running.

The full configd restart created a new watcher inside the package process tree. That
watcher survived long enough to satisfy every hook check but did not survive completion
of the package transaction. Therefore a package hook must not create a replacement
long-lived configd watcher.

The active action-reload contract is defined by
`DEC-2026-08-02-configd-worker-action-reload.md`.

## Retained constraints

- Package lifecycle must not restart the global OPNsense Web GUI.
- Runtime installation remains separate from plugin package installation.
- A previously running Zapret runtime is restored only after replacement actions and
  templates are available.
- Stopped and absent runtime states remain unchanged.
- Live OPNsense lifecycle evidence is mandatory; behavioral mocks alone cannot prove
  survival beyond the pkg process boundary.

## Affected files and documentation

- `pkg/+POST_INSTALL`
- `scripts/test-package-lifecycle-restart.sh`
- `docs/decisions/DEC-2026-08-02-configd-worker-action-reload.md`
- this historical decision record

# DEC-2026-08-02 — Package post-install reloads configd actions through the existing watcher

Status: Approved and implemented
Date: 2026-08-02

## Decision

When replacement files are installed under
`/usr/local/opnsense/service/conf/actions.d`, `+POST_INSTALL` must not restart the
configd service and must not create a new configd watcher.

The package hook reloads action definitions by preserving the existing watcher from
`/var/run/configd.pid` and terminating only its current
`/usr/local/opnsense/service/configd.py console` worker. The pre-existing watcher
automatically creates a replacement worker. The hook then requires all of the
following before continuing:

1. the watcher PID is numeric and still alive;
2. exactly one current worker is identified as a child of that watcher;
3. `SIGTERM` is sent only to that worker;
4. the watcher remains alive;
5. a different child worker PID appears;
6. `configctl system status` succeeds through the replacement worker.

Only after those conditions pass may `+POST_INSTALL` run
`rc.configure_plugins POST_INSTALL`, render `OPNsense/Zapret`, and restore a runtime
that was fully running before package upgrade.

The package lifecycle must never signal the watcher, run
`service configd restart`, execute `/usr/local/etc/rc.d/configd restart`, or restart
the global Web GUI.

## Reason

Live installation of package candidate `0.2.8_8` on OPNsense 26.7.1_1 showed that a
full configd restart from the package hook is not safe even when a real readiness
request succeeds. The replacement worker accepted `system status`, rendered Syslog and
Zapret templates, and allowed the package script to finish, but both the replacement
watcher and worker disappeared when the `pkg add` process tree ended. Stale
`/var/run/configd.pid` and `/var/run/configd.socket` remained.

The existing configd watcher is independent of the package transaction and already
implements automatic worker replacement. A focused live test preserved watcher PID
`46333`, changed worker PID `46958` to `377`, kept `service configd status` healthy,
and immediately restored `system status`, `zapret setup_status`, and
`zapret setup_releases`. This proves the required process boundary directly on the
supported OPNsense system.

## Consequences

- Package candidate advances to `0.2.8_9`.
- New configd actions become available without creating a package-owned daemon.
- Configd watcher identity is preserved across plugin installation.
- A stale or ambiguous worker state fails visibly instead of signalling an uncertain
  process.
- Readiness requires both worker replacement and a real configd request.
- Lighttpd/php-cgi are not stopped or restarted by the plugin package.
- dvtws2 and its supervisor remain governed only by the existing upgrade state-transfer
  contract.
- The focused lifecycle test executes the hook with a pre-existing watcher model,
  verifies that only the old worker receives `SIGTERM`, rejects full configd/Web GUI
  restarts, and preserves the established runtime guards.
- The live watcher/worker replacement test is the decisive evidence; CI mocks remain
  regression coverage, not a substitute for OPNsense lifecycle verification.

## Affected files and documentation

- `Makefile`
- `pkg/+POST_INSTALL`
- `scripts/test-package-lifecycle-restart.sh`
- `docs/decisions/DEC-2026-08-02-safe-post-install-action-reload.md`
- this decision record

# DEC-2026-08-03 — Upstream runtime release activation is transactional

Status: Approved and implemented
Date: 2026-08-03

## Decision

GUI installation, reinstallation, upgrade, and downgrade of bol-van/zapret2 releases
must preserve the previously active upstream checkout, compiled binaries, displayed
release, and complete Zapret service state until the selected release has completed
its build and service activation.

`setup.sh` remains the authoritative release-selection, dependency, checkout, build,
and service-refresh backend. The GUI launcher invokes it through
`setup_transaction.sh`, which adds the transaction boundary without duplicating
release discovery or build policy.

The transaction wrapper must:

- impose `umask 022` before Git checkout and build operations;
- normalize Lua and blob data to mode `0644`, their directories to `0755`, and built
  runtime executables to `0755`;
- record the previous Git commit, active stable tag, compiled `binaries/my` tree, and
  canonical running/stopped state before invoking setup.sh;
- retain the active-release marker until the selected release has started successfully;
- publish the selected tag atomically only after setup.sh succeeds and the checkout
  resolves exactly to that stable tag;
- on failure, restore the previous Git commit and compiled binaries, normalize their
  permissions, and restore the original running/stopped state;
- leave setup status as failed after a successful rollback so the GUI reports the
  failed operation while continuing to show the restored service and release.

`setup_launcher.sh status` reads `/var/db/zapret2-restyle/runtime.release` before
falling back to `git describe`. A candidate checkout therefore cannot appear as the
installed version while an operation is still running.

## Reason

A live GUI downgrade from v1.0.4 to v1.0.3 checked out and built the candidate, then
failed during service refresh. dvtws2 dropped privileges to UID/GID 65534 and could
not read `lua/zapret-lib.lua` and `lua/zapret-antidpi.lua`, which had been recreated
as `0640 root:wheel` under the setup process umask. The GUI briefly displayed
`Started v1.0.3` because service health came from the still-running old process while
version came directly from the already changed Git HEAD.

The existing orchestrator restored only `runtime-v2` configuration after candidate
startup failure. It did not restore the upstream checkout, compiled binary, Lua tree,
or prior service process, leaving the host stopped on the failed candidate tag.

## Consequences

- Package candidate advances to `0.2.8_13`.
- Restrictive caller umasks no longer create runtime data unreadable after dvtws2
  privilege drop.
- Same-version reinstall repairs permissions before setup attempts service refresh.
- Failed selected-release activation returns to the previous release and complete
  service state without reboot or manual Start/Restart commands.
- The GUI keeps showing the active release during a running operation and reports the
  candidate only after successful activation.
- The setup log records both the candidate failure and automatic rollback outcome.
- Direct CLI execution of setup.sh remains supported; the managed GUI path uses the
  transaction wrapper as the required safe activation boundary.

## Affected files

- `Makefile`
- `src/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh`
- `src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh`
- `scripts/test-gui-runtime-management.sh`
- this decision record

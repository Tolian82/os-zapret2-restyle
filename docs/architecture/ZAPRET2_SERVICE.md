# Zapret2 Service architecture

Status: implemented and live verified
Release: v0.3.0
Date: 2026-08-03

## Purpose

The **Zapret2 Service** block on the OPNsense Settings page is the managed control
surface for the installed bol-van/zapret2 runtime. It combines service health,
Start/Stop, stable-release discovery, and selected-release installation without
creating a second release-management implementation.

## Component chain

```text
general.volt
    ↓
ServiceController.php
    ↓
configd actions
    ↓
setup_launcher.sh
    ↓
setup_transaction.sh
    ↓
setup.sh
    ↓
zapret_service.sh
    ↓
Backend v2 / dvtws2 / ipfw / supervisor
```

Responsibilities are deliberately separated:

- `general.volt` renders state, collects the selected release, disables controls
  while an operation is active, and polls runtime status.
- `ServiceController.php` validates API input and requires exact configd success.
- configd owns the OPNsense privilege boundary.
- `setup_launcher.sh` starts the long-running operation outside configd and exposes
  read-only status.
- `setup_transaction.sh` owns active-release publication and rollback.
- `setup.sh` remains the authoritative release-selection, dependency, checkout,
  compilation, and service-refresh backend.
- `zapret_service.sh` owns runtime Start, Stop, Reconfigure, status, firewall, and
  supervisor lifecycle.

## Runtime state model

The GUI receives five fields:

```text
installed=0|1
service=started|stopped|error
version=vX.Y.Z|
setup=ready|installing|failed|unknown
busy=0|1
```

`installed` is based on a usable compiled `dvtws2` binary. `service` represents the
complete plugin-owned runtime contract. `version` comes from the committed active
release marker and falls back to an exact Git tag only when the marker is absent.
`setup` records the last setup result. `busy` is derived from the live setup PID.

## Active-release truth

The active release is stored in:

```text
/var/db/zapret2-restyle/runtime.release
```

The file contains one validated stable tag and is replaced atomically. It remains on
the previous value while a candidate checkout is being compiled or activated. This
prevents a transient candidate Git HEAD from being displayed as the installed
release while an older process is still running.

## Stable-release cache

Stable release metadata is cached in:

```text
/var/db/zapret2-restyle/releases.cache
```

The cache contract is:

- only validated stable tags are stored;
- refresh is serialized by `/var/run/zapret2-restyle/releases.lock`;
- fresh cache reads do not contact GitHub;
- writes use a temporary file followed by atomic `mv`;
- empty or malformed responses never replace a valid cache;
- a validated stale cache is served when GitHub is temporarily unavailable;
- exact installation validates membership against the cache and does not repeat the
  Releases API request.

The API exposes at most the four latest stable tags to the GUI.

## Selected-release transaction

Before invoking `setup.sh`, `setup_transaction.sh` captures:

- current service state;
- active stable tag;
- current upstream Git commit;
- current compiled `binaries/my` tree.

The candidate is then selected, checked out, compiled, and refreshed by the existing
setup backend.

On success:

1. runtime file permissions are normalized;
2. the exact selected Git tag is verified;
3. the active-release marker is atomically updated;
4. rollback data is removed;
5. the original Started/Stopped state is preserved.

On failure:

1. the previous Git commit is restored;
2. the previous compiled binaries are restored;
3. runtime permissions are normalized;
4. the previous active-release marker is restored;
5. the previous Started/Stopped state is restored;
6. setup state remains `failed` so the requested operation is not falsely reported as
   successful.

## Permission boundary

`dvtws2` starts with required privileges and later runs as UID/GID `65534`. Runtime
Lua and blob data therefore must remain readable after the privilege drop.

The managed path imposes `umask 022` and normalizes:

```text
Lua/blob files        0644
runtime directories   0755
compiled executables  0755
```

This normalization occurs before setup and after candidate activation or rollback,
which also repairs restrictive modes left by older installations.

## Service-state preservation

Selected-release operations and package replacement use the same product rule:

```text
Started before → Started after
Stopped before → Stopped after
Incomplete/unknown → reject
```

A package replacement records running state before old package hooks remove or replace
files. The replacement package stops the old runtime, reloads configd actions through
the existing watcher, starts replacement code when required, verifies health, and
removes transient markers before pkg completes.

## Firewall and cold start

`ipdivert`, `ipfw`, one-pass behavior, default-accept behavior, and PF reinjection
prerequisites are prepared before `dvtws2` attempts to create its DIVERT4 socket.
This ordering is mandatory for boot and cold-start operation.

Plugin-owned divert rules are installed only after the replacement runtime passes its
startup stability window. Failure cleanup removes plugin-owned processes and rules but
does not unload shared kernel modules.

## Concurrency

- setup operations use `/var/run/zapret2-restyle/setup.lock`;
- release-cache refresh uses `/var/run/zapret2-restyle/releases.lock`;
- service lifecycle uses `/var/run/zapret2-lifecycle.lock`;
- stale supervisor callbacks use an immediate try-lock and cannot queue behind a
  replacement operation.

## Failure reporting

Primary files:

```text
/var/log/zapret2/setup.log
/var/log/zapret2/dvtws2.log
/var/log/zapret2/supervisor.log
/var/db/zapret2-restyle/setup.status
/var/run/zapret2-execution.status
```

The GUI reports setup failure after polling observes completion. The restored release
and service state remain visible when automatic rollback succeeds.

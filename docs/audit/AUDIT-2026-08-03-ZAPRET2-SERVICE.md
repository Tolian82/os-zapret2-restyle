# Audit evidence — Zapret2 Service and runtime release management

Date: 2026-08-03
Status: PASS for the v0.3.0 release scope

## Scope

This evidence closes the focused live-verification matrix for:

- cold boot and automatic firewall prerequisites;
- package replacement while Started and while Stopped;
- stable-release cache reuse;
- selected upstream release installation through the GUI;
- running/stopped state preservation;
- runtime permission normalization;
- exact active-release reporting.

## Stable-release cache

Observed:

```text
configctl zapret setup_releases
v1.0.4
v1.0.3
v1.0.2
v1.0.1
```

The cache was created at `/var/db/zapret2-restyle/releases.cache`. Two consecutive
reads returned the same list and retained the same mtime:

```text
cache mtime before=1785697995
cache mtime after=1785697995
```

Result: PASS. A fresh cache is reused without another GitHub Releases API request.

## Cold boot and firewall prerequisites

After installation of package candidate `0.2.8_11` and an OPNsense reboot, no manual
`kldload`, Start, or service restart was performed.

Observed:

```text
installed=1
service=started
version=v1.0.4
setup=ready
busy=0
```

`ipdivert` and `ipfw` were loaded, rule 19000 was installed, dvtws2 and supervisor
processes were present, and execution state reached:

```text
13|13|ready|ok|...|zapret is ready
```

The dvtws2 log showed successful DIVERT4 creation and privilege drop:

```text
creating divert4 socket
binding divert4 socket
initializing raw sockets
Running as UID=65534 GID=65534
```

Result: PASS. Firewall prerequisites are prepared before dvtws2 launch.

## Package replacement while Started

A running service was replaced with `pkg add -f` using package candidate `0.2.8_12`.

Observed:

```text
configd watcher 439 → 439
dvtws2 PID       99326 → 87537
supervisor PID   15761 → 16587
```

After pkg completed, without reboot or manual service commands:

```text
installed=1
service=started
version=v1.0.4
setup=ready
busy=0
13|13|ready|ok|...|zapret is ready
```

Rule 19000 was present. Legacy and replacement state markers were absent.

Result: PASS. Started state is restored with replacement code before pkg exits.

## Package replacement while Stopped

The service was stopped and the same package was installed with `pkg add -f`.

Observed after pkg completed:

```text
installed=1
service=stopped
version=v1.0.4
setup=ready
busy=0
```

No dvtws2 or supervisor processes and no plugin-owned ipfw rules were present.

Result: PASS. Stopped state is preserved and is not promoted.

## Selected-release failure diagnosis

The first GUI downgrade attempt from v1.0.4 to v1.0.3 checked out and compiled the
candidate but failed during service refresh.

The dvtws2 log showed:

```text
Running as UID=65534 GID=65534
LUA file '/usr/local/etc/zapret2/lua/zapret-lib.lua' ... not accessible
```

Observed file modes:

```text
-rw-r----- root:wheel lua/zapret-lib.lua
-rw-r----- root:wheel lua/zapret-antidpi.lua
```

Result: confirmed defect. Candidate checkout inherited restrictive modes and became
unreadable after dvtws2 dropped privileges.

The GUI also briefly showed `Started v1.0.3` while the old process was still running,
because service health and Git HEAD were read independently. A failed refresh left the
checkout at v1.0.3 and the service stopped.

## Permission repair and stopped-state installation

Package candidate `0.2.8_13` installed the transactional release wrapper. The service
was initially stopped on v1.0.3. Through the GUI, v1.0.4 was selected and applied.

Observed:

```text
Status: Stopped v1.0.4
git describe: v1.0.4
runtime.release: v1.0.4
```

Lua files were normalized to:

```text
-rw-r--r-- root:wheel
```

Result: PASS. Exact release changed while the intentionally stopped state was
preserved.

## Running GUI downgrade

The service was started through the GUI, then v1.0.3 was selected and applied.

Observed:

```text
installed=1
service=started
version=v1.0.3
setup=ready
busy=0
zapret is running as pid 36624
git describe: v1.0.3
runtime.release: v1.0.3
```

All checked Lua files remained `0644 root:wheel`.

Result: PASS. The running service was automatically refreshed to the selected release
without reboot, manual configd restart, manual Web GUI restart, or manual Zapret
restart.

## Acceptance result

The v0.3.0 Service scope is accepted:

- correct GUI state reporting;
- stable-release cache and fallback contract;
- exact selected-release install/reinstall/upgrade/downgrade path;
- Started/Stopped preservation;
- cold boot without manual kernel-module loading;
- package replacement without reboot or manual service work;
- runtime-safe file modes after privilege drop;
- active-release marker synchronized with the working checkout;
- candidate activation covered by automatic rollback tests.

Automatic rollback is behaviorally covered in CI. Successful selected-release
activation and all service-state paths listed above were verified on live OPNsense.

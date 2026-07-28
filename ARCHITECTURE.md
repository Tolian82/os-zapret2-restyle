# os-zapret2-restyle — Architecture

Project: **os-zapret2-restyle**

## Repository

```text
https://github.com/Tolian82/os-zapret2-restyle
branch: main
baseline tag: restyle-start
development checkout: /root/os-zapret2-restyle
```

This repository is the source of truth and is an independent project.

## Pipeline

```text
OPNsense configuration
        ↓
Config loader
        ↓
Strategy parser
        ↓
Generic placeholder index
        ↓
Target Mode resolver
        ↓
Target registry and resolver
        ↓
Exclude resolver
        ↓
Blob resolver
        ↓
Port extractor
        ↓
Argument generator
        ↓
Release validator
        ↓
Atomic activation
        ↓
Launcher
        ↓
Firewall
        ↓
Supervisor
```

## Entry points

```text
src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh
```

`zapret_service.sh` exposes service actions and sources backend modules.
`orchestrator.sh` coordinates candidate build, validation, activation,
rollback, launcher, firewall, and supervisor.

## Backend modules

- `common.sh` — shared helpers.
- `config.sh` — generated configuration and interface resolution.
- `parser.sh` — Traffic Strategy profiles and generic placeholders.
- `registry.sh` — supported target type/name registry.
- `target_mode.sh` — implicit targets for placeholder-free profiles.
- `targets.sh` — HOSTLIST/IPSET normalization, validation, files, resolution.
- `exclude.sh` — global domain exclusions.
- `storage.sh` — logical, staged, and active file mapping.
- `blobs.sh` — blob resource resolution.
- `ports.sh` — TCP/UDP extraction from strategy filters.
- `generator.sh` — final dvtws2 argument generation.
- `validator.sh` — candidate release validation.
- `atomic.sh` — active runtime switch and restore.
- `launcher.sh` — one dvtws2 process and startup stability check.
- `firewall.sh` — ipfw lifecycle.
- `supervisor.sh` — monitor lifecycle.
- `stage.sh` — execution status reporting.
- `orchestrator.sh` — lifecycle coordination.

## Runtime

Engine root:

```text
/usr/local/etc/zapret2
```

Generated active runtime:

```text
/usr/local/etc/zapret2/runtime-v2
```

Important generated files:

```text
traffic.conf
extra.conf
dvtws.args
tcp-ports.txt
udp-ports.txt
managed/*
```

Generated runtime is never committed.

## Safe reconfigure

```text
build candidate while old runtime works
        ↓
validate candidate
        ↓
failure → old PID/runtime/ipfw remain unchanged
        ↓
success → controlled switch
        ↓
post-switch failure → restore previous runtime
```

Regression input:

```text
999.999.999.999
```

Expected result is `targets|failed` while the existing service remains active.

## Transactional Apply

Important files:

```text
SettingsController.php
ServiceController.php
general.volt
Zapret.xml
targets.sh
orchestrator.sh
```

The custom Apply flow validates and normalizes before persistent save. It
returns field-specific errors or normalized values, then invokes safe
reconfigure.

## Packaging independence

No runtime dependency on another OPNsense zapret plugin is allowed.

The repository must contain every project-owned file required to build and
install `zapret2-restyle` on a clean supported OPNsense system.

External zapret2 engine acquisition/build is handled by this project's own
setup and maintenance logic.

## Engineering rules

- Correctness over speed.
- Commands to the project owner are strictly sequential.
- Read current `main` before proposing code.
- Verify OPNsense framework and rendered behavior; do not guess.
- FreeBSD `/bin/sh` compatibility.
- No Bash-only syntax.
- Minimal operational documentation.

# OPNsense Zapret2 Restyle — Architecture

## Purpose

This document is a compact maintainer and AI context snapshot. It describes how the current Backend v2 is intended to work.

## Repository model

- Primary repository: `https://github.com/Tolian82/os-zapret2-restyle`
- Working branch: `main`
- Baseline tag: `restyle-start`
- Upstream plugin remote: `https://github.com/ugorur/os-zapret2`
- The GitHub repository is the source of truth.
- Development and live testing are performed on OPNsense, with the repository located at:

```text
/root/os-zapret2-restyle
```

## High-level pipeline

```text
Generated OPNsense configuration
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

The orchestrator coordinates public module APIs. It should not duplicate parsing, normalization, launch, or firewall implementation.

## Main entry points

### Service entry point

```text
src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh
```

Responsibilities:

- source backend modules;
- define runtime paths and constants;
- expose start, stop, status, restart, and reconfigure commands;
- delegate lifecycle work to the orchestrator.

### Orchestrator

```text
src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh
```

Responsibilities:

- build staged releases;
- report stage progress;
- coordinate validation;
- activate and restore runtime trees;
- coordinate launcher, firewall, and supervisor;
- implement safe reconfigure behavior.

## Backend modules

Current module directory:

```text
src/opnsense/scripts/OPNsense/Zapret/backend/
```

- `common.sh` — shared filesystem, logging, workspace, and error helpers.
- `config.sh` — generated configuration loading and OPNsense interface resolution.
- `parser.sh` — ordered Traffic Strategy profile parsing using standalone `--new`.
- `registry.sh` — target type/name registry.
- `target_mode.sh` — default target injection for profiles without explicit placeholders.
- `targets.sh` — HOSTLIST/IPSET normalization, validation, managed files, and placeholder resolution.
- `exclude.sh` — global excluded-domain hostlist.
- `storage.sh` — logical-to-staged/active target storage mapping.
- `blobs.sh` — blob resource resolution.
- `ports.sh` — TCP/UDP port extraction from strategy filters.
- `generator.sh` — final `dvtws.args` generation.
- `validator.sh` — staged release validation.
- `atomic.sh` — runtime activation and restoration.
- `launcher.sh` — one dvtws2 instance and startup stability check.
- `firewall.sh` — ipfw preparation and divert rule lifecycle.
- `supervisor.sh` — supervisor process lifecycle.
- `stage.sh` — machine-readable stage reporting.
- `orchestrator.sh` — lifecycle coordination.

## Runtime layout

Installed engine root:

```text
/usr/local/etc/zapret2
```

Active generated runtime:

```text
/usr/local/etc/zapret2/runtime-v2
```

Important generated files:

```text
runtime-v2/traffic.conf
runtime-v2/extra.conf
runtime-v2/dvtws.args
runtime-v2/tcp-ports.txt
runtime-v2/udp-ports.txt
runtime-v2/managed/*
```

Runtime files are generated artifacts and must not be committed.

## Process and firewall model

Typical runtime components:

- one dvtws2 child process;
- one supervisor daemon/monitor pair;
- ipfw divert rules in the plugin's reserved rule range;
- dvtws2 `--sockarg=0x200` loop guard;
- privilege drop to `nobody`.

Important PID files:

```text
/var/run/dvtws2.pid
/var/run/zapret2-supervisor-daemon.pid
/var/run/zapret2-supervisor-monitor.pid
```

## Safe reconfigure design

```text
build candidate while old runtime works
        ↓
fully validate candidate
        ↓
failure → keep old PID/runtime/ipfw unchanged
        ↓
success → short controlled switch
        ↓
restore previous release if post-activation startup fails
```

Confirmed regression input:

```text
999.999.999.999
```

Expected result:

- execution stage reports `targets|failed`;
- active dvtws2 PID remains unchanged;
- active `dvtws.args` remains unchanged;
- ipfw rules remain unchanged.

## GUI and API flow

Important files:

```text
src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/SettingsController.php
src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php
src/opnsense/mvc/app/views/OPNsense/Zapret/general.volt
src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml
```

The GUI uses a custom transactional Apply endpoint instead of the standard save-then-reconfigure sequence.

The endpoint must:

- validate submitted model data;
- invoke backend target normalization/validation;
- avoid persisting invalid values;
- save normalized values on success;
- call safe reconfigure;
- return field-specific errors and normalization information.

The Apply button is explicit HTML with visible text because the standard OPNsense partial creates an empty button whose label is normally inserted by standard JavaScript.

## Engineering rules

- Correct solution over quick patch.
- Commands given to the project owner must be strictly sequential and executable in the stated order.
- Verify current `main` before proposing code.
- Do not assume OPNsense HTML structure, shell behavior, command options, or framework APIs.
- FreeBSD `/bin/sh` compatibility is required.
- Do not use Bash-only syntax.
- Keep documentation minimal and operational.

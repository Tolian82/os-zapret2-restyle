# os-zapret2-restyle — Development State

Last context update: 2026-07-28

## Source of truth

```text
https://github.com/Tolian82/os-zapret2-restyle
branch: main
baseline tag: restyle-start
current project version: 0.1.0
```

Read current `main` before proposing code.

## Identity decision

The project is fully independent from the code base originally used to start
development.

The project originated from zapret by bol-van and an earlier OPNsense plugin
code base by Umur Gorur. Their copyright notices and licenses remain preserved
in `LICENSE` and `NOTICE`.

Future package identity, architecture, installation, release process,
documentation, maintenance, and ongoing development belong to
`os-zapret2-restyle`.

Goal: build and install the plugin on a clean supported OPNsense system without
references to or dependencies on another OPNsense zapret plugin repository.

## Completed

- Backend v2 modular architecture.
- Unified Traffic Strategy.
- Generic `<TYPE:name>` placeholders.
- HOSTLIST/IPSET target registry.
- Target Mode.
- Domain and IPv4/CIDR normalization and strict validation.
- Wildcard domain canonicalization.
- Exclude Domains.
- Blob resolution.
- Port extraction.
- Generated dvtws2 arguments.
- Candidate validation.
- Atomic activation and restoration.
- Launcher/supervisor separation.
- ipfw lifecycle.
- Execution stages.
- Safe reconfigure.
- Transactional Apply.
- Field-level GUI errors.
- Normalized GUI reload.
- Explicit visible Apply button.
- Public requirements, architecture, and state documentation.
- Independent package name and version approved:
  - `zapret2-restyle`
  - `0.1.0`

## Confirmed live tests

- Target placeholders resolve to separate managed files.
- `*.googlevideo.com` becomes `googlevideo.com`.
- Invalid `999.999.999.999` reports `targets|failed`.
- Invalid candidate leaves PID, active runtime, and ipfw unchanged.
- Normal runtime reaches:

```text
13|13|ready|ok
```

## Current priority

### Traffic Strategy validator

Add plugin-owned structural validation without blocking future valid zapret2
arguments.

Candidate checks:

- empty profiles;
- invalid `--new` placement;
- profile without a filter;
- malformed TCP/UDP port filters;
- unknown placeholder type;
- unknown target name;
- unresolved placeholders;
- profile and line numbers in errors.

## Packaging priority

After repository metadata is committed:

- verify every required Backend v2 file is included in package build;
- verify package name and generated package filename;
- test build;
- test fresh installation on clean OPNsense;
- remove inherited repository assumptions from setup, CI, release workflow,
  package scripts, comments, URLs, and diagnostics;
- verify uninstall and upgrade behavior.

## Known cautions

- Do not commit `/usr/local/etc/zapret2`.
- Do not commit runtime, binaries, logs, PID files, backups, or secrets.
- Use FreeBSD-compatible commands.
- Give commands strictly in execution order.
- Do not guess OPNsense HTML/CSS structure.
- The field-width experiment was reverted and remains out of scope.

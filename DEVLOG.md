# OPNsense Zapret2 Restyle — Development State

Last context update: 2026-07-28

## Source of truth

```text
https://github.com/Tolian82/os-zapret2-restyle
branch: main
tag: restyle-start
```

Read current `main` before proposing any code.

## Project state

Most of Backend v2 has been implemented and tested on a live OPNsense installation.

### Completed

- Imported upstream `ugorur/os-zapret2`.
- Imported recovered Restyle development state.
- Published the annotated tag `restyle-start`.
- Unified HTTP/HTTPS configuration into one multiline Traffic Strategy.
- Removed the separate legacy Ports field from Backend v2.
- Added profile parsing with standalone `--new`.
- Added generic `<TYPE:name>` placeholder parsing.
- Added target registry and Target Mode.
- Added:
  - `<HOSTLIST:youtube>`
  - `<HOSTLIST:user>`
  - `<IPSET:telegram>`
- Added strict separate domain and IPv4/CIDR normalization and validation.
- Added wildcard normalization: `*.googlevideo.com` → `googlevideo.com`.
- Added global Exclude Domains.
- Added Blob Resolver.
- Added TCP/UDP port extraction from strategy.
- Added staged release generation and validation.
- Added atomic activation and restore support.
- Split launcher and supervisor responsibilities.
- Added ipfw rules generated from extracted ports.
- Added machine-readable execution stages.
- Added safe reconfigure.
- Added transactional Apply with field-level errors and normalized GUI reload.
- Replaced the empty standard Apply-button partial with an explicit visible button.
- Added wildcard support to GUI domain-field masks.
- Published the tested safe reconfigure and transactional Apply changes to `main`.

### Confirmed live tests

Normal target resolution generated:

```text
hostlist-youtube.txt:
youtube.com
googlevideo.com
```

Confirmed mappings:

```text
<HOSTLIST:youtube> → --hostlist=.../hostlist-youtube.txt
<HOSTLIST:user>    → --hostlist=.../hostlist-user.txt
<IPSET:telegram>   → --ipset=.../ipset-telegram.txt
```

Invalid candidate:

```text
999.999.999.999
```

Confirmed:

- `targets|failed`;
- exact field, line, value, and reason;
- active dvtws2 PID unchanged;
- ipfw rules unchanged;
- active runtime unchanged.

Normal final runtime status:

```text
13|13|ready|ok
```

### GUI layout decision

An attempt to widen fields using guessed CSS selectors was reverted.

Current decision:

- keep current field width;
- do not change layout without inspecting verified rendered markup;
- width enhancement is not a priority.

## Current priority

### Next major task: Traffic Strategy validator

Add stronger plugin-owned semantic validation before dvtws2 launch.

Candidate checks:

- empty profiles;
- leading, trailing, or consecutive `--new`;
- profile without a filter;
- malformed `--filter-tcp=` / `--filter-udp=` port values;
- unknown placeholder type;
- unknown target name;
- unresolved placeholders;
- useful profile and line numbers in errors.

Do not over-validate native upstream zapret2 syntax. dvtws2 remains the authority for upstream argument semantics.

## Secondary tasks

- Add shell test fixtures for parser, targets, ports, validator, and safe reconfigure.
- Extend inherited GitHub Actions for Backend v2.
- Review package fresh install, upgrade, and module file inclusion.
- Review migration from legacy HTTP/HTTPS/Ports settings.
- Add minimal README installation and development instructions.
- Revisit editor height and optional line numbering later.

## Known cautions

- Do not commit `/usr/local/etc/zapret2`; it contains engine/runtime material.
- Do not commit `.orig`, `.rej`, backups, runtime-v2, PID files, logs, or secrets.
- FreeBSD behavior differs from GNU/Linux; verify command options and use `/bin/sh`.
- Commands for the user must be given strictly in execution order.
- Browser-console errors from `cs_similar_goods.js` and related scripts were browser-extension errors, not plugin errors.

## Recovery instructions for a future assistant

1. Open the public repository and read current `main`.
2. Read:
   - `REQUIREMENTS.md`
   - `ARCHITECTURE.md`
   - `DEVLOG.md`
3. Inspect commits after `restyle-start`.
4. Read `zapret_service.sh` and `backend/orchestrator.sh`.
5. Confirm the working tree state before giving patches.
6. Prefer repository state over chat memory.

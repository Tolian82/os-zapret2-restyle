# OPNsense Zapret2 Restyle — Requirements

## Status

This document records the approved product requirements for the `os-zapret2-restyle` project.

The project is a public OPNsense plugin built on top of `ugorur/os-zapret2` and upstream `bol-van/zapret2`.

## Core principles

- Prefer the correct engineering solution over a quick workaround.
- No hidden behavior or silent data loss.
- Minimize service-specific special cases.
- Keep the plugin compatible with upstream zapret2 syntax.
- Do not modify approved requirements without a strong reason.
- The GitHub `main` branch is the source of truth.
- Runtime changes must be validated before the active working service is disturbed.

## Configuration model

### Traffic Strategy

The GUI exposes one multiline field:

```text
Traffic Strategy
```

It replaces the former separate HTTP and HTTPS strategy fields.

The field supports native zapret2/dvtws2 arguments and any number of profiles separated by:

```text
--new
```

The backend must preserve all user strategy lines except recognized plugin placeholders and declarations that must be resolved.

### Target placeholders

Supported generic placeholder syntax:

```text
<TYPE:name>
```

Currently supported target types:

```text
<HOSTLIST:name>
<IPSET:name>
```

Approved built-in targets:

```text
<HOSTLIST:youtube>
<HOSTLIST:user>
<IPSET:telegram>
```

Placeholders may be combined freely in a profile.

The parser is generic and must not contain hard-coded YouTube or Telegram strategy logic.

### Targets

The GUI section is named `Targets`.

Current fields:

- Target Mode
- YouTube Domains
- Telegram IPs
- User Domains
- Exclude Domains

#### HOSTLIST format

One entry per line:

```text
example.com
*.example.com
```

Accepted input may be normalized.

Canonical stored form removes the wildcard prefix because a zapret hostlist entry covers the base domain and its subdomains:

```text
*.example.com
```

becomes:

```text
example.com
```

HOSTLIST fields must reject IP addresses, IP networks, malformed domains, and unrelated text.

#### IPSET format

One IPv4 address or IPv4 CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPSET fields must reject domains, malformed IP addresses, invalid prefixes, and unrelated text.

IPv6 is not currently part of the approved target-list requirements.

#### Normalization

On successful Apply:

- trim surrounding whitespace;
- remove empty lines;
- normalize domain names to lowercase;
- remove supported URL prefixes and irrelevant trailing path/punctuation where explicitly supported;
- convert wildcard domains to canonical base domains;
- canonicalize valid IP/CIDR entries;
- remove duplicates while preserving useful order;
- write normalized values back to persistent OPNsense configuration;
- reload the GUI with the normalized values;
- report that normalization occurred.

Invalid entries must never be silently discarded.

### Exclude Domains

`Exclude Domains` is a global HOSTLIST exclusion mechanism, not a strategy placeholder.

It applies to all generated hostlists and is emitted as a global dvtws2 hostlist-exclude argument.

It does not apply to IPSET values.

### Target Mode

Target Mode is used only for profiles that contain no explicit target placeholder.

Approved modes:

- All traffic
- Only listed targets/domains
- Auto-detect blocked domains

Explicit placeholders override Target Mode for that profile.

## Transactional Apply

The Apply operation is one transaction:

1. Read submitted GUI values.
2. Perform OPNsense model/alphabet validation.
3. Normalize and strictly validate target values.
4. Build and validate a candidate release.
5. On failure:
   - do not save invalid values to persistent configuration;
   - do not stop the active dvtws2 process;
   - do not change active runtime files;
   - do not change ipfw rules;
   - show the field, line number, invalid value, and reason in the GUI.
6. On success:
   - save normalized configuration;
   - activate the validated release;
   - safely reconfigure the service;
   - reload normalized values into the GUI.

The user's invalid input should remain visible after a validation failure so it can be corrected.

## Service controls

### Start

Start must validate the saved configuration before launching the service.

### Restart / Reconfigure

Restart and reconfigure must build and validate a candidate while the old runtime remains operational.

Invalid candidate configuration must leave the existing service, PID, runtime, and firewall rules unchanged.

### Stop

Stop may stop the service directly and does not validate or modify configuration.

## Runtime safety

A release must be built in a temporary workspace and validated before activation.

Runtime activation must be atomic where possible.

If startup, firewall installation, or supervisor startup fails after activation, the previous release must be restored.

Execution progress and failures are recorded in:

```text
/var/run/zapret2-execution.status
```

Errors must end in `failed`, not remain indefinitely in `running`.

## GUI

- Use native OPNsense styling.
- Keep a visible explicit `Apply` button.
- Show validation messages next to the affected field.
- Do not rely on hidden JavaScript to supply essential button text.
- Syntax highlighting is not required.
- Font changes are not required.
- Line numbering is approved in principle but is not implemented yet.
- Wider editor fields were discussed but intentionally left unchanged after an unsuccessful experiment.
- Traffic Strategy should eventually be taller than target-list editors.

## Compatibility and publication

- Preserve upstream plugin directory structure where practical.
- Keep OPNsense-specific logic outside the zapret2 engine.
- Do not commit runtime files, private configuration, nested engine repositories, binaries copied from a live installation, or secrets.
- The project will remain public on GitHub.

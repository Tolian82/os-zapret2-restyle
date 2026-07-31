# os-zapret2-restyle — Requirements

Project: **os-zapret2-restyle**  
Version line: **0.2.x**

## Project identity

`os-zapret2-restyle` is an independent OPNsense plugin project.

An earlier project was used as an initial code base and its copyright is
preserved in `LICENSE`. New development, package identity, versioning,
architecture, documentation, installation, releases, and maintenance belong
to this repository.

The finished plugin must install and operate on a supported OPNsense system
without depending on another OPNsense zapret plugin or its repository.

The zapret2 engine remains an external runtime component managed by this
plugin.

## Core principles

- Correct engineering solution over a quick workaround.
- No hidden behavior or silent data loss.
- Minimal special cases.
- Generic target architecture.
- Native zapret2 strategy compatibility where practical.
- Approved requirements change only when necessary.
- GitHub `main` is the source of truth.
- Candidate configuration is validated before an active service is disturbed.

## Traffic Strategy

One multiline field replaces separate HTTP and HTTPS fields.

Profiles are separated by standalone:

```text
--new
```

Supported generic placeholders:

```text
<HOSTLIST:name>
<IPSET:name>
```

Current built-in targets:

```text
<HOSTLIST:youtube>
<HOSTLIST:user>
<IPSET:telegram>
```

Multiple placeholders may be written in one user profile. The user must not be
required to duplicate the profile or add extra `--new` separators merely because
more than one target selector is present.

After parsing and Target Mode processing, the backend must normalize a profile
with multiple unique selectors into one runtime profile per selector. Each
runtime profile must retain all non-selector strategy lines and exactly one
unique selector. Selector order must follow first appearance, duplicate selector
occurrences must not create duplicate profiles, and profiles with zero or one
unique selector must remain unchanged.

Only `HOSTLIST:*` and `IPSET:*` selector families are supported. `GROUP`,
`TARGETSET`, and other generic selector families are explicitly outside the
approved architecture.

User-authored standalone `--new` separators remain part of the Traffic Strategy
syntax. The backend may generate additional runtime `--new` boundaries during
normalization. The parser must not contain target-name-specific strategy
behavior.

## Targets

Current GUI fields:

- Target Mode
- YouTube Domains
- Telegram IPs
- User Domains
- Exclude Domains

### HOSTLIST

One domain per line:

```text
example.com
*.example.com
```

Both normalize to:

```text
example.com
```

The canonical entry applies to the base domain and subdomains.

HOSTLIST fields reject IPs, networks, malformed domains, and unrelated text.

### IPSET

One IPv4 address or IPv4 CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPSET fields reject domains, malformed addresses, invalid prefixes, and
unrelated text.

IPv6 target lists are outside version 0.2.0 requirements.

### Normalization

Successful Apply:

- trims whitespace;
- removes empty lines;
- lowercases domains;
- normalizes wildcard domains;
- canonicalizes IPv4/CIDR values;
- removes duplicates;
- stores normalized values;
- reloads normalized values into the GUI;
- reports normalization.

Invalid values are never silently discarded.

## Exclude Domains

Exclude Domains is a global HOSTLIST exclusion mechanism, not a strategy
placeholder. It does not apply to IPSET values.

## Target Mode

Target Mode applies only to profiles without explicit target placeholders.

Explicit placeholders override Target Mode for their profile.

## Transactional Apply

Apply must:

1. validate submitted model values;
2. normalize and strictly validate targets;
3. build and validate a candidate release;
4. on failure, preserve persistent configuration, active PID, runtime, and
   ipfw rules and show a field/line error;
5. on success, save normalized values and safely activate the candidate.

Invalid user input remains visible for correction.

## Service lifecycle

- Start validates saved configuration before launch.
- Restart/Reconfigure validates a candidate while the old runtime works.
- Stop stops the service without modifying configuration.
- Failed candidates must not stop a working service.
- Post-activation failure must restore the previous runtime.

## GUI

- Native OPNsense appearance.
- Explicit visible Apply button.
- Field-specific validation messages.
- No essential button text supplied only by hidden JavaScript.
- No syntax highlighting requirement.
- No font change requirement.
- Line numbering may be added later.
- Field width remains unchanged until verified rendered markup is deliberately inspected.

## Packaging

The package identity is:

```text
PLUGIN_NAME=zapret2-restyle
PLUGIN_VERSION!= /bin/cat ${.CURDIR}/VERSION
```

The final package must include all project-owned MVC, service, backend,
template, hook, package-script, and setup files required for a fresh OPNsense
installation.

Runtime files, live configuration, logs, PID files, downloaded engine trees,
and secrets must not be packaged from a development firewall.


## Plugin installation and runtime preparation

- Package installation must remain short and must not download sources, install system
  packages, or compile zapret2.
- Package post-install must register the plugin, render required templates, and print:

  `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install`

- `setup.sh install` is the single runtime-preparation backend. It may initially be run
  from the shell and later from a GUI maintenance action.
- Runtime setup must install only missing dependencies, restore temporary pkg repository
  changes, checkout a project-approved fixed upstream release, compile, and verify dvtws2.
- Start, Restart, Reconfigure, and Apply must not install or update runtime components.
  They must fail clearly when no usable dvtws2 exists.
- Package removal must synchronously stop the service before plugin files disappear.
- Package removal must preserve plugin configuration, downloaded runtime content, logs,
  and shared dependencies.
- `+POST_DEINSTALL` must not restart configd.
- Destructive runtime/dependency cleanup must be a separate explicit maintenance action.
- Runtime setup operations must be logged and safe against concurrent runs.


==================================================
IMPLEMENTATION TRACEABILITY SNAPSHOT — 2026-07-30
==================================================

This section records verification state without changing the approved product requirements.

Live verified:

- independent OPNsense package installation;
- explicit one-time runtime setup after plugin installation;
- pinned bol-van/zapret2 v1.0.3 runtime source;
- dvtws2 build and execution;
- configd service control;
- unified strategy processing;
- HOSTLIST and IPSET target resolution;
- automatic one-selector-per-runtime-profile normalization;
- preservation of user-authored --new boundaries;
- candidate validation and transactional runtime activation;
- ipfw divert lifecycle;
- supervised runtime process;
- status reaching ready/ok.

Implemented but awaiting complete lifecycle live verification:

- package upgrade behavior;
- stop-only pre-deinstall behavior;
- runtime/dependency preservation after package removal;
- reinstall over preserved runtime;
- reboot startup behavior;
- controlled runtime-failure handling.

Blob requirement interpretation:

- shorthand --blob=<name> addresses files/fake/<name>.bin directly;
- actual preset blob names must correspond to installed files;
- implicit aliases are not a product requirement.

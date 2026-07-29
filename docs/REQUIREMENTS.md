# os-zapret2-restyle — Requirements

Project: **os-zapret2-restyle**  
Version line: **0.1.x**

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

IPv6 target lists are outside version 0.1.0 requirements.

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
PLUGIN_VERSION=0.1.0
```

The final package must include all project-owned MVC, service, backend,
template, hook, package-script, and setup files required for a fresh OPNsense
installation.

Runtime files, live configuration, logs, PID files, downloaded engine trees,
and secrets must not be packaged from a development firewall.

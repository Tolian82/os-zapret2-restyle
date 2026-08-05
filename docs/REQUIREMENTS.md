# os-zapret2-restyle — Requirements

Project: **os-zapret2-restyle**  
Version line: **0.3.x**

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

IPv6 target lists remain outside the approved target-list contract. Strategy Lab accepts a normalized domain only; IPv6 is detected only as an optional network capability and is not accepted as a Strategy Lab target.

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
- The Settings page must contain a native collapsible `Zapret2 Service` section after
  the existing configuration sections.
- On desktop widths, service status, exact installed release tag, Start/Stop, repository
  release selector, and the runtime Apply button must occupy one horizontal line. Narrow
  layouts may wrap without changing the control order.
- Service status is restricted to Started, Stopped, or Error and uses the standard
  success, neutral, and danger visual states. Runtime version is reported separately
  from service health and is empty when the installed tree is not at an exact valid tag.
- The repository selector presents at most the four current stable releases returned by
  `setup.sh show`. Drafts, prereleases, malformed tags, and arbitrary user values must
  not be accepted.
- Runtime Apply starts `setup.sh install VERSION` asynchronously through configd, disables
  conflicting controls while the operation is active, polls read-only status, and points
  the user to `/var/log/zapret2/setup.log` after failure.
- The GUI follows the language selected in OPNsense. English is the default; custom
  Zapret2 labels and operation messages also provide Russian text. The plugin must not
  introduce its own language selector.

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

- After packaged MVC, menu, ACL, controller, and view files are installed or replaced,
  `+POST_INSTALL` must preserve all registration/template/service-state responsibilities
  and refresh the Web GUI through the current OPNsense `webgui restart` configd action
  as its final integration step. The exact `OK` response is required; refresh failure
  must not be suppressed. The obsolete `webgui.lighttpd_reload` hook and a configd
  restart are not accepted substitutes.
- `setup.sh` is the single runtime-preparation and bol-van/zapret2 release-management
  backend. Shell commands and the GUI must reuse its `show` and `install [VERSION]`
  interfaces rather than implementing separate release discovery or installation paths.
- Running `setup.sh` without arguments or running `setup.sh install` without a version
  must obtain the published stable-release list and install its latest release.
- `setup.sh show` must print, one tag per line, up to the four latest published stable
  releases.
- `setup.sh install VERSION` must accept an exact published stable release tag such as
  `v1.0.3`, reject malformed or unpublished values before runtime mutation, and use the
  same path for first installation, repeat installation, upgrade, and downgrade.
- Numeric release tags may contain more than three dot-separated components, for
  example `v0.9.5.2`.
- `setup.sh --help` and `setup.sh -h` must provide concise command usage.
- Drafts, prereleases, and non-numeric release tags must not be presented or selected
  as stable releases.
- Release discovery must remain read-only and must fail clearly when GitHub cannot be
  reached or returns no usable stable releases.
- Runtime setup must install only missing dependencies, restore temporary pkg repository
  changes, checkout the selected published release, compile, and verify dvtws2.
- Start, Restart, Reconfigure, and Apply must not install or update runtime components.
  They must fail clearly when no usable dvtws2 exists.
- Package removal must synchronously stop the service before plugin files disappear.
- The replacement package's pre-install phase must remember whether the service was
  fully running, stop and verify it before the old deinstall hook and file replacement,
  abort when stop fails, and start replacement code only when the pre-upgrade service
  was running. A stopped service must remain stopped.
- Package removal must preserve plugin configuration, downloaded runtime content, logs,
  and shared dependencies.
- `+POST_DEINSTALL` must not restart configd.
- Destructive runtime/dependency cleanup must be a separate explicit maintenance action.
- Runtime setup operations must be logged and safe against concurrent runs.
- `setup.sh install` must capture complete service state before runtime mutation.
  After dvtws2 verification it must refresh and verify a service that was running,
  preserve and verify a service that was stopped, reject incomplete/unknown initial
  state, and never report ready when the required final state is not reached.


==================================================
CURRENT IMPLEMENTATION AND VERIFICATION STATE
==================================================

Active product baseline:

- project version line: `0.3.x`;
- published release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`;
- current verified source candidate: `os-zapret2-restyle-0.3.2_24.pkg`;
- asynchronous Strategy Lab is the only strategy-finding path;
- the initial 13-patch delivery and corrective source patches 1–11 are complete;
- complete mock-driven API/configd-to-worker regression coverage is mandatory in CI;
- final owner-assisted OPNsense verification remains required before release authorization.

Current Strategy Lab behavior is controlled by:

- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`;
- `docs/decisions/DEC-2026-08-05-strategy-lab-corrective-series.md`;
- `docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-CORRECTIVE.md`.

Historical audit, devlog, release, and patch records remain evidence only. They do not
override the current specialist authority and current project state.

Blob requirement interpretation:

- shorthand `--blob=<name>` addresses `files/fake/<name>.bin` directly;
- actual preset blob names must correspond to installed files;
- implicit aliases are not a product requirement.

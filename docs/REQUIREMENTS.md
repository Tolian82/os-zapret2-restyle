# os-zapret2-restyle — Requirements

Project: **os-zapret2-restyle**
Version line: **0.5.x**

## Project identity

`os-zapret2-restyle` is an independent OPNsense plugin project.

An earlier project was used as an initial code base and its copyright is preserved in `LICENSE`. New development, package identity, versioning, architecture, documentation, installation, releases, and maintenance belong to this repository.

The finished plugin must install and operate on a supported OPNsense system without depending on another OPNsense zapret plugin or its repository.

The zapret2 engine remains an external runtime component managed by this plugin.

## General development rules

General project-development principles are canonical only in [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) (`DEV-*`). This file defines product-specific requirements and does not duplicate that general rule book.

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

Multiple placeholders may be written in one user profile. The user must not be required to duplicate the profile or add extra `--new` separators merely because more than one target selector is present.

After parsing and Target Mode processing, the backend must normalize a profile with multiple unique selectors into one runtime profile per selector. Each runtime profile must retain all non-selector strategy lines and exactly one unique selector. Selector order must follow first appearance, duplicate selector occurrences must not create duplicate profiles, and profiles with zero or one unique selector must remain unchanged.

Only `HOSTLIST:*` and `IPSET:*` selector families are supported. `GROUP`, `TARGETSET`, and other generic selector families are explicitly outside the approved architecture.

User-authored standalone `--new` separators remain part of the Traffic Strategy syntax. The backend may generate additional runtime `--new` boundaries during normalization. The parser must not contain target-name-specific strategy behavior.

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

IPSET fields reject domains, malformed addresses, invalid prefixes, and unrelated text.

IPv6 target lists remain outside the approved target-list contract.

### Strategy Lab target identity

Strategy Lab accepts either a normalized domain or a canonical IPv4 address.

For an IPv4 target, an optional separate **Host / SNI** service identity may be supplied. The entered IPv4 remains the fixed destination used for routing, interception, attribution and final `--ipset-ip=<target>` selection, while the service hostname is used for TLS/HTTP/QUIC identity and certificate verification.

Bare IPv4 TLS certificate-identity failure is not proof that DPI bypass failed. When HTTPS identity cannot be established without a service name, Strategy Lab must return truthful `PARTIAL` guidance asking for Host/SNI rather than a misleading empty `NO_CANDIDATE` result.

IPv6 is detected as an optional network capability but is not currently accepted as a Strategy Lab target. IPv6 Laboratory target support requires a separate explicit architecture scope.

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

Exclude Domains is a global HOSTLIST exclusion mechanism, not a strategy placeholder. It does not apply to IPSET values.

## Target Mode

Target Mode applies only to profiles without explicit target placeholders.

Explicit placeholders override Target Mode for their profile.

## Transactional Apply

Apply must:

1. validate submitted model values;
2. normalize and strictly validate targets;
3. build and validate a candidate release;
4. on failure, preserve persistent configuration, active PID, runtime, and ipfw rules and show a field/line error;
5. on success, save normalized values and safely activate the candidate.

Invalid user input remains visible for correction.

## Strategy Lab adaptive search

The current Strategy Lab architecture is defined by [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md), [`architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md), [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md), and [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

Product requirements:

- search candidates use native `bol-van/zapret2` semantics only; classic zapret/nfqws1 strategy syntax is not a candidate source;
- Python is the automated planner/search/result owner and shell is limited to audited OPNsense/FreeBSD system adapters;
- **Model C is the only normal production Stage-60 execution model**; Model A and Model B remain explicit reference/benchmark/test paths and are not automatic production fallbacks;
- a simple Stage-50 representative result is evidence, not an allow/deny gate for all related Stage-60 candidates;
- each candidate has an explicit reproducible `CandidateSpec` including ordered Lua actions, technique arguments, optional ranges and resource dependencies;
- installed Lua and fake-file resources are captured in a job-scoped `ResourceInventory` rather than assumed from a fixed release-specific list;
- BLOB-free, Zapret2 built-in, inline and installed external-file resource forms are all valid when the native technique supports them;
- a reported bypass candidate contains at least one native Zapret2 Lua action; a no-action profile is baseline/pass-through evidence;
- `--out-range=-d10` is not a global Strategy Lab requirement; output range is candidate data and may be another valid value or absent when the native strategy does not need it;
- known native/owner-proven Zapret2 strategies are retained as golden representation and search-reachability regressions, not universal provider presets;
- normal adaptive discovery is centered on IPv4/TCP/TLS while preserving the current domain and fixed-IPv4 target contracts;
- candidate execution must retain deterministic endpoint attribution, controlled source-port leasing, temporary firewall ownership and bounded cleanup;
- mass discovery and finalist validation are separate evidence levels;
- strict stability remains 3/3 but stops immediately after a failure makes 3/3 impossible;
- the best two to three candidates normally receive finalist validation and form the early-stop target; a smaller truthful result remains valid;
- finalist validation uses a real bounded GET and records whether at least 16 KiB of body data was obtained; a valid shorter resource is `inconclusive` for the 16-KiB depth criterion rather than falsely reported as PASS;
- authenticated/intercepted HTTP `4xx`/`5xx` is application-layer status, not automatic DPI-path failure; such a response may remain accepted reachability evidence when endpoint/profile/interception proof succeeds;
- operation, candidate, stage and job deadlines form a measured containing hierarchy and must be reviewed from timing telemetry rather than copied indefinitely as constants;
- **Enable QUIC** is an explicit persisted setting, defaults OFF, and is the product decision that determines whether Extended Stage 80 runs the QUIC candidate catalog;
- QUIC capability/precheck evidence is diagnostic and does not silently override the explicit Enable QUIC choice;
- for a fixed IPv4 target with Host/SNI, QUIC attempts must connect to the fixed IP while verifying the supplied hostname; bare IPv4 QUIC without Host/SNI is skipped before candidate execution rather than falsely reported as tested;
- Generic UDP is an optional Extended protocol path with explicit destination port and exact payload bytes, remains independent from Host/SNI/QUIC, and UDP silence is not proof that a port is closed;
- complete fixed-IP recommendations include `--ipset-ip=<entered IPv4>` and undergo the same exact finalist replay discipline;
- all terminal paths require bounded temporary-runtime cleanup and exact Stage-90 restoration of the original Zapret2 service/configuration state.

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
- The Settings page must contain a native collapsible `Zapret2 Service` section after the existing configuration sections.
- On desktop widths, service status, exact installed release tag, Start/Stop, repository release selector, and the runtime Apply button must occupy one horizontal line. Narrow layouts may wrap without changing the control order.
- Service status is restricted to Started, Stopped, or Error and uses the standard success, neutral, and danger visual states. Runtime version is reported separately from service health and is empty when the installed tree is not at an exact valid tag.
- The repository selector presents at most the four current stable releases returned by `setup.sh show`. Drafts, prereleases, malformed tags, and arbitrary user values must not be accepted.
- Runtime Apply starts `setup.sh install VERSION` asynchronously through configd, disables conflicting controls while the operation is active, polls read-only status, and points the user to `/var/log/zapret2/setup.log` after failure.
- The GUI follows the language selected in OPNsense. English is the default; custom Zapret2 labels and operation messages also provide Russian text. The plugin must not introduce its own language selector.
- Laboratory uses the native OPNsense content frame/grid and exposes domain-or-IPv4 target input, conditional Host/SNI, Standard/Extended mode, persisted Enable QUIC, optional Generic UDP input, progress/status, stable result profiles and exact evidence without requiring a separate UI application.

## Packaging

The package identity is:

```text
PLUGIN_NAME=zapret2-restyle
PLUGIN_VERSION!= /bin/cat ${.CURDIR}/VERSION
```

The final package must include all project-owned MVC, service, backend, template, hook, package-script, and setup files required for a fresh OPNsense installation.

Runtime files, live configuration, logs, PID files, downloaded engine trees, and secrets must not be packaged from a development firewall.

## Plugin installation and runtime preparation

- Package installation must remain short and must not download sources, install system packages, or compile zapret2.
- Package post-install must register the plugin, render required templates, and print:

  `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install`

- After packaged MVC, menu, ACL, controller, and view files are installed or replaced, `+POST_INSTALL` must preserve all registration/template/service-state responsibilities and refresh the Web GUI through the current OPNsense `webgui restart` configd action as its final integration step. The exact `OK` response is required; refresh failure must not be suppressed. The obsolete `webgui.lighttpd_reload` hook and a configd restart are not accepted substitutes.
- `setup.sh` is the single runtime-preparation and bol-van/zapret2 release-management backend. Shell commands and the GUI must reuse its `show` and `install [VERSION]` interfaces rather than implementing separate release discovery or installation paths.
- Running `setup.sh` without arguments or running `setup.sh install` without a version must obtain the published stable-release list and install its latest release.
- `setup.sh show` must print, one tag per line, up to the four latest published stable releases.
- `setup.sh install VERSION` must accept an exact published stable release tag such as `v1.0.3`, reject malformed or unpublished values before runtime mutation, and use the same path for first installation, repeat installation, upgrade, and downgrade.
- Numeric release tags may contain more than three dot-separated components, for example `v0.9.5.2`.
- `setup.sh --help` and `setup.sh -h` must provide concise command usage.
- Drafts, prereleases, and non-numeric release tags must not be presented or selected as stable releases.
- Release discovery must remain read-only and must fail clearly when GitHub cannot be reached or returns no usable stable releases.
- Runtime setup must install only missing dependencies, restore temporary pkg repository changes, checkout the selected published release, compile, and verify dvtws2.
- Start, Restart, Reconfigure, and Apply must not install or update runtime components. They must fail clearly when no usable dvtws2 exists.
- Package removal must synchronously stop the service before plugin files disappear.
- The replacement package's pre-install phase must remember whether the service was fully running, stop and verify it before the old deinstall hook and file replacement, abort when stop fails, and start replacement code only when the pre-upgrade service was running. A stopped service must remain stopped.
- Package removal must preserve plugin configuration, downloaded runtime content, logs, and shared dependencies.
- `+POST_DEINSTALL` must not restart configd.
- Destructive runtime/dependency cleanup must be a separate explicit maintenance action.
- Runtime setup operations must be logged and safe against concurrent runs.
- `setup.sh install` must capture complete service state before runtime mutation. After dvtws2 verification it must refresh and verify a service that was running, preserve and verify a service that was stopped, reject incomplete/unknown initial state, and never report ready when the required final state is not reached.

## Current implementation and verification state

Current facts do not live in this requirements contract. Read [`PROJECT_STATE.md`](PROJECT_STATE.md) for the current `v0.5.x` state, [`START_HERE.md`](START_HERE.md) for the exact candidate/release handoff, and [`history/current/v0.5.x.md`](history/current/v0.5.x.md) for current-line chronology and proof.

The completed `v0.4.x` final-state archive is [`history/archive/v0.4.x.md`](history/archive/v0.4.x.md). Historical audit, devlog, release, patch and evidence records remain history/proof only and do not override current specialist authority/current state (`DOC-004`–`DOC-005`).

## BLOB requirement interpretation

- shorthand `--blob=<name>` addresses `files/fake/<name>.bin` directly;
- actual preset blob names must correspond to installed files;
- implicit aliases are not a product requirement.

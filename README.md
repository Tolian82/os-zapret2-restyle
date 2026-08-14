# os-zapret2-restyle

> Native OPNsense plugin for managing **bol-van/zapret2**, building DPI-bypass strategies and safely testing them directly on the firewall.

| Project | Current state |
|---|---|
| **Full Web/pkg release** | `v0.4.1` · package `os-zapret2-restyle-0.4.1_1.pkg` |
| **Current development candidate** | `os-zapret2-restyle-0.4.1_12.pkg` |
| **Target platform** | OPNsense 26.7 · FreeBSD 15 amd64 |
| **Runtime** | bol-van/zapret2 (`dvtws2`) |
| **OPNsense service** | `zapret` |
| **License** | MIT |

The project is an independent OPNsense integration around the upstream
[bol-van/zapret2](https://github.com/bol-van/zapret2) runtime. It provides a native Web GUI,
transactional runtime management, structured traffic strategies and **Strategy Lab** — an automated
search/verification pipeline for DPI-bypass candidates.

---

## What you get

### 🧩 Native OPNsense integration

- OPNsense MVC/API/configd integration rather than an external control panel.
- Start/stop/status management for the Zapret2 runtime.
- Automatic runtime startup, supervisor ownership and managed `ipfw` divert rules.
- State-preserving plugin upgrades: a running service returns running; a stopped service stays stopped.
- Runtime health checks that validate the complete managed state rather than only one process.

### 🧠 Traffic Strategy editor

The Settings page provides one multiline strategy editor with native Zapret2 syntax plus project
shorthand for managed target lists:

```text
<HOSTLIST:name>
<IPSET:name>
```

Profiles are separated with Zapret2's normal:

```text
--new
```

The backend validates and normalizes configuration before it becomes active. Apply is transactional:
an invalid or unhealthy candidate does not replace a working configuration.

### 🧪 Strategy Lab

Strategy Lab is the project's automated DPI-bypass strategy search engine. It runs from Diagnostics
and is designed to answer a practical question: **which Zapret2 strategy actually works for the target
from this OPNsense installation?**

Current capabilities include:

- clean baseline and network/capability checks before candidate testing;
- deterministic native Zapret2 candidate planning;
- Python-owned job orchestration and persistent progress/state;
- isolated temporary `dvtws2` candidate workers;
- exact source-port-qualified traffic attribution;
- bounded time budgets, cancellation and cleanup;
- stability/final-result verification;
- exact restoration of the pre-test Zapret2 service state;
- Russian and English user-facing progress/result text.

The current development line has selected **Model C** as the normal production Stage-60 architecture.
The remaining development transition is to remove the old automatic Model-B/Model-A fallback from the
production path; those models remain useful as benchmark/reference tooling.

### 🔄 Zapret2 Service manager

The Settings page also contains **Zapret2 Service / Служба Zapret2** for the upstream runtime itself.
It can:

- show the installed upstream release;
- show the latest stable upstream releases;
- install the runtime for the first time;
- update, reinstall or downgrade to a selected release;
- preserve the previous running/stopped state;
- roll back automatically if activation fails.

No OPNsense reboot is required after a successful managed operation.

---

## Installation from the OPNsense Web GUI

The supported full-release channel is the project-owned FreeBSD pkg repository on GitHub Pages.
Register it once on the firewall:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

Then open:

**System → Firmware → Plugins**

and install **`os-zapret2-restyle`**.

The repository is transported over HTTPS and currently uses the approved unsigned pkg configuration
`signature_type: "none"`.

> **Full release vs testing package**
>
> The Web/pkg repository carries the full project release. Newer `_N` packages may also be published
> on GitHub for owner-assisted development testing; those testing candidates do **not** automatically
> replace the Web/pkg release.

---

## First setup

After plugin installation:

1. Open **Services → Zapret2 → Settings**.
2. Open **Zapret2 Service / Служба Zapret2**.
3. Select an upstream bol-van/zapret2 release and click **Apply**.
4. Configure target lists and the **Traffic Strategy**.
5. Apply the settings.
6. Use **Diagnostics → Strategy Lab** when you need to search for a working bypass strategy for a
   blocked domain.

The plugin package and the upstream bol-van/zapret2 runtime have separate lifecycles intentionally:
plugin installation remains quick, while the desired upstream release is selected/compiled through
the managed service backend.

---

## Example strategy

```text
--filter-tcp=80
<HOSTLIST:user>
--filter-l7=http
--payload=http_req
--lua-desync=fake:blob=http_iana_org:tcp_md5
--lua-desync=multisplit:pos=method+2

--new

--filter-tcp=443
<HOSTLIST:youtube>
--filter-l7=tls
--blob=tls7
--out-range=-d8
--payload=tls_client_hello
--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=tls7

--new

--filter-tcp=443
<IPSET:telegram>
--filter-l7=mtproto,unknown
--payload=mtproto_initial,unknown
--lua-desync=fake:blob=stun:repeats=6
```

### Target placeholders

Supported managed placeholders are intentionally limited to:

```text
<HOSTLIST:name>
<IPSET:name>
```

A profile may contain several target placeholders. The backend expands them into concrete runtime
profiles while preserving the remaining Zapret2 arguments and user-authored `--new` boundaries.

### Domain targets

Enter one domain per line:

```text
youtube.com
*.youtube.com
```

Both forms are normalized to the managed domain form. Invalid names, IP addresses and unrelated text
are rejected.

### IPv4 targets

Enter one IPv4 address or CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPv6 target-list management is not currently implemented.

---

## Safe Apply and runtime lifecycle

Configuration changes use a transactional path:

1. normalize and validate model input;
2. build candidate target files and runtime arguments;
3. validate the candidate;
4. switch runtime state atomically;
5. verify firewall/process health;
6. keep or restore the previous working state if activation fails.

Runtime lifecycle operations are serialized. The plugin manages its own PID/state files, supervisor
ownership and firewall rules so stale callbacks cannot tear down a replacement runtime.

Before `dvtws2` starts, required FreeBSD firewall prerequisites are prepared automatically, including
`ipdivert`/`ipfw` support required by the managed divert path.

---

## Upstream runtime management from shell

The Web GUI uses the same authoritative backend available to administrators:

```sh
# Install the latest stable upstream release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install

# Show the latest stable upstream releases.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh show

# Install/reinstall/upgrade/downgrade to an exact release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install v1.0.3

# Help.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh --help
```

The GUI wraps this backend in a transactional activation layer that records the previous upstream
checkout/binaries/runtime marker/service state and restores them if the requested activation fails.

---

## Useful runtime files

```text
/var/db/zapret2-restyle/runtime.release
/var/db/zapret2-restyle/releases.cache
/var/db/zapret2-restyle/setup.status
/var/run/zapret2-execution.status
/var/log/zapret2/setup.log
/var/log/zapret2/dvtws2.log
/var/log/zapret2/supervisor.log
```

`dvtws2` drops privileges to UID/GID `65534`; managed runtime Lua/BLOB files and directories are
normalized to readable/executable permissions appropriate for that privilege boundary.

---

## Removal policy

Removing the OPNsense plugin stops its managed service before package files disappear. By policy the
following are preserved for later reinstall or investigation:

- saved OPNsense configuration;
- downloaded bol-van/zapret2 runtime;
- setup/runtime logs;
- shared dependencies.

---

## Release model

The project distinguishes two publication types:

| Type | Meaning |
|---|---|
| **Testing package** | Persistent GitHub `.pkg` for development/live verification. Does not promote the Pages/pkg repository. |
| **Full release** | Verified package + semantic tag + release assets/checksum + updated Pages/pkg repository, ready for install/update through the OPNsense Web GUI. |

A change to the **second numeric component** of the project version — for example
`v0.4.x → v0.5.x` — happens only after explicit owner instruction/approval and always includes a full
release. A full release can also be made without changing that second component.

Every full release includes a fresh review of this README so the repository front page describes the
actual current product rather than an accumulated historical snapshot.

---

## Documentation for contributors

Engineering documentation lives in [`docs/`](docs/). It uses a three-level memory model so a new
session can recover current state without loading the project's complete history.

Start with:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/PROJECT_PRINCIPLES.md`](docs/PROJECT_PRINCIPLES.md)
3. [`docs/START_HERE.md`](docs/START_HERE.md)
4. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
5. task-specific documents named by `START_HERE.md`

Use [`docs/INDEX.md`](docs/INDEX.md) to reach the current version-line ledger, completed version
archives, devlogs, patch records, decisions and verification evidence only when that history is needed.

---

## Acknowledgements

This independent project builds on open-source work by **bol-van** and **Umur Gorur**. Their copyright
notices and licenses are preserved in [`NOTICE`](NOTICE).

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

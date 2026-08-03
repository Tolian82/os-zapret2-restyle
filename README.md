# os-zapret2-restyle

Native OPNsense plugin for managing the bol-van/zapret2 DPI-bypass runtime.

**Current release:** `v0.3.0`  
**Package:** `os-zapret2-restyle-0.3.0_1.pkg`  
**Target:** OPNsense 26.7 / FreeBSD 15 amd64  
**Internal service name:** `zapret`

## What the plugin provides

- A unified multiline **Traffic Strategy** editor.
- Named domain and IPv4/CIDR targets through `<HOSTLIST:name>` and `<IPSET:name>`.
- Strict validation and normalization before persistent configuration is changed.
- Transactional Apply with candidate validation and automatic runtime rollback.
- Automatic `dvtws2` argument generation and TCP/UDP port extraction.
- Managed `ipfw` divert rules, launcher, supervisor, PID files, and execution status.
- A native **Zapret2 Service** section for service control and upstream runtime releases.
- State-preserving plugin updates and selected-release installation without rebooting OPNsense.

## Installation

The supported distribution channel is the project-owned FreeBSD pkg repository on
GitHub Pages. Register it once on the firewall:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

Then install or update **os-zapret2-restyle** from:

**System → Firmware → Plugins**

The repository is transported over HTTPS and currently uses the approved unsigned
configuration `signature_type: "none"`.

Plugin installation is intentionally quick. The bol-van/zapret2 runtime is selected,
downloaded, and compiled separately through the Settings page or `setup.sh`.

## Zapret2 Service

The Settings page contains a collapsible **Zapret2 Service** block. In a Russian
OPNsense interface it is shown as **Служба Zapret2**.

The block displays:

- current service state: **Started**, **Stopped**, or **Error**;
- the active bol-van/zapret2 release, for example `v1.0.4`;
- a **Start/Stop** control;
- the four latest published stable upstream releases;
- an **Apply** button for installing the selected release.

### Service state

| State | Meaning |
|---|---|
| `Started vX.Y.Z` | `dvtws2`, supervisor, and plugin-owned firewall rules are healthy. |
| `Stopped vX.Y.Z` | The runtime is installed, but the service is intentionally stopped. |
| `Error vX.Y.Z` | The runtime exists, but the complete service contract is not healthy. |
| `not installed` | No usable `dvtws2` runtime is present. |

The status endpoint checks the complete plugin-owned runtime state rather than only
looking for one process.

### Installing, reinstalling, upgrading, or downgrading

1. Open the **Zapret2 Service** block.
2. Select a stable release from **Repository Releases**.
3. Click **Apply**.
4. Wait until the busy indicator disappears.

The same action supports:

- first runtime installation;
- reinstalling the current release;
- upgrading to a newer release;
- downgrading to an older published release.

No OPNsense reboot, configd restart, Web GUI restart, or manual service restart is
required after a successful operation.

### Service-state preservation

The operation preserves the state that existed before it started:

- a running service is refreshed and returns to **Started**;
- a stopped service remains **Stopped**;
- an incomplete or unknown service state is rejected rather than promoted.

This contract also applies to plugin package replacement. `pkg add -f`,
`pkg install -f`, and ordinary package upgrades restore a previously running service
with replacement code before the package transaction finishes. A previously stopped
service remains stopped.

### Transactional release activation

GUI release installation is transactional.

Before changing the upstream runtime, the plugin records:

- the active stable release;
- the previous Git commit;
- the compiled `binaries/my` tree;
- whether the service was running or stopped.

A selected release becomes active only after checkout, compilation, permission
normalization, service refresh, and health verification succeed.

If activation fails, the plugin automatically restores:

- the previous upstream checkout;
- the previous compiled binaries;
- the previous active-release marker;
- the previous running or stopped service state.

The GUI still reports that the requested operation failed, while showing the restored
working release and service state.

The active release is recorded in:

```text
/var/db/zapret2-restyle/runtime.release
```

This marker prevents a candidate Git checkout from being displayed as installed before
activation succeeds.

### Runtime file permissions

`dvtws2` drops privileges to UID/GID `65534`. Runtime Lua and blob files therefore must
remain readable after the privilege drop.

The managed release path imposes `umask 022` and normalizes:

- Lua and blob data files to `0644`;
- runtime directories to `0755`;
- compiled runtime executables to `0755`.

This also repairs restrictive permissions left by an earlier installation.

### Release-list cache

Stable upstream releases are cached in:

```text
/var/db/zapret2-restyle/releases.cache
```

Behavior:

- a fresh cache is returned without contacting GitHub again;
- refresh is serialized with `lockf`;
- cache replacement is atomic;
- invalid or empty responses never replace a good cache;
- a validated stale cache is used during a temporary GitHub/API failure;
- selecting an already listed release does not perform another Releases API request.

The GUI normally shows the four latest stable releases, while the cache may retain a
larger validated list for exact-version verification.

### Operation logs and state

```text
/var/log/zapret2/setup.log
/var/log/zapret2/dvtws2.log
/var/log/zapret2/supervisor.log
/var/db/zapret2-restyle/setup.status
/var/run/zapret2-execution.status
```

`/var/run/zapret2-execution.status` contains the machine-readable lifecycle stage,
result, timestamp, and detail message.

## Command-line runtime management

The GUI uses the same authoritative setup backend available from the shell.

```sh
# Install the latest stable release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install

# Show the four latest stable releases.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh show

# Install, reinstall, upgrade, or downgrade to an exact stable release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install v1.0.3

# Show help.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh --help
```

The managed GUI path adds the transactional wrapper
`setup_transaction.sh` around this backend. Direct `setup.sh` execution remains
available for maintenance and diagnostics.

## Traffic Strategy

A strategy contains one or more independent profiles. User-authored profile boundaries
are separated by a standalone:

```text
--new
```

Example:

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

Supported placeholder families are intentionally limited to:

```text
<HOSTLIST:name>
<IPSET:name>
```

A user profile may contain several HOSTLIST and/or IPSET placeholders. The backend
expands the profile into one runtime profile per unique target while copying the
remaining strategy parameters. Existing user-authored `--new` boundaries are
preserved.

Profiles without an explicit placeholder are processed according to **Target Mode**.

## Domain targets

Enter one domain per line:

```text
youtube.com
*.youtube.com
```

Both forms are equivalent. During Apply, `*.youtube.com` is normalized to
`youtube.com`, which covers the base domain and subdomains.

The backend:

- converts domains to lowercase;
- removes duplicates;
- rejects IP addresses, CIDR networks, malformed names, and unrelated text.

## IP targets

Enter one IPv4 address or IPv4 CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

Domain names are rejected in IP target fields. IPv6 target lists are not currently
supported.

## Applying settings

Settings Apply is transactional:

1. the model input is normalized and validated;
2. candidate target files and `dvtws2` arguments are generated;
3. the candidate is validated;
4. the runtime is switched atomically;
5. firewall rules and supervisor state are verified.

Invalid values are not persisted. A failed candidate keeps or restores the previously
working runtime, PID ownership, managed files, and plugin-owned firewall rules. The GUI
reports the affected field or backend failure.

## Runtime and firewall lifecycle

Before `dvtws2` starts, the plugin prepares required firewall prerequisites, including
`ipdivert` and `ipfw`. This makes cold boot and automatic start work without manual
`kldload` commands.

The launcher verifies startup stability, the supervisor watches the exact expected
runtime process, and mutating lifecycle operations are serialized with a FreeBSD
`lockf` mutex. Stale supervisor callbacks cannot tear down a replacement runtime.

## Removal policy

Removing the plugin stops its service before package files disappear. The following are
preserved by policy:

- saved OPNsense configuration;
- downloaded bol-van/zapret2 runtime;
- setup and runtime logs;
- shared dependencies.

This permits later reinstall or investigation without deleting user state.

## Documentation

Engineering documentation is stored in `docs/`. Repository-aware development starts
with `AGENTS.md`, then follows the mandatory order in `docs/INDEX.md`.

Important v0.3.0 documents:

- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
- `docs/architecture/ZAPRET2_SERVICE.md`
- `docs/audit/AUDIT-2026-08-03-ZAPRET2-SERVICE.md`
- `docs/releases/v0.3.0.md`

## Acknowledgements

This independent project builds on open-source work by bol-van and Umur Gorur. Their
copyright notices and licenses are preserved in `NOTICE`.

## License

MIT. See `LICENSE` and `NOTICE`.

# os-zapret2-restyle

Native OPNsense plugin for managing the zapret2 DPI bypass engine.

Current version: **0.1.0**  
Project status: **active development**

The plugin provides a unified Traffic Strategy editor, separate domain and IP
targets, strict validation, transactional Apply, safe service reconfiguration,
and automatic generation of the dvtws2 runtime configuration.

## Traffic Strategy

A strategy contains one or more independent profiles. Profiles are separated
by a standalone:

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

Supported target placeholders currently include:

```text
<HOSTLIST:user>
<HOSTLIST:youtube>
<IPSET:telegram>
```

Placeholders may be combined in the same profile. Profiles without explicit
placeholders are processed according to **Target Mode**.

## Domain targets

Enter one domain per line:

```text
youtube.com
*.youtube.com
```

Both forms are equivalent for this plugin. During Apply:

```text
*.youtube.com
```

is normalized to:

```text
youtube.com
```

The canonical `youtube.com` entry applies to the base domain and its
subdomains. Duplicate entries are removed and domain names are stored in
lowercase.

Domain target fields reject IP addresses, CIDR networks, malformed domains,
and unrelated text.

## IP targets

Enter one IPv4 address or one IPv4 CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

Domain names are not accepted in IP target fields. IPv6 target lists are not
supported in version 0.1.0.

## Applying settings

Apply is transactional:

- invalid values are not written to the persistent OPNsense configuration;
- the currently working service remains active;
- active runtime files and ipfw rules remain unchanged;
- the GUI identifies the affected field and line;
- valid values are normalized, saved, activated, and reloaded into the form.

## Installation

Version 0.1.0 is under active development and is not yet published as a stable
OPNsense Package Manager release.

Package build and installation instructions will be added before the first
public test release.

## Documentation

Developer and project-state documents:

- [REQUIREMENTS.md](REQUIREMENTS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEVLOG.md](DEVLOG.md)
- [ROADMAP.md](ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)

## License

MIT. See [LICENSE](LICENSE).

# os-zapret2-restyle

Native OPNsense plugin for managing the zapret2 DPI bypass engine.

Current version:
0.1.0

Project status:
Active development

==================================================
PROJECT OVERVIEW
==================================================

The plugin provides:

- Unified Traffic Strategy editing.
- Separate domain and IP targets.
- Strict validation.
- Transactional Apply.
- Safe service reconfiguration.
- Automatic dvtws2 runtime generation.
- Runtime validation and rollback.
- ipfw lifecycle management.
- Supervisor lifecycle management.

==================================================
TRAFFIC STRATEGY
==================================================

A strategy contains one or more independent profiles.

Profiles are separated by a standalone:

--new

Example:

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

Supported target placeholders currently include:

<HOSTLIST:user>
<HOSTLIST:youtube>
<IPSET:telegram>

A user profile may contain several `HOSTLIST:*` and/or `IPSET:*` placeholders.
The backend automatically expands it into one runtime profile per unique target
while copying the remaining strategy parameters to every generated profile.
Extra user-authored `--new` separators are therefore not required merely to
separate target lists. Existing user `--new` boundaries are preserved.

Only `HOSTLIST:*` and `IPSET:*` placeholder families are supported.

Profiles without explicit placeholders are processed according to Target Mode.

==================================================
DOMAIN TARGETS
==================================================

Enter one domain per line.

Examples:

youtube.com
*.youtube.com

Both forms are equivalent for this plugin.

During Apply:

*.youtube.com

is normalized to:

youtube.com

The canonical youtube.com entry applies to the base domain and its subdomains.

Duplicate entries are removed.

Domain names are stored in lowercase.

Domain target fields reject:

- IP addresses.
- CIDR networks.
- Malformed domains.
- Unrelated text.

==================================================
IP TARGETS
==================================================

Enter one IPv4 address or one IPv4 CIDR network per line.

Examples:

149.154.160.1
149.154.160.0/20

Domain names are not accepted in IP target fields.

IPv6 target lists are not supported in version 0.1.0.

==================================================
APPLYING SETTINGS
==================================================

Apply is transactional.

Invalid values are not written to persistent OPNsense configuration.

The currently working service remains active.

Active runtime files and ipfw rules remain unchanged.

The GUI identifies the affected field and line.

Valid values are normalized, saved, activated, and reloaded into the form.

==================================================
INSTALLATION
==================================================

Version 0.1.0 is being prepared as the first public test release.

The supported distribution model is a project-owned FreeBSD pkg repository
published through GitHub Pages for FreeBSD:15:amd64 / supported OPNsense 26.7
systems. Package assets and checksums are also published in GitHub Releases.

Normal installation and updates are performed through the OPNsense Firmware GUI.
No manual setup.sh command is required: after the plugin is configured, the first
Apply or Start automatically installs the required runtime dependencies, downloads
zapret2, compiles dvtws2, verifies it, and starts the service. Internet access is
required for this one-time bootstrap.

The repository is registered once on the firewall by placing the published
configuration file in `/usr/local/etc/pkg/repos/` and refreshing pkg metadata:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

After that, install and update `os-zapret2-restyle` through
**System > Firmware > Plugins**. The initial prerelease repository is transported
over HTTPS but is intentionally unsigned (`signature_type: "none"`). Repository
signing is required before promotion to a stable public release.

==================================================
ENGINEERING MEMORY
==================================================

Internal development starts from `docs/INDEX.md`.

All engineering documentation is stored in the `docs/` directory.

Mandatory reading order:

1. `docs/INDEX.md`
2. `docs/PROJECT_STATE.md`
3. `docs/AUDIT.md`
4. `docs/DECISIONS.md`
5. `docs/WORKING_CONVENTIONS.md`
6. `docs/DEVELOPMENT_GUIDE.md`
7. `docs/ARCHITECTURE.md`
8. `docs/DEVLOG.md`
9. `docs/ROADMAP.md`
10. `docs/REQUIREMENTS.md`

==================================================
ACKNOWLEDGEMENTS
==================================================

This independent project originated from earlier open-source work by bol-van
and Umur Gorur.

Their copyright notices and licenses are preserved.

See NOTICE.

==================================================
LICENSE
==================================================

MIT.

See LICENSE and NOTICE.

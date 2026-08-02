# os-zapret2-restyle

Native OPNsense plugin for managing the zapret2 DPI bypass engine.

Current version:
0.2.8

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

IPv6 target lists are not supported in version 0.2.0.

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

Version 0.2.8 is the current prerelease line; this source tree builds package revision 3.

The supported distribution model is a project-owned FreeBSD pkg repository
published through GitHub Pages for FreeBSD:15:amd64 / supported OPNsense 26.7
systems. Package assets and checksums are also published in GitHub Releases.

Normal plugin installation and updates are performed through the OPNsense Firmware GUI.
The package installation itself remains quick and does not download or compile the
zapret2 runtime. After installation, the setup backend can be used as follows:

```sh
# Install the latest stable bol-van/zapret2 release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install

# Show the four latest stable releases.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh show

# Install, reinstall, upgrade, or downgrade to an exact published release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install v1.0.3

# Show command help.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh --help
```

The setup backend obtains the published stable-release list from GitHub through the
native FreeBSD `fetch` command. Without an explicit version it selects the latest
stable bol-van/zapret2 release. With an exact version it verifies that the release is
published, checks out that tag, compiles and verifies dvtws2, and records the result.
Internet access is required during setup. After verification it refreshes and verifies
the installed runtime only when the service was running before setup; a stopped service
remains stopped. A future GUI maintenance action will call the same backend.

Package upgrades preserve the prior service state. The replacement package stops a
running service before the old package hook and plugin-file replacement, then starts it
again with replacement code. A stopped service remains stopped, and an upgrade is
aborted if the installed service cannot stop cleanly.

Removing the plugin stops the service before package files disappear. Saved OPNsense
configuration, the downloaded runtime, logs, and shared dependencies are preserved.

The repository is registered once on the firewall by placing the published
configuration file in `/usr/local/etc/pkg/repos/` and refreshing pkg metadata:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

After that, install and update `os-zapret2-restyle` through
**System > Firmware > Plugins**. The initial prerelease repository is transported
over HTTPS but is intentionally unsigned (`signature_type: "none"`). This unsigned
mode is the currently approved distribution policy.

==================================================
ENGINEERING MEMORY
==================================================

Repository-aware agents start from `AGENTS.md`, which requires the complete
Engineering Memory preflight. Internal development then starts from
`docs/INDEX.md`; `AGENTS.md` does not replace or shorten the reading order.

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
11. `docs/GITHUB_WORKFLOW.md`

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


## Count-carrying profile pipeline

Backend profile preparation is an ordered pipeline: parse, target registry, Target
Mode, runtime-profile normalization, and placeholder indexing. Every step carries and
validates the current runtime profile count, so later resolution cannot accidentally
use a stale count after automatic profile expansion.

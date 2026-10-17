# os-zapret2-restyle

> Native OPNsense plugin for **bol-van/zapret2**: manage the runtime, build DPI-bypass profiles, and automatically search for strategies that actually work from your firewall.

| Project | Current release |
|---|---|
| **Full Web/pkg release** | [`v0.5.3`](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.3) · `os-zapret2-restyle-0.5.3_2.pkg` |
| **Current development candidate (not released)** | `v0.5.3_3` — Voice RU help / WAN candidate, pending CI and owner-live verification |
| **Target platform** | OPNsense 26.7 · FreeBSD 15 amd64 |
| **Runtime** | bol-van/zapret2 (`dvtws2`) |
| **OPNsense service** | `zapret` |
| **License** | MIT |

`os-zapret2-restyle` is an independent OPNsense integration around the upstream [bol-van/zapret2](https://github.com/bol-van/zapret2) runtime. The published stable release includes the native service manager, editable Traffic Strategy, managed targets and **Strategy Lab**. The **v0.5.2 full release** introduces **Voice Transmission**, a five-service STUN/UDP configuration page using the same normal Zapret2 engine and Apply lifecycle. The owner installed `0.5.2_194` and reported that its Voice menu opens “Page not found”. This is a confirmed release defect. The approved v0.5.3 corrective plan keeps the full feature scope. The published `0.5.3_2` corrects the missing Voice UI controller and passed regression tests against the actual OPNsense 26.7 Router, including the extracted FreeBSD package. The owner installed `0.5.3_2` and the Voice page now opens, but native Russian help, the WAN dropdown preview and error localization failed in live use. An unreleased `0.5.3_3` source candidate addresses those issues; Apply, runtime and voice-call acceptance remain open.

## Strategy Lab — find a working bypass strategy instead of guessing

**Strategy Lab is the flagship feature of the project.** Give it a blocked domain or IPv4 address and it automatically tests real Zapret2 strategy families from the OPNsense firewall, verifies stable winners, and returns complete profiles ready to copy into **Traffic Strategy**.

The Laboratory is designed around one practical question:

> **Which Zapret2 strategy actually works for this target, on this ISP, from this exact OPNsense installation?**

What it does:

- accepts a blocked **domain or IPv4 address**;
- supports optional **Host / SNI** for fixed-IP HTTPS/TLS/QUIC testing;
- measures a clean baseline before trying bypass candidates;
- runs deterministic native Zapret2 candidate families under the production **Model C** execution architecture;
- attributes candidate traffic to exact controlled source ports and temporary firewall rules;
- checks stability and replays finalists before recommending them;
- keeps HTTP application errors such as `4xx`/`5xx` separate from DPI-path reachability, so a reachable server is not falsely discarded just because the application returned an error;
- supports **Extended** protocol checks for TLS 1.2, HTTP, QUIC and optional Generic UDP;
- treats bare-IP QUIC truthfully: without Host/SNI it is skipped rather than reported as tested;
- can test Generic UDP independently against an IPv4 destination;
- emits complete final profiles, including `--ipset-ip=<target>` for fixed-IP strategies;
- supports Russian and English UI/status presentation;
- always performs bounded cleanup and restores the original Zapret2 service state after success, failure or cancellation.

The result is not a synthetic recommendation. Strategy Lab executes candidates on the real appliance and reports the strategies that survived the selected verification path.

## Native OPNsense integration

- OPNsense MVC/API/configd integration rather than an external control panel.
- Start/stop/status management for Zapret2.
- Managed supervisor ownership and `ipfw` divert rules.
- Transactional configuration changes with health verification.
- State-preserving package upgrades: a running service returns running; a stopped service stays stopped.
- Runtime checks validate the complete managed state instead of only one process.

## Traffic Strategy editor

The Settings page provides one multiline editor using native Zapret2 syntax plus project-managed target placeholders:

```text
<HOSTLIST:name>
<IPSET:name>
```

Profiles are separated with the normal Zapret2 boundary:

```text
--new
```

The backend expands managed targets while preserving the rest of the user-authored Zapret2 profile. Apply is transactional: invalid or unhealthy candidate configuration does not silently replace a working runtime.

## Voice Transmission — v0.5.2

The **Services → Zapret2 → Voice Transmission / Передача голоса** page (broken in released `0.5.2_194`, route corrected in released `0.5.3_2`) is a native editor for five independent, initially disabled STUN profiles: **Telegram, Discord, X (Twitter), SIP (VoIP), and Custom**. It is not a separate daemon, VPN, proxy, or a library of proven call-bypass presets.

- Each service has an enable checkbox, editable multiline native `dvtws2` STUN/UDP parameters, and one named destination IPv4 IPSET. Its text and addresses remain saved when disabled.
- Telegram shares the existing `hostlist.telegramips` dataset with Traffic Strategy; the other named IPSETs are also available to ordinary strategies.
- **Validate** checks a detached configuration without installing it. **Save inactive draft** persists an all-OFF configuration without activating it. **Apply** validates, saves and activates ON/OFF profiles through the *same* Config/FD9/runtime/IPFW transaction as Traffic Strategy.
- Enabled Voice profiles precede ordinary strategies in one `dvtws2` runtime. UDP capture is limited to selected destination IPSETs, ports and compatible WAN settings; `--filter-udp=*` does not create an unrestricted all-destination firewall rule.
- The page shows the shared service state and observable per-profile configuration, IPFW rules and counters. These observations do **not** establish packet-level STUN success, bidirectional media or a working call.
- When Apply or draft-save has an **uncertain** result, reload the page and inspect current configuration/runtime before attempting another change. Do not assume a browser timeout means nothing changed.

**Current verification boundary:** `v0.5.3` is a published full GitHub Release and FreeBSD 15 package repository update correcting the `0.5.2_194` Voice route defect. Its source and extracted `.pkg` passed the real OPNsense Router regression, and the owner confirmed that the installed `0.5.3_2` page opens with five profile fields. However, Russian field help and the WAN candidate failed in live testing; their `_3` correction is not yet accepted. GUI/CONFIG/BOOT, UDP/STUN, media and real calls remain **PENDING**, not PASS. SIP signaling/RTP, Discord discovery and Telegram non-STUN traffic remain ordinary-strategy concerns, not automatically handled by the STUN label. The existing TCP/proxy/routing configuration is outside this feature.

For details see the [current Voice specification](docs/architecture/VOICE_TRANSMISSION_GUI.md) and [completion gate](docs/VOICE_CODE_COMPLETION_GATE.md).

## Zapret2 Service manager

The GUI contains **Zapret2 Service / Служба Zapret2** for managing the upstream bol-van/zapret2 runtime independently from the OPNsense plugin package. It can:

- show the installed upstream release;
- show recent stable upstream releases;
- install Zapret2 for the first time;
- update, reinstall or downgrade to a selected release;
- preserve the previous running/stopped state;
- roll back if activation fails.

No OPNsense reboot is required after a successful managed operation.

## Installation from the OPNsense Web GUI

The stable release is published through the project-owned FreeBSD package repository on GitHub Pages. Register it once:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

Then open **System → Firmware → Plugins** and install **`os-zapret2-restyle`**.

The repository is transported over HTTPS and uses the project-approved unsigned pkg configuration `signature_type: "none"`.

## First setup

1. Open **Services → Zapret2 → Settings**.
2. Open **Zapret2 Service / Служба Zapret2** and install/select an upstream bol-van/zapret2 release.
3. Configure your managed targets and **Traffic Strategy**.
4. Apply the settings.
5. In **v0.5.2 and later**, optionally open **Services → Zapret2 → Voice Transmission** to configure destination-restricted STUN/UDP services; all profiles are OFF until explicitly enabled and applied.
6. Open **Services → Zapret2 → Laboratory** when you need to find a working bypass strategy for a blocked target.
7. Review a stable Laboratory result and add the required profile to the Traffic Strategy currently in use.

The plugin package and the upstream bol-van/zapret2 runtime intentionally have separate lifecycles.

## Example Traffic Strategy

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

### Managed domain targets

Enter one domain per line:

```text
youtube.com
*.youtube.com
```

### Managed IPv4 targets

Enter one IPv4 address or CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPv6 target-list management and IPv6 Laboratory target input are not currently implemented.

## Safe Apply and runtime lifecycle

Configuration activation follows a transactional path:

1. normalize and validate model input;
2. build candidate target files and runtime arguments;
3. validate the candidate configuration;
4. switch runtime state;
5. verify firewall/process health;
6. confirm the committed Config/runtime/firewall state; restore the prior state on a safely reversible failure, or **require inspection** when a native save/activation outcome is uncertain.

A failed or timed-out Apply does not automatically prove the original configuration is still active. The native worker and GUI distinguish pre-write rejection from states requiring explicit review.

Lifecycle operations are serialized. The plugin owns its PID/state files, supervisor state and temporary firewall rules so stale callbacks cannot tear down a replacement runtime.

## Upstream runtime management from shell

The Web GUI uses the same authoritative backend available to administrators:

```sh
# Install the latest stable upstream release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install

# Show recent stable upstream releases.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh show

# Install/reinstall/upgrade/downgrade to an exact release.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install v1.0.3

# Help.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh --help
```

## Useful runtime paths

```text
/var/db/zapret2-restyle/runtime.release
/var/db/zapret2-restyle/releases.cache
/var/db/zapret2-restyle/setup.status
/var/run/zapret2-execution.status
/var/run/zapret2-restyle/strategy-lab/
/var/log/zapret2/strategy-lab/
/var/log/zapret2/dvtws2.log
/var/log/zapret2/supervisor.log
```

`dvtws2` drops privileges to UID/GID `65534`; managed Lua/BLOB files and runtime directories are normalized to permissions appropriate for that boundary.

## Removal policy

Removing the plugin stops its managed service before package files disappear. Saved OPNsense configuration, downloaded upstream runtime, setup/runtime logs and shared dependencies are preserved for later reinstall or investigation.

## Release model

| Type | Meaning |
|---|---|
| **Testing package** | Persistent GitHub `.pkg` used for owner-assisted development/live verification. It does not automatically replace the Full Web/pkg release. |
| **Full Web/pkg release** | Verified package published through the project package repository and installable/upgradable from the OPNsense Web GUI. |

Version/product semantics are defined by `DEV-027` and the related version rules in [`docs/PROJECT_PRINCIPLES.md`](docs/PROJECT_PRINCIPLES.md). Testing/full-publication mechanics start at `GH-034` in [`docs/GITHUB_PUBLICATION.md`](docs/GITHUB_PUBLICATION.md). Those rule books are the normative source; this README only presents the user-facing release model.

## Documentation for contributors

Start with [`AGENTS.md`](AGENTS.md). It routes to the current handoff, state, rule books, roadmap and documentation index. The project keeps current state separate from historical evidence so development can continue without reconstructing old decisions from chat history.

Current published full release: **v0.5.3 / 0.5.3_2** (Voice UI route correction). [Release publication evidence](docs/verification/evidence/2026-10-17-v0.5.3-release-publication.md). Installed page opening was observed by the owner on `_2`; RU help/WAN and full Voice GUI/CONFIG/BOOT/STUN/MEDIA/CALL acceptance remain pending.

Useful entry points:

- [`docs/START_HERE.md`](docs/START_HERE.md)
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/INDEX.md`](docs/INDEX.md)
- [`docs/architecture/`](docs/architecture/)
- [`docs/verification/`](docs/verification/)

## Acknowledgements

This independent project builds on open-source work by **bol-van** and **Umur Gorur**. Their copyright notices and licenses are preserved in [`NOTICE`](NOTICE).

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

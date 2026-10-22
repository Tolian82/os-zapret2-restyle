# os-zapret2-restyle

> Native OPNsense plugin for **bol-van/zapret2**: manage the runtime, build DPI-bypass profiles, and automatically search for strategies that actually work from your firewall.

[![GitHub stars](https://img.shields.io/github/stars/Tolian82/os-zapret2-restyle?style=social)](https://github.com/Tolian82/os-zapret2-restyle)

> ⭐ **Like this project?** [Give it a star on GitHub](https://github.com/Tolian82/os-zapret2-restyle) — it helps others discover os-zapret2-restyle.  
> ⭐ **Понравился проект?** [Поставьте звёздочку на GitHub](https://github.com/Tolian82/os-zapret2-restyle) — это поможет другим пользователям найти os-zapret2-restyle.

| Project | Current release |
|---|---|
| **Full Web/pkg release** | [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) · `os-zapret2-restyle-0.5.6_1.pkg` · FreeBSD 15 stable pkg repository |
| **Current development candidate** | `v0.5.6_1` — owner-closed direct-provider Telegram Voice lab; MEDIA/CALL not achieved |
| **Target platform** | OPNsense 26.7 · FreeBSD 15 amd64 |
| **Runtime** | bol-van/zapret2 (`dvtws2`) |
| **OPNsense service** | `zapret` |
| **License** | MIT |

`os-zapret2-restyle` is an independent OPNsense integration around [bol-van/zapret2](https://github.com/bol-van/zapret2). It provides the managed engine, normal Traffic Strategies, Strategy Lab, and a five-service native Voice Transmission editor. The owner installed testing `0.5.3_28` on FreeBSD 15 OPNsense and **successfully saved Telegram ON through the shared Config/FD9/runtime/IPFW Apply**. The service and supervisor were running, the transaction journal was `committed`, and the Voice inspector reported `ready`. This confirms configuration and kernel interception, **not a working media call**.

On 20 October 2026 the owner **closed the Telegram Voice direct-provider research campaign with an unsuccessful media/call result**. On OPNsense, the native engine emitted original UDP, fake and synthetic STUN packets but reflector replies and `MEDIA_PASS/CALL_PASS` were not achieved despite bounded tests. The prior successful `tgcalls_cli` via pfSense is **not a comparable direct ISP control**: its route to Telegram Reflector uses the OpenVPN interface `ovpnc6`, next-hop `10.1.11.1`. Exact upstream blocking root cause remains undetermined; no universal impossibility of Telegram bypass is claimed. This `v0.5.6` stage **preserves Voice GUI and Config/Apply** but advertises **no verified Telegram voice-bypass profile**. [Closure evidence](docs/verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

## Architecture overview

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Arial, sans-serif","fontSize":"16px","lineColor":"#8ea5bd","background":"#0d1117"},"flowchart":{"nodeSpacing":16,"rankSpacing":23,"curve":"linear","htmlLabels":true}}}%%
flowchart LR
  subgraph CORE[" "]
    direction TB
    S["Traffic Strategies"]
    V["Voice Transmission"]
    M["Shared Zapret Model"]
    G["Shared Generator"]
    P["Regular and STUN Profiles"]
    F["TCP/UDP + IPSET<br/>IPFW Rules"]
    A["Shared Apply + Rollback"]
    R["One Managed dvtws2"]
    NOTE["Main workflow: Config → Apply → Runtime<br/>Lab temporarily pauses this service"]

    S --> M
    V --> M
    M --> G
    G --> P
    G --> F
    P --> A
    F --> A
    A --> R
    R ~~~ NOTE
  end

  subgraph LAB[" "]
    direction TB
    L["Laboratory"]
    T["Domain / IPv4 · Optional Host/SNI<br/>Standard / Extended Mode"]
    H["Capture Service State<br/>Stop Main Runtime"]
    B["Baseline Check<br/>Without Zapret2"]
    C["Search Candidates<br/>Temporary IPFW + dvtws2"]
    Q["Verify Stability<br/>TLS / HTTP / QUIC / UDP"]
    O["Cleanup and Restore<br/>Original Service State"]
    W["Results → Manual Transfer<br/>to Traffic Strategies"]

    L --> T --> H --> B --> C --> Q --> O --> W
  end

  CORE ~~~ LAB

  classDef entry fill:#052c4e,stroke:#174b72,color:#a7d8ff,stroke-width:1px,font-size:16px;
  classDef step fill:#052c4e,stroke:#174b72,color:#a7d8ff,stroke-width:1px,font-size:16px;
  classDef output fill:#07385b,stroke:#3277a2,color:#c6e8ff,stroke-width:1px,font-size:16px;
  classDef note fill:transparent,stroke:transparent,color:#8298aa,font-size:16px;
  class S,V,L entry;
  class M,G,P,F,A,T,H,B,C,Q,O step;
  class R,W output;
  class NOTE note;
  style CORE fill:transparent,stroke:transparent
  style LAB fill:transparent,stroke:transparent
```

## Strategy Lab — find a working bypass strategy instead of guessing

**Strategy Lab is the flagship feature of the project.** Give it a blocked domain or IPv4 address and it automatically tests real Zapret2 strategy families from the OPNsense firewall, verifies stable winners, and returns complete profiles ready to copy into **Traffic Strategy**.

The Laboratory is designed around one practical question:

> **Which Zapret2 strategy actually works for this target, on this ISP, from this exact OPNsense installation?**

What it does:

- accepts a blocked **domain or IPv4 address**;
- supports optional **Host / SNI** for fixed-IP HTTPS/TLS/QUIC testing;
- measures a clean baseline before trying bypass candidates;
- runs deterministic native Zapret2 strategy candidates with temporary runtime and firewall rules;
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

## Voice Transmission — native common engine (v0.5.6)

The **Services → Zapret2 → Voice Transmission / Передача голоса** page is a native editor for five independent, initially disabled STUN profiles: **Telegram, Discord, X (Twitter), SIP (VoIP), and Custom**. It is not a separate daemon, VPN, proxy, or a library of proven call-bypass presets.

- Each service has an enable checkbox, editable multiline native `dvtws2` STUN/UDP parameters, and one named destination IPv4 IPSET. Its text and addresses remain saved when disabled.
- Telegram shares the existing `hostlist.telegramips` dataset with Traffic Strategy; the other named IPSETs are also available to ordinary strategies.
- **Validate** checks a detached configuration without installing it. **Save inactive draft** persists an all-OFF configuration without activating it. **Apply** validates, saves and activates ON/OFF profiles through the *same* Config/FD9/runtime/IPFW transaction as Traffic Strategy.
- Enabled Voice profiles precede ordinary strategies in one `dvtws2` runtime. UDP capture is limited to selected destination IPSETs, ports and compatible WAN settings; `--filter-udp=*` does not create an unrestricted all-destination firewall rule.
- The page shows the shared service state and observable per-profile configuration, IPFW rules and counters. Per-profile status remains beneath its checkbox with help on or off; the three navigation labels localize correctly in Russian on regular page loads. Both GUI corrections were confirmed on the installed test package. These observations do **not** establish packet-level STUN success, bidirectional media or a working call.
- When Apply or draft-save has an **uncertain** result, reload the page and inspect current configuration/runtime before attempting another change. Do not assume a browser timeout means nothing changed.

**Current verification boundary:** Voice GUI/Config, shared Apply and managed IPFW outbound interception have been verified at their stated evidence levels. Telegram media/call through the owner's direct-provider OPNsense path **did not pass**, and this research campaign was explicitly closed. The previous pfSense direct-reflector `MEDIA_PASS` was on an OpenVPN-routed Telegram subnet, not the same ISP path; no validated Telegram bypass preset is claimed. Other Voice services remain independently unqualified for media, and the Squid/sing-box/SSH/routing lab is not managed by the plugin.

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

Full Web/pkg release: **[v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) / 0.5.6_1**. This stage preserves native GUI/engine and closes Telegram provider-path research with no MEDIA/CALL acceptance. The pfSense success was VPN-route-confounded. No new tested bypass algorithm is claimed. See [release notes](docs/releases/v0.5.6.md) and [closure](docs/verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

Useful entry points:

- [`docs/START_HERE.md`](docs/START_HERE.md)
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/INDEX.md`](docs/INDEX.md)
- [`Native Voice TNAS lab`](docs/architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md)
- [`docs/architecture/`](docs/architecture/)
- [`docs/verification/`](docs/verification/)

## Acknowledgements

This independent project builds on open-source work by **bol-van** and **Umur Gorur**. Their copyright notices and licenses are preserved in [`NOTICE`](NOTICE).

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

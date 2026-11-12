# os-zapret2-restyle

[![Release](https://img.shields.io/github/v/release/Tolian82/os-zapret2-restyle?style=flat-square&label=release)](https://github.com/Tolian82/os-zapret2-restyle/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/Tolian82/os-zapret2-restyle/ci.yml?branch=main&style=flat-square&label=build)](https://github.com/Tolian82/os-zapret2-restyle/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square)](LICENSE)

> [!IMPORTANT]
> This project and its documentation are provided for scientific, technical, and educational purposes only.
> Using these materials for purposes other than research, review, or learning may violate applicable laws and regulations.
> Users are responsible for ensuring that their use complies with applicable law. The authors do not endorse or accept responsibility for unlawful use or misuse of these materials.

> [!TIP]
> Native OPNsense plugin for **bol-van/zapret2**: manage the runtime, build DPI-bypass profiles, and automatically search for strategies that actually work from your firewall.

[![GitHub stars](https://img.shields.io/github/stars/Tolian82/os-zapret2-restyle?style=social)](https://github.com/Tolian82/os-zapret2-restyle)

> [!WARNING]
> ⭐ **Like this project?** [Give it a star on GitHub](https://github.com/Tolian82/os-zapret2-restyle) — it helps others discover os-zapret2-restyle.
>
> ⭐ **Понравился проект?** [Поставьте звёздочку на GitHub](https://github.com/Tolian82/os-zapret2-restyle) — это поможет другим пользователям найти os-zapret2-restyle.

| Project | Current release |
|---|---|
| **Full Web/pkg release** | [**v0.6.5**](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.5) / [`os-zapret2-restyle-0.6.5_1.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5/os-zapret2-restyle-0.6.5_1.pkg) — **STABLE RELEASE PUBLISHED** for OPNsense 26.7 / `FreeBSD:15:amd64`; SHA-256 `c68965787007f4b8ecb257e7ae06b2f5609c948b2b3b2246f0070ebd3fb63dc1`, [SHA256SUMS](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.5/SHA256SUMS). [Native release + Pages/pkg SUCCESS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43291066886). |
| **Previous stable release** | [v0.6.4](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.4) / `0.6.4_1.pkg` remains immutable. |
| **Current development candidate** | `v0.6.5_2` — release-evidence and current-documentation source revision **ONLY**, not an additional `.pkg`. The immutable stable package remains `0.6.5_1.pkg`. |
| **Owner-tested candidate** | [v0.6.4_50](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.4_50) — owner manually accepted complete #936 functionality and #1084 Laboratory visuals; earlier `_48` joint Apply accepted. This is prior acceptance, not physical installation of `0.6.5_1.pkg`. |
| **Target platform** | OPNsense 26.7 · FreeBSD 15 amd64 |
| **Runtime** | bol-van/zapret2 (`dvtws2`) |
| **OPNsense service** | `zapret` |
| **License** | MIT |

`os-zapret2-restyle` integrates the [bol-van/zapret2](https://github.com/bol-van/zapret2) native `dvtws2` engine with OPNsense: transactional Traffic Strategies, automatic Strategy Lab testing, upstream runtime management and a configurable Voice Transmission page. The plugin and upstream Zapret2 engine have separate installation/update lifecycles.

**v0.6.5 scope:** Owner accepted the complete [feature #936](https://github.com/Tolian82/os-zapret2-restyle/issues/936), P0–P6 and Lab Help [#1084](https://github.com/Tolian82/os-zapret2-restyle/issues/1084) on actual OPNsense. Features include native Hostlist `!`/`^`, Python domain policy, multiple native payload/Lua profiles, RU/EN Strategies/Voice, safe read-only Preview and matched Lab Help. Auto Restart is **not included**; it is separately postponed to [#1052](https://github.com/Tolian82/os-zapret2-restyle/issues/1052). [Release notes](docs/releases/v0.6.5.md).

**Verification limits:** The final `0.6.5_1.pkg` was officially built for `FreeBSD:15:amd64` and published through GitHub Release and Pages/pkg, with identical source/repository artifact identity verified by the [release pipeline](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43291066886); owner-manual GUI acceptance remains grounded in the earlier installed `0.6.4_48`/`0.6.4_50` feature builds, not a reported physical owner installation of the final `_1.pkg`. No universal ISP bypass, all Telegram MEDIA/CALL, independent owner IPv6 WAN capture or abrupt power-loss recovery is asserted.

**Stable release evidence:** [v0.6.5](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.5) is a genuine stable release, semantic tag points to `64263ef9c29093be05b3bcdda166c6f2e890a735` ([preparation PR #1089](https://github.com/Tolian82/os-zapret2-restyle/pull/1089)); native `0.6.5_1.pkg` GitHub asset is 6,848,651 bytes with SHA-256 `c68965787007f4b8ecb257e7ae06b2f5609c948b2b3b2246f0070ebd3fb63dc1`. The full [release workflow #43291066886](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43291066886) reported PASS for release validation, native OPNsense 26.7 build, immutable Release assets/checksum and Pages/pkg repository deployment. [Exact immutable release publication record](docs/verification/evidence/2026-11-12-v0.6.5-full-release-publication.md). The old [v0.6.4](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.4) remains untouched.

## IPFW rule-number ranges

The plugin uses fixed **IPFW rule numbers** (these are **not TCP/UDP ports**):

| Component | IPFW rule numbers |
|---|---|
| Normal Zapret2 / Traffic Strategies | `19000–19010` |
| Strategy Lab | `19100–19131` |

Divert socket ports are separate. Per the owner-approved native integration scope, no new system-wide IPFW collision scanner, shaper-flush listener, dynamic rule allocation or `pfilctl` conversion is planned. The plugin must not globally disable/re-enable PF as part of normal runtime or release operations. [Native OPNsense TЗ v1.5](docs/architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) and [completion plan](docs/architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) define current development priorities.

## What's new in v0.6.5

- **Native Hostlist `!` / `^`:** local-exclusion and exact-domain matching, safely validated through unified Python policy.
- **Real Zapret2 profile semantics:** first-match ordering, multiple payload/Lua handlers, `--new` and duplicate-list safeguards.
- **Complete RU/EN Strategies and Voice:** forms, validation, popup/Full Help, installed Lua/BIN inventory, consistent 13px guidance.
- **Read-only Validate and Preview:** inspect unsaved profiles and target/filter details without permanent Config/FD9/IPFW/Voice changes.
- **Native Laboratory appearance:** OPNsense gray top Help row; the owner confirmed visual parity on installed `0.6.4_50.pkg`.
- **Native lifecycle retained:** WAN-first, original FD9, shared engine/Voice and native pkg hooks. Auto Restart deferred to [#1052](https://github.com/Tolian82/os-zapret2-restyle/issues/1052).

[Full release notes, installation and verification limits](docs/releases/v0.6.5.md).

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
    T["Domain / IPv4 / IPv6 · Optional Host/SNI<br/>Standard / Extended Mode"]
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

**Strategy Lab is a major feature of the project.** Give it a target domain, IPv4 or IPv6 address and it evaluates real Zapret2 strategy families on the OPNsense firewall, checks stability, and returns verified candidates for **manual** use in Traffic Strategy. It cannot guarantee a working bypass on every ISP or target.

![Strategy Lab — completed real-world testing run](docs/screenshots/strategy-lab.png)

*Screenshot: a completed Strategy Lab run with three verified candidates and successful restoration of the original Zapret2 service. Results are specific to the tested ISP and target.*

The Laboratory is designed around one practical question:

> **Which Zapret2 strategy actually works for this target, on this ISP, from this exact OPNsense installation?**

What it does:

- accepts a blocked **domain, IPv4 address or IPv6 literal** (IPv6 targets require the Lab IPv6 checkbox);
- supports optional **Host / SNI** for fixed-IP HTTPS/TLS/QUIC testing;
- measures direct reachability with private [curl-impersonate](https://github.com/lexiforest/curl-impersonate) Chrome-compatible TLS/HTTP/HTTP/3 probing with ECH disabled for consistent accessibility checks (not a browser ECH-on compatibility test) before trying bypass candidates; direct accessible targets are not reported as needing bypass;
- runs deterministic native Zapret2 strategy candidates with temporary runtime and firewall rules;
- attributes candidate traffic to exact controlled source ports and temporary firewall rules;
- checks stability, maintains at most three confirmed finalists, and replays selected profiles before recommending them;
- counts a verified TLS or QUIC handshake **or** an authentic final HTTP response (including 4xx/5xx) as endpoint reachability; preserves the distinction between target identity, transport evidence and successful bypass;
- supports **Extended** protocol checks for TLS 1.2, HTTP, QUIC and optional Generic UDP;
- treats bare-IP QUIC truthfully: without Host/SNI it is skipped rather than reported as tested;
- can test Generic UDP independently against eligible pinned endpoints, with family-specific support and explicit unavailable outcomes;
- emits complete final profiles, including `--ipset-ip=<target>` for fixed-IP strategies;
- supports Russian and English UI/status presentation, saved-job read-only lookup by Job ID, F5 persistence of selected saved results and an inline Job ID copy control;
- supports temporary, explicitly started browser circular validation for eligible verified TLS 1.3 candidates; it can affect other LAN clients while active and automatically stops/restores service state;
- includes bounded cleanup and restoration of original Zapret2 service state after success, failure or cancellation, with restoration errors reported rather than hidden.

**IPv6 in Strategy Lab:** The checkbox under **Mode / Режим** is OFF by default. OFF runs IPv4-only checks even if a domain has AAAA records; ON adds eligible routed IPv6 endpoints, including AAAA-only names and IPv6 literals. The one-job limits are **Standard 150 s (single family) / 200 s (eligible dual family)** and **Extended 270 s / 350 s**. Merely selecting IPv6 cannot extend the deadline without actual eligible A+AAAA and IPv6 connectivity. IPv6-only QUIC is explicitly skipped when its dedicated helper cannot test it; never treat a skipped probe as success. The available native FreeBSD 15.1 IPv6 evidence is not a substitute for owner WAN acceptance.

A result reflects the selected measured path rather than a speculative recommendation. A candidate is not a proven winner without its required verification and replay. QUIC/HTTP/3 availability at one endpoint does not establish bypass on a blocked service.

## Native OPNsense integration

- OPNsense MVC/API/configd integration rather than an external control panel.
- Start/stop/status management for Zapret2.
- Managed supervisor ownership and `ipfw` divert rules.
- Transactional configuration changes with health verification.
- State-preserving package upgrades: a running service returns running; a stopped service stays stopped.
- Runtime checks validate the complete managed state instead of only one process.

## Traffic Strategy editor

The **Strategies / Стратегия** Settings page provides one multiline editor using native Zapret2 syntax plus project-managed target placeholders:

```text
<HOSTLIST:name>
<IPSET:name>
```

Profiles are separated with the normal Zapret2 boundary:

```text
--new
```

The backend expands managed targets while preserving the rest of the user-authored Zapret2 profile. Apply is transactional: invalid or unhealthy candidate configuration does not silently replace a working runtime. The **upper Apply** in the Zapret2 Service panel installs or changes the selected *upstream Zapret2 release*; the **lower Apply** saves and activates *Traffic Strategies*. They are separate operations and are serialized for safety.

## Global Exclude IPSet and dual-stack targets

**Traffic Strategies → Exclude IPSet** is directly below **Exclude Domains** in both normal and Advanced views. Enter IPv4 or IPv6 addresses/CIDRs (one per line); nested, overlapping and adjacent blocks are canonicalized without changing the represented addresses. The plugin compiles one managed exclusion set and injects `--ipset-exclude` into every executable ordinary Strategy and Voice profile, including profiles assembled with `--new`, templates/imports and installed extra resources. **Exclude Domains** remains domain-only and is not applied to Voice/STUN or converted into IP addresses.

Managed IPSET targets (including all five Voice destination lists) accept IPv4/IPv6. Every user-managed include/exclude/Voice IP list rejects `0.0.0.0/0`, `::/0` and equivalent full-family coverage such as two complementary `/1` networks. Global address exclusions are destination-based, not a guarantee that an ISP's blocking policy is bypassed. The installed audit confirms correct profile attachment and valid saved state; only separate native FreeBSD 15.1 traffic tests have qualified real IPv4/IPv6 Exclude behavior. Actual per-packet WAN exclusion on the installed gateway remains unverified.

[Detailed IPv4/IPv6 and Exclude specification](docs/architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md).

## Additional Resources — installed Lua/BIN help

os-zapret2-restyle offers **optional installation and use of an expanded, integrity-verified Lua/BIN resource pack** from [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources). **Install Additional Resources / Установить дополнительные ресурсы** on the Strategies page is a manual action: it checks the catalog and files, installs the optional resources, and uses the original native Zapret2 service restart and health verification. The pack is not installed automatically on page load, normal service start, plugin upgrade or upstream switch.

In the current plugin, **Remove Additional Resources / Удалить дополнительные ресурсы** appears directly below Install **only when Advanced mode is enabled**. After a fresh removal preview, it requires explicit confirmation of the exact resource count (`REMOVE N`). It removes all additional top-level Lua/BIN files **not tracked by the installed upstream Zapret2 Git HEAD**, including manually added files; it preserves the upstream-tracked files and saved Strategies/Voice settings. The native transaction checks current saved configuration, temporarily quarantines the additional files, then uses the existing combined Strategies+Voice Apply/Start path and verifies that Zapret2 is running correctly with standard files only. On a proven failure it restores the original files and previous working service; if restoration cannot be verified, it reports a recovery-required failure instead of claiming success. **Review the planned count and your own custom Lua/BIN files before confirming; removal is not an ordinary hide/disable operation.**

With **Full Help / Справка** enabled, the installed files appear in two cached columns: `.lua` on the left and `.bin` on the right. **Green** identifies resources tracked in the installed upstream Git HEAD, and **blue** identifies other installed files (including optional extras). The GUI reads an atomically published local JSON cache; it does not scan GitHub or Git on each Help view. After removal the Help area shows the not-installed/install explanation, and a new Strategy Lab Job uses the currently installed resource set. The owner previously confirmed the columns, colors and Help persistence after F5 on an installed testing package.

**Verification means catalog integrity, file provenance, guarded native integration, and the specific observed runtime/GUI tests.** It does **not** prove that every Lua script or BIN payload bypasses DPI, that all strategy/resource combinations interoperate, or that Telegram or other Voice calls succeed. The existing saved configuration is not automatically rewritten or Applied by installing extra resources. [Acceptance details and unrun-case limits](docs/verification/evidence/2026-10-27-v0.5.9_47-stage11-owner-final-acceptance.md).

## Voice Transmission — shared native runtime

The **Services → Zapret2 → Voice Transmission / Передача голоса** page is a native editor for five independent, initially disabled STUN profiles: **Telegram, Discord, X (Twitter), SIP (VoIP), and Custom**. It is not a separate daemon, VPN, proxy, or a library of proven call-bypass presets.

- Each service has an enable checkbox, editable multiline native `dvtws2` STUN/UDP parameters, and one named destination IPv4/IPv6 IPSET. Its text and addresses remain saved when disabled.
- Telegram shares the existing `hostlist.telegramips` dataset with Traffic Strategy; the other named IPSETs are also available to ordinary strategies.
- **Validate** checks a detached configuration without installing it. **Save inactive draft** persists an all-OFF configuration without activating it. **Apply** validates, saves and activates ON/OFF profiles through the *same* Config/FD9/runtime/IPFW transaction as Traffic Strategy.
- Enabled Voice profiles precede ordinary strategies in one `dvtws2` runtime. UDP capture is limited to selected destination IPSETs, ports and compatible WAN settings; `--filter-udp=*` does not create an unrestricted all-destination firewall rule.
- The page shows the shared service state and observable per-profile configuration, IPFW rules and counters. Per-profile status remains beneath its checkbox with help on or off; the three navigation labels localize correctly in Russian on regular page loads. Both GUI corrections were confirmed on the installed test package. These observations do **not** establish packet-level STUN success, bidirectional media or a working call.
- When Apply or draft-save has an **uncertain** result, reload the page and inspect current configuration/runtime before attempting another change. Do not assume a browser timeout means nothing changed.

**Current verification boundary:** The owner explicitly accepted the complete **Voice Transmission service test scope** on the current testing installation. This confirms the plugin's reported GUI/Config/shared runtime behavior in the tested configurations, not a guaranteed successful Telegram/Discord/SIP/X call or media bypass across providers; those network-specific results require separate evidence. The Squid/sing-box/SSH/routing lab is not managed by this plugin.

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

Full releases are published through the project-owned FreeBSD package repository on GitHub Pages. Register it once using the OPNsense **root shell**:

```sh
fetch -o /usr/local/etc/pkg/repos/zapret2-restyle.conf \
  https://tolian82.github.io/os-zapret2-restyle/zapret2-restyle.conf
pkg update -f
```

Then open **System → Firmware → Plugins** and install **`os-zapret2-restyle`**.

The repository is transported over HTTPS and uses the project-approved unsigned pkg configuration `signature_type: "none"`.

## Installing a testing package — native `.pkg` ONLY

**Owner decision 10 November 2026:** No new companion `.sh` installers, no SH download links, no wrapper commands. Each testing prerelease publishes one verified native FreeBSD:15:amd64 **`.pkg`** asset with its SHA-256. Example using the immutable, owner-tested native package `v0.6.3_52.pkg` (the next source revision `_53` was docs-only):

```sh
fetch -o /root/os-zapret2-restyle-0.6.3_52.pkg https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.3_52/os-zapret2-restyle-0.6.3_52.pkg
pkg add -f /root/os-zapret2-restyle-0.6.3_52.pkg
pkg info -x os-zapret2-restyle
```

**Dependencies:** local `pkg add -f` does not download missing dependencies. On a fresh OPNsense first inspect the verified physical `+MANIFEST` (e.g. `tar -xOf /root/os-zapret2-restyle-0.6.3_52.pkg +MANIFEST`), then install only its missing/outdated package dependencies interactively using **official OPNsense** `pkg install -r OPNsense <missing-package-names>`; review removals/upgrades before confirmation. Never enable stock FreeBSD repositories, force ignored dependencies (`pkg add -M`), bypass native package hooks, or run `pkg install -f <local.pkg>` (previous native solver SIGSEGV). Keep the package's `PLUGIN_DEPENDS` unchanged and no new testing pkg repository. Package SHA-256 is validated during release publication; the owner may verify it independently. Earlier `.sh` release assets and historic installer experiments remain immutable historical records, **not** current installation instructions. This policy supersedes prior SH delivery parts of `CHAT-027`, `GH-060`, `GH-061` and LC-16 without altering the required nine-stage acceptance scope.


## First setup

1. Open **Services → Zapret2 → Settings**.
2. Open **Zapret2 Service / Служба Zapret2** and install/select an upstream bol-van/zapret2 release.
3. Configure your managed targets and **Traffic Strategy**.
4. Apply the settings.
5. Optionally open **Services → Zapret2 → Voice Transmission** to configure destination-restricted STUN/UDP services; all profiles are OFF until explicitly enabled and applied.
6. Open **Services → Zapret2 → Laboratory** when you need to find a working bypass strategy for a blocked target.
7. Review a stable Laboratory result and add the required profile to the Traffic Strategy currently in use.

The plugin package and the upstream bol-van/zapret2 runtime intentionally have separate lifecycles.

## Clean-install YouTube defaults

On an **actually clean** first setup with no existing Zapret2 configuration, the plugin initializes exactly these ten entries in **YouTube Domains**, without automatically enabling traffic interception. Ordinary reinstall over saved user configuration does not re-seed or overwrite any user-edited or deliberately blank fields:

~~~text
youtube.com
googlevideo.com
yt.be
youtu.be
ytimg.com
youtubei.googleapis.com
youtube.googleapis.com
youtube-nocookie.com
ggpht.com
ssl.gstatic.com
~~~

The initially seeded **Traffic Strategy** is:

~~~text
--filter-tcp=80,443
--filter-l7=http,tls
<HOSTLIST:youtube>
--blob=http_iana_org
--out-range=-d10
--payload=http_req
--lua-desync=fake:blob=http_iana_org:tcp_md5
--lua-desync=multisplit:pos=method+2
--payload=tls_client_hello
--lua-desync=multisplit:pos=midsld:seqovl=1

--new

--filter-udp=443
--filter-l7=quic
<HOSTLIST:youtube>
--out-range=-d10
--payload=quic_initial
--lua-desync=fake:blob=fake_default_quic:repeats=5
~~~

These profiles use upstream `http_iana_org.bin` (resolved from the plugin shorthand `--blob=http_iana_org`) and built-in `fake_default_quic`, with **no optional Lua/BIN resources**. The default is deliberately different from the historical `tls7` example, which depended on a missing file. These values are created only for a truly empty first-install configuration; saving user-empty fields and ordinary reinstall must not restore them. A seeded strategy does **not** independently prove a working DPI bypass for a particular ISP.

### Managed domain targets

Enter one domain per line:

```text
youtube.com
*.youtube.com
```

### Managed IPv4/IPv6 targets

Enter one IPv4 address or CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPv6 targets are accepted as single addresses or CIDR networks (for example, `2001:db8:1234::/48`) subject to the full-family exclusion policy above. The example prefix is documentation-only; use addresses assigned to your environment.

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

# Uninsatll Purge.
/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh --purge
/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh --dry-run

# Help.
/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh --help
```

## Useful runtime paths

```text
/usr/local/etc/zapret2/lua/
/usr/local/etc/zapret2/files/fake/
/var/db/zapret2-restyle/runtime.release
/var/db/zapret2-restyle/releases.cache
/var/db/zapret2-restyle/setup.status
/var/run/zapret2-execution.status
/var/run/zapret2-restyle/strategy-lab/
/var/log/zapret2/strategy-lab/
/var/log/zapret2/dvtws2.log
/var/log/zapret2/supervisor.log
```

The two Zapret2 resource directories above hold both installed upstream-tracked files and optional additional resources; the Lua/BIN Help and removal plan distinguish their provenance using the local upstream Git HEAD.

The managed `dvtws2` process drops privileges to UID/GID `65534`; managed Lua/BLOB files and runtime directories are normalized to permissions appropriate for that boundary.

## Independent full removal — persistent CLI

**Normal GUI uninstall is not purge.** It preserves user data and the separately owned purge CLI; destructive complete removal requires an explicit confirmation and verified private backup.

The [canonical G01 purge script](scripts/purge-os-zapret2-restyle.sh) is deployed by native `POST_INSTALL` from a package-owned template as a separately owned CLI at `/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh`. **Ordinary GUI/`pkg delete` uninstall preserves this CLI** and user Config/upstream runtime/Lua/BIN; an explicitly confirmed **full purge** removes the plugin if still installed, then all owned Zapret2 remnants and the independent script itself. This behavior was checked in previous owner testing, and the owner also reports successful full purge and clean reinstall of the published `_52` package. Historical `_33` is defective (interactive stdin EOF and purge-script removed on ordinary uninstall) and must not be used for these operations.

Read-only root-console inspection:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh --dry-run
```

Only when independently authorizing irreversible complete removal:

```sh
/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh --purge
```

Full purge requires the exact `PURGE OS-ZAPRET2-RESTYLE` phrase through controlling `/dev/tty` **before any mutation**, a verified private `/conf/config.xml` backup under `/root/zapret2-restyle-purge-backups`, and scoped process/FD9/IPFW ownership checks. The same process works if the package was already removed ordinarily; foreign system data, shared dependencies and unrelated services must remain untouched. `--keep-repo` is not full removal; `--yes-disposable` is isolated-CI-only. The «Полезные ссылки» purge card is removed from the Strategies GUI. Review the [G01 guide](docs/verification/G01_STANDALONE_PURGE_GUIDE.md) and [nine-step G11 acceptance](docs/verification/G11_PUBLISHED_EXISTING_UPGRADE_PURGE_CLEAN.md). **The owner has confirmed clean purge/reinstall and prior ordinary GUI uninstall/reinstall preservation; see the v0.6.4 release notes for the separately stated evidence limits.**

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

The full [v0.6.4 release](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.4) is **published** with package `0.6.4_1.pkg`; [v0.6.4 release notes](docs/releases/v0.6.4.md) distinguish native release verification from prior owner's `_52` functional acceptance. [v0.6.3](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.3) remains immutable. [#954](https://github.com/Tolian82/os-zapret2-restyle/issues/954) tracks intermittent isolated Guest B network egress; independent [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936) covers future UI semantics. The owner subsequently confirmed successful GUI upgrade and clean installation of the final stable `_1` archive. This does not imply universal ISP/media/IPv6 success.

Useful entry points:

- [`docs/START_HERE.md`](docs/START_HERE.md)
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/INDEX.md`](docs/INDEX.md)
- [`Native Voice TNAS lab`](docs/architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md)
- [`docs/architecture/`](docs/architecture/)
- [`docs/verification/`](docs/verification/)

## Acknowledgements

This independent project builds on open-source work by **bol-van** and **Umur Gorur**, and uses the browser-compatible HTTP client from **[lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate)**. See [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for project credits and [`NOTICE`](NOTICE) for copyright attribution.

## License

MIT. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE) and [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for upstream attribution.

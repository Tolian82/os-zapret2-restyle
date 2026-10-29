# Stage 5 — bounded WAN capture acquisition plan (no execution)

**State (29 October 2026): source/CI-qualified via [PR #723 Project/Voice/FreeBSD15/package checks](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40920798059); owner-live execution and WAN acceptance OPEN.** **No owner-live test, service modification, IPFW rule, Config write, WAN capture or TLS probe has been performed.** Stable release `v0.6.0` and published/owner-installed `os-zapret2-restyle-0.6.1_12` remain unchanged.

## Why this increment exists

The existing [WAN target preflight](STAGE5_WAN_TARGET_READONLY.md) proposes at most four TLS/443 candidates but cannot confirm actual source IP/port or selected strategy. The [offline packet attribution helper](STAGE5_WAN_OFFLINE_PCAP_ATTRIBUTION.md) can correlate two **existing** Ethernet PCAPs when it receives a strict manifest with the source/destination five-tuple; it cannot itself acquire or attest those captures. [The approved A/B safety protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) requires an attributable source before any authorized GUI Exclude edit.

This incremental [standalone acquisition-plan generator](../../scripts/stage5-wan-acquisition-plan.py) bridges only the **plan format**: an IPv4 or IPv6 destination, same-family source address, WAN interface, DNS host and one designated local TCP port become *two proposed* tcpdump BPF filters, two pinned curl HEAD command-argument arrays, strict per-phase bounds and one manifest exactly matching the preexisting offline analyzer. **It does not execute even one command in the plan.** It imports no socket, subprocess, network or system-mutation module.

The plan labels itself `PLAN_ONLY_UNEXECUTED`. Every evidence flag remains false; installed A07/A08 remain `OPEN`. The interface is only declared, not verified; a remotely resolved target may be stale; source IP may not be configured on the stated WAN; source port may already be busy; the host may be unavailable; source port reuse between connections may be blocked by TCP state. Those are future **fail-closed** preflight conditions, not excuses to silently choose a different endpoint.

## Safe developer-only example — generates JSON; no network traffic

```sh
python3 scripts/stage5-wan-acquisition-plan.py \
  --domain yt3.ggpht.com \
  --remote-ip 142.251.127.198 \
  --source-ip 192.168.80.251 \
  --source-port 54111 \
  --wan vtnet1 > example-unexecuted-plan.json
```

The example reuses an owner-observed historical IPv4 route; it is **not proof these source/target addresses are correct today**. IPv6 plans require two legitimate same-family IPv6 addresses and use curl's bracketed `--resolve` syntax. The helper never assumes an IPv4-only WAN can test IPv6.

## Proposed future command sequence — not authorized for direct execution

Each phase has a strictly scoped BPF expression for *both directions* of exactly `source_ip:source_port <-> remote_ip:443`, one `tcpdump` argument vector (`-i`, `-nn`, `-s 4096`, `-c 128`, `-w`), and a single curl request pinned by `--resolve`, `--interface host!<source_ip>`, `--local-port <source_port>`, `--noproxy '*'`, `--http1.1`, `--head`, `--retry 0`, `--connect-timeout 5`, `--max-time 12`. Planned hard capture deadline: **18 seconds**. These numbers are **parameters only** until a separately tested controller actually enforces the deadline, process cleanup, native interface link type and packet ownership. **Do not copy and run the output command arrays on OPNsense.**

Before a single authorized real capture: attest the current production Voice/Config/IPFW owner, native active strategy selection, existing WAN/route, source-address ownership, BPF linktype `DLT_EN10MB`, exclusive free TCP source port, destination still in the intended HOSTLIST and **not** in global Exclude or Voice IPSET for baseline. The current candidate selector/owner snapshot evidence may help, but cannot establish baseline Lua modification.

The consent-gated live controller must reliably start and *observe readiness of* tcpdump **before** starting curl; use a hard deadline and handle every exception/interrupt with process termination and removal of its temporary artifacts; leave raw PCAP locally. If the first phase lacks direct evidence of actual strategy modification, **do not request or perform GUI Apply**. A successful HTTPS status or a differing SHA-256 fingerprint is never sufficient. The owner must separately authorize and apply temporary Exclude in the supported GUI and restore the exact previous state. After independent post-restoration health checks, the [offline analyzer](STAGE5_WAN_OFFLINE_PCAP_ATTRIBUTION.md) can classify attributable observations, not alone prove A07/A08 or Stage-5 installed IPv6.

## Executed verification and open gates

[`scripts/test-stage5-wan-acquisition-plan.py`](../../scripts/test-stage5-wan-acquisition-plan.py) contains 13 **locally executed** offline regressions including IPv4/IPv6, bracketed IPv6 pinned resolution, same flow filters and manifest, bounded capture/probe, strict domain/interface/port/address input rejection, no network imports/automatic execution, and permanent `OPEN`/false evidence flags. Python syntax and focused unit checks passed locally before PR. The source is registered in GitHub CI, and [PR #723 Project/Voice/native FreeBSD15/package CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40920798059) PASS on this source candidate, including all 13 focused acquisition-plan tests. No real WAN packets were observed.

Still **OPEN**: confirmed live WAN source/port ownership, bounded real capture lifecycle and provenance, baseline active Lua modification, Exclude suppression of that same modification, successful normal GUI Apply/restoration, IPv6 WAN reinjection, real Telegram Voice calls/media, Stage 6 Strategy Lab IPv6 checkbox, EN/F5 installed UI acceptance. No new package or version is needed for this plan-only tool.

# Telegram: OpenWrt reference — GOST, Podkop and youtubeUnblock

**Status 20.10.2026:** confirmed **installed/configured component roles** based on owner-supplied screenshots and GOST UCI; observed **one successful same-binary direct-UDP reflector control** through pfSense `192.168.1.140`, failures via OPNsense `192.168.1.2` and directly via OpenWrt `192.168.1.236`. The **path of real Telegram UDP configured for SOCKS5 is not yet packet-qualified**. **No causal attribution to youtubeUnblock has been established.**

This reference is the active conceptual architecture. Owner-provided facts and individual tests remain preserved in [contemporaneous evidence](../verification/evidence/2026-10-20-openwrt-236-youtubeunblock-topology.md) and [positive pfSense control](../verification/evidence/2026-10-20-tgvoice-gateway-140-positive-control.md). It must not silently override owner correction with the earlier idea that Squid forwards arbitrary Telegram UDP to OpenWrt.

## Actual elements and known configuration

| Element | Proven configuration | Traffic effect that remains to be measured |
|---|---|---|
| Real Telegram app | **explicit SOCKS5 `192.168.1.236:1070`** | Whether its live voice UDP uses SOCKS5 UDP ASSOCIATE, goes directly to another destination, or chooses a different transport |
| OpenWrt VM on TNAS | `192.168.1.236`, separate VM, not Docker | Its route, forwarding, effective nft/netfilter hooks, actual egress interfaces and NAT for the real Telegram stream |
| GOST `universal_lan` | `mode=auto`, `listen=0.0.0.0:1070`, enabled | The section itself specifies **no upstream**; do not equate it automatically to HTTP parent or prove UDP relay |
| Podkop MAIN | Proxy, Telegram community selection, `socks5://127.0.0.1:1088`; **UDP-through-TCP off** in GUI | Effective DNS/routing/mark/nft rules and whether real app voice flow matches them |
| GOST `main` | `mode=socks5`, `listen=127.0.0.1:1088?dns=0`, upstream `http://185.203.117.88:33128?keepalive=true`, enabled | Exactly which Telegram flows traverse this chain |
| GOST `socks_wan` | separate authenticated SOCKS5 `:1050`, enabled | Outside the current analysis; no credential published |
| youtubeUnblock — Telegram section | `udp-mode=fake`, `udp-faking-strategy=none`, `udp-fake-seq-len=6`, `udp-fake-len=64`, STUN filter on, UDP dport empty, QUIC disabled, QUIC drop off; Telegram SNI list | **Whether real UDP packets are enqueued, selected by the Telegram section and cause actual outgoing 6×64 fakes** |
| pfSense `192.168.1.140` | Squid `telegram_sites ssl::server_name` ACL, `cache_peer_access voiceproxy`, `never_direct`, `ssl_bump splice`, external HTTP parent `185.203.117.88:33128` | Real route/NAT for *direct* UDP, separate from TCP/TLS Squid |
| OPNsense `192.168.1.2` | Native Zapret2 Voice STUN #1 + ordinary Telegram non-STUN Strategy #4; Squid/sing-box for Telegram TCP/TLS | Real STUN matches/responses, and effect of ordinary unknown fake on direct reflector run |

## Distinct packet paths — do not force a false global order

```text
REAL TELEGRAM APPLICATION (with explicit SOCKS5 192.168.1.236:1070)
  └── OpenWrt VM / GOST auto :1070
        ├── Selected TCP/TLS may match Podkop Telegram rule
        │     → local GOST SOCKS5 :1088 → HTTP parent :33128
        └── VOICE UDP: exact transport and route UNKNOWN
              ↳ Depending on actual OpenWrt hooks and matching,
                youtubeUnblock could act on packets at netfilter POSTROUTING/NFQUEUE.
                Process order and observed fake emission UNKNOWN.

PINNED LAB `tgcalls_cli --mode reflector`
  └── direct non-STUN UDP 91.108.13.10:596, NO SOCKS5 :1070
        ├── via pfSense .1.140 → Established, BWE > 0 (owner-live PASS)
        ├── via OpenWrt .1.236 → Reconnecting (owner-live FAIL)
        └── via OPNsense .1.2 → Reconnecting; WAN fake×2+original, RX=0
```

### Upstream source evidence vs installed-device evidence

Source: [`Waujito/youtubeUnblock` README](https://github.com/Waujito/youtubeUnblock/blob/main/README.md) documents Linux nftables `postrouting` + NFQUEUE (default queue 537), separate UDP selectors and faking. Its [`src/quic.c`](https://github.com/Waujito/youtubeUnblock/blob/main/src/quic.c) `detect_udp_filtered` tests (1) enabled QUIC initial, (2) explicitly configured UDP destination ranges, then (3) `udp_stun_filter && is_stun_message`. Its [`src/dpi.c`](https://github.com/Waujito/youtubeUnblock/blob/main/src/dpi.c) emits configured number and length of UDP fake packets and then reinjects original. Thus **SNI list alone is not a selector for arbitrary non-QUIC UDP**.

Important subtlety: upstream `is_stun_message` checks 20-byte minimum, type flags and message-length consistency; it **does not explicitly check STUN magic cookie**, so protocol names alone do not prove its exact classification. For the owner's sampled pinned 40-byte non-STUN Reflector Hello starting `00 8c 47 3a...`, purported length `0x473a` cannot equal the remaining `20` bytes, so this **specific** Hello fails the upstream STUN heuristic. This is source analysis, **not** verification that the installed youtubeUnblock build/hook is active or behaved identically.

The available youtubeUnblock Telegram screenshot only proves **saved UI selection**. Until the active OpenWrt process/firewall/netfilter queue and a **single successful actual call** are observed, do not label `fake 6×64` as the reason the real call works and do not blindly port it into native Zapret2 `unknown` Strategy #4.

## Current live OpenWrt snapshot — 20.10.2026

[Owner's read-only live inventory and Podkop GUI diagnostics](../verification/evidence/2026-10-20-openwrt-podkop-running-runtime.md):
- OpenWrt 25.12.5 kernel 6.12.94, route to `91.108.13.10` via **`192.168.80.1` / `eth2` with local source `192.168.80.236`.
- **GOST and youtubeUnblock are running**, `sing-box` process is running; GOST TCP listeners `1070/1088/1050` exist; netfilter **queue 537 is registered**.
- Podkop `/etc/init.d/podkop status` reported `not running` yet **Podkop-owned NFT rules and a functioning sing-box are observable**; owner GUI diagnostics pass DNS, nftables and `main` outbound (409 ms). Do **not** label Podkop routing globally stopped based solely on init script state.
- Existing Podkop TPROXY UDP rule to `127.0.0.1:1602` and matching mark rule each show cumulative `180 packets / 12240 bytes`; **no correlation to a real call**, no proof of particular UDP destination, and no proof of successful youtubeUnblock fake injection.
- GUI flags installed Podkop version `0.7.21` as outdated and a sing-box-version-compatibility warning; these observations are not yet a demonstrated UDP failure.

**After package update, actual UDP hooks were examined read-only.** The installed `youtubeUnblock` chain has `hook postrouting priority mangle - 1`, UDP `ct original packets < 9`, `queue flags bypass to 537` (453 packet counter), TCP/443 queued (807), while Podkop's UDP TPROXY receiver `127.0.0.1:1602` is alive but its matched UDP counters are 0. Podkop now `0.7.24` with sing-box `1.14.3-extended-2.7.3`; successful compatibility and 377ms outbound. The GUI mangle-counter warning corresponds to zero `prerouting mangle` counter lines in upstream `check_nft_rules`. [After-update evidence](../verification/evidence/2026-10-20-openwrt-upgraded-nfqueue-podkop-nft.md).

**Owner unavailable for human live call:** use the headless UDP probes below. Actual Telegram client is `192.168.1.101` and uses OpenWrt `:1070`, but its **voice** traffic path is not measured. Do not demand another user for the synthetic proof.

## Headless UDP probes — no human Telegram call required

**Decision:** User has no available call recipient; do not require real human call as a prerequisite to research. Replace that immediate measurement with two **separate** reproducible self-contained probes; the real-client Telegram-over-SOCKS voice path remains **unverified**.

1. **STUN selection/wire-effect on OpenWrt (next single owner-live action):** send exactly **one 20-byte RFC5389 STUN Binding Request** (`00 01 00 00 21 12 a4 42` plus 12-byte transaction ID) using a **supported UDP sender** on OpenWrt: prefer installed Python 3 `socket.socket(AF_INET, SOCK_DGRAM).sendto(...)`, else `socat -4 -u - UDP4:stun.l.google.com:19302`. **Do not use BusyBox `nc`:** on-device BusyBox v1.37.0 only supports `nc [IPADDR PORT]`, not `-u` or `-w`. Preflight `command -v python3` / `command -v socat` **before** starting a capture; fail without mutation if neither exists. Google documents `stun.l.google.com:19302` as a WebRTC STUN server: https://developers.home.google.com/tools/webrtc-validator . Before/after (never reset) read `nft list chain inet fw4 youtubeUnblock` UDP queue counter; perform a bounded `tcpdump` on OpenWrt `eth2`, filtering **source `192.168.80.236` and destination UDP port 19302**, using text-only UDP lengths, no sensitive payloads. With active configured `udp-mode=fake`, `udp-stun-filter`, `seq=6`, `len=64`, a matching section may yield **six UDP payloads length 64 and one original length 20**. This is an *expectation*, not source/installed acceptance; compare actual output. Abort cleanly if both `python3` and `socat` are missing, or `tcpdump` is missing. A failed sender means **no STUN test occurred** and cannot count as an unsuccessful youtubeUnblock outcome. A returned STUN Binding Success Response, if any, would be extra evidence of bidirectional STUN to Google — **not Telegram voice**.
2. **Non-STUN Telegram reflector self-emulation:** existing pinned `tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15` starts local Caller/Callee and needs no person. Contemporary owner-live control `/32 via 192.168.1.140` yielded both Established + BWE non-zero; controls via OPNsense `.1.2` and directly via OpenWrt `.1.236` yielded no media; original TNAS route restored. Pinned 40-byte Hello is **not** STUN and should not be misclassified as covered by the displayed youtubeUnblock `udp-stun-filter`. Do not mechanically rerun established old paths without a novel one-factor reason.

**Limits:** STUN generated by OpenWrt's own `eth2` OUTPUT is **not** the same as a real Telegram client-origin request via `GOST :1070`, nor does a queue counter increment alone prove six fakes. Conditional OpenWrt nft hooks and source route are assessed through captured WAN metadata. If no egress packet, first classify DNS, source interface, Podkop interception or missing tools; do not proclaim a blocker or change routes. A future genuine Telegram SOCKS voice call, when possible, remains a separate acceptance/evidence criterion, not required to perform the headless probes now.


**Owner resolved the public test server address without configuration edits (20.10.2026):** OpenWrt local DNS `@127.0.0.1` gave FakeIP `198.18.0.10`, but pfSense DNS `@192.168.1.140` gave globally routable IPv4 **`74.125.250.129`** for `stun.l.google.com`. Attempts to query `dns.google` over HTTPS via GOST and OPNsense Squid both failed with TLS `curl (35)`, unrelated to STUN UDP proof; no reason to disable Podkop. **Next single owner test:** pin numeric `74.125.250.129:19302`, emit one Python UDP STUN20, capture `tcpdump -i any` only that IP and port, and compare true `eth2 Out` vs `lo In`, payload lengths, and queue counters. [Exact DNS/TLS evidence](../verification/evidence/2026-10-20-openwrt-public-stun-resolve-pfsense.md).

**Owner observed third execution (20.10.2026):** Linux `tcpdump -i any` found `lo In` only: **12 UDP64 + 1 UDP20** from source `192.168.80.236:39459` to `198.18.0.10:19302`, when one 20-byte STUN request was sent. Resolver returned Podkop **FakeIP `198.18.0.10`**, which belongs to the upstream-known `198.18.0.0/15` range; queue537 changed 8614→8624 (+10). No real Google STUN server IPv4 or WAN egress was observed; 12 fake-shaped packets do not establish why 6 configured repeats became 12. **Next:** use local GOST SOCKS `:1088` for external JSON DoH A resolution, validate global IPv4, send one STUN request to that **numeric IP** and observe all interfaces plus counter deltas. Never change Podkop DNS or nft rules simply to run this control. [Owner evidence](../verification/evidence/2026-10-20-openwrt-stun-fakeip-loopback-12x64.md).

**Owner observed second execution (20.10.2026):** Python3 sent 20 bytes successfully to its UDP socket, while `eth2` capture filtered by source `192.168.80.236` and destination `19302` showed **0 packets**; youtubeUnblock UDP queue537 global counter rose **7752→7768 (+16)**. None of this proves egress via `eth2`, any fake datagrams, STUN server reception, or association of +16 with the synthetic probe. Next **one** bounded owner test: resolved IPv4 + `ip route get`, Python `getsockname`, `tcpdump -i any 'udp and port 19302'`, no `src host` assumption, record interface/direction and UDP lengths. [Live evidence](../verification/evidence/2026-10-20-openwrt-stun-sent-nfqueue16-no-eth2-capture.md).

**Owner observed failed first execution (20.10.2026):** `NC_EXIT=1`, BusyBox v1.37.0 printed `Usage: nc [IPADDR PORT]`; during that attempted run youtubeUnblock UDP NFQUEUE counter remained **3786 packets / 393502 bytes** and tcpdump `eth2` captured **zero** UDP/19302 packets. This is **CLI invocation failure before the network experiment**, not STUN/non-STUN, DPI or youtubeUnblock failure. [Evidence](../verification/evidence/2026-10-20-openwrt-stun-busybox-nc-not-sent.md).

## Next one observation gate (owner-approved)

**Read-only OpenWrt inventory** from the **OpenWrt VM's own console** (not OPNsense; its SSH trust to unrelated `192.168.4.1` is unknown). Check:
- actual OpenWrt interface and route for selected Telegram reflector;
- service statuses GOST, Podkop, youtubeUnblock;
- active nftables/iptables selection and `youtubeUnblock` queue, or evidence of kernel-module mode;
- netfilter queue registration in `/proc/net/netfilter/nfnetlink_queue`, if present.

The immediate next action is the **headless STUN probe** above, which requires no real user call. A future genuine Telegram call through SOCKS5 `:1070` may corroborate the actual application UDP transport, but must not be silently presumed from the synthetic STUN or CLI outcomes. Do not collect unrelated traffic or payloads/secrets.

The separate **same-reflector direct-UDP no-fake** OPNsense comparison remains an optional *next distinct experiment* once the owner-approved OpenWrt observation is complete. If used: temporarily neutralize **only ordinary Strategy #4**, keep native STUN #1 and routing unchanged, verify WAN only original 40-byte UDP payloads, restore full original strategy; never disable all Zapret2 or rewrite IPFW/NAT to simplify the test.

No product code, package revision, OpenWrt running settings or OPNsense firewall/route/proxy is changed by this document.

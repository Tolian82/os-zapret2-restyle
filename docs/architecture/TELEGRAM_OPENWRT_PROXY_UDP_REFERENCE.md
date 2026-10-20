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

**Next precise read-only step:** inspect actual `youtubeUnblock` NFQUEUE hook rule and Podkop TPROXY socket/routing state. Then only one correlated, limited real Telegram call with explicit SOCKS5 `:1070`, and inspect metadata/counter deltas to determine youtubeUnblock/Podkop involvement.

## Next one observation gate (owner-approved)

**Read-only OpenWrt inventory** from the **OpenWrt VM's own console** (not OPNsense; its SSH trust to unrelated `192.168.4.1` is unknown). Check:
- actual OpenWrt interface and route for selected Telegram reflector;
- service statuses GOST, Podkop, youtubeUnblock;
- active nftables/iptables selection and `youtubeUnblock` queue, or evidence of kernel-module mode;
- netfilter queue registration in `/proc/net/netfilter/nfnetlink_queue`, if present.

Only after identifying the real hooks and the app's client source IP, plan **one owner-live working Telegram voice call with SOCKS5 :1070** and targeted, privacy-conscious observation of **UDP (or its absence)** and youtubeUnblock activity at OpenWrt ingress and egress. A successful call alone is not UDP attribution: correlate actual packets, destination and direction, and whether `6×64` fakes appeared. Do not collect unrelated traffic or full payloads/secrets.

The separate **same-reflector direct-UDP no-fake** OPNsense comparison remains an optional *next distinct experiment* once the owner-approved OpenWrt observation is complete. If used: temporarily neutralize **only ordinary Strategy #4**, keep native STUN #1 and routing unchanged, verify WAN only original 40-byte UDP payloads, restore full original strategy; never disable all Zapret2 or rewrite IPFW/NAT to simplify the test.

No product code, package revision, OpenWrt running settings or OPNsense firewall/route/proxy is changed by this document.

# 20 October 2026 — Owner-live OpenWrt upgraded Podkop, youtubeUnblock NFQUEUE and real rule counters

**Proof level:** owner-supplied vOpenWrt root read-only nft/netstat/ip outputs and Podkop Diagnostics screenshot **after package update**; not correlated to a real Telegram voice call. No application voice test, router changes, packet capture or screenshot-based claim about UDP bypass success.

## Observed versions and GUI diagnostics (after update)

| Item | Owner evidence |
|---|---|
| Podkop | **0.7.24**, GUI label "Последняя" |
| LuCI app Podkop | **0.7.21** |
| sing-box | **1.14.3-extended-2.7.3** |
| Sing-box version compatibility | **PASS** in updated Diagnostics screenshot |
| Sing-box process / listeners | **PASS** in updated Diagnostics screenshot |
| DNS checks | **PASS** in updated Diagnostics screenshot |
| NFT table/mangle/output existence | **PASS** in updated Diagnostics screenshot |
| NFT `Rules mangle counters` | **FAIL/warning** in updated Diagnostics screenshot |
| Outbound main | **PASS, 377ms** |
| FakeIP browser | Diagnostic red ("browser does not use FakeIP") — **not** evidence of a Telegram voice defect |

Prior OpenWrt snapshot with `Podkop 0.7.21`, `sing-box 1.13.18-extended-2.6.5`, `/etc/init.d/podkop status: not running`, and TPROXY UDP cumulative 180 packets is **older evidence**. Never apply old version/status and counters to the upgraded instance. Latest screenshot confirms Podkop dataplane diagnostics, but was not a retest of init status.

## Actual nftables rules (owner read-only output)

```text
table inet fw4 {
  chain youtubeUnblock {
    type filter hook postrouting priority mangle - 1; policy accept;
    tcp dport 443 ct original packets < 20 counter packets 807 bytes 223114 queue flags bypass to 537
    meta l4proto udp ct original packets < 9 counter packets 453 bytes 46829 queue flags bypass to 537
  }
}
```

This verifies **453 UDP packets traversed the hook rule since the relevant counter epoch and were eligible to be queued to 537**; it does not prove that all packets were consumed, matched the Telegram STUN section, resulted in fake emission, or belong to a live Telegram call. The `bypass` queue flag permits ACCEPT without an available queue listener; earlier `/proc/net/netfilter/nfnetlink_queue` showed queue 537 registered, but **consumer must be rechecked after update** if required.

```text
PodkopTable mangle, prerouting: destination @podkop_subnets tcp packets=0, udp packets=0
PodkopTable mangle_output: destination @podkop_subnets tcp packets=133 bytes=11521, udp packets=0
PodkopTable proxy: marked tcp tproxy ip to 127.0.0.1:1602 packets=161 bytes=14907
PodkopTable proxy: marked udp tproxy ip to 127.0.0.1:1602 packets=0
```

`127.0.0.1:1602/udp` **is listening**, process `5048/sing-box`. IPv4 rules include `from all fwmark 0x100000/0x100000 lookup podkop` at priority 105. This proves the **mechanism is installed** and TCP has matched; there is **no measured Podkop TPROXY UDP hit** in this post-update snapshot. It does **not** prove that UDP never works or will not match the actual call.

### Meaning of red mangle-counter diagnostic

Source [Podkop main shell `check_nft_rules`](https://github.com/itdoginfo/podkop/blob/main/podkop/files/usr/bin/podkop) tests `nft list chain inet PodkopTable mangle` for `counter` entries and flags `rules_mangle_counters=1` only if **any** of their lines is **not** exactly `packets 0 bytes 0` (see upstream around `check_nft_rules`). The owner's `mangle` rules are all at zero after the package update. Thus the warning is consistent with no traffic hitting **prerouting mangle** since the counters were reset, rather than a demonstrated absence of Podkop packet-processing capabilities. Source corresponds to upstream `main`, not an on-device 0.7.24 implementation diff; do not assert version-specific logic beyond evidence.

## Next exact task

One **real Telegram voice call with client configured to SOCKS5 `192.168.1.236:1070`**, using the **Telegram client's actual LAN source IPv4** for privacy-bounded packet observation. Before the call request the owner provide the client IPv4 or interface/origin, so the capture observes only that source and port 1070 plus narrow on-WAN Telegram UDP. Take before/after snapshots of existing NFT counters, no counter reset. This can establish whether actual call uses SOCKS TCP, direct UDP, or another path and whether youtubeUnblock queue delta correlates. **Queue delta alone is insufficient evidence of generated 6×64 fake packets**; packet sizes or classifier activity would be required for attribution. Do not modify GOST, Podkop, youtubeUnblock, OpenWrt fw4 or OPNsense native strategies.

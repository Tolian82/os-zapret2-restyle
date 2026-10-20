# 2026-10-20 — OpenWrt live runtime and Podkop GUI diagnostics (owner supplied)

**Scope:** strictly read-only OpenWrt `root@vOpenWrt` outputs and owner's Podkop 0.7.21 Diagnostics GUI screenshots. No calls, traffic captures, CLI debugger, firewall changes, restarts or plugin update occurred for this evidence.

## Observed system and route

- OpenWrt 25.12.5 x86/64 kernel 6.12.94; `br-lan 192.168.1.236/24`, `eth1 192.168.2.236/24`, `eth2 192.168.80.236/24`.
- `ip -4 route get 91.108.13.10`: **`via 192.168.80.1 dev eth2 src 192.168.80.236`**. This is a route lookup, not packet-forwarding or Telegram call proof.

## Service status and actual dataplane — reconcile instead of dropping Podkop

Initial read-only `/etc/init.d` service status:
- `youtubeUnblock: running`; `gost: running`; `podkop: not running`.
- Process list contains **`gost`, `sing-box`, `youtubeUnblock`**. GOST TCP listeners observed `0.0.0.0:1070`, `127.0.0.1:1088`, `0.0.0.0:1050`.
- `nft` shows `chain youtubeUnblock`, `table inet PodkopTable`, and live Podkop rules matching Telegram subnets (candidate) and TPROXY UDP/TCP. Specifically, `iifname @interfaces ip daddr @podkop_subnets meta l4proto udp meta mark set 0x00100000 counter packets 180 bytes 12240` and `meta mark & 0x00100000 == 0x00100000 meta l4proto udp tproxy ip to 127.0.0.1:1602 counter packets 180 bytes 12240`. These counters are **cumulative** and have no demonstrated correlation to the pinned Telegram CLI or a human voice call.
- `/proc/net/netfilter/nfnetlink_queue` has queue **537** registered to a consumer. Registration **does not prove** that traffic was selected or caused UDP fakes; complete queue-rule content and current delta not yet observed.
- Owner's **Podkop GUI Diagnostics** shows DNS checks passed (bootstrap 1.0.0.1, primary 1.1.1.1 DoT, router DNS, DHCP), installed/running/listening sing-box, enabled autostart, nftables table/mangle/output rule checks passed and **outbound `main` passed at 409 ms**. Therefore treating Podkop as entirely stopped based only on `/etc/init.d/podkop status` is contradicted by live dataplane and GUI evidence. **More precise: Podkop-managed sing-box and nft rules are functionally present, but actual Telegram voice UDP treatment is unverified.**
- Diagnostics warns version compatibility and marks Podkop `0.7.21` outdated; sing-box UI version `1.13.18-extended-2.6.5`. This **does not itself establish** an actual traffic defect. FakeIP browser warning is not voice UDP path proof.

## Next controlled gate

Read-only, on OpenWrt itself:
1. Show `nft -a list chain inet fw4 youtubeUnblock`, including actual NFQUEUE rules / counters.
2. Show only `chain`, `hook`, `meta mark`, `tproxy`, `udp` excerpts of `nft -a list table inet PodkopTable`; note `ip -4 rule show` and actual UDP socket `:1602`, without exposing full proxy credentials, connection secrets or unrelated traffic.
3. Once hooks and listening socket are confirmed, instrument **one real Telegram SOCKS5 `192.168.1.236:1070` voice call**, comparing read-only counters and narrowly scoped packet metadata; no DNS/proxy/voice strategy modifications.

The future OPNsense direct non-STUN no-fake test remains separate and deferred. No assertions of STUN classification for the user's real Telegram voice path before packet evidence.

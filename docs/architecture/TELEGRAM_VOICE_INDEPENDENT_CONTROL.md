# Telegram Voice — safe independent same-endpoint working-path control

**Status:** READ-ONLY INVENTORY FIRST; current same-endpoint independent path **NOT YET QUALIFIED**. This is an independent lab operation, not an additional plugin component, new strategy candidate, package release or real human call.

## Why this gate is necessary

October 3 A1 and A2 were independently wire-qualified for the exact same 40-byte fixed-reflector Hello. Both emitted all 60 genuine Hellos post-NAT and two short fakes before each, differing only by bad versus valid fake UDP checksums. Neither received any captured reply. This cannot distinguish a present unavailable/moved reflector from route-specific provider filtering or endpoint-side processing. A working UDP test to a **different** address, the historical `192.168.1.140` route or TCP success through the external parent does **not** prove the current exact reflector is ready. See [A2 recorded evidence](../verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md) and [current oracle](TELEGRAM_VOICE_EMULATION_LAB.md).

**Established laboratory TCP/TLS route (preserve unchanged):** the owner configured `185.203.117.88:33128` as the **external Squid parent proxy in the OPNsense Squid GUI**, not as an unassigned or hypothetical external gateway. The currently operating Telegram IPv4 TCP/80,443 paths use the existing PF/Squid or SOCKS5 sing-box→Squid integration to reach this **GUI-configured parent**; LAN and SOCKS5 Telegram TCP/TLS traffic through that parent have already passed owner-live checks, including Squid `FIRSTUP_PARENT`. See [existing live operations inventory](TELEGRAM_LAB_OPERATIONS.md) and [traffic policy](TELEGRAM_TRAFFIC_POLICY.md). The corresponding `pre-auth/parentproxy.conf` exists, but whether this specific file is generated from the GUI has **not** been established; do not delete or rewrite it. This proven Telegram TCP/TLS exit is **not** an independently proven UDP transport for the fixed-reflector Docker control. Do not treat the parent server as a new proposed TCP exit, assume SOCKS UDP ASSOCIATE or UDP forwarding through the HTTP parent, change the GUI entry, or restart the working Squid/sing-box/TCP route. Current preferred alternate `192.168.3.140` was owner-observed for **Windows real calls** only and is not a qualified exact-endpoint current Docker CLI path. The old TNAS `192.168.1.140` Voice route remains **retired**.

## Gate zero — one read-only operator run on OPNsense

Tracked independent helper: [`run-control-inventory-opnsense.sh`](../../tools/telegram-voice-lab/run-control-inventory-opnsense.sh). Transfer the merged immutable source to `/root/tgvoice-lab/run-control-inventory-opnsense.sh` through the owner's functioning HTTP proxy `192.168.1.2:3128`, syntax-check, then run:

```sh
/bin/sh /root/tgvoice-lab/run-control-inventory-opnsense.sh
```

The helper reuses the **existing** restricted noninteractive OPNsense → TNAS SSH identity, target and absolute Docker command. **Unlike** the A1/A2 media runner, it does **not** invoke the owner route guard, start the container, execute a media call, change the TNAS default or any host route, configure a tunnel, edit GUI/IPFW/PFIL/PF/NAT or restart Squid/sing-box. It verifies the existing TNAS `91.108.13.10/32 via 192.168.1.2 dev ovs_eth1` baseline and reads interface/rule/route information, tunnel *tool presence* and pinned Docker/binary identity **only if already running**. It prints one **private** `control-inventory-*.tgz` archive with self-checksums and explicit `independent_same_endpoint_media_path=UNVERIFIED`. No private SSH key or OPNsense config.xml is archived. Only send the archive privately for design review, never attach it to a public PR.

### What to choose after the archive

A usable control must demonstrate a **genuinely different externally routed egress**, the **same exact current `91.108.13.10:596`**, the **same pinned CLI bytes** and fresh `--mode reflector --duration 15` with both peers established, non-zero BWE/stats, exit 0 and independent packet evidence. A quick ping, HTTP proxy CONNECT, installed tunnel program, a result on a **different endpoint**, local P2P smoke or successful Telegram GUI voice call alone is **insufficient**.

Candidate architecture, conditional on measured capability: a genuinely working **UDP-capable, independently routed** tunnel/egress (potentially through a separately validated owner-controlled external server) or a compatible isolated Linux host running the verified same CLI binary. Do **not** assume the existing pfSense external HTTP parent can route arbitrary UDP or that Tailscale/WireGuard exists on the OPNsense/TNAS nodes. Do not move the existing host-network Docker's `/32` route or install an untested persistent tunnel. Prefer a separately isolated, reversible test path **after** capability inspection, with source identification, simultaneous narrow captures and exact restoration safeguards.

A positive remote-host check (different machine) can establish **current endpoint/CLI viability** but, by itself, cannot prove the old TNAS host path under an alternate gateway will succeed or identify where packets are discarded. Distinguish these evidentiary scopes in the final control report. A negative independent control also does **not** establish an ISP/DPI cause; mark `CONTROL_NOT_VALIDATED` and investigate current endpoint readiness/compatibility before more A-series strategy trials.

No Cron, TNAS Docker autostart, permanent router changes, or new plugin version for this diagnostic.

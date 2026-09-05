# Telegram Voice Phase C — fixed-reflector control and host-only routing decision

**Status:** OWNER-LIVE EVIDENCE · EXACT-ENDPOINT CONTROL `MEDIA_PASS` · OPNsense PROVIDER BASELINE NOT YET RUN
**Observed:** 2026-09-05
**Package identity:** `VERSION=0.5.0`, `PLUGIN_REVISION=3` — unchanged
**Architecture authority:** [`TELEGRAM_VOICE_EMULATION_LAB.md`](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md)

## Scope and result

The owner executed the qualified pinned `tgcalls_cli` against one fixed endpoint from the current official Telegram reflector list.

| Item | Value |
|---|---|
| run UTC | `2026-09-05T07:50:15Z` |
| reflector-list SHA-256 | `b81eed3b72d1fd002752f6ea5546de52f6e4231ce40ea033aeed494112d0ff46` |
| fixed endpoint | `91.108.13.10:596` |
| container image | `sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517` |
| `tgcalls_cli` SHA-256 | `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a` |
| duration | 15 seconds |

```text
Caller state:      Established
Callee state:      Established
Call established:  yes (at 1.587s)
Stats log:         caller=15 callee=15 bitrate records
BWE non-zero:      yes
Errors:            none
control_exit=0
```

This satisfies exact-endpoint control `MEDIA_PASS`.

## Route and network identity

Before and after the run:

```text
91.108.13.10 via 192.168.1.140 dev ovs_eth1 src 192.168.1.100
```

The container used Docker `host`. It therefore shared the TNAS network namespace and had no independent container IP, MAC, DHCP lease or route. The flow validates endpoint/harness health but did not traverse OPNsense `192.168.1.2`.

## Owner decision after measurement

- keep the existing TOS/Docker network named `host` and use no other Docker network;
- do not attempt a separate container DHCP lease such as `192.168.1.239`, because host mode exposes no per-container MAC;
- do not change the TNAS default route;
- select the provider path with one temporary exact reflector `/32` route on TNAS via `192.168.1.2`;
- launch repeated jobs from the OPNsense console using temporary key-only SSH to TNAS and `docker exec tgvoice-lab ...`;
- add no GUI or permanent Telegram Voice lab code;
- remove temporary route/SSH/scripts when research closes.

pfSense DHCP may assign routes by the visible TNAS MAC, but they apply to the TNAS host and every host-network workload using the destination, not uniquely to this container. The experiment accepts that mechanism only for an exact reflector `/32`, with effective-route and restoration evidence.

## Next gate

Prove the exact `91.108.13.10/32` add/check/delete/restore transaction through `192.168.1.2`, then run the same endpoint from the OPNsense console with no desynchronization while capturing LAN/WAN truth.

No raw reflector list, full console transcript, PCAP, peer tag, proxy endpoint or credential is committed.

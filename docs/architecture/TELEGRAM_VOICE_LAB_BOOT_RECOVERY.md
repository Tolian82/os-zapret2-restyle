# Telegram Voice lab: GUI versus helper, IPFW/PF/NAT and one-shot reboot decision

**Status:** source audit completed against main `857ff3f8c0e01c1aefa2be1b523e28ee01a6dbb2`; **no new boot action installed; no current post-reboot acceptance**. This independent laboratory is separate from the approved plugin product stage 3.

**Owner decision (supersedes an unpublished, unmerged earlier draft):** absolutely **no Cron, periodic checking or recurring telegram-voice-enable**. If the existing helper remains part of the lab, run it **only once during OPNsense boot, after regular Zapret2 becomes ready**, with a bounded delay/readiness check, never by a permanently enabled periodic task. Do not automatically enable the unrelated TNAS route guard or Docker container. First determine whether the helper is actually needed compared with the existing GUI configuration.

This file is the active design/audit record, not instructions to run an unqualified new boot hook. Consult the [owner-live operations inventory](TELEGRAM_LAB_OPERATIONS.md) and [dated evidence](../verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) before operating on the appliance.

## Confirmed: two profile sources but just one dvtws2

The persistent settings of `os-zapret2-restyle` are modeled in [Zapret.xml](../../src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml); the [generated template](../../src/opnsense/service/templates/OPNsense/Zapret/zapret.conf) reads `OPNsense.Zapret.strategy.trafficargs` and `OPNsense.Zapret.hostlist.telegramips` into `/usr/local/etc/zapret2/zapret.conf`. The ordinary [orchestrator](../../src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh) normalizes the GUI strategy, writes `/usr/local/etc/zapret2/runtime-v2/traffic-user.conf` and a managed `runtime-v2/managed/ipset-telegram.txt`. The installed helper defined in [telegram_voice.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/telegram_voice.sh) **prepends**, rather than separately launching, a STUN-oriented `telegram-voice-poc` profile to the effective `runtime-v2/traffic.conf` **only if** `/var/run/zapret2-telegram-voice-poc.enabled` exists. The effective runtime is launched as **one dvtws2 instance**, using generated `runtime-v2/dvtws.args`.

The currently installed helper profile has `--filter-l3=ipv4 --filter-udp=* --filter-l7=stun --ipset=.../managed/ipset-telegram.txt --payload=stun --lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2`. Its name, filters, fake content and repeat count are **source-code constants**, not separately editable/persisted GUI Voice fields. The `/var/run` marker remembers only transient ON; `runtime-v2/telegram-voice-poc.state` is a generated runtime observation, **not a permanent preference**.

Owner's regular GUI strategy contains YouTube HTTP/TLS, then Telegram TCP `80,443,5222,8888` MTProto and Telegram UDP **the same four ports** with `<IPSET:telegram>` and `--filter-l7=mtproto`, and then user TLS. The Telegram TCP and UDP lines are separated by **no** `--new`; by normal strategy syntax, they are part of the same successive block, not independently selectable STUN and MTProto Voice strategies. This regular GUI strategy contains **no Voice-specific STUN or current-reflector profile**.

`<IPSET:telegram>` is expanded from the same managed data the helper uses: the GUI's 14 listed IPv4 prefixes are normalized into `runtime-v2/managed/ipset-telegram.txt`. The helper additionally constructs an **IPFW table** `zapret2_tgvoice` from that managed file. This is one configured Telegram-address dataset represented twice in different runtime subsystems, **not two unrelated permanent IP lists**. Do not mistake this for the *separate* PF aliases `Telegram`/`Telegram_IPs` or sing-box's static `ip_cidr` snapshot: these lists are currently not automatically synchronized.

## Why GUI alone is not equivalent with the current firewall backend

Current code in [ports.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/ports.sh) extracts **only numerical** `--filter-tcp=` and `--filter-udp=` ports and ranges from **traffic-user.conf**, i.e. from GUI strategy *without* the injected helper. The current extractor rejects the wildcard `*`; the extracted values generate common IPFW rules in [firewall.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh):

```text
udp from any to any 80,443,5222,8888 out not diverted not sockarg xmit vtnet1
```

The `<IPSET:telegram>` in GUI's dvtws2 profile is **not** an IPFW destination selector. Common UDP interception covers only its configured ports but across **all WAN destination IPs**. To capture all ports by adding `1-65535` to GUI would cause very broad interception of virtually all outbound UDP, **not a narrow Telegram Voice solution**. Copying `--filter-udp=*` to the GUI cannot currently substitute for the helper either, as the port extractor rejects `*`.

With Voice helper ON, [firewall.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh) first inserts an additional dedicated rule at the start of the plugin-owned rule range:

```text
udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit vtnet1
```

It then shifts the ordinary port rules down one number. The dedicated rule captures Telegram-destination UDP on **any** port; for Telegram UDP/443 both rule families could match *before* first interception, but the earlier dedicated rule catches it and the `not diverted` condition stops subsequent recapture after return from the same divert socket. Thus this is **overlap in capture eligibility**, not double interception by two separate dvtws2 instances, double encryption or automatically applying two fake strategies. The upstream Zapret2 profile engine selects the **first applicable profile**. The helper STUN profile precedes the regular GUI profiles; for non-STUN packets it does not apply, and the later profiles are still individually filter-dependent.

**Today this narrowly scoped capture is real, but the helper's STUN strategy is not a solution for the current non-STUN reflector.** The latest [October 1 owner evidence](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md) saw 60 intercepted 40-byte non-STUN Reflector Hello packets, no modified Hello, zero inbound replies, no `MEDIA_PASS`. GUI's MTProto-initial profiles also do **not** establish processing of these non-STUN/non-MTProto-intial 40-byte packets. Whether a future effective Voice strategy can be expressed as GUI text **after** adding safe destination-scoped capture is an architecture question; do not discard the current capture guard while answering it.

**Other possible limited use:** a known single reflector UDP port could be included in GUI port filters for a bounded experiment, but common IPFW would also divert that port for *any* destination. This is neither equivalent to all Telegram UDP ports nor a persistent narrow solution. Do not change the working GUI strategy as part of this audit.

## NAT and hook order are important, but not a GUI/helper distinction

Both rule families are constructed by the **same** plugin firewall backend, target the **same** outgoing WAN `xmit` interface, use the **same** divert port (currently `989`) and return to the **same** single dvtws2. There is **no separate pre-NAT/post-NAT hook chosen per profile**. They differ by **IPFW match**, not their place relative to PF.

PF and IPFW can run in different output hook orders; read their **actual** order on the live OPNsense with the csh-compatible `pfilctl heads` before drawing a conclusion. Historical [2026-09-21 post-NAT fragmentation evidence](../verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) recorded the original `IPFW → PF` order, a **temporary lab-only** `PF → IPFW` reorder to avoid post-NAT invalid fragment UDP checksums, and verified restoration. Those historical observations do **not** prove the actual order after the latest boot/configuration epoch. Never reorder all outgoing IPv4 PFIL hooks merely to make an ordinary STUN fake work: it affects traffic outside Telegram. Such output-order changes require a separate bounded test, snapshots and exact restoration.

To check current state **read-only** from OPNsense's *default csh*:

```sh
pfilctl heads
ipfw -a list
cat /usr/local/etc/zapret2/runtime-v2/udp-ports.txt
configctl zapret telegram_voice_status
```

Current `ipfw` counters confirm packet interception, **not** a successful transformation or voice call. Current output hook order can only be established from this live check, not deduced from whether a profile originated in GUI.

## One-shot boot requirement: decision, not installed functionality

**No new boot mechanism is installed or verified. No Cron.** If the owner retains the helper while current stage-1 experiments proceed, a future independent one-shot OPNsense startup action must first establish a deliberate durable desired state **ON** without relying on `/var/run`, run **after** the existing package's `start/20-zapret` has made normal Zapret2 ready, wait only for a **bounded** time, invoke `configctl zapret telegram_voice_enable` **at most once on success**, and verify full `requested/effective/active_profile/table/rule` state before reporting success. Do not use a fixed sleep as readiness proof, endlessly retry in a daemon, schedule a recurring job or automatically re-enable Voice during intentionally disabled live experiments.

A startup-stage OPNsense native `rc.syshook.d/start` script *could* meet the once-per-boot condition if its owner, execution order, persistence and interaction with existing package hook are checked. OPNsense's [rc.syshook](https://github.com/opnsense/core/blob/master/src/etc/rc.syshook) runs sorted start hooks. But this would be an **independent, explicitly approved laboratory mechanism**, not local modification of `os-zapret2-restyle` package files, not a claimed product feature and not an installed/tested action. The choice must be reconciled with the repo's warning against **unreviewed ad-hoc product hooks**, and documented before any device mutation. Alternatively, moving capture and persistent Voice ON preference to the plugin GUI requires owner-approved plugin code changes, appropriate package qualification and live tests, and is separate from merely pasting a profile into the current GUI.

Actual reboot acceptance is still open: after any approved implementation, boot with chosen ON, do **not** manually enable Voice while measuring, verify regular Zapret status, native Voice requested/effective/profile/table/firewall and preserve already-working Squid/sing-box TCP paths. Restoring interception is only a lab **startup pass**, never `MEDIA_PASS` or `CALL_PASS`. TNAS host routes and the `tgvoice-lab` Docker container remain **manual-only**, as separately decided.

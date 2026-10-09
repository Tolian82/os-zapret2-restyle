# Telegram Voice helper: configuration, test controls and reboot recovery

**Updated:** 2026-10-09. Source rechecked at `3f7d5e413da9b224f34dce6cfccd441e23b27b23`; installed package reports `0.5.0_3`. **Measured: ON before reboot, OFF after boot, manual native status/table/rule ON restored. Automatic recovery is still unimplemented/unaccepted.** [Dated evidence and private snapshot hashes](../verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md).

This is the primary technical/operator reference for the temporary `telegram_voice` helper: purpose, configuration ownership, commands and recovery. The [campaign control matrix](TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#telegram_voice-controls-for-every-trial) owns per-test invariants and deliberate parameter-change records. Current mechanism details are retained here; the approved replacement is [the October 8 Voice page specification](VOICE_TRANSMISSION_GUI.md). Its implementation is now the next task, independently of media qualification.

**Owner decision (supersedes an unpublished, unmerged earlier draft):** absolutely **no Cron, periodic checking or recurring telegram-voice-enable**. The current campaign retains helper ON as a fixed baseline. Any future automatic laboratory recovery runs **only once during OPNsense boot, after regular Zapret2 becomes ready**, with bounded readiness checking. It is not installed by this document. Do not automatically enable the unrelated TNAS route guard or Docker container.

This file is the active design/audit record, not instructions to run an unqualified new boot hook. Consult the [owner-live operations inventory](TELEGRAM_LAB_OPERATIONS.md) and [dated evidence](../verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) before operating on the appliance.

## Confirmed: two profile sources but just one dvtws2

The persistent settings of `os-zapret2-restyle` are modeled in [Zapret.xml](../../src/opnsense/mvc/app/models/OPNsense/Zapret/Zapret.xml); the [generated template](../../src/opnsense/service/templates/OPNsense/Zapret/zapret.conf) reads `OPNsense.Zapret.strategy.trafficargs` and `OPNsense.Zapret.hostlist.telegramips` into `/usr/local/etc/zapret2/zapret.conf`. The ordinary [orchestrator](../../src/opnsense/scripts/OPNsense/Zapret/backend/orchestrator.sh) normalizes the GUI strategy, writes `/usr/local/etc/zapret2/runtime-v2/traffic-user.conf` and a managed `runtime-v2/managed/ipset-telegram.txt`. The installed helper defined in [telegram_voice.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/telegram_voice.sh) **prepends**, rather than separately launching, a STUN-oriented `telegram-voice-poc` profile to the effective `runtime-v2/traffic.conf` **only if** `/var/run/zapret2-telegram-voice-poc.enabled` exists. The effective runtime is launched as **one dvtws2 instance**, using generated `runtime-v2/dvtws.args`.

The currently installed helper profile has `--filter-l3=ipv4 --filter-udp=* --filter-l7=stun --ipset=.../managed/ipset-telegram.txt --payload=stun --lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2`. Its name, filters, fake content and repeat count are **source-code constants**, not separately editable/persisted GUI Voice fields. The `/var/run` marker remembers only transient ON; `runtime-v2/telegram-voice-poc.state` is a generated runtime observation, **not a permanent preference**.

**Current GUI baseline, measured October 7:** YouTube HTTP/TLS, a separate Telegram IPv4 UDP `596–599` / `unknown` A2 block, then user TLS, separated by `--new`. A2 uses `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`, with no `badsum`, explicit fake TTL or fragmentation. The former MTProto TCP/UDP `80,443,5222,8888` example belongs to the earlier epoch, not today's active configuration. Saved GUI placeholders resolve exactly to the observed `traffic-user.conf`; the running process matched the generated arguments in both reboot snapshots.

**Two distinct decisions:** IPFW decides which packets enter dvtws2; the first applicable dvtws2 profile decides their treatment. The helper supplies all-port Telegram capture **and** a fixed STUN action. A1/A2 supply a separate `unknown` action in GUI. Capturing a packet does not prove which action ran. The current non-STUN Hello is treated by the matching GUI candidate, not by the helper's STUN action.

`<IPSET:telegram>` is expanded from the same managed data the helper uses: the GUI's 14 listed IPv4 prefixes are normalized into `runtime-v2/managed/ipset-telegram.txt`. The helper additionally constructs an **IPFW table** `zapret2_tgvoice` from that managed file. This is one configured Telegram-address dataset represented twice in different runtime subsystems, **not two unrelated permanent IP lists**. Do not mistake this for the *separate* PF aliases `Telegram`/`Telegram_IPs` or sing-box's static `ip_cidr` snapshot: these lists are currently not automatically synchronized.

## Why GUI alone is not equivalent with the current firewall backend

Current code in [ports.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/ports.sh) extracts **only numerical** `--filter-tcp=` and `--filter-udp=` ports and ranges from **traffic-user.conf**, i.e. from GUI strategy *without* the injected helper. The current extractor rejects the wildcard `*`; the extracted values generate common IPFW rules in [firewall.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh):

```text
udp from any to any 596-599 out not diverted not sockarg xmit vtnet1
```

The `<IPSET:telegram>` in GUI's dvtws2 profile is **not** an IPFW destination selector. Common UDP interception covers only its configured ports but across **all WAN destination IPs**. To capture all ports by adding `1-65535` to GUI would cause very broad interception of virtually all outbound UDP, **not a narrow Telegram Voice solution**. Copying `--filter-udp=*` to the GUI cannot currently substitute for the helper either, as the port extractor rejects `*`.

With Voice helper ON, [firewall.sh](../../src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh) first inserts an additional dedicated rule at the start of the plugin-owned rule range:

```text
udp from any to table(zapret2_tgvoice) out not diverted not sockarg xmit vtnet1
```

It then shifts the ordinary port rules down one number. The dedicated rule captures Telegram-destination UDP on **any** port; for current Telegram UDP/596 both rule families could match *before* first interception, but the earlier dedicated rule catches it and the `not diverted` condition stops subsequent recapture after return from the same divert socket. Thus this is **overlap in capture eligibility**, not double interception by two separate dvtws2 instances, double encryption or automatically applying two fake strategies. The upstream Zapret2 profile engine selects the **first applicable profile**. The helper STUN profile precedes the regular GUI profiles; for non-STUN packets it does not apply, and the later profiles are still individually filter-dependent.

**The helper's STUN strategy is not a solution for the current non-STUN reflector.** The [October 1 control](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md) intercepted 60 Hello packets without a matching Hello action or replies. Subsequent [A1](../verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) and [A2](../verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md) kept helper ON and did emit their GUI-selected fakes, but still had no replies/media. The October 7 reboot loss does not invalidate those ON-qualified measurements.

**Measured limited coverage:** after the October 7 reboot helper OFF removed its table/rule and STUN profile, but GUI A2 and common UDP `596–599` interception survived. A UDP/596 test can therefore still be intercepted without satisfying the campaign's helper-ON baseline. Other Telegram UDP ports lose dedicated capture. Conversely, helper ON does not expand A2's `596–599` action to every port: real-client acceptance must verify its actual endpoint/protocol/profile separately.

## NAT and hook order are important, but not a GUI/helper distinction

Both rule families are constructed by the **same** plugin firewall backend, target the **same** outgoing WAN `xmit` interface, use the **same** divert port (currently `989`) and return to the **same** single dvtws2. There is **no separate pre-NAT/post-NAT hook chosen per profile**. They differ by **IPFW match**, not their place relative to PF.

PF and IPFW can run in different output hook orders; read their **actual** order on the live OPNsense with the csh-compatible `pfilctl heads` before drawing a conclusion. **The October 2 owner-live real-call read-only `pfilctl heads` now confirms actual IPv4 output `ipfw:default → pf:default-out` for that captured epoch**; no hook alteration occurred. The historically corrected post-NAT fragment experiment still requires a deliberate separate bounded change if ever revisited. [Matched current live call/counter evidence](../verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md). Historical [2026-09-21 post-NAT fragmentation evidence](../verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) recorded the original `IPFW → PF` order, a **temporary lab-only** `PF → IPFW` reorder to avoid post-NAT invalid fragment UDP checksums, and verified restoration. Those historical observations do **not** prove the actual order after the latest boot/configuration epoch. Never reorder all outgoing IPv4 PFIL hooks merely to make an ordinary STUN fake work: it affects traffic outside Telegram. Such output-order changes require a separate bounded test, snapshots and exact restoration.

To check current state **read-only** from OPNsense's *default csh*:

```sh
pfilctl heads
ipfw -a list
cat /usr/local/etc/zapret2/runtime-v2/udp-ports.txt
configctl zapret telegram_voice_status
```

Current `ipfw` counters confirm packet interception, **not** a successful transformation or voice call. October 7 before/after reboot snapshots both measured **IPFW→PF**, unchanged route, IPFW sysctls and PF NAT/rdr. Future boot/hook changes require another read-only measurement. The earlier real-call PCAP captured zero inbound Telegram UDP despite good audible voice; no actual media-path proof or STUN-helper causal attribution.

## Configuration, commands and parameter ownership

| Item | Authority / supported operation | Treatment in the current campaign |
|---|---|---|
| Helper ON/OFF | Native enable/disable actions; transient `/var/run` marker | Fixed ON; observed before/after every trial |
| STUN filters, zero16 blob, repeats=2, no explicit short TTL | Constants in `backend/telegram_voice.sh` | Unchanged in A1/A2 and planned TTL series; enable accepts no strategy/repeats/TTL settings |
| Candidate filters and action | Ordinary GUI `OPNsense.Zapret.strategy.trafficargs` | A1→A2 changed only candidate `badsum`; next qualified series changes only candidate fake `ip_ttl` |
| Telegram IPv4/CIDR set | GUI `OPNsense.Zapret.hostlist.telegramips` | Freeze exact contents/target coverage; managed file and helper table represent the same set |
| Runtime state/profile/arguments | Generated by the normal lifecycle | Observe and compare; do not hand-edit as permanent configuration |
| WAN/divert/rule range | Existing plugin settings/lifecycle | Freeze and record; current `vtnet1`/`989`/`19000` are lab identities, not universal Voice constants |

Changing the helper's STUN repeats/TTL cannot test the identified non-STUN Hello. A future STUN-specific hypothesis or different capture architecture may justify a helper change, but requires a separate documented comparison, candidate ID, exact old/new values, reason, expected packet effect and restoration. Plugin-source changes go through GitHub, never edits to installed source. Because the helper is first, appending a new GUI STUN profile does not establish it will be selected. No helper-parameter change is required or delivered for the present reflector TTL plan.

Exact csh-compatible actions from [configd](../../src/opnsense/service/conf/actions.d/actions_zapret.conf) and [service source](../../src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh):

| Command | Meaning |
|---|---|
| `configctl zapret status` | Observe ordinary service completeness, not Voice ON |
| `configctl zapret telegram_voice_status` | Read request, generated state, service and firewall; changes nothing |
| `configctl zapret telegram_voice_enable` | Requires a complete running service, creates the marker and reconfigures when needed; already requested/effectively ON simply returns status |
| `configctl zapret telegram_voice_disable` | Removes request and helper profile/table/rule through the lifecycle, retaining GUI strategy; not a control for disabling only a candidate action |

`telegram_voice` is the action family, not a second daemon or a command with free-form strategy parameters. No enable invocation is needed before every trial when the baseline already verifies ON. After any error inspect the returned state; do not infer restoration from invoking a command.

Status interpretation:

- `requested` reflects the marker; `active_profile` reflects generated `telegram-voice-poc.state`, not an independent full process comparison.
- `effective` additionally requires running service and complete helper firewall runtime. Confirm the actual process, profile and table contents separately.
- `strategy` and `scope` are fixed labels **also printed while OFF**; they do not identify the GUI candidate or prove treatment/success.
- `rule=19000` alone does not prove Voice interception: OFF reused that number for TCP. Check rule content/destination table/divert/WAN.
- `table_entries=14` is the measured baseline, not a protocol constant. Check membership and exact intended set, not count alone; staging-table absence is normal after a completed transaction.
- The configd status wrapper ends with `exit 0`; inspect fields, not only shell status. Compare packet/byte deltas within a trial; zero counters after reconfigure/reboot are normal.

### Manual recovery and reboot measurement order

Observe service/helper/IPFW first. If normal Zapret2 is healthy and selected ON was lost, restore it explicitly:

```sh
configctl zapret telegram_voice_enable
configctl zapret telegram_voice_status
ipfw -a list
```

Validate the full campaign baseline before traffic. A stopped/incomplete normal service is a separate preflight error, not permission to loop enable commands. The runner must not silently enable the helper.

For a reboot audit, save the before snapshot under `/root`, reboot OPNsense only, then collect the identical after snapshot **before enable, GUI Apply or the runner's route/container operations**. Include UTC/boot time, package/process/divert socket, selected saved GUI fields only (never full private XML), resolved/effective strategy/args, marker/state, IPFW rules/table contents, PFIL, PF NAT/rdr and reflector route. Preserve that evidence, then record manual recovery as a distinct third phase. [October 7 evidence](../verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md) completed this comparison; do not repeat it unchanged instead of addressing the persistence task.

## Persistent startup replacement — approved, not implemented

**October 8 superseding decision:** implement [«Передача голоса»](VOICE_TRANSMISSION_GUI.md) with persistent per-service settings and restoration through the existing normal Zapret2 lifecycle. This replaces the earlier proposal to design an independent lab-only one-shot enable hook. No additional hook, Cron, watcher or repeated enable is selected. The page has no boot/local-UDP/LAN toggles; saved ON/OFF is restored automatically and global service OFF remains respected.

The new implementation must replace the transient marker and hard-coded STUN builder, retain one engine, shared Telegram IPSET and compatible Telegram configctl commands on the same persistent authority. The source map, native input contract, migration and boot acceptance live in the new specification. Current no-argument commands above still have the old transient semantics until that package is implemented and installed; this documentation changes no appliance behavior.

The [existing start hook](../../src/etc/rc.syshook.d/start/20-zapret) did start ordinary Zapret2 on October 7, but helper ON was lost. Manual enable restored native ON/table14/rule19000, without a new full post-enable process/profile snapshot, parent probe or media result. Preserve that evidence; after the new implementation test selected ON, OFF and global OFF after reboot **before any manual repair**. Startup/configuration acceptance is never MEDIA_PASS/CALL_PASS. Until migration, documented manual recovery and fresh full preflight remain necessary. TNAS routes and Docker stay manual-only.

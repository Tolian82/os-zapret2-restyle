# 2026-10-07 — Telegram Voice reboot loss and manual recovery

**Recorded:** 2026-10-08.

**Result:** helper ON before OPNsense reboot → helper OFF after boot while GUI A2 and ordinary Zapret2 survived → native helper status/table/rule ON after manual enable. **No new voice trial, MEDIA_PASS, CALL_PASS or automatic-recovery acceptance.** Installed package reports `os-zapret2-restyle-0.5.0_3`.

## Sources and time boundaries

The owner supplied two private read-only snapshots and a subsequent console recovery transcript. Raw runtime/process/configuration files remain outside public GitHub; only measured summaries and immutable source identities are recorded here.

| Source | Embedded UTC time | SHA-256 |
|---|---|---|
| Before, `state.txt`, 12,594 bytes | `2026-10-07T16:20:00Z` | `94839b54057c812d815cc41c09db37985af799ffd762537e681185658177235f` |
| After, `state(2).txt`, 11,570 bytes | `2026-10-07T16:44:23Z` | `d4ddd355f8cabd4af212832dcf0317bd5ffd26f380719e472a063062cd32b4ac` |
| Subsequent console: enable, status, IPFW | October 7 submission; no embedded command timestamp | No standalone file/hash supplied; do not invent execution time |

Before `kern.boottime` epoch `1790788293` is September 30 17:11:33 UTC / 20:11:33 Moscow. After epoch `1791391064` is October 7 **16:37:44 UTC / 19:37:44 Moscow**. The second snapshot is **399 seconds after boot**, with ordinary service already running. The requested procedure preserved this state before manual recovery. No TNAS route/Docker post-reboot measurement is included.

## Three observed states

| Item | Before reboot | After reboot | After manual enable |
|---|---|---|---|
| Normal Zapret service | Running, dvtws2 PID `25786` | Running, dvtws2 PID `2711` | Enable reports running PID `30350` |
| Voice requested/effective/active_profile | ON / ON / ON | OFF / OFF / OFF | ON / ON / ON |
| Request marker | Present under `/var/run` | Absent | Not independently listed; native requested=ON |
| Generated Voice state | `enabled` | `disabled` | Not independently copied; native active_profile=ON |
| IPFW `zapret2_tgvoice` | Present, 14 prefixes | Absent | Present, 14 entries in status; contents not independently re-listed |
| Dedicated UDP-to-Telegram rule | `19000`, divert `989`, WAN `vtnet1` | Absent; `19000` now TCP `80,443` | `19000` restored with the same match expression |
| Ordinary UDP `596–599` rule | `19002` | `19001` | `19002` |
| Voice counters | Accumulated `60 / 4080` | Unavailable | `0 / 0` after reconfiguration |
| GUI A2 / actual process | Present and matching | Identical A2 still present and matching | No new full GUI/process snapshot supplied |

The owner executed `configctl zapret telegram_voice_enable`, `configctl zapret telegram_voice_status` and `ipfw -a list`. Both native responses report running/ON/table14/no staging table. IPFW independently shows the restored earlier destination-table UDP rule, TCP `80,443`, then ordinary UDP `596–599`. Initial zero counters are normal; no call/capture accompanied these commands.

## Exact before/after comparison

Independent parsing verified:

- Saved GUI strategy and Telegram IP fields are identical. GUI placeholders resolve exactly to captured `traffic-user.conf` in both snapshots.
- Resolved GUI strategy, managed Telegram IPSET and extracted TCP `80,443` / UDP `596–599` ports are unchanged.
- Before boot, effective traffic is the fixed prepended STUN helper followed by exact GUI strategy. After boot, it is exactly GUI strategy: the helper is the only removed profile block.
- Both running dvtws2 command lines match their generated args plus runtime `--sockarg=0x200 --user=nobody`. Each has one engine and one IPv4 divert listener `989`; daemon/supervisor wrappers are not extra engines.
- Before boot, all 14 GUI prefixes equal the managed file and IPFW table, covering `91.108.13.10` through `91.108.12.0/22`. After boot the managed file survives but the helper IPFW table does not.
- PFIL IPv4 output remains **IPFW → PF**; IPFW enable/one_pass stay `1`; the reflector route remains via `192.168.80.1` on `vtnet1`; PF NAT/rdr and package information are identical.

These snapshots do not establish post-boot Squid/sing-box listener/parent connectivity, TNAS route/container state, or actual packet transformation. Pre-boot `60/4080` is cumulative, not a newly observed call or independently dated October 3 delta.

## Meaning for the campaign

Loss of the marker and regenerated runtime agree with the [source-defined transient lifecycle](../../architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). This is **automatic Voice restoration failure relative to the desired ON baseline**, with **manual native status/firewall recovery verified**. Ordinary GUI A2 persistence succeeded.

UDP/596 remained eligible for common-port interception after boot. A fixed-port test can therefore emit A2 packets with helper OFF while losing all-port Telegram capture and the STUN profile; that does not meet the campaign's frozen helper-ON baseline. Conversely, [October 3 A1](2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) and [A2](2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md) explicitly had helper ON/table14 and measured Voice-rule growth. This later reboot does not invalidate or explain away their no-reply outcomes.

The owner requires the helper's purpose, configuration, startup, fixed test conditions and any deliberate future parameter changes to be explicit. The [per-trial matrix](../../architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#telegram_voice-controls-for-every-trial) retains helper ON/STUN constants while candidate actions vary separately. Automatic one-shot recovery remains pending; no Cron, source change or new package is delivered in this documentation scope.

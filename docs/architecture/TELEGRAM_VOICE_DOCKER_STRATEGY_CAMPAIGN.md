# Telegram Voice UDP strategy campaign — Docker-first Reflector Hello experiments

**Date:** 2026-10-02. **Status:** owner installed GUI candidate `HELLO-FAKE-A1` as reported; **no new lab run, WAN wire verification, replies, or MEDIA_PASS yet**. This document is the required design/test handoff, not a claim that a candidate works. Existing measured evidence remains authoritative.

## Binding mission and owner constraints

**Fact supplied by owner:** the local provider blocks Telegram through DPI. Telegram TCP is **already handled** by the separately configured OPNsense Squid/sing-box/PF -> external parent `185.203.117.88:33128`. **Do not reopen the provider-blocking premise, replace or disturb working Telegram TCP/HTTPS, or substitute another proxy for this research.** The unresolved engineering objective is to find a **Zapret2 UDP desynchronization strategy** which makes the Telegram Reflector handshake succeed on this provider path, supports ICE selection and encrypted voice transport, and remains reproducible.

**New explicit owner execution boundary:** **do not require another real Windows/Android call for each candidate.** Stage-1 candidate search runs **first and by default via the existing TNAS Docker `tgvoice-lab`**, with the qualified current `tgcalls_cli` fixed-reflector oracle. Real P2P-disabled Windows/Android `CALL_PASS` is a *final* validation only after a candidate has repeated fixed-reflector `MEDIA_PASS` through OPNsense. A captured alternate-gateway successful Windows call is an optional *separate diagnostic/control for causal attribution*, **not a prerequisite to running the already available Docker A1 experiment**. No per-candidate real-person-call requests.

Before changing any strategy, commit goals, current evidence, precise candidate, test/restore procedure and success/unknown/failure classification to GitHub. After each **actual** measured laboratory run, attach sanitized outcome and archive/hash identities in a dated evidence document, reconcile `START_HERE`, `PROJECT_STATE`, roadmap and current chronology, and **only then** select another candidate. Do not conflate design, owner-reported Apply, observed wire transformation, remote reply and successful media.

Three approved product stages remain **unchanged**: repeated `MEDIA_PASS` on current Docker oracle -> real remote `CALL_PASS` with sustained two-way UDP and good sound -> only then approved Voice-UDP-only integration into the existing plugin Settings GUI, with IPSET/firewall lifecycle and persistent ON. Do not package temporary Docker runners, add a plugin page or implement recurring Cron as part of candidate research.

## What we have proved and why A1 is a different question

- Qualified pinned TNAS host-network Docker companion: `tgvoice-lab`; `/results/tgcalls_cli`; upstream source `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; qualified binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; caller/callee engines 13.0.0. The *local five-second P2P smoke gate passed*, verifying the binary, **not** remote reflector access.
- Current **pinned reflector epoch**: `91.108.13.10:596`, **15 seconds**, fresh `--mode reflector` per trial with both test peers within the qualified harness; TNAS host `192.168.1.100` on Docker `host`, selected **specific `91.108.13.10/32` TNAS host route via OPNsense `192.168.1.2`**, OPNsense WAN `vtnet1`, upstream `192.168.80.1`. An operator-tested independent SSH port-9222 connection and **manual** guarded TNAS-route script already exist. Docker/container and route recovery remain **manual-only** after TNAS reboot, by owner decision.
- Real-client October 2: one earlier audible successful real call had unproven media transport. Seven later deliberately OPNsense-gateway real calls failed media setup: 345 unchanged **40-byte non-STUN Reflector Hellos** + 45 STUN originals, all 390 NAT-forwarded on WAN, 90 additional zero16 STUN fakes, **no Telegram UDP replies** in seven captures. All **480** observed outbound WAN UDP datagrams had valid recorded IPv4/UDP checksums (unfragmented). A subsequent distinct Telegram Desktop WebRTC log received remote signaling/ICE candidates but timed out after ~20 seconds without a usable ICE/media connection. Do not convert these into an unfounded "Zapret2 does not work" verdict.
- Current temporary `telegram_voice_enable` prepends a **STUN-only** `--filter-l7=stun --payload=stun` fake profile and adds the **essential all-UDP-to-Telegram-IPSET** IPFW rule; it **does not transform** the identified non-STUN 40-byte Reflector Hello. GUI and helper share **one dvtws2**, not double encryption. The current IPFW outgoing hook was previously observed **before PF**; re-read actual `pfilctl heads` on a later boot.
- **Already completed; don't blindly retest:** unmodified current reflector baseline; ordered UDP-position-8 fragments; reverse position 8/16/24/32; fakefrag8 + reverse24; fakefrag8 + original (lost originals locally); and tee where original preceded fake. Their detailed `WIRE_OK / NO_REPLY_UNKNOWN` or local failure and restoration outcomes are preserved in existing [oracle architecture](TELEGRAM_VOICE_EMULATION_LAB.md) and [October 1 measured evidence](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md). A1 is **not** a claim that this old, complete fragmentation sweep is untested.
- The historical September 5 `MEDIA_PASS` used the **retired** `192.168.1.140` path and older testing epoch; do not silently reuse it as a current working control. The owner's September 22 positive-call report remains historically documented without verified attribution to the claimed fragment strategy.

## Candidate HELLO-FAKE-A1 — current operator-reported configuration

The owner **reports that the following block has been added and Applied in the ordinary OPNsense GUI Strategy**. **Only GUI Apply is reported**; exact generated active profile and IPFW rules have not yet been re-measured at this new epoch.

```text
--filter-l3=ipv4
--filter-udp=596-599
<IPSET:telegram>
--payload=unknown
--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2

--new
```

**Only hypothesis to test:** the pinned Docker reflector's **non-STUN 40-byte Hello to UDP/596** will be classified/matched as `unknown` by the *actual installed* dvtws2, and this GUI profile will cause **two additional bad-checksum zero16 UDP fakes before/around each otherwise unmodified genuine Hello**. Check the actual order in the capture; it is **not yet observed** that the fake precedes the original or that `badsum` survives WAN PF/NAT. A local configuration/capture mismatch is `PROFILE_NOT_SELECTED` or `WIRE_FAIL` and must be fixed **before** any provider efficacy interpretation.

**Non-duplication / interception:** the temporary Voice helper remains ON for this first diagnostic epoch **only for its known destination-IP-scoped IPFW interception** and existing STUN profile. In the one active dvtws2 process, A1 should match non-STUN Hello while the helper's earlier profile addresses recognized STUN. The new ordinary GUI UDP port extractor also adds `596-599` to *common* outgoing WAN IPFW capture for **all destinations** on these ports, while the dvtws2 profile itself has the resolved Telegram IPSET. Keep this extra common-port capture exposure **bounded to the laboratory trial**; inspect the actual rules and consider removing the extra capture path from the eventual approved product design, retaining destination-scoped Voice interception. The IPSET must contain `91.108.13.10` (existing GUI includes `91.108.12.0/22`); check generated runtime and selection rather than assuming success.

**Caveat:** this A1 **nonfragmented 16-byte badsum fake before an intact genuine Hello** is a different local-wire hypothesis from the earlier **40-byte fragmented fake8** plus reverse24, but it is still a **fake-packet family test**, not evidence of a new upstream vulnerability. If LAN/WAN capture shows no fakes, re-examine generated config and installed classifier; don't request a real call to determine whether the profile is selected.

## Exact planned first Docker experiment — NO real Telegram call

**Before running:** save/verify the GUI baseline (A1 already Applied), `configctl zapret status`, `configctl zapret telegram_voice_status`, `ipfw -a list`, `pfilctl heads`, and read-only `grep` of generated `runtime-v2/traffic.conf` (check A1 and STUN profile coexist and actual order) and the managed Telegram IPSET. Do not change PFIL hooks, restart Squid/sing-box or reset other firewall rules. Confirm the regular Zapret2 listener on divert 989 is actually active. Record source binary SHA as above, Docker host network/active container, and verify TNAS `ip route get 91.108.13.10 from 192.168.1.100` points via OPNsense `192.168.1.2`, not the TNAS default `192.168.1.140`. **If the TNAS reboot removed those two pre-agreed routes, only the owner may run the existing manual route script**; do not introduce automatic route recovery. If the helper is now OFF after an OPNsense reboot, **stop and reestablish the explicitly selected baseline deliberately**, not invisibly.

**Run only one 15-second fresh fixed-reflector process**, using the canonical Linux TNAS command (start captures first):

```sh
/Volume1/@apps/DockerEngine/dockerd/bin/docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15
echo "tgcalls_exit=$?"
```

Run locally on TNAS **Linux shell**, or use the [already established SSH method](TELEGRAM_LAB_OPERATIONS.md) from OPNsense with absolute `/usr/local/bin/ssh` and the documented identity/port 9222; do not paste Bash or multiline script syntax into OPNsense's default **csh**. For this already configured, ordinary GUI Strategy candidate **do not install an additional IPFW divert 990/standalone experimental dvtws2 runner**: that would mix two interventions and complicate attribution.

**Simultaneous captures from separate OPNsense csh consoles** (each one line; operator stop with Ctrl-C after CLI finishes):

```sh
tcpdump -ni vtnet0 -s 0 -U -w /tmp/tgvoice-a1-docker-lan.pcap 'host 192.168.1.100 and host 91.108.13.10 and ip'
tcpdump -ni vtnet1 -s 0 -U -w /tmp/tgvoice-a1-docker-wan.pcap 'host 91.108.13.10 and ip'
```

The WAN filter intentionally matches **IP**, not merely UDP port: it would otherwise miss non-initial IP fragments. Capture source/destination and post-NAT flow, entire genuine Hello and extra fakes, packet timing/order and IP/UDP checksums. Confirm the two snapshots and capture actually cover the *same* bounded CLI interval, and retain the CLI stdout/stderr plus exact exit status and both peers' state, stats and BWE. The exact fixed reflector endpoint/engine/duration remain constant; changing them starts a separately identified epoch. Capture original PCAP privately; publish only redacted summaries and SHA-256 hashes.

**After one trial:** record final `telegram_voice_status`, `ipfw -a list` counter deltas (if concurrent traffic exists, attribute per-PCAP rather than claiming all counters are the test), `pfilctl heads`, current runtime A1 and any failure logs. No temporary runner or extra route is installed by this planned first A1 procedure, so normal snapshot comparison should show no intentional firewall, PFIL or route mutations. Restore the previous GUI strategy **only after recording evidence and according to owner's chosen retention**, and verify the same active ordinary TCP path. Never silently change the installed A1 in the middle of the test.

## Result gates, next decision and limits

| Measured evidence | Honest status | Next action |
|---|---|---|
| A1 absent or `unknown` profile does not match 40-byte Hello; no A1 fake on WAN | `PROFILE_NOT_SELECTED` / `WIRE_FAIL` | Fix exact classifier/profile or unintended profile precedence **in the Docker lab**, after documenting. No real call. |
| Correct 16-byte zero fakes and original Hello visible, checksums/order verified; no valid reflector response | `WIRE_OK / NO_REPLY_UNKNOWN` | Retain WAN transformation and exact CLI negative outcome. Do **not** increase repeats or repeat identical A1 endlessly; select one **new** source-justified single-variable hypothesis, and record differences from completed fakefrag/fragment work before another test. |
| Valid reflector response received and qualified client accepts it | `REFLECTOR_READY` | Verify both peers' ICE state, stats/BWE and exit; **a single reply alone is not MEDIA_PASS**. |
| Both peers Established, non-zero BWE/stats on both, complete bilateral UDP and `tgcalls_exit=0` | provisional `MEDIA_PASS` | Repeat a fresh independent Docker process using the same exact A1 and fixed reflector. Only *repeated* MEDIA_PASS opens the real-user CALL_PASS gate. |
| No control-proven endpoint reply across all candidates, despite WIRE_OK | `NO_REPLY_UNKNOWN` (not proven strategy/provider cause) | Record ambiguity and choose one targeted new hypothesis or obtain a recent same-endpoint working-path control for *causal attribution*, without requiring live human calls for every candidate. |

**One-factor discipline:** do not mix helper OFF/ON, STUN repeats, GUI fake blob/badsum, fragment order, PFIL hook order, NAT, endpoint and binary changes in the same comparison. The current A1 epoch keeps current helper state and known TCP paths as its baseline. No real calls, no TCPSquid debugging and no recurring Cron before the Docker oracle shows a promising repeatable outcome.

**References:** [canonical Docker oracle and existing closed candidate order](TELEGRAM_VOICE_EMULATION_LAB.md), [TNAS SSH/route and operator-tested manual recovery](TELEGRAM_LAB_OPERATIONS.md), [GUI vs Voice destination capture and PFIL order](TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md), [existing cumulative past results](../verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [seven real-call LAN/WAN failures and checksum findings](../verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md), [subsequent WebRTC ICE timeout](../verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md).

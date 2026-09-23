# Telegram Voice traffic emulation and strategy oracle

**Status:** CURRENT TEMPORARY DESIGN · STANDALONE FRAGMENT SWEEP CLOSED · FAKEFRAG8 + REVERSE24 NEXT
**Updated:** 2026-09-23
**Project package identity on `main`:** `VERSION=0.5.0`, `PLUGIN_REVISION=3`
**Research authority:** [`TELEGRAM_VOICE_UDP.md`](../research/TELEGRAM_VOICE_UDP.md)
**Phase A evidence:** [`2026-08-28-telegram-voice-phase-a-live-observation.md`](../verification/evidence/2026-08-28-telegram-voice-phase-a-live-observation.md)
**Phase B evidence:** [`2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md`](../verification/evidence/2026-09-02-telegram-voice-phase-b-stun-baseline-live-fail.md)
**Historical September 2 Zapret2 pin:** [`2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](../verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md)
**Companion build/runtime evidence:** [`2026-09-04-telegram-voice-companion-build-runtime-pass.md`](../verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md)
**Current tgcalls owner-live evidence:** [`2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md`](../verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md)
**Current OPNsense/provider baseline:** [`2026-09-20-telegram-voice-current-opnsense-baseline.md`](../verification/evidence/2026-09-20-telegram-voice-current-opnsense-baseline.md)
**Historical fixed-reflector control/host-topology evidence:** [`2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](../verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md)

## Current task and retired route

**Establish and repeat a call carrying bidirectional media through OPNsense in the rebuilt laboratory.** A correct packet transformation is an intermediate gate; the required laboratory result is `MEDIA_PASS`, followed by a real remote Windows/Android `CALL_PASS` before product acceptance.

The owner explicitly confirms that `192.168.1.140` is no longer a working route. Do not use it as a current independent control, prescribe a detour through it, or assume it is the restoration destination. Its September 5 success belongs to the old epoch and binary. No fresh independent working control is currently established; this limits causal classification, not permission to continue the lab campaign.

The laboratory was rebuilt because the owner reports a change in Telegram voice transport. [Current protocol research](../research/TELEGRAM_VOICE_UDP.md) records the upstream networking/MTProto changes, disabled-by-default experiments and the remaining real-client parity question. Current runs select engine `13.0.0` on both peers without custom overrides.

The [September 21 ordered run](../verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) remains `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, with no established call in that run. For the [September 22 reverse run](../verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), the owner reports an established call with correct routing at call time. Its captures contain no records under `host 91.108.13.10`, and the UDP/596 fragmentation rule has zero hits. The owner later identified the same fixed-reflector CLI command; its positive output remains unavailable. These narrow captures neither refute the call nor prove fragmentation caused it. The separate [post-reboot repeat](../verification/evidence/2026-09-22-telegram-voice-reverse8-postreboot.md) now correlates that command with 60 valid reverse pairs and zero replies: both peers `Reconnecting`, zero BWE, exit 1, exact restoration. This repeat qualifies reverse position-8 emission but has no media pass. The [September 23 reverse position-32 run](../verification/evidence/2026-09-23-telegram-voice-reverse32.md), [guarded reverse position-16 run](../verification/evidence/2026-09-23-telegram-voice-reverse16.md), and [guarded reverse position-24 run](../verification/evidence/2026-09-23-telegram-voice-reverse24.md) all emitted the intended valid local-WAN reverse fragment pairs with no replies/media and exact restoration. Position 24 closes standalone position widening for this reflector epoch. The next bounded candidate adds one fragmented checksum-invalid zero fake before the already-qualified real reverse24 path; the earlier positive owner report remains separate.

## 2026-09-20 current-tgcalls oracle update

The owner uses Telegram calls on Windows and Android, not Telegram-iOS. The
historical `e3069322a3d1e16ecb11a5e302242e59ddd7f09e` laboratory binary is no
longer a useful active oracle for this scope.

The TOS compose recipe now builds only the current public tgcalls commit
`efd330ca04f74706024a5abdfb5b41f4e4dd1065` and installs it as
`/results/tgcalls_cli`, replacing any older laboratory binary.

The public tgcalls head contains newer reflector/networking work, including the
current 11/13/14 engines, reflector-keying experiments and MTProto transport
plumbing. Its public standalone tree does not carry the outer Bazel targets
needed for the new test-only v2wasm 18/19 engines. The Linux lab therefore makes
one explicit build-only adaptation: it removes the CLI registration/data
dependency for 18/19 and adds the two current C++ sources required by the outer
`tgcalls_core` target. It does not alter the 11/13/14 networking implementation.

The current binary is accepted only if a local five-second P2P smoke test exits
zero. Its exact source SHA, patchset label and SHA-256 are written to
`/results/build-manifest.txt`; smoke output is written to
`/results/smoke.txt`.

Earlier Phase C evidence that used the historical binary remains valid evidence
for those exact epochs, but new provider experiments use only the current
`/results/tgcalls_cli`. Real Windows/Android behaviour still requires one final
P2P-disabled client call.

## Purpose

Build a truthful, repeatable way to generate traffic that is materially equivalent to the Telegram UDP call path and use that traffic to search Zapret2 strategies without requiring a human Telegram call for every candidate.

The lab must answer two different questions separately:

1. did OPNsense and `dvtws2` emit the intended packets;
2. did a live Telegram UDP endpoint accept the resulting path and carry bidirectional media.

Offline packet transformation can answer the first question. It cannot predict an unknown provider DPI or destination-routing policy with enough confidence to answer the second. A live endpoint oracle is mandatory for media success. A fresh independent working control is required to isolate provider-path failure causally; its absence does not prevent recording a direct media success or continuing bounded experiments.

## Current truth and decision

The selected design is a three-tier live oracle supported by an offline wire predictor:

| Layer | Probe | What it proves | What it does not prove |
|---|---|---|---|
| Offline | captured/synthetic packet transformed with the selected profile | rule/profile match, generated byte layout, fragments, order, checksums | any provider or remote-endpoint result |
| Tier 1 | standards-valid TURN Allocate transaction | reachable Telegram TURN/STUN response path | reflector readiness or media |
| Tier 2 | pinned official `tgcalls_cli` through a real Telegram UDP reflector | reflector handshake plus bidirectional WebRTC media transport with no TCP fallback | real Telegram API signaling or decoded audible speech |
| Tier 3 | one real P2P-disabled remote Telegram call | end-to-end product behavior | universal behavior across providers/endpoints |

Tier 2 is the primary automatic strategy oracle. Tier 1 is a fast discriminator and diagnostic probe. Tier 3 is the final acceptance row, not the search loop.

The current companion has passed its local gate. Endpoint `91.108.13.10:596` was then run through the OPNsense/provider path selected by TNAS gateway `192.168.1.2`. The 2026-09-20 LAN/WAN capture proved two current 40-byte Reflector Hello flows crossed OPNsense/NAT cleanly: 60/60 LAN packets appeared on WAN, payloads matched byte-for-byte, TTL changed only by forwarding, and checksums remained valid. No UDP reply returned and both tgcalls sides remained `Reconnecting`. The current no-desynchronization baseline is therefore `WIRE_OK` / `NO_REPLY_UNKNOWN`, not a claim that provider DPI has already been isolated. The current exchange is non-STUN, so the paused STUN-only `_4` profile is not a direct candidate for this baseline. The subsequent September 21 ordered position-8 candidate is now wire-qualified but still receives no reply. The September 22 post-reboot reverse position-8 repeat also has 60 valid pairs, zero replies and a failed call, with exact restoration. The September 23 reverse position-32, reverse position-16 and reverse position-24 runs all emitted their intended valid reverse pairs without replies/media and restored the measured state exactly. The final position-24 run produced 60 equal IP length-44 pairs and closes standalone position widening. Next, keep the real reverse24 serialization fixed and add one fragmented fake before it; full media success remains the objective.

The previous plan to publish and immediately live-test one STUN-only ordered-fragment candidate is paused. The remote branch `v0.5.0_4-telegram-voice-ipfrag` at `3ecdd1b3326fe7655e1d7df9edd51808e2a68dc9` contains one prepared candidate, but it has no PR, exact-head CI, merge, package publication, or owner-live result. It must not be merged as-is. After Phase C evidence, it will be rebased/reworked, replaced, or rejected.

## Test topology and fixed facts

Owner-live Phase A/B topology:

- OPNsense 26.7.3_8;
- LAN `vtnet0`, WAN `vtnet1`;
- Windows 11 LAN test client; the exact RFC1918 address remains private and is represented as `<probe-client>` in public procedures;
- Telegram P2P disabled on both participants for the clean comparison;
- ordinary Telegram signaling/TCP remained redirected through a router-local proxy path to an external HTTP proxy;
- the external proxy endpoint is deliberately not recorded;
- the normal Traffic Strategy remained active during every call.

The concurrent Telegram UDP profile covered only destination ports `80,443,5222,8888` and selected `mtproto`. The observed voice candidates used ports `596–599` and `1400`, so those call packets did not enter that ordinary UDP rule. The YouTube and user TLS profiles were TCP-only. The concurrent TCP proxy path is relevant because it explains audible fallback, but the ordinary strategy does not explain the observed voice-UDP failure or the Phase B helper packets.

A separate generic STUN exchange to `141.101.90.1:3478` was bidirectional on the same WAN environment. This proves that UDP and STUN-shaped traffic were not universally blocked. It does not prove that a Telegram destination is reachable, which is why a control must use the exact same Telegram endpoint as the provider-path candidate epoch.

## Phase C companion placement on TOS 7

Owner decision: retain the existing TOS/Docker network named `host` and use no other Docker network for this experiment.

Docker host mode shares the TNAS network namespace. The container has no independent IP address, MAC address, DHCP lease or default route. Its packets use the TNAS host identity. The 2026-09-05 control therefore appeared as source `192.168.1.100` and followed gateway `192.168.1.140`.

Consequences:

- there is no per-container MAC that pfSense DHCP can match; it can match only the TNAS MAC;
- a separate DHCP lease such as `192.168.1.239` cannot be assigned to this host-network container;
- pfSense may deliver a classless destination route keyed to the TNAS MAC, but the route belongs to the shared TNAS namespace and is not container-private;
- changing default-gateway data for the visible MAC changes the TNAS host path, affecting all host-network workloads;
- do not change the TNAS default route for this temporary experiment.

The effective provider path must go through OPNsense `192.168.1.2`. If the current route already does so, leave it in place. When a change is necessary, the accepted selector is one destination-specific `/32` route on TNAS, supplied by owner policy or a bounded explicit transaction. Prove the effective route and restore the actual pre-test snapshot; never hardcode retired `192.168.1.140`:

1. record `ip route get <reflector-ip>`;
2. add only `<reflector-ip>/32 via 192.168.1.2` on `ovs_eth1`;
3. require the selected route before starting the process;
4. run one isolated epoch;
5. remove only the route owned by the epoch;
6. require byte-for-byte semantic restoration of the original route.

The current tests use the existing TNAS and OPNsense consoles with `docker exec tgvoice-lab ...`. Temporary key-only SSH may later centralize repeated execution on OPNsense, but it is not a prerequisite for the next candidate and introduces no GUI or permanent service.

Because a host route affects every TNAS process contacting that exact reflector, the endpoint must be isolated for the epoch. A failed route restore is `RESTORE_FAILED`.

## Captured protocol fixtures

### TURN/STUN initial request

The clean calls emitted a 28-byte unauthenticated TURN Allocate Request:

```text
0003 0008 2112a442 <12-byte transaction ID>
0019 0004 11000000
```

Interpretation:

- STUN method: Allocate Request;
- magic cookie: `0x2112A442`;
- one `REQUESTED-TRANSPORT` attribute requesting UDP;
- 96-bit transaction ID;
- retransmissions reuse the same transaction ID.

The observed nine-send schedule, relative to the first request, was approximately:

```text
0, 0.25, 0.75, 1.75, 3.75, 7.75, 15.75, 23.75, 31.75 seconds
```

This corresponds to intervals of `0.25, 0.5, 1, 2, 4, 8, 8, 8` seconds. The semantic probe should stop early after a correlated reply but otherwise reproduce this bounded schedule.

RFC 8656 says an unauthenticated Allocate Request normally receives an authentication error containing realm/nonce information. For the reachability oracle, a correlated STUN error is useful success: the server replied. Full TURN credentials are not required to prove the first response path and must not be harvested from or stored from a real call.

### Telegram Reflector Hello

The observed reflector probe is a separate 40-byte non-STUN datagram:

```text
<16-byte peer/session tag>
fffffffffffffffffffffffffeffffff
000000000000007b
```

The captured 16-byte tag consists of a 12-byte session/routing prefix and a 4-byte local tag. The constant tail is 16 marker bytes followed by the big-endian value 123. Telegram retransmits the Hello approximately every 500 ms while the reflector port is not ready; clean captures contained 90 sends over about 44.5 seconds.

The official reflector implementation accepts only replies from the selected server and requires the first 12 bytes to match the local peer-tag prefix. Media packets are wrapped as:

```text
<16-byte target peer tag><4-byte sender tag><4-byte payload length>
<encrypted media payload><zero padding to a 4-byte boundary>
```

A captured Hello is a format/timing fixture, not a reusable live credential. Blind PCAP replay is not a valid media oracle because it reuses stale per-call tags, provides no paired peer, and cannot establish the WebRTC state machine.

## Authoritative reflector emulator

Use the official [`TelegramMessenger/tgcalls`](https://github.com/TelegramMessenger/tgcalls) CLI as the protocol implementation authority. The active build-validated executable pin is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`, built inside the pinned outer Telegram-iOS workspace `6ad963e5b62d354da79040f388ae2b9132fb17b8`. The outer workspace supplies Bazel/WebRTC dependencies only; the active voice engine source is the current tgcalls pin.

Why it is the current authority:

- it runs caller and callee `tgcalls` instances in one process;
- signaling is bridged locally, so no Telegram account or Telegram API session is required;
- reflector mode routes both instances through a real Telegram UDP reflector;
- it generates paired random peer tags and a shared encryption key;
- it generates 440 Hz audio frames with the project fake audio device;
- reflector servers are configured with `isTurn=true` and `isTcp=false`, so a successful run cannot be masked by the owner's TCP/HTTP-proxy fallback;
- exit status 0 requires a call to reach Established, statistics to be collected for both sides, and non-zero bandwidth estimation on both sides.

Current limitation: the renderer discards received audio. Exit 0 proves bidirectional media transport and WebRTC state, not waveform identity or human-audible quality. The result name must therefore be `MEDIA_PASS`, not `AUDIO_PASS`.

Build-validated source:

- [outer Telegram-iOS workspace](https://github.com/TelegramMessenger/Telegram-iOS/tree/6ad963e5b62d354da79040f388ae2b9132fb17b8);
- [UDP-only reflector server, generated audio, local signaling and exit gate](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/main.cpp);
- [official reflector-list runner](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tools/cli/run-test.sh);
- [reflector Hello/retry and framing implementation](https://github.com/TelegramMessenger/tgcalls/blob/efd330ca04f74706024a5abdfb5b41f4e4dd1065/tgcalls/v2/ReflectorPort.cpp);
- Historical `e3069322...` build evidence remains archived for the earlier Phase C epochs; it is no longer the active executable.

### Reproducible companion build gate — passed

The standalone tgcalls Dockerfile is not a standalone build context: it refers to outer `build-input/` and `//submodules/TgVoipWebrtc/...` paths. The working TOS recipe uses the complete pinned Telegram-iOS build workspace and explicitly replaces its historical tgcalls gitlink with the current `efd330ca...` source pin.

Recorded build identity:

| Item | Immutable value |
|---|---|
| Telegram-iOS | `6ad963e5b62d354da79040f388ae2b9132fb17b8` |
| tgcalls | `efd330ca04f74706024a5abdfb5b41f4e4dd1065` |
| Ubuntu image | `sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517` |
| Bazel | `8.4.2`, SHA-256 `4dc8e99dfa802e252dac176d08201fd15c542ae78c448c8a89974b6f387c282c` |
| `tgcalls_cli` | SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc` |

The canonical host-network recipe is [`tools/telegram-voice-lab/compose.tos.yml`](../../tools/telegram-voice-lab/compose.tos.yml). It pins the exact Ubuntu digest and records the bounded Linux/OpenH264/WebRTC/CRC32C/FFmpeg/header fixes needed by this outer workspace. The [September 4 evidence](../verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md) records the historical outer-workspace build; [September 20 qualification](../verification/evidence/2026-09-20-telegram-voice-current-tgcalls-owner-live-pass.md) identifies the active rebuilt binary.

The owner then ran a five-second `--mode p2p` self-test of the current binary. Both sides reached `Established` at 0.039 seconds, each produced five bitrate records, BWE was non-zero, no error was reported, and the process exited 0. This is the accepted local build/runtime gate only. Changing either source pin, the image digest, or the recorded build recipe requires a new binary digest and repeat qualification.

The companion remains a reproducible Linux container outside the OPNsense package. Do not add Bazel, WebRTC, an Ubuntu image, or the `tgcalls` runtime to the plugin package.

After the tgcalls control capture establishes exact wire behavior, a lightweight native OPNsense/Python two-socket reflector probe may be investigated for fast screening. It would need fresh paired tags, Hello validation, framed payload in both directions and exact transaction/state isolation. Until byte-for-byte equivalence is proven, it is only a hypothesis. Even when valid it can provide at most `REFLECTOR_READY` plus a framed-data result; pinned tgcalls remains the `MEDIA_PASS` authority.

## Tier 1 — semantic TURN probe

For each candidate:

1. keep one fixed live endpoint `IP:port` for the complete search epoch;
2. open a fresh UDP socket/source port;
3. generate a fresh random 96-bit transaction ID;
4. build the exact 28-byte Allocate Request with `REQUESTED-TRANSPORT=UDP`;
5. retransmit the byte-identical request with the captured bounded schedule;
6. stop on a valid correlated response;
7. close the socket before the next candidate.

A reply is `TURN_REPLY` only when all of these match:

- source IP and UDP port are the selected endpoint;
- STUN framing and magic cookie are valid;
- message method is Allocate and class is a response/error response;
- transaction ID exactly equals the current request ID.

Authentication error `401`, stale-nonce `438`, an alternate-server response, another valid Allocate error, or Allocate success all prove a returned STUN path. An arbitrary non-empty UDP datagram does not.

This corrects the current Generic UDP contract, which treats any non-empty reply as candidate success and does not correlate a STUN transaction.

## Tier 2 — real-reflector media probe

For one search epoch:

1. select one explicit reflector `IP:port`, keep source/binary/engine/custom parameters fixed and record them;
2. record any fresh independent control, if available; otherwise preserve the `NO_REPLY_UNKNOWN` limitation without routing through retired `192.168.1.140`;
3. record the TNAS route and require the selected path through OPNsense; change only an owned endpoint `/32` if necessary;
4. start capture and the qualified bounded runner on OPNsense, wait for its `READY`, then start a fresh TNAS `docker exec` process;
5. record both CLI peer states, stats/BWE, exit status, IPFW counters, complete LAN/WAN evidence and cleanup;
6. restore only owned runtime/rule/hook/route mutations to their measured pre-test state;
7. repeat any winner with fresh process/flow state.

Do not select a random reflector during a comparison. An endpoint change begins another epoch.

Current TNAS command (Bash):

```sh
docker exec tgvoice-lab /results/tgcalls_cli \
  --mode reflector --reflector 91.108.13.10:596 --duration 15
echo "tgcalls_exit=$?"
```

Temporary key-only SSH may invoke the same command; direct TNAS execution is already proven.

The official list is available from `https://core.telegram.org/getReflectorList`.

## Temporary OPNsense-console orchestration boundary

The existing Generic UDP Strategy Lab is not modified. It generates firewall-local probes, accepts arbitrary replies and cannot model reflector media.

The owner selected console-only temporary orchestration:

- the TNAS console starts `docker exec`; optional temporary key-only SSH may centralize execution on OPNsense;
- any orchestration script is staged outside installed plugin paths, preferably under `/tmp`;
- the script owns only its temporary changes: one fixed reflector/port, IPFW/dvtws2 state, captures, hook ordering and, only when needed, an endpoint `/32` route;
- every baseline/candidate uses a fresh companion process/source-flow;
- every exit path proves route and Zapret2/firewall restoration;
- temporary SSH keys/scripts are removed when the research closes.

No Telegram Voice GUI, MVC/API/configd addition, daemon, persistent controller or Generic UDP semantic change is authorized. The temporary laboratory will not become permanent plugin code.

Do not assume WAN IPFW source identity. Prove pre/post-NAT visibility on the no-desynchronization epoch before installing a candidate rule.

### Qualified post-NAT position-8 runner

The corrected temporary download is named `tgvoice_ipfrag8_postnat_v2.py`, with revision marker `postnat-nofrag-v2`. The distinct filename prevents confusion with earlier `tgvoice_ipfrag8.py` runs. On OPNsense it is invoked with `/usr/local/bin/python3 -u /tmp/tgvoice_ipfrag8_postnat_v2.py --after-nat`.

The measured contract is:

- one temporary dvtws2 listener on divert 990 and owned rule 18990, bounded to the translated test flow's WAN source, fixed destination `91.108.13.10` and UDP port 596;
- a reflector profile selecting IPv4, that destination/port and `--payload=all`, with `send:ipfrag:ipfrag_pos_udp=8` followed by `drop`;
- fragmentation after PF has translated the intact UDP datagram and its checksum;
- temporary IPv4 output hook order PF then IPFW, restored to its original order afterward; this hook-order change affects **all outgoing IPv4** while active, although the divert rule is narrow;
- `frag !mf,!offset` on the divert rule, requiring both MF=0 and offset=0. Plain `not frag` is insufficient because the first fragment has offset zero;
- WAN capture by endpoint address/IP protocol, retaining non-initial fragments; filtering only by UDP port loses necessary evidence;
- a bounded 120-second window, with rule removal before hook restoration and listener shutdown; no route mutation in the measured runner.

The earlier pre-NAT attempt produced invalid UDP checksums after translation. The first post-NAT implementation then recaptured first fragments; only second fragments appeared on WAN. Neither is a network-strategy failure. The corrected run intercepted 60 originals/4080 bytes, emitted 60 complete ordered pairs with valid checksums, received no reply and restored the pre-test snapshot. See the [evidence](../verification/evidence/2026-09-21-telegram-voice-postnat-ipfrag8.md) for exact hashes and state limits.

Narrow WAN-source/destination matching is not per-container isolation under Docker host mode: isolate other TNAS activity to the same reflector for the epoch. Normal rules 19000/19001 were already absent in the post-NAT snapshots; restoring those snapshots must not be described as re-enabling the normal Zapret rule set.

## Offline wire predictor

Use the captured 28-byte TURN and 40-byte Hello fixtures to predict deterministic local behavior:

- whether the IPFW tuple would intercept the packet;
- which dvtws2 profile would select it;
- whether the action applies to STUN only or to the exact reflector flow;
- number/order/length of generated packets;
- IPv4 fragment ID, offsets and MF flags;
- byte-exact reassembly and UDP checksum;
- absence of the unmodified original when `send:ipfrag` is followed by `drop`.

This predictor is a regression oracle for implementation and a way to reject malformed candidates before live testing. It must never label a strategy as provider-working. The provider response remains a black-box live measurement.

## Result taxonomy

Use these names consistently:

| Result | Required evidence |
|---|---|
| `WIRE_OK` | intended transformed packets observed on WAN with valid structure/checksums and required original suppression |
| `TURN_REPLY` | semantically valid correlated Allocate response |
| `REFLECTOR_READY` | valid reflector response accepted by the pinned client/peer-tag check |
| `MEDIA_PASS` | both tgcalls sides establish, both collect stats, both have non-zero BWE, exit 0 |
| `CALL_PASS` | final real remote-participant Telegram call passes the selected packet and user-visible checks |
| `NO_REPLY_UNKNOWN` | no valid reply and the same endpoint has not passed a fresh independent control |
| `NETWORK_FAIL` | endpoint passed fresh control, candidate is `WIRE_OK`, but the provider-path oracle failed |
| `RESTORE_FAILED` | temporary runtime/firewall/profile state was not semantically restored; this overrides other results |

Do not collapse `TURN_REPLY` into `MEDIA_PASS`, or `MEDIA_PASS` into `CALL_PASS`.

## Control-path requirement for causal failure attribution

A silent UDP endpoint is ambiguous. It may be blocked, offline, rate-limited, stale, or rejecting the probe.

Before assigning a causal `NETWORK_FAIL` verdict:

- the exact reflector `IP:port` must have a recent `MEDIA_PASS` from an independently unblocked path;
- a TURN endpoint should have a recent correlated reply on a control path where practical;
- endpoint, port, tgcalls commit, probe command, and observation window must match;
- if the control also fails or no working control exists, retain the wire/media observations and report `NO_REPLY_UNKNOWN`; the cause is unresolved, so do not discard useful local evidence or claim strategy-wide failure.

A fresh working control can use another ISP/mobile path or an authorized UDP-capable tunnel. None is established now, and `192.168.1.140` is explicitly retired. Do not block the current lab goal on that route. The existing TCP-only proxy is not a UDP control.

## Initial candidate order

Keep TURN/STUN and reflector candidates as separate families because they are different protocols and can fail independently.

### Reflector family — highest current value

1. no desynchronization — completed on September 20, `WIRE_OK / NO_REPLY_UNKNOWN`;
2. ordered IPv4 fragmentation at UDP position 8 — corrected post-NAT setup completed on September 21, `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`;
3. reverse fragment order at position 8 using Zapret2's `ipfrag_disorder` option — post-reboot repeat wire-qualified on September 22, `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, no media pass; the earlier positive owner report remains separate;
4. guarded reverse positions 32, 16 and 24 — all live-qualified on September 23 as `WIRE_OK / NO_REPLY_UNKNOWN / RESTORE_OK`, with no media pass; position 24 closes standalone position widening;
5. fragmented fake plus qualified real fragmentation — next bounded family. The first candidate is one 40-byte zero fake with bad UDP checksum and random IPv4 ID, fragmented ordered at UDP position 8, followed by the already-qualified real reverse24 pair;
6. stop widening if the control-proven endpoint remains silent for every on-wire-correct family.

Position 8 separates the UDP header from the complete 40-byte Hello. Position 32 cuts inside the constant reflector marker. Exact reverse position-8, position-32, position-16 and position-24 serialization are now live-qualified. Position 24 produced 60/60 equal IP length-44 reverse pairs, offset 24/MF=0 first and offset 0/MF=1 second; all intercepted application payloads were 40 bytes, so its <=16-byte short guard was not exercised. The corrected standalone position sweep therefore ends. The next candidate keeps real reverse24 unchanged and prepends a fake pair. The fake uses 40 zero application bytes, `badsum`, `ip_id=rnd`, and ordered UDP-position-8 fragmentation; fragmenting the fake is required because an unfragmented raw-sent fake could re-enter the post-NAT `frag !mf,!offset` divert rule. Archive analysis must verify that fake and real fragment IDs differ, the fake reassembled UDP checksum is intentionally invalid, and the real pair remains checksum-valid and payload-exact. Do not count pre-NAT or first-fragment-recapture defects as failed candidates for the corrected setup. Engine/custom-parameter comparisons belong to separate epochs so their effects are not mixed with fragmentation changes.

### TURN/STUN family

1. no desynchronization;
2. zero16/repeats=2 — already `WIRE_OK` and `NETWORK_FAIL` on the owner path;
3. ordered IPv4 fragmentation at position 8 — prepared but not network-tested in the paused `_4` branch;
4. reverse position-8 fragmentation;
5. bounded alternate positions;
6. fake-plus-fragment only after the independent families.

Do not increase fake repeats blindly. Do not interpret the Phase B zero-fake result as evidence about reflector strategies: `--filter-l7=stun` and `--payload=stun` deliberately left every Reflector Hello unchanged.

## Decision tree after measurement

| Evidence | Interpretation and action |
|---|---|
| control `MEDIA_PASS`; provider baseline fails; one candidate passes | provider-specific working candidate found; repeat and verify real call |
| control `MEDIA_PASS`; all candidates `WIRE_OK` but all network probes fail | destination-IP/direction/routing or fragmentation policy becomes the leading explanation; payload-only Zapret2 is not demonstrated as sufficient |
| TURN replies return but reflector/media stays silent | treat reflector as the active blocker; do not promote a TURN-only strategy |
| reflector `MEDIA_PASS` but TURN stays silent | reflector path may be sufficient for calls; verify with one real P2P-disabled call before product decision |
| both control and provider fail | harness/endpoint epoch invalid; no DPI conclusion |
| provider baseline passes | no bypass is needed for that endpoint/epoch; use it as a positive harness control, not a strategy win |

If no payload/fragment strategy passes while the same endpoints pass on an unblocked path, the practical solution moves outside a Zapret2-only payload strategy: UDP-capable tunneling/relay or continued Telegram TCP-reflector fallback through the existing proxy path.

## Real-call final gate

After one candidate has repeated `MEDIA_PASS`:

- remote participant, not the same LAN;
- P2P disabled on both Telegram clients;
- existing Telegram TCP proxy unchanged;
- clean helper OFF/ON/OFF comparison;
- on-wire proof that the selected strategy acted on its intended UDP protocol;
- inbound and sustained bidirectional Telegram UDP;
- two-way sound and no material delay;
- exact cleanup.

Only this row is `CALL_PASS`. Audio without sustained UDP remains fallback evidence, exactly as Phase A demonstrated.

## Implementation sequence and current acceptance

1. [x] Rebuild and digest-pin the current companion; pass its local P2P runtime gate.
2. [x] Keep the existing Docker `host` topology and use the measured TNAS path through OPNsense.
3. [x] Retire `192.168.1.140` as a current working control; preserve the September 5 result as history.
4. [x] Measure the current fixed-endpoint no-desynchronization baseline with LAN/WAN attribution.
5. [x] Correct pre-NAT checksum corruption and post-NAT recapture; qualify ordered position-8 output and exact restoration.
6. [x] Validate reverse position-8 syntax and preserve the first archive together with the owner's established-call/correct-route observation.
7. [x] Correlate the post-reboot CLI repeat and qualify reverse position-8 wire output/restoration; preserve the earlier positive report separately.
8. [x] Live-qualify reverse position-32 output and exact restoration; record no replies/media.
9. [x] Live-qualify guarded reverse position-16 output and exact restoration; record no replies/media.
10. [x] Live-qualify guarded reverse position-24 output and exact restoration; record no replies/media and close standalone position widening.
11. [x] Prepare the first fragmented-fake + qualified reverse24 runner with explicit bad-checksum fake and separate fake/real fragment identity requirements.
12. [ ] Live-test fragmented fake8 + reverse24 and qualify wire/media/restoration evidence.
13. [ ] Investigate real-client engine/configuration parity in separate experiments where source evidence justifies it.
14. [ ] Reach and repeat `MEDIA_PASS` through OPNsense with both peers established, stats/BWE on both sides and exit 0.
15. [ ] Complete one remote P2P-disabled Windows/Android call with two-way sound and sustained bidirectional UDP (`CALL_PASS`).
16. [ ] Remove temporary owned routes/access/scripts at closeout; archive results and decide the paused `_4` branch.

Every new candidate must retain exact endpoint/process isolation, complete wire/media evidence and exact restoration. Optional SSH automation and a secondary correlated TURN probe are not blockers for the present reflector-call objective. Package identity remains `VERSION=0.5.0`, `PLUGIN_REVISION=3`; the laboratory stays outside permanent plugin code.

## Recorded concurrent normal Traffic Strategy

The following redacted strategy was active during Phase A/B. Host/IP list placeholders are project macros; no external proxy endpoint is included.

```text
--filter-tcp=80
<HOSTLIST:youtube>
--filter-l7=http
--payload=http_req
--lua-desync=fake:blob=http_iana_org:tcp_md5
--lua-desync=multisplit:pos=method+2

--new

--filter-tcp=443
<HOSTLIST:youtube>
--filter-l7=tls
--out-range=-d10
--payload=tls_client_hello
--lua-desync=multidisorder:pos=midsld

--new

--filter-tcp=80,443,5222,8888
<IPSET:telegram>
--filter-l7=mtproto
--payload=mtproto_initial
--lua-desync=fake:blob=stun:tcp_ts=-600000:repeats=6
--lua-desync=fake:blob=tls_4pda:tcp_ts=-600000:repeats=6
--lua-desync=fake:blob=tls_max:tcp_ts=-600000:repeats=6

--filter-udp=80,443,5222,8888
<IPSET:telegram>
--filter-l7=mtproto
--payload=mtproto_initial
--lua-desync=fake:blob=stun:tcp_ts=-600000:repeats=6
--lua-desync=fake:blob=tls_4pda:tcp_ts=-600000:repeats=6
--lua-desync=fake:blob=tls_max:tcp_ts=-600000:repeats=6

--filter-tcp=443
--filter-l7=tls
<HOSTLIST:user>
--out-range=-d10
--payload=tls_client_hello
--lua-desync=multisplit:pos=1:seqovl=1
```

## Primary standards and protocol references

- [Telegram calls API](https://core.telegram.org/api/calls)
- [Telegram WebRTC connection object](https://core.telegram.org/constructor/phoneConnectionWebrtc)
- [STUN RFC 8489](https://www.rfc-editor.org/rfc/rfc8489.html)
- [TURN RFC 8656](https://www.rfc-editor.org/rfc/rfc8656.html)
- [Zapret2 v1.0.4 standard IP fragmentation](https://github.com/bol-van/zapret2/blob/2c21faa80e1acb71ddceb8b49176f266b7d33f05/docs/manual.en.md#standard-ipfrag)

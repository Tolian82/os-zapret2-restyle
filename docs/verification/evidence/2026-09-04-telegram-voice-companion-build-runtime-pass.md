# Telegram Voice Phase C companion — reproducible build and local runtime gate

**Status:** OWNER-LIVE EVIDENCE · BUILD/RUNTIME GATE PASS · FIXED-REFLECTOR NETWORK ORACLE NOT YET RUN
**Observed:** 2026-09-04
**Host:** TerraMaster TOS 7 · `linux/amd64`
**Container network:** Docker `host`
**Architecture authority:** [`TELEGRAM_VOICE_EMULATION_LAB.md`](../../architecture/TELEGRAM_VOICE_EMULATION_LAB.md)
**Canonical TOS recipe:** [`compose.tos.yml`](../../../tools/telegram-voice-lab/compose.tos.yml)

## Scope and result

The owner built the official Telegram `tgcalls_cli` from a complete pinned Telegram-iOS workspace on the TNAS and ran its in-process P2P self-test. The build completed successfully and the self-test reached `Established` on both sides, collected statistics for both peers, reported non-zero bandwidth estimation, reported no errors, and exited with status 0.

This closes the companion **build/runtime gate**. It does not establish `REFLECTOR_READY`, `MEDIA_PASS`, provider reachability, OPNsense routing, or DPI-bypass effectiveness. The P2P test keeps both peers inside one process and the host network namespace; a real fixed Telegram reflector is the next network boundary.

## Immutable build identity

| Input/artifact | Recorded identity |
|---|---|
| outer source workspace | `TelegramMessenger/Telegram-iOS@6ad963e5b62d354da79040f388ae2b9132fb17b8` |
| tgcalls gitlink inside that workspace | `TelegramMessenger/tgcalls@e3069322a3d1e16ecb11a5e302242e59ddd7f09e` |
| Ubuntu image used by the running container | `ubuntu@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517` |
| Bazel | `8.4.2` |
| Bazel binary SHA-256 | `4dc8e99dfa802e252dac176d08201fd15c542ae78c448c8a89974b6f387c282c` |
| Bazel Central Registry snapshot | `6acdcdaceec1d16120c7f44765e3240cab7f6b67` |
| produced binary | `/results/tgcalls_cli` |
| produced binary SHA-256 | `c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a` |
| manifest build time | `2026-09-04T18:54:52Z` |
| canonical repository recipe SHA-256 | `336eef0ce0cf5dc3f983c1436ffe7cbe0096d614d75846a5b22fedddffe14817` |

Host tooling reported Docker Engine `29.4.0` and Docker Compose `5.1.2`. Container inspection reported `network=host`, `status=running`, and the same immutable Ubuntu image ID recorded above.

The owner-executed LF Compose source had SHA-256 `c057d271daba4b896a53bec2f5d973ffa36da03fd3f94018cf2c5e451bb7a316`. TOS stored the deployed file with CRLF line endings at SHA-256 `eb095b519111d2e2774f48defbc9cc61f847ddb8df43714ae285feeb6d31a5bf`; exact LF-to-CRLF conversion accounts for the byte-digest difference. The committed canonical recipe makes one reproducibility hardening change: its image reference pins the exact already-used Ubuntu digest instead of relying on the mutable `ubuntu:24.04` tag.

## Build compatibility work recorded by the recipe

The outer Telegram-iOS tree is required because the standalone tgcalls Dockerfile refers to outer `build-input/` and `//submodules/TgVoipWebrtc/...` paths. The canonical recipe records the complete build context and the bounded Linux fixes that were required:

- use a pinned raw Bazel Central Registry snapshot after the default BCR endpoint failed PKIX certificate validation in the build environment;
- add the missing `linux_x86_64` OpenH264 architecture selections;
- correct WebRTC Linux architecture selections so x86_64 uses the required generic SPL sources without ARM64/NEON flags;
- preserve `WEBRTC_ARCH_X86_64`, 64-bit and little-endian detection while disabling only undeclared optional x86 SIMD dispatch in this monolithic target;
- force the already-declared portable CRC32C implementation because the target does not compile its SSE4.2 implementation;
- order FFmpeg static archives for GNU ld dependency resolution;
- add the missing standard `<condition_variable>` and `<mutex>` includes;
- build the exact target `//submodules/TgVoipWebrtc/tgcalls/tools/cli:tgcalls_cli` and write a manifest plus binary checksum.

The successful incremental qualification ended with one up-to-date target, `1,963` action-cache hits, 7 total actions, and Bazel success in 54.054 seconds. Those timing/cache values are observational, not reproducibility requirements.

## Source-pin reconciliation

Earlier research inspected tgcalls commit `78d07f3e46a4bb12b611ccc2816ff59ca63a83fb`. The reproducible build must instead name the source actually linked by the pinned Telegram-iOS workspace: `e3069322a3d1e16ecb11a5e302242e59ddd7f09e`.

`78d07f...` is 14 commits newer than `e306932...`. The required native CLI behavior already exists in `e306932...`: `p2p` and `reflector` modes, local caller/callee signaling, a UDP-only reflector server configuration, generated audio, per-side statistics/BWE, and the success exit gate. The later commit adds functions that are not required for the current native reflector oracle. Therefore:

- `e306932...` is the build-validated executable pin;
- `78d07f...` remains useful later-source research, not a claim about the bytes that were built;
- changing either source pin requires a new build digest and runtime qualification.

## Local P2P runtime observation

The owner ran:

```text
tgcalls_cli --mode p2p --duration 5
```

Recorded summary:

```text
Duration:          5s
Mode:              p2p
Caller state:      Established
Callee state:      Established
Call established:  yes (at 0.021s)
Stats log:         caller=5 callee=5 bitrate records
BWE non-zero:      yes
Errors:            none
p2p_exit=0
```

This proves that the built binary starts both peers, bridges signaling, establishes its local P2P session, runs for the requested bounded duration, gathers the expected media statistics, stops cleanly, and returns the intended success code.

It is not `MEDIA_PASS` because no real Telegram reflector was selected. It also does not exercise the provider, the temporary `/32` route, OPNsense, IPFW, PF/NAT, `dvtws2`, or any candidate strategy.

## Next evidence boundary

1. Fetch the current official reflector list and select one fixed explicit `IPv4:596–599` endpoint.
2. With no lab route installed, record `ip route get <reflector-ip>` and run one fresh `--mode reflector` epoch on the ordinary TNAS path.
3. Only an exit-0 run with both peers established and non-zero BWE is the exact-endpoint control `MEDIA_PASS`; a silent or failed endpoint is `NO_REPLY_UNKNOWN` until another independent path proves it.
4. Capture the successful control and compare Hello/retry/media framing with the real-call fixture.
5. Record and test the exact `/32` route transaction through OPNsense, including restoration to the original route.
6. Run the no-desynchronization provider baseline against the same endpoint before adding any reflector strategy.

No raw build log, private address, ephemeral source port, external proxy endpoint, peer tag, credential, or raw PCAP is committed in this record.

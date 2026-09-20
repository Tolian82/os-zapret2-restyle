# 2026-09-20 — Telegram Voice Windows/Android source parity and live matrix update

**Status:** SOURCE AUDIT RECORDED · LIVE FRAGMENT MATRIX RECORDED · ZAPRET2 v1.0.5.2 REQUALIFICATION PENDING  
**Package identity:** `VERSION=0.5.0`, `PLUGIN_REVISION=3` — no package/runtime source change in this record.

## Owner scope correction

The owner uses Telegram calls on **Windows and Android**, not Telegram-iOS. The Telegram-iOS checkout used by the Linux companion is therefore a reproducible Bazel/WebRTC build workspace only; it is not the client-version authority for this research.

The owner also clarified the routing topology: both historical gateway `192.168.1.140` and the selected OPNsense gateway `192.168.1.2` are upstream of the same MTS/MGTS provider DPI. Therefore `.140` is **not** an independent DPI-free control path and must not be used as one. Current provider-path research is performed through `192.168.1.2`.

## Windows source identity

At the source-audit epoch:

- Telegram Desktop repository head: `4d4da471fbee771c10e173a83c003ba1728989f1`;
- its `Telegram/ThirdParty/tgcalls` submodule points to:
  `24694f64b03e301ec2c90792566046e61a2c4967`.

Source:

- <https://github.com/telegramdesktop/tdesktop/tree/4d4da471fbee771c10e173a83c003ba1728989f1>
- <https://github.com/TelegramMessenger/tgcalls/tree/24694f64b03e301ec2c90792566046e61a2c4967>

## Android reflector/network parity

At the same epoch the public Telegram Android repository head was
`9552e5541e1274b9557c9832b204dbfcaf44b3dc`.

The following Android-vendored source files were compared byte-for-byte with
`TelegramMessenger/tgcalls@24694f64b03e301ec2c90792566046e61a2c4967` and matched exactly:

- `TMessagesProj/jni/voip/tgcalls/v2/ReflectorPort.cpp`;
- `TMessagesProj/jni/voip/tgcalls/v2/NativeNetworkingImpl.cpp`;
- `TMessagesProj/jni/voip/tgcalls/EncryptedConnection.cpp`.

This is sufficient to establish Windows/Android parity for the reflector/network code relevant to the current laboratory. It is **not** a claim that every Android tgcalls source file or every call-engine behavior is identical to Telegram Desktop.

Android source:

- <https://github.com/DrKLO/Telegram/tree/9552e5541e1274b9557c9832b204dbfcaf44b3dc>

## Why the existing CLI binary remains the reflector oracle

The qualified laboratory binary was built from
`TelegramMessenger/tgcalls@e3069322a3d1e16ecb11a5e302242e59ddd7f09e`.
That commit is 32 commits newer than the Windows production submodule pin
`24694f64b03e301ec2c90792566046e61a2c4967`.

The older production pin does not contain `tools/cli`; the official CLI testbench was introduced later. Rebuilding the current testbench by simply checking out the older production SHA would therefore be invalid.

A focused compare of the reflector path found:

- `ReflectorPort.cpp`: the newer code only adds a length guard/fallback around the parsed peer tag; for the CLI's valid 16-byte generated peer tag, the same 12-byte prefix plus local 4-byte tag path is used;
- `NativeNetworkingImpl.cpp`: the relevant compare hunk is whitespace only;
- `EncryptedConnection.cpp`: unchanged between these pins.

Therefore the existing qualified binary remains a valid **reflector-path wire/media oracle** for the current Windows/Android reflector protocol. This conclusion is intentionally narrow: it does not claim complete equivalence of every call-engine state transition, signaling experiment, or client feature.

Qualified binary identity remains:

`SHA-256 c2bd9e8b55d5542e4471154c832efc4cf0cdd483669dbeb747c706afbe53b11a`

The Linux companion recipe now records both identities separately:

- build/harness pin: `e3069322a3d1e16ecb11a5e302242e59ddd7f09e`;
- Windows/Android reflector-network reference pin: `24694f64b03e301ec2c90792566046e61a2c4967`.

## 2026-09-20 live reflector-fragment matrix

The owner ran the fixed reflector endpoint `91.108.13.10:596` through
OPNsense `192.168.1.2` with the then-installed Zapret2 `v1.0.4`.

Measured candidates:

| Candidate | Wire result | Reflector/media result | Cleanup |
|---|---|---|---|
| no desynchronization | unmodified reflector datagrams sent | no establishment / exit 1 | clean |
| ordered IPv4 fragment, UDP pos 8 | two correct fragments per original | no inbound reflector reply / no establishment | clean |
| reverse IPv4 fragment, UDP pos 8 | reverse fragment order confirmed | no inbound reflector reply / no establishment | clean |
| ordered IPv4 fragment, UDP pos 32 | correct two-fragment layout | no inbound reflector reply / no establishment | clean |
| ordered IPv4 fragment, UDP pos 16 | correct two-fragment layout | no inbound reflector reply / no establishment | clean |
| ordered IPv4 fragment, UDP pos 24 | correct two-fragment layout | no inbound reflector reply / no establishment | clean |

The temporary IPFW rule counted the expected reflector packets in the fragment runs, the WAN captures showed the intended fragment structure/order, and the temporary rule/divert process was removed afterward.

These measurements establish that the standalone IPv4-fragmentation family was emitted correctly but did not obtain a reflector response on the selected `.2` path. They are **not** classified by comparison with `.140`, because `.140` is not an independent DPI-free control.

## Zapret2 runtime change

After the matrix above, the owner upgraded the installed Zapret2 runtime from
`v1.0.4` to **`v1.0.5.2`**.

Consequences:

- the v1.0.4 fragmentation captures remain valid historical wire evidence;
- they do not qualify the newly installed runtime;
- before further candidate testing, the required v1.0.5.2 Lua/desync primitives and serialization must be rechecked on the live appliance;
- no v1.0.5.2 live runtime result is recorded as PASS by this document.

## Current next boundary

1. Keep the existing Docker `host` network and qualified `tgcalls_cli` binary.
2. Use `192.168.1.2` as the selected OPNsense path; do not use `.140` as a control criterion.
3. Refresh the companion recipe so it emits `source-provenance.txt` with the separate harness and Windows/Android source identities.
4. Requalify the needed Zapret2 v1.0.5.2 primitives on the live appliance.
5. Fetch/select a current Telegram reflector endpoint and run a fresh no-desynchronization baseline through `.2`.
6. Continue only with bounded candidate families after that fresh runtime/endpoint baseline.

No GUI, permanent laboratory subsystem, Generic UDP semantic change, package revision bump, or publication belongs to this update.

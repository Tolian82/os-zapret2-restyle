# Telegram Voice current tgcalls owner-live build/runtime pass

**Date:** 2026-09-20  
**Scope:** TOS 7 / TNAS Linux x86_64 companion only  
**Package impact:** none; OPNsense package identity remains `0.5.0_3`

## Qualified source/runtime identity

- Telegram-iOS outer build workspace: `6ad963e5b62d354da79040f388ae2b9132fb17b8`
- Active tgcalls source: `efd330ca04f74706024a5abdfb5b41f4e4dd1065`
- Bazel: `8.4.2`
- Lab patchset: `linux-x86_64-no-v2wasm-18-19`
- Built binary: `/results/tgcalls_cli`
- SHA-256: `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`

The owner-live build completed successfully on TNAS. The current tgcalls checkout
replaced the historical `e3069322...` active lab binary.

## Local runtime gate

The five-second local P2P smoke test completed successfully:

- mode: `p2p`
- caller: `Established`
- callee: `Established`
- established at: `0.039s`
- caller bitrate records: `5`
- callee bitrate records: `5`
- BWE non-zero: yes
- errors: none

Verdict: **OWNER-LIVE PASS** for current-source build and local runtime viability.

This proves the refreshed laboratory binary can establish and carry a local
tgcalls media session on the TNAS host. It does not prove the MTS/MGTS provider
path or any Zapret2 bypass candidate. The next live gate is the fixed Telegram
reflector through OPNsense `192.168.1.2`.

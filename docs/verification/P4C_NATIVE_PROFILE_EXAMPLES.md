# P4c2 — native executable-profile qualification (isolated evidence)

**Status:** `v0.6.4_28` source-only candidate. Previous head `ca87b12e84c02b630051a89ed934d655b7725311` passed [isolated native run #43112156572](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43112156572): all three HTTP/TLS/QUIC `--dry-run` and Lua-init probes passed. That is **not** a PASS for a subsequently changed PR head; exact-head verification is required before merge. **Feature:** #936 / P4; parent P4c1 [PR #1061](https://github.com/Tolian82/os-zapret2-restyle/pull/1061) is merged. Stable `v0.6.4_1.pkg` is unchanged.

## Engine and inputs

The native probe pins upstream `bol-van/zapret2 v1.0.7` to exact commit `038c97e5819df10f8e8c22a2f1fffe57f2f7379b`. It compiles one disposable copy in the isolated `/tmp/p4c2-native-…` directory of a GitHub-hosted **OPNsense 26.7 / FreeBSD** guest; this is never the owner's service runtime or a second installed Zapret2 instance. The test requires actual `nfq2/dvtws2`, `lua/zapret-lib.lua`, and `lua/zapret-antidpi.lua`, with a source-SHA guard and bounded timeouts.

| Profile | L4 / L7 / payload | Real upstream Lua function and params |
| --- | --- | --- |
| HTTP | TCP/80 · `http` · `http_req` | `multisplit:pos=method+2` |
| TLS/HTTPS | TCP/443 · `tls` · `tls_client_hello` | `multisplit:pos=midsld:seqovl=1` |
| QUIC | UDP/443 · `quic` · `quic_initial` | `fake:blob=fake_default_quic:repeats=5` |

The test applies **both** native `--dry-run` and `--intercept=0` with the real upstream Lua files loaded in order and an in-Lua assertion that `multisplit` and `fake` exist. According to upstream documentation, `--dry-run` checks command-line parameters and file existence, **not Lua code correctness**. In contrast, `--intercept=0` initializes Lua but does not start interception. This is a CLI/file/Lua-initialization proof, **not** a packet-handler execution, client connection, ISP bypass, or Voice call success.

## Strict execution isolation

- Default is read-only `--self-test` on any OS; the native mode needs both `GITHUB_ACTIONS=true` and `ZAPRET2_P4C2_DISPOSABLE_NATIVE=1`, FreeBSD root and a checkout that is directly beneath `/tmp` with the fixed temporary prefix.
- Exact upstream tag commit, executable native binary and non-symlink Lua dependencies must exist. The native workflow uses exactly **one** disposable guest with a 24-minute ceiling, short network/compile/test timeouts and guaranteed temporary checkout cleanup.
- Test calls only native `--dry-run` and `--intercept=0`; it does **not** write `/conf/config.xml`, edit IPFW rules, install the plugin, start the shared daemon, request WAN, access SSH credentials, or alter FD9. It fails closed on absent/unsupported resources, unsuccessful process exit or timeout.
- STUN/WireGuard/generic UDP **must not be promoted** to an executable strategy by these HTTP/TLS/QUIC results. Their recognizable payload types are documented in P4c1, but complete handlers, resource inventory and real protocol-specific replay need independent evidence.

## Test and release boundaries

`scripts/test-p4c2-native-profile-examples.py --self-test` proves structure and safe refusal on non-FreeBSD; `.github/workflows/p4c2-native-examples.yml` performs the pinned real engine build and native checks. The workflow is scoped to its two P4c2 files, rather than activating historical G03, Stage 5 RUNNING/Voice or Stage 6 Strategy Lab matrices. No new product GUI examples are advertised as validated until this native fixture passes **and** the separately required endpoint/profile-level replay proves appropriate behavior. Owner A17, release P6 and physical acceptance remain OPEN.

**Delivery transition:** P4c1 PR #1061 passed its exact-head installed Chromium and CI gates and merged into `main` as `a2669f78fa101a447774fbe590f0ce25f09426b0`. P4c2 now targets `main` independently as revision `_28`. The temporary checkout is mode `0755` solely inside disposable CI so the privilege-dropped `dvtws2` can read verified Lua; disposable FreeBSD `ipdivert` is loaded if absent for the engine's socket initialization. Neither fix changes owner OPNsense or installs interception rules. Full P4, packet replay and owner A17/P6 are still pending.

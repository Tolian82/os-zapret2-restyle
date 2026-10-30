# Stage 5 — isolated native selected-Strategy TCP byte attribution

**Authority and boundary:** source/CI test under current `v0.6.1` Stage 5 Exclude IPSet IPv4/IPv6. **Never execute on OPNsense** and never interpret as owner-installed WAN A07/A08, real TLS/SNI modification, IPv6 WAN reachability, Telegram media, authorization for GUI Apply, or a new package. The current owner-installed testing package remains `v0.6.1_12`.

## Observable scenario and proof

The previously qualified native Exclude harness uses a **synthetic Lua DROP** callback and proves precedence and native delivery/blocking. It does **not** establish that a selected native upstream Strategy changed packet contents. This complementary test uses the **real pinned upstream** `dvtws2 v1.0.6`, `zapret-lib.lua` and `zapret-antidpi.lua` instead of a test-defined packet modification function. Three executable `--new` TCP profiles select native `http_hostcase:spell=host` for three distinct destination ports 6531–6533; the production `global_exclusions.compose/audit` inserts the global `--ipset-exclude` on every executable profile.

For each of IPv4 `127.0.0.1` and IPv6 `::1`, all testing stays inside a disposable FreeBSD **15.1** VM on `lo0`. A real TCP client transmits exactly `GET /proof HTTP/1.1` with `Host: Stage5.Example` and `Connection: close`; the independent listening TCP server records **the exact received byte string**. Expected one-for-one transformation is **only `Host:` to `host:`** with unchanged payload length.

| Phase | Exclude content | Expected receiving TCP bytes |
|---|---|---|
| A — baseline | Empty global Exclude | Exact modified request (`host:`) |
| N — negative control | Other, nonmatching IPv4 and IPv6 CIDRs | Exact modified request (`host:`) |
| B — positive Exclude | Exact `127.0.0.1/32` and `::1/128` | Exact untouched original request (`Host:`) |

Each phase additionally tests un-diverted transport and an out-of-profile destination port, checks process continuity and actual IPFW rule identity/counters, and removes the **one test-owned** IPFW rule before leaving the phase. Kernel default-allow baseline and the existing guard are checked at exit. Failed or ambiguous byte comparison is FAIL, not PASS. No external destination, raw capture upload, owner service restart, runtime configuration mutation or synthetic assertion substituted for native receiver bytes.

## Guardrails and reproducibility

The executable [native witness](../../scripts/test-freebsd15-native-strategy-mutation.py) imports the existing [isolated native FreeBSD gate](../../scripts/test-freebsd15-native-engine-exclude.py). It requires explicit `ZAPRET2_ISOLATED_FREEBSD_VM_EXCLUDE_WIRE_TEST=1`, root, a FreeBSD 15.1 guest, exact default-allow kernel state and no OPNsense filesystem. It uses a temporary fixture tree; the native engine drops privileges when loading compiled managed and Lua resources. The [project CI](../../.github/workflows/ci.yml) builds **the exact pinned upstream** commit `221d7dff24bfec0cd5ac0a5070b8acef2008af3d` in that VM and requires an exact native PASS marker; a skipped, failed, or inconclusive native job cannot qualify the result.

Static local preflight (not a substitute for the native trial):

```sh
python3.13 -m py_compile scripts/test-freebsd15-native-strategy-mutation.py
python3.13 scripts/test-freebsd15-native-strategy-mutation.py --static
```

Native invocation is exclusively inside the CI disposable VM, **not an operator instruction for the installed OPNsense gateway**. The CI job also independently runs the existing actual-kernel table, IPv6 UDP, transaction/rollback and synthetic-drop Exclude checks.

## What this does not establish

This demonstrates the *possibility* of independent byte attribution for a selected upstream HTTP-based native Strategy in a controlled loopback. It is **not** a proof that the owner's selected on-WAN TLS Strategy actually performs its prescribed fake/split/desync action, that tcpdump sees every injected fake segment, or that matching Exclude suppresses it on the owner's interface. Stage 5 A07/A08 and installed IPv6/Voice acceptance remain **OPEN**. Before any owner-approved WAN A/B, independently qualify a **TLS-specific active-Strategy** witness tied to a verified eligible Strategy and packet provenance; follow the [binding owner-gated WAN protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) and [offline A/B review](STAGE5_WAN_AB_READINESS.md). No previous consent may be reused.

**Native result (30 October 2026):** Exact-head [PR #745 CI #41084009703](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41084009703) passed with `NATIVE_STRATEGY_PACKET_ATTRIBUTION=PASS`; [postmerge CI #41085570846](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41085570846) also PASS. This closes only the isolated HTTP receiver-byte gate. The follow-on isolated [real TLS ClientHello header witness](STAGE5_TLS_NATIVE_HEADER_ATTRIBUTION.md) remains a separate proof, not installed WAN A07.

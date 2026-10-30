# Stage 5 — native TLS ClientHello IPv4/IPv6 header-attribution witness

**Scope:** independently prove that a **selected real upstream TCP/TLS Strategy** modifies the IP header of a packet carrying an authentic OpenSSL ClientHello, and that global `Exclude IPSet` suppresses the same modification. Test runs exclusively in a disposable FreeBSD **15.1** VM, on **`lo0`**, with the pinned upstream `dvtws2 v1.0.6` and real kernel IPFW divert. Not an installed OPNsense test, external WAN traffic, TLS-bypass outcome, certificate handshake, raw fake/split Strategy witness or Stage 5 A07/A08 acceptance.

## Specific observable control

The isolated native [test](../../scripts/test-freebsd15-native-tls-strategy.py) generates one actual **TLS 1.2 ClientHello** using Python's OpenSSL-backed `ssl.MemoryBIO` (TLS 1.2 maximum avoids modern >1500-byte TLS 1.3 hybrid-key offers, preserving a single bounded record) and SNI `stage5.example`; no external connection, credentials or certificate is involved. The same exact ClientHello bytes are sent through independent TCP connections over both IPv4 `127.0.0.1` and IPv6 `::1`.

The **production** `global_exclusions.compose()/audit()` builds three executable profiles for ports **6541–6543** and the global per-profile `--ipset-exclude`. Each profile selects the **real pinned upstream** `--filter-l7=tls --payload=tls_client_hello --lua-desync=pktmod:ip_ttl=23:ip6_ttl=37`. This native strategy does not rewrite the ClientHello application payload: its expected effect is the IPv4 TTL or IPv6 Hop Limit **in the outgoing IP packet header**. The listening TCP socket separately verifies that the TLS record arrived byte-for-byte unchanged; socket delivery alone does not count as header mutation.

The native FreeBSD `tcpdump` captures `lo0` into a private bounded PCAP; a strict **test-only DLT_NULL/DLT_LOOP decoder** attributes each observation to an exact source port, destination port, IP family and complete original ClientHello byte string. This parser is purposefully **not reused for installed WAN PCAPs**: installed WAN requires Ethernet `DLT_EN10MB` and its existing production parser continues to reject `lo0`.

| Phase | Global Exclude | Expected real outgoing header |
|---|---|---|
| A: no Exclude | Empty | Selected native packets show IPv4 TTL **23** / IPv6 Hop Limit **37** |
| N: negative Exclude | Unrelated `192.0.2.1/32` and `2001:db8::1/128` | Same mutation must remain present |
| B: matching Exclude | `127.0.0.1/32` and `::1/128` | No packet of the attributed flow may have the selected Strategy TTL/Hop Limit |

Every capture includes one un-diverted matching-port control, and the same ClientHello is sent to an out-of-profile TCP port. Three separate executable profiles must each pass for both IP families. Ambiguous/truncated BPF packet evidence, collisions in sender ports, missing original ClientHello, absent selected mutation, or selected TTL/Hop Limit in the matching-Exclude case all **FAIL**. Test-owned IPFW rule numbers are checked and removed between phases; the existing guest gate rejects OPNsense and refuses foreign IPFW ownership. All traffic and PCAPs remain inside the VM.

## Evidence levels and qualification

- **Source/static:** parse strict synthetic DLT_NULL IPv4/IPv6 PCAP fixtures and actual locally generated OpenSSL ClientHello, reject truncated/Ethernet PCAPs and false-positive/missing-flow attribution. `python3.13 scripts/test-freebsd15-native-tls-strategy.py --static` does **not** count as native PASS.
- **Isolated real FreeBSD:** mandatory [CI workflow](../../.github/workflows/ci.yml) checks out pinned upstream SHA `221d7dff24bfec0cd5ac0a5070b8acef2008af3d` and builds real `dvtws2`; an exact `NATIVE_TLS_CLIENTHELLO_HEADER=PASS` marker is mandatory. No SKIP can substitute for genuine observed packet mutation. Do not claim native qualification before the exact-head CI has passed.
- **Owner-installed:** A07, A08, real WAN TLS fakes/splits and native IPv6/Voice/FD9/Apply remain **OPEN** regardless of isolated CI. An isolated `pktmod` header witness is **not** proof of whatever Strategy is actually enabled on the user's gateway.

**Next action after native PASS:** reconcile the real installed eligible Strategy and design the precise, owner-reviewed *read-only* same-endpoint WAN Phase-A attribution, with independent outbound packet provenance; owner approval is still required for any new WAN capture or GUI Apply. The binding [installed WAN protocol](STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) and [offline A/B gate](STAGE5_WAN_AB_READINESS.md) remain unchanged. Python interpreter unification is cancelled within this technical specification. `VERSION=0.6.1` remains unchanged; this source-test increment has `PLUGIN_REVISION=15` and **does not publish a new package**.

## Qualified isolated native result (30 October 2026)

[PR #746 FreeBSD native CI #41090693443](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41090693443) **PASS**: exact actual `NATIVE_TLS_CLIENTHELLO_HEADER=PASS` marker from real pinned dvtws2, native FreeBSD15.1 IPFW and tcpdump/lo0, both families and all three Exclude phases. [Evidence and harness-debug history](evidence/2026-10-30-v0.6.1_15-native-tls-header.md). This closes the **isolated selected-TLS-header** witness only; the next Phase-A installed plan must identify the **actual owner's eligible Strategy** and actual WAN provenance before any new consent-gated capture. Installed A07/A08 remain OPEN.

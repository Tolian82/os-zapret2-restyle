# P4c3b — native HTTP `http_req` / `multisplit:pos=method+2` loopback witness

**Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936) · **candidate:** `v0.6.4_31` source-only · **status:** exact-head native CI **PENDING**. Stable public package `v0.6.4_1.pkg` unchanged.

## Scope and expected evidence

P4c3a [qualified the real TLS handler](P4C3_TLS_HANDLER_REPLAY.md) with kernel divert, upstream Lua packet-send markers, PCAP and exact cleanup in a disposable OPNsense 26.7 VM. P4c3b **reuses** that accepted test's existing `guest_gate`, pinned SHA `038c97e5819df10f8e8c22a2f1fffe57f2f7379b`, native `dvtws2` launch configuration, TCP sender, and strict FreeBSD `lo0` DLT_NULL/DLT_LOOP decoder. No second kernel/firewall/policy implementation is introduced.

One authentic synthetic HTTP/1.1 request, `GET /p4c3b HTTP/1.1\r\nHost: p4c3.example\r\n...`, is sent to `127.0.0.1:6544`. This is a throwaway loopback port, **not** the production HTTP port 80 or a live host. The active profile runs real pinned Lua with:

```text
--filter-tcp=6544
--filter-l7=http
--payload=http_req
--lua-desync=multisplit:pos=method+2
```

For this `GET` fixture, upstream Zapret2 v1.0.7 `protocol.c` computes `HttpPos(PM_HTTP_METHOD,+2)=2` (zero-based). The expected active payloads are **`GE`** and **`T /p4c3b HTTP/1.1...`**, both with `seqovl=0`. Exact per-packet native Lua `multisplit: sending part 1/2` log shapes and C `payload_type 'http_req' satisfy filter` must agree with these lengths. Lua initialization or a bare `multisplit` function declaration is insufficient.

Independent native PCAP must contain: the full unmodified HTTP request on the baseline TCP source port; the exact two active split payloads on a **different** TCP source port; and the positive native `ipfw -a list` counter for the single test-only `19350` divert rule. The IPFW rule number and divert port `19898` are outside the plugin and Strategy Lab ranges, and all changes are strictly confined to the disposable CI guest.

The test rejects: wrong upstream SHA, installed plugin or preexisting engine, non-default firewall ownership, unsupported guest/kernel, missed IPDIVERT, missing handler/payload filter, wrong method split, absent or incorrect PCAP, insufficient IPFW counter or incomplete cleanup. Safe cold-start/default-allow checks come directly from the qualified P4c3a gate. Test-owned IPFW rule and processes are torn down and the original kernel rule list is compared.

## Efficient qualification

The narrow workflow `.github/workflows/p4c3-native-http-replay.yml` runs one fast Linux source/negative guard and **one bounded native OPNsense guest**, not the historical Voice, Strategy Lab or package matrix. Local synthetic PCAP negatives, missing-part/wrong-position logs and foreign-IPFW checks fail closed; they **do not** count as native PASS.

**Exit gate:** exact-head `P4C3_HTTP_MULTISPLIT_NATIVE_HANDLER=PASS` and `P4C3_HTTP_MULTISPLIT=PASS_NATIVE_HTTP_HANDLER_AND_SPLIT_PCAP_ONLY`, with applicable PR CI/policy checks successful and source receipt recorded before merging.

**No claim:** HTTP response delivery, full TCP/HTTP transaction, ISP DPI bypass, real WAN, runtime/GUI preset, YouTube or other traffic effectiveness, Voice/QUIC/STUN/WireGuard, P4/A17 owner acceptance or P6 release qualification. No new `.pkg` is generated or published.

# Telegram voice / UDP — installed Zapret2 fragmentation runtime pin

**Status:** OWNER-LIVE RUNTIME EVIDENCE · NATIVE PRIMITIVE CONFIRMED · NETWORK EFFECTIVENESS NOT MEASURED
**Observed:** 2026-09-02
**Appliance:** OPNsense 26.7.3_8
**Installed Zapret2 tag:** `v1.0.4`
**Installed Zapret2 commit:** `2c21faa80e1acb71ddceb8b49176f266b7d33f05`
**Research authority:** [`TELEGRAM_VOICE_UDP.md`](../../research/TELEGRAM_VOICE_UDP.md)

## Owner-live commands and result

The owner recorded the exact runtime installed under `/usr/local/etc/zapret2`:

```text
$ git -C /usr/local/etc/zapret2 describe --tags --exact-match
v1.0.4

$ git -C /usr/local/etc/zapret2 rev-parse HEAD
2c21faa80e1acb71ddceb8b49176f266b7d33f05
```

The installed `blockcheck2.d/standard/90-quic.sh` contains:

```text
30: pktws_curl_test_update ... --lua-desync=send:ipfrag:ipfrag_pos_udp=$pos --lua-desync=drop ...
34: pktws_curl_test_update ... --lua-desync=fake:... --lua-desync=send:ipfrag:ipfrag_pos_udp=$pos --lua-desync=drop ...
```

Ellipses redact unrelated shell arguments only; the action order is preserved.

## Gate result

The runtime compatibility gate is **PASS**:

- the installed runtime exactly matches the previously pinned Zapret2 v1.0.4 source commit;
- the native fragmentation-only family sends `ipfrag` before dropping the original;
- the separate combined fake-plus-fragment family also exists but is intentionally excluded;
- the bounded candidate can use `ipfrag_pos_udp=8` without changing the runtime installer or firewall architecture.

This is a runtime-capability result only. It does not show that the provider accepts IPv4 fragments, returns TURN/STUN, or carries Telegram voice over UDP. Those remain packet-based owner-live acceptance gates for the `0.5.0_4` testing candidate.

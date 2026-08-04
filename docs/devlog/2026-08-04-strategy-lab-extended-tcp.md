# 2026-08-04 — Strategy Lab Patch 9

Implemented the extended TCP stage for TLS 1.2 and plain HTTP.

TLS 1.2 uses explicit IPv4, TLS 1.2 minimum/maximum, HTTP/1.1, bounded GET, TCP/443, and TLS filtering. Plain HTTP uses explicit IPv4, HTTP-only protocol, HTTP/1.1, bounded GET, TCP/80, and HTTP filtering.

Each protocol uses a small Zapret2-only catalog, one active candidate at a time, the reserved temporary runtime, target-scoped firewall rules, and structured protocol results. The standard mode remains unchanged; extended mode records the first working candidate or the exhausted negative result for each protocol.

QUIC, arbitrary UDP, circular validation, GUI activation, and legacy Blockcheck removal remain later patches.

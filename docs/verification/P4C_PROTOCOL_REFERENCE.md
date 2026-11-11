# P4c1 — Protocol and payload reference in RU/EN Full Help

**Source candidate:** `v0.6.4_27`, source-only, not published. **Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). **Parent:** merged P4b [PR #1060](https://github.com/Tolian82/os-zapret2-restyle/pull/1060), main `d1694532160c74462ecf7c2890171bd4590eebca`.

## Scope and authoritative vocabulary

The upstream [Zapret2 manual, recognizable payload types](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md) records the following matching L4/L7/payload families. These are **filter/payload selection fragments, not complete runnable desync profiles**:

| Traffic | L4 and typical port | Native L7 selector | Recognized payload |
| --- | --- | --- | --- |
| HTTP | TCP, often 80 | `http` | `http_req` |
| TLS/HTTPS | TCP, often 443 | `tls` | `tls_client_hello` |
| QUIC | UDP, often 443 | `quic` | `quic_initial` |
| STUN | UDP, actual application port | `stun` | `stun` |
| WireGuard | UDP, actual configured port | `wireguard` | `wireguard_initiation` |
| Generic UDP | UDP, actual destination port | No invented protocol classification | No fabricated `quic_initial` / `stun` type for unrecognized packets |

**Version/capability boundary:** Upstream documentation describes recognized types; it does not prove that an owner's selected/installed engine has a suitable Lua handler, required BLOB/BIN, live IPFW interception, port or destination target. No runnable STUN/WireGuard/generic-UDP desync command is fabricated. Every actual complete profile still requires its own capability/resource check, native dry-run, safe runtime validation and relevant endpoint replay. Neither a syntactically accepted profile nor a Strategy Lab status is proof of ISP DPI bypass or a completed voice call.

The built-in common Voice service can handle STUN within its selected voice profile; non-STUN UDP traffic stays with Strategies. This is a help-only distinction, not a second engine or WAN.

## Implemented increment

- Add exact, compact English reference to the existing native `general.xml` Traffic Strategy help.
- Add equivalent Russian reference in the existing `strategiesHelpRU` dictionary, retaining original EN fallback and UI locale machinery.
- Do not introduce a second parser, a new config field, a copy/apply button, additional files, or any Config mutation.
- The source contract `scripts/test-strategies-i18n.py` checks shared vocabulary, and the real installed Chromium script checks bilingual reference text on the native help source while preserving existing popup, Full Help, F5, WAN and Voice regression checks.

## Acceptance boundary

**P4c1 is a documentation/protocol-selection increment only.** It does not satisfy P4's requirement for **native-checked executable profile examples**. P4c2 must present and run exact complete native examples for supported HTTP/TLS/QUIC (and UDP/STUN/WireGuard only where actually supported by the installed engine and resources) in an isolated, read-only native test, with hard failure or explicit not-tested for unavailable capabilities. No additional VM matrix beyond one relevant actual installed browser check for this UI-only change. Owner A17, final P4 gate, physical acceptance and P6 remain OPEN. No `_27.pkg` release; published stable `v0.6.4_1.pkg` stays unchanged.

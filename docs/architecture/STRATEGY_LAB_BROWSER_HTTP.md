# Strategy Lab — private Chrome reachability contract

**Status:** CURRENT TECHNICAL CONTRACT. The completed Stages 1–6 execution plan, source integration investigation and owner receipts are [archived](/docs/history/stages/browser-http-2026-10-22/STRATEGY_LAB_BROWSER_HTTP_PLAN.md). Product-level BH-01–BH-12 and the narrowly scoped direct-baseline certificate exception are owned by [REQUIREMENTS](../REQUIREMENTS.md); current implementation/evidence belongs to [PROJECT_STATE](../PROJECT_STATE.md).

The private client is bundled at build time. Its exact signed FreeBSD source/ELF identities, supported profile and ABI/capabilities come from the single `compatibility.json`. Routine installed setup never downloads/replaces system curl. Endpoint-family support follows the [dual-stack specification](ZAPRET2_EXCLUDE_IPSET_SPEC.md); this contract does not promise an unqualified IPv6-only QUIC path.

## Probe and result contract

### Client acquisition and installation

- Private executable location: `/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate`. Never replace `/usr/local/bin/curl`.
- For exploratory development builds, fetch the available prebuilt `curl-impersonate` package from official signed FreeBSD `latest`, following [ugorur/build-curl-h3.sh](https://github.com/ugorur/os-zapret2/blob/main/scripts/build-curl-h3.sh); **for release-candidate qualification, consume the exact manifest-locked signed package and verify its package/ELF SHA-256**. The upstream project reference is [lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate). Installing the plugin must not download or compile the client.
- Do not pin a browser/Chrome release as a blanket runtime assumption. Exploratory builds may float; **release candidates must pin the selected FreeBSD source package and ELF bytes**, not an arbitrary upstream Git tag. Select one actually supported Chrome profile centrally and keep it stable within each installed plugin.
- Bundle the binary and necessary licenses. Record enough to identify the **produced plugin package** (e.g., ABI and SHA-256); a diagnostic upstream version may be logged, but no upstream version is a selection gate.
- Check required executable/profile/CA/capabilities **before stopping the regular service**. Use the existing FreeBSD/OPNsense trusted CA store, do not add `-k`, do not mutate system client/proxy settings. Report missing prerequisites as technical errors. No Firefox or ordinary curl fallback.

### Exact endpoint accessibility rule

For **each required endpoint**, the following independent evidence is sufficient:

1. **TLS:** verified completion of a TLS handshake with the intended HTTPS endpoint using the prescribed host/SNI, server identity and address/attribution.
2. **QUIC:** verified completion of a QUIC handshake with the intended UDP/443 endpoint, with the prescribed endpoint identity and attribution. Merely connecting with TCP does not prove QUIC.
3. **HTTP response:** a genuine final HTTP response from the intended endpoint, with an observed final status code (2xx, 3xx, 4xx or 5xx), on an allowed HTTP version and transport. **Any** such response means that endpoint is accessible; 4xx and 5xx are positive reachability evidence, not automatic DPI failures. A separate handshake report, response body, deep download or expected status code is **not** required.

In symbols: `accessible(endpoint) = verified_target_TLS_handshake OR verified_target_QUIC_handshake OR authentic_target_HTTP_response`, constrained by the requested transport/mode and endpoint identity. This is an **OR**, not an **AND**, and not a three-step sequence. It must not silently allow a TCP handshake to substitute for a requested QUIC handshake, or an HTTP response from another IP, an unexpected proxy, or a redirect destination to count for the pinned endpoint.

A truncated transfer **after a genuine final HTTP status/headers have been received** does not revoke the positive HTTP-response evidence. A connection-only event, malformed response, 1xx-only interim status, timeout without proven evidence, or guessed TLS version/HTTP status does not qualify.

| Mode | Request policy | Accepted positive evidence |
| --- | --- | --- |
| Standard HTTPS | `--impersonate <selected Chrome>`; Chrome-default TLS negotiation (1.2/1.3); HTTP/2 or HTTP/1.1 if negotiated | Verified intended TLS handshake **OR** genuine HTTPS response; neither needs the other |
| Extended forced TLS 1.2 | Same Chrome with `--tlsv1.2 --tls-max 1.2` | Verified TLS 1.2 handshake **OR** genuine HTTPS response over that explicitly requested TLS policy |
| Extended cleartext HTTP | Same private client over `http://`, TCP/80 | Genuine HTTP response from the intended endpoint, any final 2xx–5xx |
| Extended QUIC | Intended UDP/443; Enable QUIC ON | Verified target QUIC handshake **OR** genuine HTTP/3 response on QUIC; no TCP fallback; no mandatory HTTP/3 GET response |

Transport correctness, selected/observed remote IP, Host/SNI, server certificate/CA when TLS is in use, and required IPFW/source-port interception evidence remain mandatory. HTTP replies from the wrong endpoint, through an unintended proxy or following an unintended redirect do not qualify.

### Request isolation, comparability and validation

- Use `-q` first to suppress user curlrc; clear ambient proxy use, keep cookies and Alt-Svc caches isolated per job. Do not change system-wide proxy settings.
- Keep the selected fixed address/family epoch, the same URL and Host/SNI for baseline and candidates, `--resolve` where appropriate, no automatic cross-endpoint redirects, zero retries and bounded connect/overall timeouts.
- Remove forced `--http1.1`, `Connection: close`, manual ciphers/ALPN and forced TLS 1.3 from Standard. An HTTP/1.1 response is as positive as HTTP/2; a Chrome-negotiated TLS 1.2 connection is as valid as TLS 1.3.
- Ranged GET, actual HTTP version/status, response bytes, download completeness and 16 KiB depth can be retained as **extra diagnostics** where observed. The existing short GET-4K and deeper replay up to 64 KiB are not new hard success gates. Server ignoring Range, short complete content or a body transfer error does not revoke an independently established handshake or genuine response.
- Existing candidate reliability rules remain: successful checks in **3/3 independent attempts on each mandatory endpoint**, then **one exact finalist profile replay** using the same protocol/port/flags/resources. Each attempt is successful if one allowed evidence type qualifies for its requested mode. A replay cannot be waived merely because one discovery attempt succeeded.
- A technically invalid client/certificate/identity/attribution result is distinct from a valid network-negative attempt. Stopping/cancellation, budget expiration and restore failure also remain separate outcomes.

### Evidence fields and display

Reuse the existing structured results; do not introduce a second persistence or diagnostic subsystem.

Minimum evidence: mode, selected Chrome profile, target URL and Host/SNI, pinned IPv4 and actually observed remote IP, requested/observed local port where needed, success signal **type** (TLS handshake, QUIC handshake, HTTP response, possibly more than one), protocol/policy actually observed, relevant identity/certificate result, HTTP final status when present, process exit and timeout, attempt numbers, endpoint epoch, candidate/spec/resource identity, interception/attribution decision and terminal reason.

HTTP version, HTTP/3 response, status, bytes and depth are reported only when measured. Do not label QUIC handshake as proven HTTP/3 GET; do not label all Standard successes as TLS 1.3 merely because an older internal key is `tls13`. A successful HTTP response is **not merely diagnostic**: it is independently positive reachability evidence. Missing optional data is "not measured" rather than a fabricated value.

One parser must serve the real installed Model C, fixed-address overrides and other active handlers. Read previous jobs without rewriting them or adding retroactive Chrome/QUIC/HTTP observations.

### QUIC branching

1. If **all mandatory HTTPS endpoints** are directly accessible via an accepted target TLS handshake **or** genuine direct HTTPS response, immediately return `TARGET_ACCESSIBLE`, skip search/Extended/QUIC even with Enable QUIC ON, and perform Stage 90. QUIC candidate count is zero.
2. Otherwise, QUIC is considered only for Extended with Enable QUIC ON and enough Host/SNI identity. Standard, OFF and bare IPv4 without necessary identity skip with a truthful reason.
3. Stage 30 OpenSSL remains an auxiliary control. A negative Stage 30 result does **not** prevent Stage 80. A handshake with an unrelated control server is not proof that the target endpoint is reachable.
4. Before starting QUIC candidates, run **one direct target QUIC check without dvtws2**. A verified target QUIC handshake or genuine HTTP/3 response proves direct QUIC availability, with zero winning candidate strategies; an HTTP/3 GET response is not mandatory.
5. If direct QUIC is not confirmed, run the bounded candidate search. QUIC success is proven by the requested transport signal, not by TCP fallback. The candidate must also have actual IPFW interception and correct remote IP/identity.
6. A timeout does not establish whether the remote server lacks QUIC or DPI interferes. Missing client capability, CA, options, attribution or restoration is a technical error, not a "blocked site" conclusion.

## Current source route

Use the existing `scripts/run-curl-impersonate.sh` launcher and installed Python request/probe/Model-C/extended/replay owners. Top-level Domain Connectivity remains a separate informational diagnostic through `test_domain.sh`; it does not silently use the baseline-only certificate exception. [Source architecture](../ARCHITECTURE.md) routes the production entrypoints.

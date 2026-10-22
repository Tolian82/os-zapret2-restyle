# Strategy Lab — detailed browser-profile HTTP verification development plan

**Top-level legacy Domain Connectivity bug (source `_12`, CI pending):** separate from Strategy Lab. The old plain `curl -sk` checked exit only and declared SUCCESS on an HTTP 200 response with observed LAN IP 192.168.1.2 and TLS Verify 19/20 despite public DNS. The new private Chrome launcher (system CA) pins DNS-selected target IPv4, explicitly bypasses proxies and requires matching actual remote IP, TLS Verify 0, positive handshake duration, successful process and HTTP 2xx-5xx before SUCCESS. API status `ok` still means report delivered only; Stage 50 PASS means the screening stage finished, possibly with zero working families. ([owner evidence](../verification/evidence/2026-10-22-domain-https-false-success-owner.md))


**Owner decision (22 October 2026):** Stage 3 is closed for planning purposes and Stage 4 is active. This is NOT evidence of a winning QUIC bypass on a blocked HTTP/3 target. The Stage-4 `v0.5.6_14` source/FreeBSD15 CI and testing prerelease are PASS ([source merge `a8a658f0`](https://github.com/Tolian82/os-zapret2-restyle/commit/a8a658f0ed85f9363a6cc040067ea061cdab3e4f), [testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.6_14/os-zapret2-restyle-0.5.6_14.pkg)); installed `_15` bounded GUI acceptance is now [PASS for the observed `x.com` Extended Stage80/Stage85/restoration-summary scenario](../verification/evidence/2026-10-22-v0.5.6_15-owner-xcom-extended-stage4-pass.md). All 13 QUIC candidates were listed as tested, but none won; TLS/TCP443 and HTTP/TCP80 finalists each had 1/1 replay. This does not prove working QUIC bypass or independently audited Stage90 kernel state. Stage 5 GUI/persisted jobs remains the next accepted milestone. Historical observations below retain their original evidence limits.

**Status:** Stage 1 FreeBSD 15 private-client `_3` test package is published; owner-installed `chrome150` has certificate-verified HTTPS/HTTP2 and UDP443 QUIC/HTTP3-only response evidence ([record](../verification/evidence/2026-10-21-v0.5.6_3-owner-live-chrome-tls-quic.md)). The owner then confirmed forced TLS1.2-only against GitHub: negotiated TLSv1.2, certificate verification PASS, HTTP2 200, exit 0. **Stage 1 / V1 is complete on installed OPNsense.** Stage 2 Chrome Standard/Model C source migration was published in `_5`; the `_5` native shared-owner startup failure was corrected in the published `_6` test package. **Owner GUI Standard `github.com` direct-accessible baseline and Stage 90 semantic restoration PASS on `_6`** ([evidence](../verification/evidence/2026-10-21-v0.5.6_6-owner-standard-stage90-pass.md)). **Owner GUI `www.youtube.com` Standard candidate search shows three shortlisted stable profiles (`multidisorder`, two `seqovl`), each with `1/1` successful final profile replay, and Zapret2 restoration PASS** ([evidence](../verification/evidence/2026-10-21-v0.5.6_6-owner-youtube-standard-candidates.md)). The `1/1` UI label is the final replay, **not** 3/3 Stage 70 counts. **Follow-up owner saved-job `job.CxYTst` confirms the V3 production path:** `C-warm-bucket-source-port-dispatch`, `model_c_only=true`, warm bucket source-port selector, overlap 3/3/1; three 3/3 Stage-70 candidates, each 1/1 pinned, TLS-verified HTTP/2 200 replay with positive final IPFW counters; initial RUNNING state semantically restored ([same evidence](../verification/evidence/2026-10-21-v0.5.6_6-owner-youtube-standard-candidates.md)). Individual Stage-60 bucket IPFW counters are not present in the compact saved-job excerpt. V2 alternative/negative verification scenarios remain open. **Development source candidate `v0.5.6_7` (unpublished):** focused existing-test V2 negative/OR matrix for Chrome-default TLS (without forcing version), HTTP/1.x/H2 status 3xx–5xx, empty/truncated body, bad certificate/pinned IP/source port and missing interception. Model C production attribution helper is tested without changing production code. Existing controlled source tests **PASS** ([CI 39641447499](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39641447499), [evidence](../verification/evidence/2026-10-21-v0.5.6_7-stage2-v2-controlled-ci-pass.md)); this does not add owner-live negative HTTP/identity observations. The full V2 controlled qualification and prior `_6` live Standard/Model C/Stage 90 evidence are accepted, while Extended Stage 3 remains open. **Stage 3 `v0.5.6_8` source-only slice — [Project/Voice/FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39644646037) ([evidence](../verification/evidence/2026-10-21-v0.5.6_8-stage3-extended-ci-pass.md)):** Extended TLS1.2 and HTTP previously treated exit code zero as reachability; production candidate and IP-target/Host-SNI paths now reuse verified pinned HTTPS/TLS or genuine HTTP response, with mandatory IPFW interception. Controlled production-function tests include incomplete body, TLS handshake alone, 4xx/5xx, invalid certificate/remote IP and missing interception. QUIC remains unaccepted: actual UDP/443 remote identity is not independently observed by the current OpenSSL candidate handler; no direct target QUIC precheck, stable 3/3 or exact finalist replay yet. Do not infer QUIC from process exit. **Stage 3 GUI clarity candidate `v0.5.6_11` (source-only, [Project/Voice/FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39685655181)):** owner Extended `mask-h2.icloud.com` report shows a **single HTTP/TCP80** final profile (1/1), not a TLS/TCP443 or QUIC/UDP443 profile; four QUIC candidates and three generic UDP443 candidates were *tested* but not verified. Direct-control generic UDP response is not a bypass candidate. The GUI must display verified profile counts by transport with an explicit HTTP80-vs-TCP443/QUIC limitation, without fabricating working candidates, altering shortlist ranking, direct UDP semantics, native FD9, Stage90 or any previously accepted Standard behavior. The actual Apple host is TCP/443 fallback, so the HTTP/80 finalist does not by itself establish Private Relay reachability.

**Owner Extended GUI check after `v0.5.6_11` publication (22 October 2026):** the real displayed RU protocol-scope notice for `mask.icloud.com` correctly distinguishes one final HTTP/TCP80 replayed candidate from **zero** TLS/TCP443, QUIC/UDP443 or generic UDP finalists, with restored service; another `x.com` screenshot reports two shortlisted candidates but does not show their protocol rows. Stage80 on x.com tested four QUIC and three generic UDP443 candidates with no winners. The uploaded 114-byte essay text is just a raw UDP payload, not QUIC or authenticated MASQUE, and a generic UDP control reply cannot validate either protocol. Apple's [endpoint contract](https://support.apple.com/en-ie/101555) confirms `mask.icloud.com` UDP443, but Apple's [developer documentation](https://developer.apple.com/icloud/prepare-your-network-for-icloud-private-relay/) says Private Relay validates Apple devices/accounts and uses single-use authentication tokens; a bare Chrome `--http3-only` URL request is not an application-valid Private Relay session. Thus no-positive-QUIC on this target is **inconclusive as DPI-bypass evidence**. To close Stage3, require a known unauthenticated HTTP3 endpoint genuinely blocked in the owner's route plus the existing actual network, pinning, certificate, UDP IPFW, 3/3, exact replay and Stage90 evidence; do not use arbitrary text payload or expand the catalog based only on these results ([owner record](../verification/evidence/2026-10-22-owner-extended-mask-icloud-xcom-gui.md)).

**Stage 3 owner negative-target selection clarification (22 October 2026):** owner job JSON for `mask-h2.icloud.com` confirms an executed HTTP/3-only probe with direct curl(7), QUIC fake curl(7), IP fragmentation curl(28), no QUIC handshake or final HTTP/3, and actual candidate IPFW intercept counters on rule 19100 (3–4 packets). Apple's own [network endpoint specification](https://support.apple.com/en-ie/101555) lists `mask-h2.icloud.com` as the **TCP/443 Private Relay fallback**, and `mask.icloud.com` as **UDP/443**. Therefore the `mask-h2` QUIC-negative cannot be used as censorship or bypass-performance evidence; the outcome is expected to be non-qualifying for **target QUIC** even when per-candidate UDP packets were diverted. Do not add a host-specific runtime special case or make a second run against `mask-h2`; choose a genuinely QUIC-capable target and preserve direct/three-pass/replay/restore conditions ([evidence](../verification/evidence/2026-10-22-mask-h2-quic-owner-job.md)).

**Stage 3 narrow source correction `v0.5.6_10` (unpublished; [Project/Voice/FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39662180060)):** A clearly unsupported private QUIC client (curl exit 4 or an explicit unsupported `--http3-only` option) is now treated as a technical failure, not four blocked candidates and `not_found`; a timeout remains a network-negative. The owner Extended `x.com` screenshot shows two TLS13/HTTP finalists, four QUIC candidates without a winner, and restored service ([bounded observation](../verification/evidence/2026-10-21-v0.5.6_9-owner-xcom-extended-observation.md)). The screenshot does not provide the QUIC raw command errors, so it does not prove that the new capability classification was the cause.

**Stage 3 QUIC source candidate `v0.5.6_9` (unpublished; [Project/Voice/FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39648319643), [record](../verification/evidence/2026-10-21-v0.5.6_9-stage3-target-quic-ci-pass.md)):** private Chrome `--http3-only` pinned target/CA, no TCP fallback, actual returned remote IP, verified QUIC handshake OR final HTTP/3 response; candidate proof requires IPFW packets. Direct target check after managed service stop bypasses candidate search on accepted evidence; otherwise 3/3 candidate passes then exact Stage85 replay. This is not yet an owner-installed QUIC confirmation. Stages 4–6 remain outside accepted modernization scope.
**Owner decisions:** 20–21 October 2026. The success rule is **logical OR**: a verified successful target TLS handshake, a verified successful target QUIC handshake, **or a genuine HTTP response from the intended endpoint** is individually sufficient to mark that endpoint accessible. No HTTP response is required after a successful handshake, and no body download is required after a valid HTTP response.
**Audited restyle source:** `8b31fa49cfcf00617f3137b8eb7bc80427d1f19f`.
**Execution boundary:** This document specifies requirements and order. Source changes and packages start only on a separate implementation instruction from the owner. It does not authorize a stable release.

## Purpose and completion definition

The normative product requirements are `BH-01`–`BH-12` in [REQUIREMENTS](../REQUIREMENTS.md), section "Strategy Lab — browser-profile reachability target". This document defines code integration points, decisions, dependencies, stages and observable acceptance evidence.

The installed Strategy Lab must use one explicit Chrome profile to determine direct accessibility; if necessary, it must find and confirm native Zapret2 strategies; show what was actually observed; and restore the original service state after success, failure or cancellation. **An authentic HTTP response is affirmative evidence of accessibility even if no separately reported handshake observation is available.** An HTTP response with final status 2xx, 3xx, 4xx or 5xx qualifies, including an error page. HTTP/1.1 and HTTP/2 are equally valid. A 3xx response proves reachability of the checked endpoint, not reachability of a redirect destination. The response body and a 16 KiB depth target are not prerequisites. Conversely, a successful target TLS/QUIC handshake is sufficient even if no HTTP response arrives.

"Accessible" here means that at least one accepted reachability signal was observed **for the checked endpoint**. It is not a guarantee that a complete browser page, JavaScript or all application features work, or that arbitrary providers can be bypassed. An exhaustive search without a winning strategy may legitimately end with no winner.

Development order: **1 → 2 → 3 → 4 → 5 → 6**. These are development stages, not runtime laboratory Stage 00–99 identifiers. Each development stage lists its tasks and acceptance criteria. A blocking same-scope defect must be fixed before proceeding (`DEV-007`).

## 1. Evidence behind the plan: audited source

This is a source audit, **not** evidence that a new package has been built or run on OPNsense.

| Source | Audited snapshot | Decision based on that snapshot |
| --- | --- | --- |
| [restyle](https://github.com/Tolian82/os-zapret2-restyle/tree/8b31fa49cfcf00617f3137b8eb7bc80427d1f19f) | `8b31fa49cfcf00617f3137b8eb7bc80427d1f19f` | Keep Python, Model C, CandidateSpec, ResourceInventory, pinned endpoints, attribution and Stage 90 |
| [ugorur/os-zapret2](https://github.com/ugorur/os-zapret2/tree/bee24be58fb65d1f1fae0a9fd3f80c9dd5e5597a) | `bee24be58fb65d1f1fae0a9fd3f80c9dd5e5597a` | Fetch the current FreeBSD `latest` binary package for **each build**, without version pinning, and bundle it privately |
| [lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate/tree/5e62540e0553f45b7ffcc9742ed9cb22b92172cc) | `5e62540e0553f45b7ffcc9742ed9cb22b92172cc` | Browser impersonation reference; select one actual supported Chrome profile from the fetched binary |

The audited ugorur [build-curl-h3.sh](https://github.com/ugorur/os-zapret2/blob/bee24be58fb65d1f1fae0a9fd3f80c9dd5e5597a/scripts/build-curl-h3.sh) creates a temporary repository configuration for the official FreeBSD `latest`, uses `pkg fetch`, extracts the binary and licenses, checks the advertised HTTP3 capability, and includes the result in its own package. It does **not** compile curl. Its [blockcheck.sh](https://github.com/ugorur/os-zapret2/blob/bee24be58fb65d1f1fae0a9fd3f80c9dd5e5597a/src/opnsense/scripts/OPNsense/Zapret/blockcheck.sh) passes the private client path to upstream checks but does not itself set a Chrome profile. Do **not** copy ugorur's separate PF/IPFW/service ownership or fallback to ordinary system curl.

Lexiforest's audited [quick start](https://github.com/lexiforest/curl-impersonate/blob/5e62540e0553f45b7ffcc9742ed9cb22b92172cc/docs/quick_start.rst) and [curl.patch](https://github.com/lexiforest/curl-impersonate/blob/5e62540e0553f45b7ffcc9742ed9cb22b92172cc/patches/curl.patch) show that the executable name does not implicitly select a browser profile, and explicit HTTP/TLS flags may override profile defaults. HTTP3 capability and Chrome-like HTTP3 fingerprinting are separate properties. A Chrome profile can negotiate TLS 1.2/1.3; Standard must use default negotiation, whereas forcing TLS 1.2 is an Extended-only branch.

**Snapshot SHAs are audit references, not build pins.** For every new build use the currently available official FreeBSD `latest` package according to ugorur's acquisition method; it need not match lexiforest's most recent GitHub Release. Do not reject or choose a package based on a predetermined upstream version or Chrome version. The build artifact remains identifiable by its final package digest. If FreeBSD `latest` metadata uses a newer 15.x OSVERSION than the 15.0 build host, `IGNORE_OSVERSION=yes` is allowed solely for repository catalog/fetch operations; executing the binary successfully on target FreeBSD remains mandatory. Never use that override for plugin installation.

### Actual code integration points

The Python paths below are relative to `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/`.

| Entrypoint | Audited behavior | Required change |
| --- | --- | --- |
| `scripts/build-pkg.sh` | Does not contain private curl-impersonate | Add client and licenses before plist creation |
| `request.py` | System curl; forced HTTP/1.1 and TLS; `Connection: close`, ranged GET; OpenSSL QUIC | Common client command and parser for handshake **OR** authentic HTTP-response accessibility |
| `probe.py`, `ip_target_support.py` | Direct probe and separately installed fixed-IPv4/Host/SNI handlers | Equivalent conditions and observed remote IP for baseline and candidates |
| `strategy_lab_python.py` | Calls `ip_target_support.install()` then `truthful_result_support.install()` | Verify the actual installed production handlers, not only their unpatched originals |
| `candidate.py`, `ip_target_support.py` | Multiple endpoint-probe implementations; QUIC handshake may count | Use one coherent success classification in every invoked handler |
| `model_b_parallel.py`, `model_b_parallel_attribution.py`, `stage60_model_c.py` | Model C reuses parallel helpers; separate source-port, Range, write-out and interception | Migrate commands and parsing together; keep IP/port attribution |
| `adaptive_validation.py` | GET-4K discovery/stability and deep replay; QUIC not in HTTP depth checks | Require three successful attempts and exact replay under the revised OR criterion; HTTP size remains optional |
| `truthful_result_support.py` | Handles actual HTTP 4xx/5xx and missing Host/SNI | Treat a genuine HTTP error response as accessibility, not as automatic DPI failure |
| `extended.py` and `strategy_lab/catalog/quic*` | Four QUIC candidates; stops after first `all_pass` | Confirm actual target QUIC success without mandatory HTTP3 GET, then extend catalog |
| `result.py` and `adaptive_result_compat.py` | QUIC is already a result source; top three outputs; HTTPS circular handoff | Keep limits, prevent false TLS/HTTP claims, publish reachability evidence type |
| `orchestrator.py` | `TARGET_ACCESSIBLE` terminates before search and Extended, then Stage 90 | Preserve early exit for **either** valid direct TLS handshake **or** genuine HTTPS response |
| Existing view, GUI and persisted results | Historical protocol labels and partially observed data | Show observed facts only, support old jobs without inventing new values |

Replacing only `request.curl_request()` is insufficient: Model C constructs commands separately, and the production Python entrypoint installs replacement endpoint handlers. All are part of the same Stage 2 migration.

## 2. Implementation decisions

### Client acquisition and installation

- Private executable location: `/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate`. Never replace `/usr/local/bin/curl`.
- In **each new build**, fetch the available prebuilt `curl-impersonate` package from the official signed FreeBSD `latest` repository using the approach of [ugorur/build-curl-h3.sh](https://github.com/ugorur/os-zapret2/blob/main/scripts/build-curl-h3.sh). The upstream project reference is [lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate). Installing the plugin must not download or compile the client.
- Do not pin upstream release, Git commit, package version, or Chrome version. From the fetched binary select **one supported Chrome profile** centrally; every check within a particular installed plugin uses that same profile. Deciding how to discover the supported profile is a Stage 1 implementation task, not a new product decision.
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
- Keep a fixed IPv4 destination epoch, the same URL and Host/SNI for baseline and candidates, `--resolve` where appropriate, no automatic cross-endpoint redirects, zero retries and bounded connect/overall timeouts.
- Remove forced `--http1.1`, `Connection: close`, manual ciphers/ALPN and forced TLS 1.3 from Standard. An HTTP/1.1 response is as positive as HTTP/2; a Chrome-negotiated TLS 1.2 connection is as valid as TLS 1.3.
- Ranged GET, actual HTTP version/status, response bytes, download completeness and 16 KiB depth can be retained as **extra diagnostics** where observed. The existing short GET-4K and deeper replay up to 64 KiB are not new hard success gates. Server ignoring Range, short complete content or a body transfer error does not revoke an independently established handshake or genuine response.
- Existing candidate reliability rules remain: successful checks in **3/3 independent attempts on each mandatory endpoint**, then **one exact finalist profile replay** using the same protocol/port/flags/resources. Each attempt is successful if one allowed evidence type qualifies for its requested mode. A replay cannot be waived merely because one discovery attempt succeeded.
- A technically invalid client/certificate/identity/attribution result is distinct from a valid network-negative attempt. Stopping/cancellation, budget expiration and restore failure also remain separate outcomes.

### Evidence fields and display

Reuse the existing structured results; do not introduce a second persistence or diagnostic subsystem.

Minimum evidence: mode, selected Chrome profile, target URL and Host/SNI, pinned IPv4 and actually observed remote IP, requested/observed local port where needed, success signal **type** (TLS handshake, QUIC handshake, HTTP response, possibly more than one), protocol/policy actually observed, relevant identity/certificate result, HTTP final status when present, process exit and timeout, attempt numbers, endpoint epoch, candidate/spec/resource identity, interception/attribution decision and terminal reason.

HTTP version, HTTP/3 response, status, bytes and depth are reported only when measured. Do not label QUIC handshake as proven HTTP/3 GET; do not label all Standard successes as TLS 1.3 merely because an older internal key is `tls13`. A successful HTTP response is **not merely diagnostic**: it is independently positive reachability evidence. Missing optional data is "not measured" rather than a fabricated value.

One parser must serve the real installed Model C, fixed-IPv4 overrides and other active handlers. Read previous jobs without rewriting them or adding retroactive Chrome/QUIC/HTTP observations.

### QUIC branching

1. If **all mandatory HTTPS endpoints** are directly accessible via an accepted target TLS handshake **or** genuine direct HTTPS response, immediately return `TARGET_ACCESSIBLE`, skip search/Extended/QUIC even with Enable QUIC ON, and perform Stage 90. QUIC candidate count is zero.
2. Otherwise, QUIC is considered only for Extended with Enable QUIC ON and enough Host/SNI identity. Standard, OFF and bare IPv4 without necessary identity skip with a truthful reason.
3. Stage 30 OpenSSL remains an auxiliary control. A negative Stage 30 result does **not** prevent Stage 80. A handshake with an unrelated control server is not proof that the target endpoint is reachable.
4. Before starting QUIC candidates, run **one direct target QUIC check without dvtws2**. A verified target QUIC handshake or genuine HTTP/3 response proves direct QUIC availability, with zero winning candidate strategies; an HTTP/3 GET response is not mandatory.
5. If direct QUIC is not confirmed, run the bounded candidate search. QUIC success is proven by the requested transport signal, not by TCP fallback. The candidate must also have actual IPFW interception and correct remote IP/identity.
6. A timeout does not establish whether the remote server lacks QUIC or DPI interferes. Missing client capability, CA, options, attribution or restoration is a technical error, not a "blocked site" conclusion.

## 3. Development stages

### Stage 1 — bundle a ready-to-run private client

**Dependency:** Owner authorized implementation on 21 October 2026; signed FreeBSD package, Chrome/CA and installed authenticated H2/H3 network responses have been observed. The owner subsequently observed a forced TLS1.2-only GitHub handshake with verified server certificate and HTTP2 200; Stage 1 V1 is accepted.
**Observable outcome:** The plugin package contains a runnable private curl-impersonate with one supported Chrome profile.

1. Add a small build helper modeled on ugorur and invoke it in `scripts/build-pkg.sh` before creating the plist.
2. For **each new package build**, obtain the current signed FreeBSD `latest` package for the target ABI; extract binary, required files and licenses. No upstream version pin, source compilation, system curl replacement or install-time download.
3. Choose one Chrome profile supported by the fetched binary; determine usable CA and TLS/QUIC capabilities; never gate on a specific upstream version number.
4. Add bounded client readiness checks before stopping the service. Keep production probe migration for Stage 2.

**Acceptance:** Exact packaged content and final package digest are known; the private binary runs on FreeBSD 15, using the selected Chrome profile, and produces verifiable target TLS and QUIC handshake evidence, including TLS 1.2. Genuine HTTP responses (HTTP/1.1/2/3) also qualify as reachability evidence when obtained, **but no HTTP response is necessary after a confirmed handshake**. System curl/service configuration remain unchanged. FreeBSD CI is not owner-live installed acceptance.

### Stage 2 — migrate the entire Standard HTTPS path

**Dependency:** Stage 1.
**Observable outcome:** Standard baseline, discovery, stability and finalist recommendation use the same Chrome profile and the OR accessibility rule.

1. Create a shared command builder and evidence parser in `request.py`; isolate curlrc/proxy, CA, Host/SNI, fixed IP and timeouts. Distinguish authenticated handshake success from genuine HTTP response. If the client cannot expose handshake evidence independently of the HTTP result, establish a real supported observation method with that binary; do not guess from process invocation.
2. Migrate `probe.py`, `candidate.py`, actual `ip_target_support.py` overrides, direct `_curl_command` callers in `model_b_parallel.py`, local-port/write-out parsing in `model_b_parallel_attribution.py` and their real `stage60_model_c_production`/`stage60_model_c` callers. Update `adaptive_validation.py` and installed `truthful_result_support.py` in the same scope.
3. Compare baseline and candidates using equal Chrome/TLS policy, URL, Host/SNI, pinned address/epoch, Range and timeout conditions. Preserve source-port leasing, exact IPFW attribution, Model C width up to three, CandidateSpec/ResourceInventory, ranking and endpoint ordering.
4. Enforce 3/3 allowed reachability signals per endpoint and one exact finalist replay; optional HTTP response/body/depth is not an extra gate when TLS handshake succeeds. Accept genuine 4xx/5xx as reachable.
5. Preserve early `TARGET_ACCESSIBLE` for a valid direct TLS handshake **or** genuine HTTPS response, even if the other is not separately observed. Do not run QUIC/search afterward, but always restore through Stage 90; never incorrectly label negotiated TLS 1.2 as TLS 1.3.
6. Remove ordinary system curl from **production** Strategy Lab HTTP/HTTPS checks, without changing unrelated plugin subsystems.

**Acceptance:** Direct TLS 1.2, HTTP/1.1-only and HTTP/2 endpoints qualify by TLS handshake or their real HTTP response. A genuine HTTPS 4xx/5xx counts as reachable; a response with no body is enough. Negative baseline triggers the actual Model C production entrypoint, and an attributed candidate needs 3/3 and exact replay. Wrong IP/port, invalid server identity/certificate, wrong proxy and missing interception cannot win. Direct success yields zero QUIC candidates.

### Stage 3 — Extended TLS/HTTP and target QUIC

**Dependency:** Stage 2.
**Observable outcome:** Extended uses correct TLS 1.2/cleartext HTTP evidence and proves QUIC reachability without requiring HTTP/3 GET.

1. Integrate forced TLS 1.2 with the same client and OR evidence classifier. Cleartext HTTP TCP/80 is independently positive on a genuine HTTP response.
2. Use the client/path that actually proves a target UDP/443 QUIC handshake with required IP/Host/SNI/identity. `--http3-only`, if used, initiates QUIC; it does **not** mean an HTTP/3 response is mandatory or can be inferred. Stage 30 does not gate Stage 80.
3. Implement one direct QUIC baseline check before dvtws2. Verified direct QUIC handshake **or** actual target HTTP/3 response is accessible without a strategy.
4. Reuse the same parser in all live QUIC candidate handlers, including IPv4 replacements; verify real UDP/443, observed remote IP and IPFW attribution. Reject TCP fallback.
5. For the initial four QUIC candidates, require 3/3 independent qualifying attempts and one exact finalist replay. If unstable, reject early and continue admissible search; reuse the same endpoint epoch.
6. Include proven QUIC finalists in the existing recommendation pipeline, but keep Generic UDP separate. Distinguish technical/client/CA/option problems, network negatives, budget and cancellation. Cover ON/OFF, missing Host/SNI and bare IPv4.

**Acceptance:** Genuine target QUIC handshake qualifies even with no HTTP/3 response. A real HTTP/3 response is also positive evidence. A successful HTTPS/TCP endpoint does **not** imply successful QUIC when the requested transport is UDP/443. Negative Stage 30 does not disable Enable QUIC ON; OFF and prior direct HTTPS success do not enter QUIC. Direct QUIC success does not create a fictitious strategy; candidate recommendations require 3/3 and replay.

### Stage 4 — bounded QUIC catalog expansion

**Dependency:** Stage 3. Do not broaden search until winner classification is correct.
**Observable outcome:** More useful native candidates can be tested within the existing finite budget.

| Family | Values | Initial count |
| --- | --- | --- |
| Fake | repeats `1, 2, 5, 10, 20` | 5 |
| IP fragmentation | `8, 16, 32, 64` | 4 |
| Fake + fragmentation | repeats `2` and fragmentation `8, 16, 32, 64` | 4 |

There are 13 initial variants before filtering duplicates/resource-incompatible cases. Preserve initial IDs and order: `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`. Use [upstream 90-quic.sh](https://github.com/bol-van/zapret2/blob/master/blockcheck2.d/standard/90-quic.sh) as an approach reference; capture the actually used upstream revision and validate native syntax with installed dvtws2.

1. Model new variants using existing CandidateSpec/ResourceInventory, exact action order and real resources. Do not import blockcheck2 or produce a full Cartesian product.
2. Use supported builtin or already installed fake resources; explicitly exclude variants when unavailable rather than silently substituting payloads.
3. Admit only candidates whose estimated cost fits remaining absolute time across mandatory endpoints, 3/3 confirmation, replay, Stage 85 and mandatory restoration; account for the actual Python launcher and its QUIC timeout.
4. Keep existing top-level budgets and their starting point; finish on a confirmed winner, cancel or no admissible time. Show tested, incompatible and time-deferred variants separately.

**Acceptance:** Each of the 13 initial argument sets is reproducible, and each executed candidate has proper attribution. With adequate time and no winner all eligible variants are reachable; with insufficient time the honest incomplete outcome and clean restoration are mandatory. Do not enlarge time budgets without measured need.

### Stage 5 — results, GUI and persisted jobs

**Stage-5 delivered scope:** Published `_16` exposed the read-only historical result lookup by validated Job ID; selected history is restored after F5 only when current active-job discovery is idle. Historical result views disable circular mutations, do not automatically resurrect unrelated jobs, and require `profile_replay.verified=true` before calling an older shortlist entry a verified winner. Published `_17` added the compact Job ID clipboard control and RU/EN help. The owner reported successful saved-job retrieval, F5, RU/EN and GUI behavior.

**Stage-5 current decision (22 October 2026):** **CLOSED by explicit owner acceptance**, not by a claim that every previously listed result-semantic variation was independently audited. The `_16` read-only historical job and `_17` F5, RU/EN and GUI checks were reported PASS; avoid repeating them. See [Stage 5 closure and Stage 6 Stop evidence](../verification/evidence/2026-10-22-v0.5.6_17-owner-stage5-closure-stage6-stop-gui.md). Historical replay proof still requires `profile_replay.verified=true`; unsupported old schemas or unverified protocol signals cannot be relabeled wins. If a concrete critical report mismatch arises during Stage 6, treat it as a new reproducible defect rather than silently treating every untested branch as verified.

**Dependency:** Stages 2–4.
**Observable outcome:** The UI distinguishes direct reachability, successful candidate reachability and precisely which evidence was observed.

1. Extend existing JSON/report/view to show Chrome profile, TLS/QUIC/HTTP positive signal type, endpoint/identity/attribution, attempts and reason. Show negotiated TLS/HTTP, status, response bytes and depth only if actually measured.
2. A genuine HTTP response is an affirmative reachability observation, **not merely a diagnostic entry**. Treat HTTP/1.1 and HTTP/2 equally and TLS 1.2 as valid. Show how many QUIC candidates were actually tried, with skip/budget reasons. Never relabel a QUIC handshake as a verified HTTP/3 GET.
3. Keep at most three confirmed recommendation profiles and current preference for primary HTTPS. Show other proven QUIC results in protocol details; do not recommend an unvalidated candidate after one discovery success.
4. Preserve the existing separate HTTPS circular handoff and manual Apply. Do not add QUIC circular or a new lifecycle system.
5. Preserve RU/EN GUI text, Enable QUIC default OFF and persistence after F5. Read historic results without making up new Chrome/QUIC/HTTP observations. Synchronize user guide, main architecture, QUIC control, shortlist and affected live-matrix entries when actual code changes are implemented.

**Acceptance:** Direct TLS success, direct HTTPS response without a separate handshake observation, TLS candidate, direct QUIC, QUIC candidate, cleartext HTTP response, no winner, incomplete budget, technical failure and cancellation have consistent detailed and summary display. F5 does not change the meaning. A real response without a complete body is positive evidence, but absent HTTP measurements remain "not measured". No auto-Apply.

### Stage 6 — installed-package qualification and completion

**Current owner evidence (22 October 2026):** the owner ran **two consecutive GUI Stop checks** and reported no GUI problems: **PASS by owner report**, without raw Stage90/IPFW/process inspection or an explicitly recorded original RUNNING/STOPPED state. Do not repeat the same manual Stop scenario; prefer one bounded read-only hygiene inspection and existing CI test evidence. [Evidence](../verification/evidence/2026-10-22-v0.5.6_17-owner-stage5-closure-stage6-stop-gui.md).

**Dependency:** Stages 1–5.
**Observable outcome:** Owner has a usable Strategy Lab in an accurately verified OPNsense package.

1. Build and deliver the exact test package for FreeBSD 15 amd64 through the normal persistent GitHub testing-package path. Record source commit, package, SHA-256, Chrome profile and actual checks; Actions artifacts alone are not delivery.
2. Run only the selected matrix below on installed OPNsense. Reuse evidence from the same unchanged artifact/scenario when still applicable.
3. For timing comparisons use the same targets, modes, endpoint set and budgets. Changing success criteria can change the winner count; that alone proves neither an optimization nor a regression.
4. For Stop, negative search and technical failure, confirm no temporary processes/IPFW rules and the originally RUNNING/STOPPED state restored. `RESTORE_FAILED` blocks completion.
5. Close `BH-01`–`BH-12` only with actual CI/package/FreeBSD/owner-live evidence. Reconcile current documentation. A full stable Web/pkg release requires a separate owner command.

**Acceptance:** The required rows of the new matrix are proven, package delivery is persistent, documentation matches installed behavior and no known critical result/restoration defect remains. Unrun checks remain open.

## 4. Minimum acceptance-evidence matrix

**V1 is owner-live PASS on `_3`; V2 direct-accessible Standard and Stage 90 restoration PASS on `_6` for `github.com`. On `_6`, owner saved-job `www.youtube.com` **V3 production-path PASS**: Model C warm selector/source-port routing, 3/3 Stage-70 for all three candidates, exact 1/1 finalist replay each and restoration PASS. This is application-reported native attribution, not independent raw Stage-60 packet capture. V2 protocol negatives and V4–V11 remain incompletely accepted.** The [older live matrix](../verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md) supports the previous implementation, not this Chrome/handshake-or-HTTP-response path.

| ID | Scenario and expected behavior | Required evidence | Stage / requirements |
| --- | --- | --- | --- |
| V1 | Private current FreeBSD `latest` client, no version pin, one Chrome profile/CA, actual TLS/QUIC | Actual intended-target handshake on FreeBSD, binary/license contents, final package SHA-256 | 1 / BH-01, BH-02 |
| V2 | Direct HTTPS accepts verified TLS handshake **OR** genuine HTTP response (H1/H2, TLS 1.2); no QUIC afterward | Production entrypoint and controlled endpoints, one installed direct run | 2 / BH-03, BH-04 |
| V3 | Failed direct check → Model C → 3/3 successful attempts → exact replay → recommendation | Automated production-path test and one reproducible attributed installed run | 2, 6 / BH-05, BH-08 |
| V4 | Pinned IPv4 with Host/SNI, correct remote IP/source port and certificate | Mismatch-negative tests and an installed pinned target | 2, 3 / BH-05, BH-06 |
| V5 | QUIC OFF/ON despite negative Stage 30; actual QUIC handshake or actual HTTP/3 response counts | Branching checks plus actual target UDP/443 and installed IPFW attribution | 3 / BH-04, BH-06 |
| V6 | Direct QUIC / candidate / timeout / technical error; no TCP fallback | Distinct outcomes, real QUIC evidence and exact candidate replay | 3 / BH-06, BH-09 |
| V7 | Up to 13 native candidates, early success, cancel and finite budget | Reproducible flags/resources, attribution and honest executed/remaining counts | 4 / BH-07 |
| V8 | HTTP 2xx–5xx (including 4xx/5xx), missing/short/truncated body, and handshake without HTTP | OR classifier with positive genuine HTTP response and independent handshake success | 2, 3 / BH-08, BH-09 |
| V9 | RU/EN, F5, old results, no auto-Apply | Data tests and installed GUI observation | 5, 6 / BH-09, BH-10 |
| V10 | Stop/error/empty search from originally RUNNING and STOPPED | Automated restoration and selected installed checks, no residue | 2–6 / BH-11 |
| V11 | Exact test package and accurate final documents | Persistent GitHub package delivery and recorded installed acceptance | 6 / BH-12 |

If a provider does not allow QUIC, do not claim live QUIC success. A controlled QUIC endpoint may verify the client and integration, but that is **not** evidence of bypassing a specific blocked website. An unproven positive installed candidate leaves its acceptance row open; do not run unlimited speculative searches.

Relevant existing test entries include `test-strategy-lab-python-probes.sh`, `test-strategy-lab-python-candidate-family.sh`, `test-strategy-lab-python-orchestration.sh`, `test-strategy-lab-python-search-extended.sh`, `test-strategy-lab-adaptive-validation.sh`, `test-strategy-lab-ip-targets.sh`, `test-strategy-lab-truthful-results.sh`, `test-strategy-lab-python-final-results.sh`, Model C/attribution and semantic restoration. Update affected existing tests; do not create a competing test subsystem. A mock can prove branching, **not** an actual network handshake or response.

## 5. Execution records and documentation ownership

Current stage/status: [PROJECT_STATE](../PROJECT_STATE.md). Exactly one next action: [START_HERE](../START_HERE.md). Product directions: [ROADMAP](../ROADMAP.md). Change chronology and evidence: [v0.5.x ledger](../history/current/v0.5.x.md). This technical plan is not a per-push diary.

At every implementation stage: define the observable owner scenario and acceptance evidence; implement the coherent scope; run affected checks; synchronize any changed requirements/current facts; follow the GitHub PR/CI/exact-head merge procedure in `GH-010`–`GH-030`. Distinguish source, CI/package and installed OPNsense proof (`DEV-011`, `CHAT-003`).

**Current implementation identity:** `VERSION=0.5.6`, `PLUGIN_REVISION=6`, published testing asset `v0.5.6_6`, immutable source/digest in [publication record](../verification/evidence/testing-publications/v0.5.6_6.md). The owner has already performed the **single** live Standard blocked-target test using `www.youtube.com`, yielding three stable finalists, one successful final replay each, overall SUCCESS and restoration SUCCESS; see the [owner evidence](../verification/evidence/2026-10-21-v0.5.6_6-owner-youtube-standard-candidates.md). **Do not rerun.** The owner supplied the actual saved-job `parameter-expansion.json`, `stability.json`, `shortlist.json` and `status.json` inspection. Mark V3 production-path owner-live **PASS for this bounded `www.youtube.com` scenario**, and retain untested Stage-2 identity/HTTP alternative-negative cases until source/tests verify them. The owner reports `rutracker.net` unsuitable due to upstream IP blocking in their environment; do not propose it for this test. `NO_CANDIDATE` would not be a bypass success; Stage 90 failure remains blocking. The separate basic domain connection widget is not proof of verified Chrome target TLS if its TLS Verify value is nonzero. No repeated exploratory runs or new runtime/architecture changes without a specific new failure. A future source update follows `DEV-027`–`DEV-035`; this plan does not authorize changing the stable v0.5.6 or reopening Telegram Voice.

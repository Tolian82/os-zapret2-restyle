# G09 Stage50 → Stage60: real installed negative control

**Source candidate** `v0.6.3_27` (`VERSION=0.6.3`, `PLUGIN_REVISION=27`, `os-zapret2-restyle-0.6.3_27.pkg`); not published. Stable remains `v0.6.3_1`.

Issue [#973](https://github.com/Tolian82/os-zapret2-restyle/issues/973): genuine owner `www.youtube.com` blocked-target Stage50 no families, Stage60 internal ERROR and Stage90 PASS. Original job details are unavailable. The old empty-family hard gate was fixed already in v0.4.0_2; do not reintroduce it.

One disposable OPNsense 26.7 native guest: G05 genuine WAN Save without upstream, G03 stock configd upstream v1.0.7 while STOPPED, then real authenticated HTTPS Standard Lab job against `192.0.2.42` RFC5737 TEST-NET-1 with IPv6 disabled. Require unreachable baseline, actual rejected Stage50 families, Stage60 graph exhaustion after actual candidate attempts, Stage70/85 PASS, Stage99 truthful `NO_CANDIDATE`, Stage90 STOPPED restoration and preserved Config/foreign IPFW. Capture saved state, candidate and expansion evidence on failure. CI-local time budgets are bounded for the unavailable address; production defaults untouched.

**Not proved by TEST-NET:** ISP DPI, www.youtube.com bypass, Host/SNI/TLS positive attribution, IPv6/QUIC, cancel/timeout or owner-live UI. G09 A15 remains pending those distinct gates. Do not publish a package from this candidate.

## 9 November 2026 — real G09 failure and source correction

Exact-head native run [#42685477550](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42685477550) reproduced owner-type G09 at first search: seven Stage-50 candidates all ended with structured `candidate system adapter firewall-install-protocol failed`, but Stage50 incorrectly reported PASS/no families. Stage60 Model C then failed before candidates on `Model B system adapter preflight failed`. Stage90 verified original STOPPED. Focused second native diagnostic [#42686896529](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42686896529) established both ipfw/ipdivert are unloaded, `sysctl net.inet.ip.fw.enable` unavailable, `ipfw -q list` exit 71, and the engine/daemon executable. This proves the cold-kernel prerequisite cause, not an empty accepted-family algorithm bug.

Correction: only after WAN-first, Stage20 service STOP and inaccessible Stage40, Stage50 invokes the **existing guarded** `backend/firewall.sh::firewall_cold_load_ipfw` for the exact cold-empty signature, then loads ipdivert; no `firewall_prepare`, no `pfctl -d/-e`, no foreign rule edits or alternative FD9. Any Stage50 candidate `error:true` now causes explicit infrastructure ERROR before Stage60, never fabricated `no families`. This fix still needs an actual exact-head native G09 PASS before acceptance.

## Routed-control correction / ongoing native qualification

The G09 native run #42687927570 reproduced Stage50 all seven rejected and Stage60 Model C route attribution error, while Stage90 restored STOPPED. RFC5737 TEST-NET-1 may never generate an outbound WAN packet and is not a valid *interception* control. The disposable test now selects from known public IPv4 addresses only after read-only native route and TCP/443 negative checks; no route or foreign IPFW changes. It is NOT an ISP DPI-blocked target or proof of bypass.

The Linux CI corrective-matrix fixture lacked a kldload executable. An explicit test-only kldload mock with preloaded kldstat fixes the fixture without weakening native cold IPFW safety. Model C now preserves bounded counter and source-port attribution evidence on structural failure. Native acceptance remains PENDING until exact-head SUCCESS.

## Native exact-cause G09 correction

[Real OPNsense run #42692590791](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42692590791) selected public routed `4.2.2.2` with TCP/443 inaccessible. Genuine Stage50 tested all seven; Stage60 IPFW rule 19128 **did** intercept packets (329014 packets vs initial 0), controlled source port 42000 was correct, cleanup succeeded, but `command_endpoint_match=false`. The exact source cause: `request._curl_command` correctly omits `--resolve` for an IPv4 literal, whereas `model_b_parallel_attribution._command_binding_matches` unconditionally expected `--resolve` for every endpoint, so Model C falsely reported infrastructure failure. Fix branch: for literal IPv4 require strict same literal/pinned IPv4, HTTPS URL, `--ipv4`, no `--resolve`, exact controlled port and positive actual IPFW counters; domain case continues strict `--resolve`. Add forged-URL/mismatched-address/forged-resolve/family negative tests. This is not a DPI bypass or equivalent to owner blocked youtube.com.

CI corrective matrix run #42692591026 passed the E2E fixture after the `kldload` fix but next exposed an unmocked cold-kernel requirement in the older Linux lifecycle/precheck fixtures. Only test-local kernel mocks are added; production cold-loader safety is not bypassed. G09 acceptance remains pending fresh exact-head installed results.

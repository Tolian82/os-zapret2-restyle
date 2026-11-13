# os-zapret2-restyle — product requirements

This file owns product-level behavior and the BH reachability requirements. Detailed subsystem contracts have one primary home. Implementation facts and test outcomes live in [PROJECT_STATE](PROJECT_STATE.md); [START_HERE](START_HERE.md) owns the immediate task. General engineering/governance rules are referenced from the four canonical rule books.

## Contract map

| Product boundary | Detailed authority | Scope / status |
|---|---|---|
| Native packaging, dependencies and lifecycle hooks | [Native packaging specification](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) | Current product contract; completed execution plan is historical |
| Clean install, saved defaults, WAN-first, empty Strategy, uninstall and full purge | [Lifecycle v1.3](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md) | Accepted; no repeated development/acceptance queue |
| HOSTLIST modifiers, Python list/profile policy, native profiles, RU/EN and preview | [Strategies #936](architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) | Completed / owner accepted; requirements remain active |
| Mixed-family lists, global Exclude IPSet and Laboratory IPv6 | [Dual-stack DS-01–DS-26](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md) | Shipped; owner live IPv6 waiver remains distinct from native CI |
| Additional Resources | [Install](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md), [Remove](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) | Native transactions and resource ownership; no universal bypass claim |
| Voice Transmission | [Five-service shared-backend contract](architecture/VOICE_TRANSMISSION_GUI.md) | Current STUN/IPSET feature; media/call evidence is independent |
| Laboratory | [Lab architecture](architecture/STRATEGY_LAB.md), [browser probes](architecture/STRATEGY_LAB_BROWSER_HTTP.md) | Current asynchronous Python/Model-C product |
| Auto-detect / Auto Hostlist / scheduled restart | [#1052 specification](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) | Approved work with partial source implementation; [P0–P5 plan](architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md) and state own progress |

## Product identity

`os-zapret2-restyle` is an independent OPNsense plugin with internal service namespace `zapret`. Preserve inherited copyrights and external-runtime attribution. Installation must not depend on another OPNsense zapret plugin or its repository. Zapret2 remains a separately managed upstream runtime. Project identity/version and supported external dependencies have their established machine-readable sources, not independent constants in each document.

## Traffic Strategy

One multiline field replaces separate HTTP and HTTPS fields.

Native profile boundaries include standalone:

```text
--new
```

Supported generic placeholders:

```text
<HOSTLIST:name>
<IPSET:name>
```

Current built-in targets:

```text
<HOSTLIST:youtube>
<HOSTLIST:user>
<IPSET:telegram>
```

Multiple placeholders may be written in one user profile. The user must not be required to duplicate the profile or add extra `--new` separators merely because more than one target selector is present.

After parsing and Target Mode processing, the backend must normalize a profile with multiple unique selectors into one runtime profile per selector. Each runtime profile must retain all non-selector strategy lines and exactly one unique selector. Selector order must follow first appearance, duplicate selector occurrences must not create duplicate profiles, and profiles with zero or one unique selector must remain unchanged.

Only `HOSTLIST:*` and `IPSET:*` selector families are supported. `GROUP`, `TARGETSET`, and other generic selector families are explicitly outside the approved architecture.

User-authored standalone `--new` separators remain part of the Traffic Strategy syntax. The backend may generate additional runtime `--new` boundaries during normalization. The parser must not contain target-name-specific strategy behavior.

Named native profiles/templates/imports and duplicate resolved-list validation follow the [Strategies specification](architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md).

## Targets and exclusions

- One Python domain policy validates YouTube, User and Exclude Domains. Native `!`/`^` modifiers, wildcard handling, IDNA and duplicate semantics follow the Strategies specification. Invalid content produces a field/line error rather than silent loss.
- One Python IP policy validates managed IPv4/IPv6 addresses and CIDRs, including all five Voice lists and Exclude IPSet. Explicit or effective whole-family `/0` is forbidden. Empty lists do not imply destination-any capture.
- Exclude Domains is domain-only and is not translated to IPs or injected into Voice/STUN. Exclude IPSet applies to every executable ordinary/Voice profile after native imports/templates, preserving profile semantics.
- Explicit HOSTLIST/IPSET placeholders select their own profile targets; Target Mode applies to profiles without an explicit selector. #1052 does not implicitly turn `Target Mode=auto` into `<HOSTLIST:auto>` or a universal bypass profile.
- Laboratory accepts domains and fixed addresses with the applicable Host/SNI and explicit IPv6 family rules. Missing IPv6 capability is reported honestly and does not break IPv4.
- On Apply, normalize only the approved/changed inputs through the same privileged and unprivileged policies, persist through the single native Config owner and show canonical saved values. Keep invalid user input available for correction.

## Transactional Apply

Apply must:

1. validate submitted model values;
2. normalize and strictly validate targets;
3. build and validate a candidate release;
4. on failure, preserve persistent configuration, active PID, runtime, and ipfw rules and show a field/line error;
5. on success, save normalized values and safely activate the candidate.

Invalid user input remains visible for correction.

## Strategy Lab adaptive search

The current Strategy Lab architecture is defined by [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md), [`architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md), [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md), and [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

Product requirements:

- search candidates use native `bol-van/zapret2` semantics only; classic zapret/nfqws1 strategy syntax is not a candidate source;
- Python is the automated planner/search/result owner and shell is limited to audited OPNsense/FreeBSD system adapters;
- **Model C is the only normal production Stage-60 execution model**; Model A and Model B remain explicit reference/benchmark/test paths and are not automatic production fallbacks;
- a simple Stage-50 representative result is evidence, not an allow/deny gate for all related Stage-60 candidates;
- each candidate has an explicit reproducible `CandidateSpec` including ordered Lua actions, technique arguments, optional ranges and resource dependencies;
- installed Lua and fake-file resources are captured in a job-scoped `ResourceInventory` rather than assumed from a fixed release-specific list;
- BLOB-free, Zapret2 built-in, inline and installed external-file resource forms are all valid when the native technique supports them;
- a reported bypass candidate contains at least one native Zapret2 Lua action; a no-action profile is baseline/pass-through evidence;
- `--out-range=-d10` is not a global Strategy Lab requirement; output range is candidate data and may be another valid value or absent when the native strategy does not need it;
- known native/owner-proven Zapret2 strategies are retained as golden representation and search-reachability regressions, not universal provider presets;
- normal adaptive discovery preserves domain, fixed-IP/Host-SNI, endpoint-family and explicit IPv6 eligibility under the dual-stack specification;
- candidate execution must retain deterministic endpoint attribution, controlled source-port leasing, temporary firewall ownership and bounded cleanup;
- mass discovery and finalist validation are separate evidence levels;
- strict stability remains 3/3 but stops immediately after a failure makes 3/3 impossible;
- the best two to three candidates normally receive finalist validation and form the early-stop target; a smaller truthful result remains valid;
- finalist validation uses the exact complete profile and requested transport; body size/depth are diagnostic, not additional reachability gates under BH-08;
- authenticated/intercepted HTTP `4xx`/`5xx` is application-layer status, not automatic DPI-path failure; such a response may remain accepted reachability evidence when endpoint/profile/interception proof succeeds;
- operation, candidate, stage and job deadlines form a measured containing hierarchy and must be reviewed from timing telemetry rather than copied indefinitely as constants;
- **Enable QUIC** is an explicit persisted setting, defaults OFF, and enables the QUIC catalog when the job reaches Extended Stage 80; direct target accessibility, cancellation, finite budgets and missing required Host/SNI retain their own termination/eligibility boundaries;
- QUIC capability/precheck evidence is diagnostic and does not silently override the explicit Enable QUIC choice;
- for a fixed IPv4 target with Host/SNI, QUIC attempts must connect to the fixed IP while verifying the supplied hostname; bare IPv4 QUIC without Host/SNI is skipped before candidate execution rather than falsely reported as tested;
- Generic UDP is an optional Extended protocol path with explicit destination port and exact payload bytes, remains independent from Host/SNI/QUIC, and UDP silence is not proof that a port is closed;
- complete fixed-IP recommendations include `--ipset-ip=<entered IPv4>` and undergo the same exact finalist replay discipline;
- all terminal paths require bounded temporary-runtime cleanup and exact Stage-90 restoration of the original Zapret2 service/configuration state.

## Strategy Lab — browser-profile reachability target

**Status:** Current accepted product requirements. Implementation and evidence limits are recorded in [PROJECT_STATE](PROJECT_STATE.md); the [browser probe contract](architecture/STRATEGY_LAB_BROWSER_HTTP.md) owns technical details.

### Target outcome

A user installs the package on supported OPNsense / FreeBSD 15 amd64, opens the existing Strategy Lab page, enters a domain or IPv4 with required Host/SNI and runs Standard or Extended. One explicitly selected Chrome profile first checks direct accessibility. If **all mandatory HTTPS endpoints** are directly accessible by verified TLS handshake **or** genuine HTTPS response, stop search immediately, including QUIC. Otherwise try native Zapret2 strategies. Extended with Enable QUIC ON additionally tests target UDP/443 QUIC. Produce up to three confirmed profiles or honestly report no confirmed strategy. After success, error or cancellation, restore the exact original service state.

A response with a genuine final HTTP status **2xx, 3xx, 4xx or 5xx** from the intended endpoint qualifies as accessible. It does **not** have to be status 200, HTTP/2, a complete document body or 16 KiB of content. A 3xx proves reachability of the tested endpoint, not a redirect destination. A real response received before a later transfer/body error remains positive evidence. An unrelated proxy, wrong remote IP, forged/malformed/nonfinal response, unsupported transport, or absent mandatory interception evidence must not produce a false positive. A TLS/QUIC handshake alone meets the owner's reachability criterion but does not claim the full web page or HTTP/3 GET was loaded.

The source project is [lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate). The existing private bundling path obtains the prebuilt binary and licenses at **build time** from the official signed FreeBSD `latest` repository, following [ugorur's acquisition approach](https://github.com/ugorur/os-zapret2/blob/main/scripts/build-curl-h3.sh). Development-only exploratory builds may retain that floating acquisition. **Before any testing/stable release-candidate build is qualified for publication**, explicitly select one signed FreeBSD package for the supported `FreeBSD:15:amd64` target and lock its exact source identity and SHA-256 together with the extracted ELF SHA-256 in the project's single authoritative machine-readable compatibility manifest. Include the package version/source coordinates, chosen supported Chrome profile and qualified ABI/library requirements. The release build must consume the recorded artifact, reject missing or mismatching bytes, and never silently substitute a newer `latest` package; every rebuild of that release candidate uses the same locked input. Continue validating ELF, target dependencies, HTTPS/HTTP3/QUIC, CA and ECH-off behavior. The private client and licenses stay inside the plugin `.pkg` and must not be downloaded or installed as a system package on the appliance. An intentional client update changes the lock and requires renewed native qualification; do not pin a particular Chrome version as a product-wide runtime assumption.

Keep three SHA-256 identities distinct: the byte digest of the final plugin `.pkg` must match for the **same physical archive** passed to clean and RUNNING guests; the local Additional Resources Remove plan SHA reflects each appliance's current runtime/configuration and is recomputed for that installation; the bundled curl-impersonate ELF SHA proves the selected executable's bytes. Different local Remove-plan SHAs are not grounds to weaken package/binary checks. An isolated `EXTRA_REMOVE_UNEXPECTED_INSTALLED_PLAN_OR_COUNTS` response is not, by itself, proof of a SHA mismatch.

### Requirements and acceptance signals

| ID | Requirement | Observable acceptance |
| --- | --- | --- |
| BH-01 | Only private curl-impersonate performs Strategy Lab HTTP/HTTPS. Floating signed FreeBSD `latest` acquisition is allowed for exploratory builds; each release candidate locks one selected official FreeBSD package and its ELF SHA-256 using the project compatibility manifest, with one supported Chrome profile. | Binary/licenses bundled, no install-time download or system curl replacement; exact locked package/ELF digests checked, target ABI/capabilities valid, intentional updates requalified. |
| BH-02 | No compile or network install at plugin installation; missing client/profile/capability/CA is a technical error | Readiness checked before stopping service; no ordinary curl control/fallback, Firefox or GUI browser selection |
| BH-03 | Standard uses Chrome-default TLS 1.2/1.3 negotiation; HTTP/1.1 and HTTP/2 are equally acceptable | Verified intended TLS handshake **OR** genuine final HTTPS response proves accessibility; one signal is sufficient, regardless of missing other observations |
| BH-04 | Direct accessibility of all required HTTPS endpoints terminates search immediately | `TARGET_ACCESSIBLE` on qualifying direct TLS handshake or HTTPS response; a pinned direct domain `curl(60)` certificate-verification failure is also reachability evidence and stops search; zero QUIC candidates; Stage 90 restoration even with Enable QUIC ON |
| BH-05 | Baseline and candidate use the same client/profile, URL, Host/SNI, pinned endpoint epoch and request policy | Correct observed target remote IP/port/identity, certificate when applicable and required IPFW/source-port attribution; no unintended proxy or redirect success |
| BH-06 | Extended preserves forced TLS 1.2 and cleartext HTTP TCP/80; QUIC only with Enable QUIC ON when direct HTTPS is not confirmed | Cleartext genuine HTTP response is success; QUIC handshake **OR** genuine HTTP/3 response on UDP/443 is positive **for QUIC/UDP443 only** without mandatory HTTP3 GET response or TCP fallback; direct QUIC success skips QUIC fake candidates but **never skips the Stage 85 replay of stable TLS candidates** after a negative HTTPS/TCP baseline; Stage 30 does not block |
| BH-07 | Expand native QUIC fake/repeats/fragmentation catalog while retaining finite budgets/resources | Reproducible, attributed candidates; cancellation, early success and budget expiration stop search honestly; unexecuted candidates are not reported tested |
| BH-08 | Recommendations require repeated success and exact full-profile replay | 3/3 independent attempts on each required endpoint using allowed OR success criterion, plus exact finalist replay; body download and 16 KiB depth are not gates |
| BH-09 | Report accessibility signal and actual measured data; separate network negative, technical error, cancellation and budget | Evidence type (TLS/QUIC handshake, actual HTTP response, or direct pinned domain certificate-verification failure), Chrome, target IP/Host/SNI, attempts and reasons; real 4xx/5xx are positive reachability evidence; unmeasured data remain unknown |
| BH-10 | Keep page, RU/EN, saved jobs, existing HTTPS circular and manual Apply | F5 and Enable QUIC persistence, default OFF; do not fabricate Chrome/HTTP3 measurements for historical results; no automatic Apply or QUIC circular |
| BH-11 | Keep Python/Model C, CandidateSpec/ResourceInventory, finite budgets, cancel, IPFW ownership and Stage 90 | No residual processes/rules; restore original RUNNING/STOPPED; never hide `RESTORE_FAILED` behind positive reachability |
| BH-12 | Deliver and qualify exact testing pkg with evidence boundaries | Persistent GitHub test package; truthful source/CI/FreeBSD/installed OPNsense evidence; synchronized docs; stable release only by separate owner order |

**ECH policy (owner-approved, 23 October 2026):** All private `curl-impersonate` HTTP(S)/HTTP3 requests use the existing Chrome profile with ECH disabled (`--ech false`), enforced by the shared launcher after caller options. Standard and Extended baseline, family, candidate, replay and standalone Domain Connectivity diagnostic must use the same ECH policy. No ECH toggle, alternate ECH retry, or system-curl fallback is added. ECH-disabled reachability describes this test client; it does not guarantee identical behavior for external browsers that enable ECH. Preserve endpoint pinning, proxy bypass, CA verification, transport identity and IPFW attribution.

**BH-04/BH-09 certificate exception (owner clarification, 22 October 2026):** A direct domain baseline using private Chrome and the DNS-pinned destination may classify curl exit 60 with a nonzero certificate verification result as **accessible without bypass**, even if the certificate is expired, self-signed or mismatched and HTTP code/time_appconnect are zero. It must observe the **exact selected remote IP** and must not have timed out. When curl(60) leaves remote IP empty, make at most one bounded private-Chrome `--insecure` retry with the same DNS-pinned IPv4 and Host/SNI, with proxy bypass maintained. Accept only an actual remote-IP match plus a measured TLS handshake or genuine final HTTP response on this retry. Record the original certificate failure and the untrusted retry separately; do not relax candidate probes or the top-level diagnostic. This is evidence that the peer reached TLS certificate validation, **not proof of a completed trusted TLS handshake, page rendering, or a usable browser session**. The Stage 40 RU/EN message distinguishes the certificate failure; the final Stage 99 message displays `CERTIFICATE VERIFICATION FAILED — Цель доступна без обхода; поиск стратегий не требуется.` / `CERTIFICATE VERIFICATION FAILED — The target is accessible without bypass; strategy search is not required.` with overall PASS and restoration required. The stored `outcome=TARGET_ACCESSIBLE` remains unchanged for saved-job compatibility. Candidate probes and bare IPv4 without a Host/SNI keep strict verified-certificate requirements; wrong remote IP, missing evidence and timeouts never qualify. Chrome-default TLS may negotiate TLS 1.2 or 1.3, so do not assert TLS 1.3 when it was not measured. Existing top-level Domain Connectivity diagnostic remains informational and reports the actual certificate error rather than masking it with `-k`.

Browser-like profile selection is not a promise of JavaScript, DOM or full-browser page rendering. Generic UDP retains its own client and exact-byte contract. This task does not reopen closed Telegram Voice testing, replace Python/Model C with blockcheck2, introduce a new recovery subsystem or publish a stable release.

## Service and GUI

- Start validates the saved candidate; Restart/Reconfigure validates before replacing a working runtime. Stop does not rewrite saved settings. Post-activation failure restores the previous same-operation state or reports restoration failure.
- Use native OPNsense appearance, explicit Apply, field-specific errors, user-profile English/Russian locale and native Help/Advanced controls. Full #936 wording, 13px Help and read-only preview behavior follow its specification.
- Lifecycle display uses the five-state contract in lifecycle v1.3; do not restore the older three-state-only display rule. Runtime release identity and service health remain separate.
- The existing upstream selector and asynchronous `setup.sh` route expose only qualified published stable upstream tags. Setup progress and failure remain visible; Start/Apply do not install or compile the engine.
- No automatic permanent strategy modification or assumed DPI/media success follows from a Lab result, syntax check or package installation. Manual transfer and requested #1052 behavior retain their separate contracts.

## Packaging

Native package metadata derives its project version from `VERSION` and source revision from `PLUGIN_REVISION`. Include all required current MVC/backend/template/hook/setup files and qualified private client/licenses. Exclude runtime directories, owner Config, logs, PID files, downloaded engine trees and secrets.

## Plugin installation and runtime preparation

- Package installation must remain short and must not download sources, install system packages, or compile zapret2.
- Package post-install must register the plugin, render required templates, and print:

  `/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh install`

- After packaged MVC, menu, ACL, controller, and view files are installed or replaced, `+POST_INSTALL` must preserve all registration/template/service-state responsibilities and refresh the Web GUI through the current OPNsense `webgui restart` configd action as its final integration step. The exact `OK` response is required; refresh failure must not be suppressed. The obsolete `webgui.lighttpd_reload` hook and a configd restart are not accepted substitutes.
- `setup.sh` is the single runtime-preparation and bol-van/zapret2 release-management backend. Shell commands and the GUI must reuse its `show` and `install [VERSION]` interfaces rather than implementing separate release discovery or installation paths.
- Running `setup.sh` without arguments or running `setup.sh install` without a version must obtain the published stable-release list and install its latest release.
- `setup.sh show` must print, one tag per line, up to the four latest published stable releases.
- `setup.sh install VERSION` must accept an exact published stable release tag such as `v1.0.3`, reject malformed or unpublished values before runtime mutation, and use the same path for first installation, repeat installation, upgrade, and downgrade.
- Numeric release tags may contain more than three dot-separated components, for example `v0.9.5.2`.
- `setup.sh --help` and `setup.sh -h` must provide concise command usage.
- Drafts, prereleases, and non-numeric release tags must not be presented or selected as stable releases.
- Release discovery must remain read-only and must fail clearly when GitHub cannot be reached or returns no usable stable releases.
- Runtime setup verifies manifest-declared native dependencies, checks out the selected published release, compiles and verifies dvtws2. Native OPNsense `pkg` owns system dependency provisioning; setup does not enable a stock FreeBSD repository or install/replace system packages.
- Start, Restart, Reconfigure, and Apply must not install or update runtime components. They must fail clearly when no usable dvtws2 exists.
- Package removal must synchronously stop the service before plugin files disappear.
- The replacement package preserves the verified initial RUNNING/STOPPED lifecycle state under the current native package contract. Inspect process ownership and original FD9 before replacement; a hook refusal is not a universal native pkg veto guarantee. Start replacement code only for a previously running owner, keep a stopped service stopped, and fail closed on unknown state.
- Package removal must preserve plugin configuration, downloaded runtime content, logs, and shared dependencies.
- `+POST_DEINSTALL` must not restart configd.
- Destructive runtime/dependency cleanup must be a separate explicit maintenance action.
- Runtime setup operations must be logged and safe against concurrent runs.
- `setup.sh install` must capture complete service state before runtime mutation. After dvtws2 verification it must refresh and verify a service that was running, preserve and verify a service that was stopped, reject incomplete/unknown initial state, and never report ready when the required final state is not reached.

## Scope exclusions and history

Voice UDP ports, an additional IPv6 checkbox and P2P remain deferred long-term requirements/proposals in the [active future design](architecture/VOICE_PORTS_IPV6_P2P_FUTURE.md), under the owner's latest 13 November instruction. They do not change present capture semantics. Closed Telegram media research, cancelled external pkg approval and superseded IPv4-only requirements are retained in the [historical source snapshot](history/stages/documentation-2026-11-13/snapshots/REQUIREMENTS.md) and [history map](history/README.md). [Owner clarification](decisions/DEC-2026-11-13-documentation-review-owner-clarifications.md).

## BLOB requirement interpretation

- Shorthand `--blob=<name>` addresses `files/fake/<name>.bin` directly.
- Actual preset blob names must correspond to installed files.
- Implicit aliases are not a product requirement.

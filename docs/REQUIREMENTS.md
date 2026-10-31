# os-zapret2-restyle — Requirements

Project: **os-zapret2-restyle**
Current version line: **0.6.x**. The older requirements below retain historical approved milestones and code-state assertions at their recorded dates; the current owner-approved next target is explicitly identified below.

## Project identity

`os-zapret2-restyle` is an independent OPNsense plugin project.

An earlier project was used as an initial code base and its copyright is preserved in `LICENSE`. New development, package identity, versioning, architecture, documentation, installation, releases, and maintenance belong to this repository.

The finished plugin must install and operate on a supported OPNsense system without depending on another OPNsense zapret plugin or its repository.

The zapret2 engine remains an external runtime component managed by this plugin.

## General development rules

General project-development principles are canonical only in [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) (`DEV-*`). This file defines product-specific requirements and does not duplicate that general rule book.

## Current first-priority requirements — IPv4/IPv6 and global Exclude IPSet (2026-10-28)

**Implemented in source and native CI; bounded owner-installed acceptance now available:** [Technical specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md) (DS-01–DS-26; acceptance A01–A26) and [staged implementation plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md). Both documents have precedence for this **new** work over older IPv4-only *future* language elsewhere in this historical requirements file; they do **not** retroactively change descriptions of currently installed IPv4-only behavior.

- Introduce one `Exclude IPSet` field directly below `Exclude Domains` in normal/Advanced Strategies, with mixed IPv4/IPv6 and RU/EN help; enforce destination IP exclusion across all executable Strategies and Voice profiles, including profile boundaries, templates, imports and Extra Arguments.
- Keep `Exclude Domains` domain-only, with no DNS-to-A/AAAA resolution or injection into Voice/STUN. Keep YouTube/User Domains HOSTLIST and one existing OPNsense Config/common Apply/`zapret` owner.
- Migrate all managed Targets and existing five Voice IPSETs to dual-stack through one Python batch compilation and immutable manifest; stage IPv4/IPv6 Voice IPFW tables and qualify Strategy Lab IPv6 through existing runtime/probes.
- Forbid `0.0.0.0/0`, `::/0` and equivalent full-family union (including complementary `/1`) in **every** user-managed include and exclude IP list, including all five Voice services. Never synthesize global capture from a blank list.
- In **Strategy Lab only**, add the separate owner-approved `IPv6` checkbox directly beneath `Режим:` / `Mode:` in the existing Mode column, label left/indicator aligned under the selector; unchecked by default. OFF selects IPv4 only even for A+AAAA domains; ON permits independently pinned A and AAAA tests when present and routed. Literal IPv4 stays IPv4 only; IPv6 literals require ON. Set one total per-job duration of Standard **150 seconds single-family / 200 seconds dual-family**, Extended **270 / 350 seconds**; checkbox alone cannot increase the budget without both eligible families. Preserve current adaptive Model-C and safe restoration while reconciling budgets in Stage 6.
- New **Voice-page** `UDP ports` fields, Voice IPv6 checkbox, port-only destination-any P2P capture, media protocol strategies and empty-IPSET P2P enablement are **not part of this task**; preserve their discussion in [DECISIONS.md](DECISIONS.md). Real installed FreeBSD15 evidence is required before claiming the feature complete.

**Current release gate (31 October 2026):** Stages 1–7 implementation/source/native CI completed; three owner-limited real FreeBSD15 IPv6 acceptance scenarios PASS. The installed `_30` read-only audit passed 18 checks; owner observed the IPv4 Strategy Lab success/restoration and explicitly waived unavailable live IPv6. Real installed A07/A08 WAN packet effects and Voice media/calls are not proven. Owner approved the full stable `v0.6.2_1` publication; README and release workflow, package integrity and FreeBSD15 Web/pkg delivery must be verified, not inferred.

## Additional Zapret2 Lua/BLOB resources — owner-approved GUI (2026-10-22)

**Approved target; not implemented yet.** The normative technical specification is [ZAPRET2_EXTRA_RESOURCES_GUI.md](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md).

- Source repository: [Tolian82/zapret2-extra-resources](https://github.com/Tolian82/zapret2-extra-resources), currently 19 supplementary Lua modules and 54 deduplicated packet-payload BIN files; inventory is revision-driven, not a fixed total.
- The **Strategies** page (existing `general.volt`) must show a **separate manual button below the left-side «Статус:» block**, with definitive labels RU **«Установить дополнительные ресурсы»**, EN **“Install Additional Resources”**. Lua scripts and BLOB payloads are called *resources*, not *models*. Do not move or repurpose Start/Stop, upstream-release Apply or Strategies Apply. Native RU/EN status and help are mandatory.
- The button initiates a separate, asynchronous, serialized install/update transaction with pinned source revision, per-file integrity checks, collision avoidance for the selected bol-van/zapret2 runtime, no user-file overwrite, and rollback. **An actual Zapret2 service Stop→Start and health verification are mandatory after every successful manual installation or repeat, even if the resource content is unchanged; copying files alone is not success.** Use the existing service lifecycle; do **not** reboot OPNsense. For an unambiguously mandatory restart, permit this manual button only when the service is already `Started`; when `Stopped`, disable it and prompt the user to start Zapret2 first. After restart failure, rollback resources and restore the previously working service or report explicit restore failure. **Do not download additions automatically during ordinary upstream install, package upgrade, or service restart**; retain previously installed managed extras safely across upstream version changes.
- Successful installation must expose new Lua/BIN in a fresh job-scoped **ResourceInventory**, without altering snapshots for completed jobs.
- **Dynamically** extend the **native Strategy Lab search graph** and `CandidateSpec` from the **actual installed Lua/BIN files** recorded by a new Job's `ResourceInventory`, using generic native candidate families plus resource capability metadata as data, **not a hardcoded list of resource filenames or a fixed number of files in plugin code**. Adding/removing compatible files and their Lua call/dependency descriptions must change new Job candidate eligibility without a plugin patch/rebuild. File presence without a safe callable/protocol contract is recorded as `unsupported`, not executed blindly. See the [approved five-stage implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md).
- Load only the Lua modules required by each candidate (plus existing mandatory common modules), preserving the bounded Model-C batching/ordered dependency behavior.
- Preserve adaptive scheduling, final budgets and per-stage cancellation/restore; **never form a blind Cartesian product of all installed resources**.
- Do not alter existing user-authored strategies, Voice Transmission settings or HOSTLIST/IPSET values; the historical strategies predate this catalog and remain independent of installing it.

Implementation, installed-package acceptance and release require separate changes. This requirement is documentation-only and does not claim that the GUI button or expanded search works today.

## Voice UDP/STUN — approved product scope (2026-10-08)

Implement the native **«Передача голоса»** page now, between Strategies and Laboratory, using the same native form design. It provides one Voice WAN selector, per-service enable checkbox and multiline parameters, and separate shared IPv4/CIDR IPSET fields for **Telegram, Discord, X (Twitter), SIP (VoIP), Custom**. No LAN selector or local-UDP/boot-restore toggles: matching local and forwarded outgoing UDP are included, and the saved selection restores through normal Zapret2 startup. Global service OFF remains respected. Exact UI, native input context, parameter capabilities, migration and acceptance live in [VOICE_TRANSMISSION_GUI.md](architecture/VOICE_TRANSMISSION_GUI.md).

**Backend architecture approved 2026-10-13:** Voice and Strategies reuse one OPNsense model, full-runtime generator, serialized Apply/rollback and normal service lifecycle. Voice adds STUN profiles and destination-scoped UDP/IPSET rules; it has no independent Config writer, process owner or normal Apply protocol. Frontend, all five services and full acceptance remain unchanged. The normative contract is [section 12](architecture/VOICE_TRANSMISSION_GUI.md#12-общий-backend-со-стратегиями-утверждено-13102026). The architecture is recorded; the detailed [v0.5.2 code-change plan and controls](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) are accepted for execution by the owner’s instruction to start programming according to that plan. The owner opened this development stage without a release; implementation is still unfinished. A one-profile check is not a reduced deliverable.

This owner decision supersedes the October 1 restriction postponing all GUI/persistence development until a successful call and limiting initial UI to one switch in existing Settings. The page is configuration machinery, **not a proven strategy preset or embedded testing controller**. Qualification remains separate: repeated current-oracle `MEDIA_PASS` through OPNsense/SAME ISP, followed by a real remote Windows/Android P2P-disabled `CALL_PASS` with sustained bidirectional UDP and audible two-way speech. No service is declared working merely because its form or interception works.

Use a single normal dvtws2 and transactional destination-scoped UDP rules/tables. Replace transient PoC request authority with persistent OPNsense configuration and configurable STUN profiles; retain compatible Telegram configctl commands on that same state. Preserve native first-match/action semantics, detect conflicting scope, normalize shared targets and reject invalid candidates before affecting current service. WAN selection controls interception, not routing. No testbed-specific IP/interface/divert/rule identities become product defaults; no empty-IPSET global fallback, second daemon, recurring Cron or parallel boot restorer.

Non-STUN remains in ordinary Strategies, including the current Telegram `unknown` A2 profile. Telegram's IPSET is one shared dataset on both pages, not a copied list. Additional service names require managed target registration; they do not imply native L7 detectors or tested Discord/X/SIP presets. IPv4-only target validation remains in force. The new configuration fields and page are **not implemented in the currently documented `0.5.0_3` package**.

**Binding research premise:** the owner reports local ISP DPI restricting Telegram voice UDP. The goal remains reproducible real calls through **OPNsense `192.168.1.2` and the same provider**, not another VPN/UDP relay/gateway. Intact WAN output with no reply does not independently locate a drop. Docker screening remains first; independent same-endpoint working-path control is optional causal diagnosis, not a mandatory alternate-egress project.

**Preserve the working TCP lane:** the owner's existing Squid GUI external parent is `185.203.117.88:33128`; selected LAN/SOCKS HTTP/HTTPS parent tests passed. Squid's HTTP parent does not carry voice UDP; sing-box UDP direct still traverses applicable output firewall/Zapret2. TCP/TLS proxy integration, Squid, sing-box, PF proxy redirects, SOCKS implementation, TNAS routes and a persistent voice testing controller remain outside this plugin feature.

The separate three-origin laboratory still requires LAN/router-local/SOCKS Telegram TCP-parent and UDP-Zapret2 behavior, including OPNsense reboot recovery. Current manual Voice enable does not satisfy persistence. TNAS's two host routes are deliberately repaired **manually** through the existing OPNsense SSH script after TNAS reboot; Docker starts only on demand (`restart=no`). No route Cron/configd/boot automation or Docker autostart. Router-local Telegram selection is not blanket console proxying. Read [operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [helper reference](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) and [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) for facts and remaining qualification.

All plugin source/model/GUI/lifecycle changes use the normal GitHub branch/PR/CI/merge procedure; no direct installed-source patches. Lab proxies/routes remain independently managed. A configuration/boot PASS must never substitute for `MEDIA_PASS` or `CALL_PASS`.

## Traffic Strategy

One multiline field replaces separate HTTP and HTTPS fields.

Profiles are separated by standalone:

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

## Targets

Current GUI fields:

- Target Mode
- YouTube Domains
- Telegram IPs
- User Domains
- Exclude Domains

### HOSTLIST

One domain per line:

```text
example.com
*.example.com
```

Both normalize to:

```text
example.com
```

The canonical entry applies to the base domain and subdomains.

HOSTLIST fields reject IPs, networks, malformed domains, and unrelated text.

### IPSET

One IPv4 address or IPv4 CIDR network per line:

```text
149.154.160.1
149.154.160.0/20
```

IPSET fields reject domains, malformed addresses, invalid prefixes, and unrelated text.

IPv6 target lists remain outside the approved target-list contract.

### Strategy Lab target identity

Strategy Lab accepts either a normalized domain or a canonical IPv4 address.

For an IPv4 target, an optional separate **Host / SNI** service identity may be supplied. The entered IPv4 remains the fixed destination used for routing, interception, attribution and final `--ipset-ip=<target>` selection, while the service hostname is used for TLS/HTTP/QUIC identity and certificate verification.

Bare IPv4 TLS certificate-identity failure is not proof that DPI bypass failed. When HTTPS identity cannot be established without a service name, Strategy Lab must return truthful `PARTIAL` guidance asking for Host/SNI rather than a misleading empty `NO_CANDIDATE` result.

IPv6 is detected as an optional network capability but is not currently accepted as a Strategy Lab target. IPv6 Laboratory target support requires a separate explicit architecture scope.

### Normalization

Successful Apply:

- trims whitespace;
- removes empty lines;
- lowercases domains;
- normalizes wildcard domains;
- canonicalizes IPv4/CIDR values;
- removes duplicates;
- stores normalized values;
- reloads normalized values into the GUI;
- reports normalization.

Invalid values are never silently discarded.

## Exclude Domains

Exclude Domains is a global HOSTLIST exclusion mechanism, not a strategy placeholder. It does not apply to IPSET values.

## Target Mode

Target Mode applies only to profiles without explicit target placeholders.

Explicit placeholders override Target Mode for their profile.

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
- normal adaptive discovery is centered on IPv4/TCP/TLS while preserving the current domain and fixed-IPv4 target contracts;
- candidate execution must retain deterministic endpoint attribution, controlled source-port leasing, temporary firewall ownership and bounded cleanup;
- mass discovery and finalist validation are separate evidence levels;
- strict stability remains 3/3 but stops immediately after a failure makes 3/3 impossible;
- the best two to three candidates normally receive finalist validation and form the early-stop target; a smaller truthful result remains valid;
- finalist validation uses a real bounded GET and records whether at least 16 KiB of body data was obtained; a valid shorter resource is `inconclusive` for the 16-KiB depth criterion rather than falsely reported as PASS;
- authenticated/intercepted HTTP `4xx`/`5xx` is application-layer status, not automatic DPI-path failure; such a response may remain accepted reachability evidence when endpoint/profile/interception proof succeeds;
- operation, candidate, stage and job deadlines form a measured containing hierarchy and must be reviewed from timing telemetry rather than copied indefinitely as constants;
- **Enable QUIC** is an explicit persisted setting, defaults OFF, and enables the QUIC catalog when the job reaches Extended Stage 80; direct target accessibility, cancellation, finite budgets and missing required Host/SNI retain their own termination/eligibility boundaries;
- QUIC capability/precheck evidence is diagnostic and does not silently override the explicit Enable QUIC choice;
- for a fixed IPv4 target with Host/SNI, QUIC attempts must connect to the fixed IP while verifying the supplied hostname; bare IPv4 QUIC without Host/SNI is skipped before candidate execution rather than falsely reported as tested;
- Generic UDP is an optional Extended protocol path with explicit destination port and exact payload bytes, remains independent from Host/SNI/QUIC, and UDP silence is not proof that a port is closed;
- complete fixed-IP recommendations include `--ipset-ip=<entered IPv4>` and undergo the same exact finalist replay discipline;
- all terminal paths require bounded temporary-runtime cleanup and exact Stage-90 restoration of the original Zapret2 service/configuration state.

## Strategy Lab — browser-profile reachability target

**Status:** Approved modernization requirements, amended by the owner on 21 October 2026; implementation has not started. The definitive accessibility rule is a logical **OR**: a verified target TLS handshake, a verified target QUIC handshake, **or a genuine final HTTP response from the target** is individually sufficient. A valid HTTP response is affirmative evidence, not just optional diagnostic data. No HTTP response is required if the intended handshake already succeeded. See [PROJECT_STATE](PROJECT_STATE.md) for implemented status and the [detailed development plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) for the full algorithm, stages and acceptance matrix.

### Target outcome

A user installs the package on supported OPNsense / FreeBSD 15 amd64, opens the existing Strategy Lab page, enters a domain or IPv4 with required Host/SNI and runs Standard or Extended. One explicitly selected Chrome profile first checks direct accessibility. If **all mandatory HTTPS endpoints** are directly accessible by verified TLS handshake **or** genuine HTTPS response, stop search immediately, including QUIC. Otherwise try native Zapret2 strategies. Extended with Enable QUIC ON additionally tests target UDP/443 QUIC. Produce up to three confirmed profiles or honestly report no confirmed strategy. After success, error or cancellation, restore the exact original service state.

A response with a genuine final HTTP status **2xx, 3xx, 4xx or 5xx** from the intended endpoint qualifies as accessible. It does **not** have to be status 200, HTTP/2, a complete document body or 16 KiB of content. A 3xx proves reachability of the tested endpoint, not a redirect destination. A real response received before a later transfer/body error remains positive evidence. An unrelated proxy, wrong remote IP, forged/malformed/nonfinal response, unsupported transport, or absent mandatory interception evidence must not produce a false positive. A TLS/QUIC handshake alone meets the owner's reachability criterion but does not claim the full web page or HTTP/3 GET was loaded.

The source project is [lexiforest/curl-impersonate](https://github.com/lexiforest/curl-impersonate). For **every new plugin build**, fetch the available prebuilt package from official signed FreeBSD `latest` using [ugorur's acquisition approach](https://github.com/ugorur/os-zapret2/blob/main/scripts/build-curl-h3.sh). Do not pin or gate on an upstream version, GitHub release or Chrome version. FreeBSD `latest` may lag or differ from GitHub releases. Pick one supported Chrome profile from the actual binary, keep it stable for that installed package, and verify its required capabilities/CA. Final plugin package digest may be recorded without pinning upstream version.

### Requirements and acceptance signals

| ID | Requirement | Observable acceptance |
| --- | --- | --- |
| BH-01 | Only private curl-impersonate performs Strategy Lab HTTP/HTTPS; obtain a prebuilt client from FreeBSD `latest` at each build; no upstream version pin; one explicit supported Chrome profile | Binary/licenses included in plugin, system curl unchanged, source and resulting plugin pkg identity known; no exact-version gate |
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

## Service lifecycle

- Start validates saved configuration before launch.
- Restart/Reconfigure validates a candidate while the old runtime works.
- Stop stops the service without modifying configuration.
- Failed candidates must not stop a working service.
- Post-activation failure must restore the previous runtime.

## GUI

- Native OPNsense appearance.
- Explicit visible Apply button.
- Field-specific validation messages.
- No essential button text supplied only by hidden JavaScript.
- No syntax highlighting requirement.
- No font change requirement.
- Line numbering may be added later.
- Field width remains unchanged until verified rendered markup is deliberately inspected.
- The Settings page must contain a native collapsible `Zapret2 Service` section after the existing configuration sections.
- On desktop widths, service status, exact installed release tag, Start/Stop, repository release selector, and the runtime Apply button must occupy one horizontal line. Narrow layouts may wrap without changing the control order.
- Service status is restricted to Started, Stopped, or Error and uses the standard success, neutral, and danger visual states. Runtime version is reported separately from service health and is empty when the installed tree is not at an exact valid tag.
- The repository selector presents at most the four current stable releases returned by `setup.sh show`. Drafts, prereleases, malformed tags, and arbitrary user values must not be accepted.
- Runtime Apply starts `setup.sh install VERSION` asynchronously through configd, disables conflicting controls while the operation is active, polls read-only status, and points the user to `/var/log/zapret2/setup.log` after failure.
- The GUI follows the language selected in OPNsense. English is the default; custom Zapret2 labels and operation messages also provide Russian text. The plugin must not introduce its own language selector.
- Laboratory uses the native OPNsense content frame/grid and exposes domain-or-IPv4 target input, conditional Host/SNI, Standard/Extended mode, persisted Enable QUIC, optional Generic UDP input, progress/status, stable result profiles and exact evidence without requiring a separate UI application.

## Packaging

The package identity is:

```text
PLUGIN_NAME=zapret2-restyle
PLUGIN_VERSION!= /bin/cat ${.CURDIR}/VERSION
```

The final package must include all project-owned MVC, service, backend, template, hook, package-script, and setup files required for a fresh OPNsense installation.

Runtime files, live configuration, logs, PID files, downloaded engine trees, and secrets must not be packaged from a development firewall.

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
- Runtime setup must install only missing dependencies, restore temporary pkg repository changes, checkout the selected published release, compile, and verify dvtws2.
- Start, Restart, Reconfigure, and Apply must not install or update runtime components. They must fail clearly when no usable dvtws2 exists.
- Package removal must synchronously stop the service before plugin files disappear.
- The replacement package's pre-install phase must remember whether the service was fully running, stop and verify it before the old deinstall hook and file replacement, abort when stop fails, and start replacement code only when the pre-upgrade service was running. A stopped service must remain stopped.
- Package removal must preserve plugin configuration, downloaded runtime content, logs, and shared dependencies.
- `+POST_DEINSTALL` must not restart configd.
- Destructive runtime/dependency cleanup must be a separate explicit maintenance action.
- Runtime setup operations must be logged and safe against concurrent runs.
- `setup.sh install` must capture complete service state before runtime mutation. After dvtws2 verification it must refresh and verify a service that was running, preserve and verify a service that was stopped, reject incomplete/unknown initial state, and never report ready when the required final state is not reached.

## Current implementation and verification state

Current facts do not live in this requirements contract. Read [`PROJECT_STATE.md`](PROJECT_STATE.md) for the current `v0.5.x` state, [`START_HERE.md`](START_HERE.md) for the exact candidate/release handoff, and [`history/current/v0.5.x.md`](history/current/v0.5.x.md) for current-line chronology and proof.

The completed `v0.4.x` final-state archive is [`history/archive/v0.4.x.md`](history/archive/v0.4.x.md). Historical audit, devlog, release, patch and evidence records remain history/proof only and do not override current specialist authority/current state (`DOC-004`–`DOC-005`).

## BLOB requirement interpretation

- shorthand `--blob=<name>` addresses `files/fake/<name>.bin` directly;
- actual preset blob names must correspond to installed files;
- implicit aliases are not a product requirement.

# os-zapret2-restyle — Master development plan

- [x] Current candidate `v0.5.1_28`: production FreeBSD IPFW executor wired to service lockf FD9; native Voice OFF ownership seed and journal/argv-bound real kernel activation available under locked lifecycle
- [ ] Next: wire the complete Config/runtime/one-engine/supervisor rollback and boot recovery around the real IPFW executor; enable GUI Voice ON only then
- [x] Previous candidate `v0.5.1_27`: real native one-engine runtime/IPFW handoff works with full-sized /conf/config.xml, bounded and stream-hashed
- [ ] Next: production single-engine IPFW/Config/supervisor cutover and rollback, then GUI Voice ON and reboot acceptance
- [x] Previous candidate `v0.5.1_26`: real production Voice+Strategies native dvtws2 argument generation and canonical owned IPFW manifest + source fingerprint handoff
- [ ] Next: complete single-engine IPFW/runtime/Config transactional activation with rollback, then enable GUI Voice ON
- [x] Previous candidate `v0.5.1_25`: production orchestrator compiles native Voice/ordinary merged candidate and resolved IPFW plan inside each staged runtime release, before activation; active legacy traffic/rules still intact
- [ ] Next: adopt native candidate in one dvtws2 with transactional Voice IPFW+supervisor/Config rollback; then enable real GUI Voice ON
- [x] Previous candidate `v0.5.1_24`: qualify genuine OFF-only Voice Apply regression after matching the read-only assertion to the deliberate failed-backend Config save
- [ ] Next: native one-engine Voice ON cutover, IPFW capture/rollback and boot recovery, not additional model-only lock research
- [x] Previous candidate `v0.5.1_23`: real GUI OFF-only Apply drives native Config save and existing configd Zapret reconfigure, with diagnostic busy/ON refusal and honest failure reporting
- [ ] Next production feature: single dvtws2 with active native Voice/STUN profiles and destination-scoped IPFW rule/table runtime plus durable rollback; do not mistake OFF-only Apply for Telegram call support
- [x] Previous candidate `v0.5.1_22`: qualify real OFF-only draft Config persistence after correcting GET/POST HTTP contract in integration regression
- [ ] Next: live shared-engine Voice Apply and UDP/IPFW activation; no unrelated mock-only backlog
- [x] Previous candidate `v0.5.1_21`: real native Voice OFF-only draft persistence via the GUI and audited Config; five service parameters and shared IPSETs persist across GUI reloads/reboots without runtime activation
- [ ] Next: implement the unified real Apply transaction and one-engine live UDP/IPFW generator; replace OFF-only gate with verified ON cutover; test owner OPNsense before shipping
- [x] Previous candidate `v0.5.1_20`: isolated cross-process flock and native FreeBSD /usr/bin/lockf inherited-FD9 kernel interoperability tests, wired into Voice and package CI
- [ ] Next: qualify FreeBSD exact-head results, then establish true Config+lifecycle transaction ownership across Config::save()/configd; no native Apply
- [x] Previous candidate `v0.5.1_19`: reject ABA lock unlock/reacquire in mock cutover and prove Config::save() LOCK_UN exposure in isolated PHP test
- [ ] Next: establish real shared ownership/serialization across Config.save, consistent lock acquisition order and durable native recovery; still no Voice Apply
- [x] Previous candidate `v0.5.1_18`: repeated owner lock attestations in disconnected mock Voice cutover; loss retains journal and prevents unlocked rollback after Config.save()
- [ ] Next: design and qualify real Config+lifecycle ownership across Config::save(), strict lock order, and FreeBSD recovery; do not wire Voice Apply yet
- [x] Previous candidate `v0.5.1_17`: use verified numeric FreeBSD kern.proc.args MIB + PID, retaining native smoke and injected failure regressions
- [x] Exact source HEAD `87de312` passed CI #38017644559 attempt 2 including FreeBSD 15 package, native kernel argv self-test and Linux Voice regressions
- [ ] Next: build and test Config/lifecycle lock order + Config::save() release semantics under a non-authorizing offline contract, then qualify owner-device role policy and actual service before Voice Apply

- [x] Current candidate `v0.5.1_16`: correct confirmed native FreeBSD pathname PID sysctl ABI with strict negative tests
- [ ] Verify Linux and FreeBSD 15 package CI at exact HEAD, then establish native Config/lifecycle lock ordering and Config::save() lock lifetime

- [x] Current candidate `v0.5.1_15`: correct schema-3 policy module syntax and gate Python compilation explicitly ahead of behavioral regression tests
- [ ] Qualify schema-3 full matrix, owner native policy authority and lock-held recovery before enabling any Voice Apply


- [x] Current candidate `v0.5.1_14`: schema-3 cutover journal pins immutable previous process kernel image/credential policy to validated five-way previous-state evidence and read-only security reader
- [ ] Qualify owner-device role UID/GID and kernel executable identities, immutable launch trust and semantic readiness; production Config+lifecycle lock-held restore remains gated


- [x] Current candidate `v0.5.1_13`: read-only native FreeBSD process text pathname + numeric UID/GID witness with PID/start stability; test kernel self-process in FreeBSD 15 CI
- [ ] Bind verified actual OPNsense process image/credential policy to durable intended state; test on owner device and certify kernel argv provenance/readiness before any native recovery


- [x] Current candidate `v0.5.1_12`: kernel-exposed NUL-delimited FreeBSD argv reading with strict bounds, PID/start double-probe and offline tests, still unwired
- [ ] Validate real FreeBSD kern.proc.args behavior and mutable process-title risk on owner appliance; qualify executable path/credential proofs and UDP readiness under native locks before Voice Apply


- [x] Current candidate `v0.5.1_11`: exact kernel argv-array restart attestation against saved dvtws.args + fixed launcher flags, double observations, new PID/start token safeguards (test-only reader)
- [ ] Qualify genuine FreeBSD kernel argv provider, semantic supervisor launcher and readiness evidence before allowing any Voice Apply/restart


- [x] Current candidate `v0.5.1_10`: seal-bound live Config permissions checked alongside unchanged canonical byte SHA256
- [ ] Native dual-lock-held process/Config/IPFW restart and semantic argv verification before Voice Apply


- [x] Current candidate `v0.5.1_9`: compose all five native, injection-only read-only prior-instance fingerprints and test with complete cutover preflight; no activation capability
- [ ] Wire production Config/lifecycle locks and verify semantic process argv + post-boot new-instance attestation before replay or Voice Apply


- [x] Current candidate `v0.5.1_8`: read-only live Config/runtime canonical SHA256 witness, strict `dir_fd` no-follow traversal and double-scan race checks
- [x] Compose the five read-only witnesses in offline staging; production lifecycle/Config lock entry remains pending


- [x] Current candidate `v0.5.1_7`: real kernel IPFW ownership witness, read-only and strictly ledger-matched
- [ ] Qualify lock-held FreeBSD Config/runtime/process observer and stage-to-live recovery before exposing Voice Save/Apply


- [x] Current candidate `v0.5.1_6`: five-way read-only recovery attestation with fail-closed mixed-state and committed-target rejection; no live restore
- [x] Reconcile GH-014 / DEV-029–DEV-033 cross-reference tables after v0.5.1_5 repository-integrity failure
- [ ] Implement and qualify real lock-held Config, dvtws2/supervisor, IPFW and boot restore; currently staging-only


- [x] Current candidate `v0.5.1_5`: tolerate blank native ps rows, reject malformed rows; retain strict three-role inventory


- [x] Correct DEV-032 missed revision bump forward to v0.5.1_2; guard future packaged-code pushes
- [ ] Preserve per-commit revision increments on future product code changes; docs/CI-only stay unchanged


- [x] Staged private verified Config/runtime restoration payload without appliance mutation or overwrite
- [x] Stage private, runtime-bound process evidence for old one-engine dvtws2 and supervisor with restart-read tests
- [x] Stage read-only FreeBSD process PIDfile/ps inventory adapter and fake process-table tests; no live call site
- [ ] Native dual-lock held restore adapter: previous engine, supervisor, Config and IPFW; verify on reboot before Voice activation


- [x] Remove misleading disabled Voice settings Apply button while keeping release installer, Validate and service controls (Draft PR #328; 2026-10-09)
- [ ] Integrate real transactional Voice save/activation only after native locks, dual journals and reboot validation qualify the one-engine cutover


- [x] Stage optional Voice whole-cutover journal schema 2 with desired canonical IPFW digest; retain schema 1 compatibility, restart checks, and both native diagnostic/boot guard fail-closed tests
- [x] Cross-check previous sealed Config/runtime snapshot and previous/desired IPFW ownership against separate dual journals in read-only offline tests
- [ ] Validate full Linux + FreeBSD 15 CI at exact current PR #328 HEAD after schema-2 stage
- [ ] Implement native lock-held writer/adapters, engine/supervisor recovery evidence, verified power-loss handling, old Telegram PoC retirement and installer qualification BEFORE enabling Apply


- [x] Repair Strategy Lab mocked backend fixture for mandatory Voice journal guard; distinguish parent-before-worker and inherited-lock internal stop denials with no prior service mutation
- [ ] Confirm final full corrective matrix and FreeBSD 15 package on exact PR #328 head after fixture correction

- [x] Correct Linux Strategy Lab CI incompatibility from fixed FreeBSD guard Python without adding production bypass; test real function status propagation
- [x] Close inherited-lock Strategy Lab internal start/stop route around pending Voice cutover journal inspection; preserve read-only status/evidence
- [ ] Qualify exact-head full Strategy Lab + Voice + FreeBSD package CI and test real OPNsense boot/lifecycle after eventual native cutover

- [x] Bind verifiable previous Config/runtime byte snapshots to two corresponding durable whole-cutover journal resource hashes, with tamper regression
- [ ] Bind actual previous engine, supervisor and plugin-owned IPFW snapshots and implement full lock-held recovery before Apply

- [x] Stage private previous Config.xml + runtime byte snapshot, sealed manifest, source race detection and read-only integrity tests (Linux/FreeBSD)
- [ ] Verify installed runtime directory structure and symlink policy; persist trusted snapshots of IPFW and supervisor/engine metadata and bind all resources to journal under one lock
- [ ] Implement authenticated OPNsense persistent Voice Apply, native single-engine IPFW handoff, power-loss recovery and owner-live acceptance

- [x] Preserve active runtime during failed rollback backup rename using parked candidate and verified inverse rename, with fault-injected Linux/FreeBSD test
- [ ] Add durable whole-cutover recovery across power loss and verified OPNsense live acceptance, rather than treating two renames as fully atomic

- [x] Fix non-destructive shared runtime rollback: validate backup before deleting current release, deny symlinks/missing backup, Linux/FreeBSD regression
- [ ] Implement real native Voice Apply using validated backup + full journal/IPFW rollback; test hard power-loss recovery and owner-live OPNsense behavior before publishing

- [x] Enforce read-only pending dual-journal/native-owner gate under the actual zapret_service.sh lifecycle lock, before legacy runtime mutation; test FreeBSD and no-journal compatibility
- [ ] Implement a native-owner-aware Start/Stop/Reconfigure dispatcher and reviewed cold-boot journal recovery; safely migrate old Telegram Voice PoC and enable Apply only after end-to-end rollback acceptance

- [x] Wire private whole-cutover pending-intent classification into native read-only Voice configd diagnostics before IPFW readiness; RU/EN stage text and CI regression
- [ ] Adopt and coordinate full-runtime/IPFW journals in actual Config/lifecycle locked native Apply and cold-boot recovery, without automatically clearing ambiguity

- [x] Stage isolated full-system Voice cutover coordinator with verified old state, ordered single-engine/IPFW/supervisor/config handoff and fault-injected rollback (test adapters only)
- [x] Stage durable private whole-runtime fsync journal, crash-phase inspection and integration with mock coordinator; verify restart/permissions and package inclusion
- [ ] Implement real OPNsense native cutover adapter under Config/lifecycle locks, coordinate both journals, decommission old PoC, bootstrap persistent Voice ON after restart and qualify owner-live packet/media acceptance

- [x] Stage immutable Voice/Strategies/native dvtws2/IPFW handoff integrity preflight; SHA checks, original ordinary port cross-check and old-PoC conflict detection
- [x] Verify port agreement using actual `backend/ports.sh` and one-engine generation with `generator.sh` on Linux/FreeBSD CI
- [x] Correct FreeBSD CI test-only `python3` resolution without altering production OPNsense/Python
- [ ] Attach approved handoff to lock-held single-engine config/dvtws2/IPFW transaction with rollback, migration and boot recovery

- [x] Cross-check all five native Voice IPSET fields against production Targets normalization and candidate compiler on Linux/FreeBSD CI

- [x] Gate native saved Voice ON before top-level firewall_prepare and before destructive orchestrator START cleanup; permit global Zapret OFF
- [x] Mock regression for START preserving existing process/IPFW on rejected Voice ON, plus real service entrypoint preflight order
- [x] Offline bridge of staged Voice + unchanged ordinary Profiles through production generator.sh and scoped IPFW plan in CI/FreeBSD
- [x] Detect mid-stage source XML/managed IPSET/ordinary changes with checksums, reject symlink sources and fsync published staging directory
- [ ] Wire installed-runtime capability preflight, atomic release/config/IPFW/dvtws2 cutover, durable crash recovery, native Voice Save/Apply and legacy PoC retirement

- [x] Stage pure VoiceApplyCandidate plan: baseline+whitelist, enabled IPSET normalization and OFF draft preservation, field diffs, WAN-isolation gate; reuse in Validate
- [x] Add native generated-config five-checkbox staged-only gate so future saved Voice ON cannot silently run through old Telegram PoC
- [x] Test pure Voice Apply plan, foreign settings stability, stale tabs and native backend ON-gate under CI
- [ ] Remove temporary staged-only guard **only with** full one-engine native Voice runtime, atomic config/IPFW/dvtws handoff, compatibility migration and restart recovery

- [x] Native Voice load returns model + stable baseline from a single Config-locked read
- [x] Voice Validate rejects stale Strategies/Voice/shared target edits under same Config lock, strict field whitelist and localized errors
- [x] Model-stub PHP test proves stale/conflict/missing-token, read-only behavior and lock release
- [ ] Persist and apply Voice under one validated transaction, rechecking baseline before config/runtime mutation and restoring all resources on failure

- [x] Add native Voice form Validate action: unsaved IPv4/STUN/UDP scope checks without config mutation; localized RU/EN field errors
- [x] Add standalone PHP validator regression and PHP/Python candidate acceptance parity CI; correct CI host/container interpreter ownership
- [ ] Qualify native GUI AJAX/DOM form and field-error display on owner OPNsense; ensure dark/light theme and RU/EN
- [ ] Implement persistent Voice Save/Apply behind unified lifecycle lock, installed engine preflight, transaction and reboot restore; retire temporary PoC only after verified cutover

- [x] Stage explicit old PoC migration plan from config.xml, transient marker and active state; preserve native preference and refuse ambiguous live state
- [ ] Implement one-way atomic migration and persistent native Voice Apply; decommission marker/old hard-coded profile/rules after verified handoff

- [x] Stage FreeBSD IPFW adapter, non-mutating by default, narrow argv/table/rule parsing and native-VM test coverage (not production-wired)
- [x] Stage read-only Voice configd/API status with RU/EN GUI labels; no save/apply route
- [x] Compare IPFW address tables as unordered unique CIDR sets across rollback and journal
- [x] Stage bounded fake TTL/checksum/fragment/out-range parsing with negative examples (installed-engine gate pending)
- [x] Reject competing ordinary STUN during Voice candidate merging while preserving non-STUN A2
- [ ] Wire lock-held real IPFW activation, persistent native Voice Apply, replacement of Telegram PoC, boot recovery, exact-head full CI and owner-live review

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-10-09

- Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md)
- Exact handoff: [`START_HERE.md`](START_HERE.md)
- Current-line detail: [`history/current/v0.5.x.md`](history/current/v0.5.x.md)

## Active `v0.5.1_1` — Voice Transmission development, Draft PR #328

The current in-progress candidate is `v0.5.1_1` (unmerged, not published). The existing `v0.5.0_3` remains the latest experimental prerelease; stable Web/pkg remains `v0.5.0_1`.

- [x] Stage native Voice page between Strategy and Laboratory with the existing form style and RU/EN guidance
- [x] Stage five OFF-by-default service fields, WAN selector, shared IPv4/CIDR target fields
- [x] Stage new named target registry, storage and normalization for Discord, X, SIP and Custom (pending CI)
- [x] Stage standalone fail-closed STUN compiler, initial allowlist and per-service conflict/line validation tests (not yet applied)
- [x] Stage declarative Voice IPFW address-and-port capture plan with five-service range/overlap checks (not yet installed)
- [x] Stage read-only native OPNsense Voice config.xml export and end-to-end candidate pipeline tests (not yet activated)
- [x] Stage inert candidate-release bundling with exact normalized managed-IPSET verification, resolved physical WAN and private atomic artifacts
- [x] Stage one-engine Voice + unchanged ordinary Strategies text merge, reject legacy PoC identity/double-prepend
- [x] Stage ownership-checked IPFW transaction algorithm and mocked failure-injection rollback (not wired to production)
- [x] Stage durable owner-private IPFW manifest/intent files, fsync/atomic rename and read-only crash-triage; mock-test tampering, permissions and unfinished transitions
- [x] Stage checked retryable post-commit table cleanup and fix foreign-rule collision rollback in mock core
- [x] Stage mock-only activation controller connecting ledger, IPFW swap, verified cleanup and abort; ON/change/OFF/crash failure-injection tests
- [ ] Wire real FreeBSD IPFW adapter and lifecycle lock, dvtws2/manifest rollback, and recovery before enabling Apply
- [ ] Implement and verify real FreeBSD IPFW adapter, lock-held activation, atomic manifest handoff and crash recovery before enabling Voice Apply
- [ ] Wire real IPFW adapter, persistent ownership manifest/journal and crash recovery; qualify staged swap/rollback on FreeBSD
- [x] Stage Voice-only payload whitelist and symmetric Telegram-IPSET freshness validation helper (future API still pending)
- [x] Scope Strategies Apply to Strategies-owned fields without resetting Voice/other IPSETs
- [x] Guard existing Strategies Apply against stale Telegram IPSET input under config lock
- [ ] Enforce the same Telegram IPSET concurrency guard for future Voice Apply
- [ ] Expand and qualify native options (TTL/ranges/fragmentation) and connect fully transactional independent Apply
- [ ] Replace hard-coded ephemeral `telegram_voice` with persistent per-service profiles and compatible commands
- [ ] Destination/port-scoped IPFW and WAN isolation, ownership, overlap detection and rollback
- [ ] Boot persistence / OFF and global OFF safety / legacy migration / single-engine regression
- [ ] Exact-head CI, FreeBSD package qualification, documentation synchronization and user-live review
- [ ] Controlled post-install WAN and reboot acceptance; distinct from MEDIA_PASS/CALL_PASS

## Completed project path

- [x] Initial OPNsense plugin and independent project identity
- [x] Runtime/service lifecycle and transactional Apply
- [x] Unified Traffic Strategy and managed HOSTLIST/IPSET targets
- [x] Zapret2 Service GUI for upstream install/update/reinstall/downgrade
- [x] Diagnostics fixes and blockcheck redesign
- [x] Strategy Lab foundation and Python migration
- [x] Adaptive candidate search and timeout/budget containment
- [x] Model A/B/C experimentation and **Model C selection**
- [x] Model-C-only normal production execution
- [x] Source-port attribution/leasing and readiness hardening
- [x] Lua/BLOB/discovery measurement cycle and production decisions
- [x] Generic UDP exact-byte path and QUIC execution observability
- [x] Explicit persisted **Enable QUIC** execution control
- [x] Enable QUIC ON/OFF execution semantics
- [x] **Enable QUIC preference reload/revisit persistence — OWNER-LIVE PASS**
- [x] Strategy Lab RU/EN presentation and native OPNsense Laboratory layout
- [x] Laboratory domain + IPv4 targets with optional Host/SNI
- [x] Truthful HTTP `4xx`/`5xx`, bare-IP identity and QUIC result classification
- [x] Final fixed-IP `--ipset-ip=<target>` profile/replay
- [x] Selected Stage-90 restoration/residue owner-live coverage
- [x] `v0.4.x` owner-live feature closeout

## `v0.5.0_1` release transition — COMPLETE

- [x] owner explicitly selected second-component transition `v0.4.x -> v0.5.x`
- [x] close Enable QUIC preference persistence from owner confirmation
- [x] set `VERSION=0.5.0`
- [x] reset `PLUGIN_REVISION=1`
- [x] roll current documentation to `v0.5.x`
- [x] archive final `v0.4.x` line
- [x] complete README release review and feature presentation
- [x] exact-head complete CI — run `31915884270`
- [x] FreeBSD 15 package qualification — run `31915884270`
- [x] exact squash merge `v0.5.0_1: Prepare release v0.5.0` — `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`
- [x] immutable stable tag `v0.5.0` points to the exact release merge
- [x] stable GitHub Release package/checksum publication — workflow `31916256043`
- [x] matching Pages/pkg repository deployment and verification — workflow `31916256043`

Stable package: `os-zapret2-restyle-0.5.0_1.pkg`.

SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`.

Full release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

## `v0.5.0_2` file-picker localization corrective — COMPLETE

Fresh owner evidence selected a concrete post-release defect: the visible Generic UDP browser-native file picker could show Russian browser/OS labels while OPNsense/Strategy Lab was set to English.

- [x] identify browser-native `<input type="file">` chrome as the localization leak
- [x] keep the real native input only as the hidden file-selection mechanism
- [x] add Strategy Lab-owned RU/EN picker button and filename text
- [x] preserve selected filename, busy-state disabling, FileReader/Base64 staging and 1–4096-byte validation
- [x] add regression coverage forbidding return of the visible native `form-control` file picker
- [x] exact-head complete CI — run `31917466421`
- [x] FreeBSD 15 package qualification — run `31917466421`
- [x] exact squash merge for `v0.5.0_2` — `1ae952185dbae80ec34c0a89b441feddbe8b403a`
- [x] persistent GitHub testing-package publication — `v0.5.0_2`, workflow `31917806438`
- [x] bounded publication-record reconciliation — PR `#270` merged, generated evidence state closed afterward
- [x] focused owner-live RU/EN file-picker verification — **OWNER-LIVE PASS**

Testing package: `os-zapret2-restyle-0.5.0_2.pkg`.

SHA-256: `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_2.md`](verification/evidence/testing-publications/v0.5.0_2.md).

Owner-live evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

The stable Pages/pkg repository remains on `v0.5.0_1`; `_2` was not automatically promoted.

## `v0.5.0_3` current testing line — TELEGRAM VOICE LAB ACTIVE

- [x] keep package identity at `VERSION=0.5.0`, `PLUGIN_REVISION=3`
- [x] retire the `e3069322...` binary from active laboratory use
- [x] pin the only active tgcalls oracle to `efd330ca04f74706024a5abdfb5b41f4e4dd1065`
- [x] require a local P2P smoke gate and SHA-256 manifest for that current oracle
- [x] qualify current `efd330ca...` build/runtime on TNAS — **OWNER-LIVE PASS**, SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`
- [x] record owner runtime update to Zapret2 v1.0.5.2 for future live candidate epochs
- [x] keep this change lab/docs-only; no package payload or revision bump

## Voice configuration and Telegram media qualification

**October 8 product update:** the approved [Voice page specification](architecture/VOICE_TRANSMISSION_GUI.md) is the immediate implementation task. Configuration GUI/persistent lifecycle no longer waits for a successful call; the older stage-3-only restriction below is superseded. Repeated Docker `MEDIA_PASS` and real UDP `CALL_PASS` remain qualification gates for a working Telegram strategy. Squid/sing-box/PF proxies, TNAS routes and the testing controller remain independent laboratory infrastructure. The same-provider mission and manual TNAS/Docker boundary are unchanged. [Requirements](REQUIREMENTS.md) · [current handoff](START_HERE.md).

### Immediate implementation — «Передача голоса»

- [x] Record the approved native Strategies-style layout, five service fields/IPSETs, top WAN, removed LAN/local/boot controls and non-STUN ownership; reconcile old conflicting plans.
- [ ] Define concrete persistent model/native argument validation, shared target registration, legacy migration and single-engine independent-WAN isolation; no copied Telegram IPSET or silently changed ordinary WAN.
- [ ] Implement native menu/form/API/view, RU/EN and common service presentation; preserve values when disabled and reject invalid/ambiguous active profiles before Apply.
- [ ] Replace fixed PoC/marker authority with configurable STUN profiles, scoped UDP table/rule lifecycle and compatible native commands; restore saved choices through the existing service startup without Cron or a second daemon.
- [ ] Qualify model/profile/firewall/rollback/upgrade regressions, rendered layout and package integration through GitHub/CI; then measure owner-live ON/OFF/global-OFF and OPNsense reboot restoration before any manual repair.
- [ ] Reconcile laboratory runner/baseline after migration and resume bounded one-variable strategy research. Configuration PASS is separate from media/service-specific efficacy.

### Parallel requirement — independent persistent laboratory (not plugin stage 4)

- [x] Prove the bounded October 1 LAN HTTPS and SOCKS5 Telegram IPv4 TCP/80,443 paths through Squid to the external parent. Retain the working setup unchanged for now.
- [ ] Maintain a single documented lab baseline for **LAN, router-local Telegram traffic and SOCKS5 clients** with separate TCP/TLS parent-proxy and Telegram UDP/Zapret2 paths. Router-local Telegram TCP/TLS without explicit SOCKS and SOCKS UDP ASSOCIATE are not yet qualified; this is not a request for global console proxy variables.
- [ ] Prefer supported OPNsense GUI configuration and service persistence for Squid, PF and eligible settings; explicitly verify how non-GUI sing-box/ACL/snapshot state survives regeneration. Do not invent GUI features or modify plugin code directly on the appliance.
- [ ] Restore the selected **Voice-helper ON** state after **OPNsense reboot**, **one time only** after regular Zapret2 is ready. **No Cron/recurring `telegram-voice-enable`**, per explicit owner decision. Current transient `/var/run` state is lost at reboot; no fix installed or owner-live validated yet. The selected implementation is now the native persistent Voice page above, not an additional lab hook. Preserve the facts in the [source audit of GUI strategy versus destination-scoped Voice IPFW capture and PF/NAT order](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Retain ordinary services, firewall state and ACL/alias synchronization without uncontrolled changes.
- [x] Install and owner-test **manual** OPNsense→TNAS Ed25519 SSH on port 9222 and a guarded two-host-route repair script on OPNsense; manual test passed with both current routes intact.
- [ ] After a future TNAS reboot, owner manually runs the verified route script and verifies actual route restoration. **No TNAS route Cron/configd/boot scheduling and no tgvoice-lab Docker autostart**, by explicit owner decision.
- [x] Compare the October 7 OPNsense before/after-reboot configuration snapshots and record manual native recovery: helper ON→OFF→ON/table14; GUI A2/target data/ordinary UDP596–599/PF configuration survive. [Three-phase result and limits](verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md). Native re-enablement is **not automatic recovery acceptance** or a new media pass.
- [ ] Complete the remaining post-reboot acceptance: full post-enable effective helper/candidate/process/target snapshot, service and LAN/SOCKS/router-local TCP-to-parent probes, and separate relevant UDP/interception tests. Record failures independently. Separately verify the owner-selected *manual* TNAS routes after an actual TNAS reboot.

This parallel lab requirement is tracked in the [exact owner-live operations/reboot/SSH runbook](architecture/TELEGRAM_LAB_OPERATIONS.md) and [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md) and does **not** add Squid, sing-box, TCP proxy functionality, SOCKS integration or routes to the `os-zapret2-restyle` package.

### Completed research and lab setup (evidence, not product acceptance)

- [x] Phase A/B Telegram TURN/STUN and reflector traffic observation; STUN zero-fake helper mechanically qualified but did not restore UDP replies/media on the provider path.
- [x] Build and qualify the current `tgcalls_cli` oracle and local P2P smoke; fix reflector endpoint `91.108.13.10:596` for comparable epochs.
- [x] Preserve the historical September 5 reflector `MEDIA_PASS` via retired `192.168.1.140`; record the owner's September 22 established-call report through OPNsense without inventing strategy attribution.
- [x] Establish actual non-STUN 40-byte current Reflector Hello behavior, normal forwarding/NAT, post-NAT local fragmentation fidelity and all already-completed standalone reverse-position/combined-fake experiments without media replies.
- [x] Verify October 1 Telegram IPv4 TCP/80,443 over laboratory LAN/Squid/parent and SOCKS5/sing-box/Squid/parent, followed by renewed owner-live LAN HTTP 200 and Squid parent tunnel after route correction. Keep this working lab configuration unchanged.
- [x] Preserve the October 2 *early* real Windows → remote Android P2P-disabled call with good owner-reported sound: two matching PCAPs confirm 90 unchanged non-STUN Hellos + 9 STUN originals traversed Voice IPFW, plus 18 WAN fake payloads, *no inbound Telegram UDP*. Packet counters 99/6624 match originals exactly. **Not** UDP `CALL_PASS`; TCP/audio path was not recorded. [Exact evidence](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md). Owner subsequently clarified Windows' **default gateway was not OPNsense**. Direct capture Ethernet analysis confirms the **observed 99 Telegram UDP originals nevertheless targeted OPNsense's LAN MAC**, matching its DNS-server source MAC; don't extrapolate this to all media. A repeat requires confirmed per-destination Windows routes to `192.168.1.2` and synchronized TCP+UDP captures.
- [x] Archive seven follow-up real Windows calls #2–#8 with **only OPNsense as IPv4 default**, all voice-connection failures despite Telegram connectivity: **14 correlated LAN/WAN TCP+UDP PCAPs**, 345 non-STUN reflector Hellos + 45 STUN originals all seen on WAN, 90 extra zero16 STUN fakes, **no captured inbound Telegram UDP**. After restoring other preferred gateway `192.168.3.140`, owner reports real calls connected; successful-route PCAP and identical in-app proxy conditions **not yet measured**. [Dated seven-call A/B evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- [x] Preserve subsequent **16:16 October 2 Telegram Desktop WebRTC failure** from a separate private detailed call log with owner-reported OPNsense-only default and no app proxy: remote signaling/ICE candidate exchange works, correct-NIC reflector and TURN requests occur, **no confirmed ICE/DTLS secured media**, timeout at ~20 seconds; separate newer main log is not the same call. [Source-scoped sanitized evidence](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). No same-call PCAP or verified alternate successful media trace, so root cause/accepted gates unchanged.
- [x] Verify `telegram_voice` ON/interception of 60 current reflector Hellos in the October 1 control. These non-STUN packets were not transformed and no media established; the result is **not** `MEDIA_PASS`.

**Historical October 2 priority, since completed A1/A2 (see latest current priority above):** perform repeated experimental strategy qualification **in the existing TNAS Docker laboratory**, not by asking humans to make a real Telegram call for each candidate. The provider's Telegram DPI block is the owner-established premise; keep functioning Telegram TCP via external Squid parent unchanged. The operator reports that candidate `HELLO-FAKE-A1` has already been Applied in ordinary GUI Strategy, but **no wire profile/call outcome is yet known**. [Read and follow the complete campaign and preflight before experiment](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md). The fixed target remains `91.108.13.10:596`, current binary/engine pinned, TNAS `/32` through OPNsense and one new 15-second Docker test with simultaneous LAN/WAN IP captures.

- [x] Analyze first one-shot A1 owner archive: existing TNAS routes correct and Voice ON, **effective `traffic.conf` has no A1** and IPFW rule19002 has no UDP/596–599; no Docker call/capture occurred, so `PREFLIGHT_FAIL` **is not** `WIRE_FAIL` or `MEDIA_FAIL`. [Exact archived evidence](verification/evidence/2026-10-02-docker-a1-preflight-absent-effective-profile.md).
- [x] Publish and qualify the GitHub [one-command A1 runner](../tools/telegram-voice-lab/run-a1-opnsense.sh) with safe persisted/effective flags; owner already downloaded and ran v2, confirming it correctly stops before Docker when saved A1 is missing.

- [x] Second owner-run v2 diagnosis **determined root state boundary**: saved GUI Strategy readable, but A1 port/payload/fake all absent; live profile and numeric UDP/596–599 IPFW rule also absent, Voice ON. `A1_NOT_IN_SAVED_GUI` is **not** an A1 network result. [Private-source evidence](verification/evidence/2026-10-02-docker-a1-second-preflight-saved-gui-absent.md).
- [x] Tracked v2 one-command runner with saved GUI flags and offline CI qualification was source-merged via PR #315; it is already installed on owner's OPNsense. Do **not** develop or download another runner without new evidence.
- [x] Corrective **ordinary persistent GUI Strategy Apply** (completed; A1 and A2 were subsequently tested), verifying success and preserving all earlier profiles, followed by a single existing OPNsense runner invocation. If Apply fails/reverts, record its error before any further test. If preflight passes, capture first real Docker A1 epoch.
- [x] Third owner A1 archive (2026-10-03) verified saved GUI/full effective A1, ordinary IPFW UDP/596–599 capture, Voice ON/table14 and pre-existing TNAS route guard PASS. **Runner** falsely rejected a valid Linux `ip route get ... from` response because its duplicate check required `src`. **No Docker trial or A1 media result**. [Source-scoped evidence](verification/evidence/2026-10-03-docker-a1-preflight-linux-route-from-mismatch.md).
- [x] Correct the existing runner's source-NIC and route `via`/`dev` validation; require regression on Linux `from`/`src`, wrong gateway and missing source, exact-head CI and merged main. Update only the already installed independent runner from pinned GitHub SHA via existing Squid; then **one** fresh Docker A1 run/one private archive (no new GUI Apply or TNAS login).
- [x] **First actual Docker A1 experiment acquired (2026-10-03)**: one qualified pinned 15-second reflector process; all 60 genuine Hello packets matched LAN→WAN after NAT, **120 bad-checksum zero16 fake packets (two before each genuine)**, 0 captured inbound reflector UDP, both peers Reconnecting/zero BWE/`tgcalls_exit=1`. Accurate classification **`A1 WIRE_OK / NO_REPLY_UNKNOWN`**; IPFW19000 +60/+4080, ordinary19002 zero due earlier Voice interception, no captures dropped. [Full measured record](verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md).
- [x] **A2 candidate design and actual result:** hold target/engine/routes/active helper/profile scope/zero16 fake/repeats=2 constant, remove **only `:badsum`** to see whether valid-UDP-checksum fakes change outcome; A2 subsequently **applied and measured**, with 120 valid-checksum fakes/60 genuine WAN Hellos, zero replies/media. The existing single-command runner was updated and regression-tested to accept explicit A2; this historical requirement is complete. Preserve one archive, no real human calls, and never treat failed media as proven packet-block root cause.
### Stage 1 — reproduce a working UDP voice transport through OPNsense

- [x] Preserve owner's October 2 Docker-first decision and exact A1 GUI candidate **Applied-reported only**; [complete canonical plan](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).
- [x] Replace multi-console, interactive-TNAS A1 procedure with one independently maintained OPNsense `sh` runner that invokes the **existing** owner-tested route guard and restricted SSH, verifies active A1/Voice/IPFW and pinned current Docker binary, owns two concurrent IP captures and one bounded 15-second fixed-reflector CLI invocation, cleans up and outputs one private `.tgz`. [Source](../tools/telegram-voice-lab/run-a1-opnsense.sh) · [campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md). Source, mocked tests and initial actual A1/A2 live wire qualification complete; repeatable MEDIA_PASS remains open.
- [x] Verified generated A1/helper/IPFW/IPSET/routing baseline read-only; run one qualified **15-second pinned Docker reflector A1** on existing OPNsense path with WAN/LAN IP captures, peer stats/BWE/exit and honest `PROFILE_NOT_SELECTED` / `WIRE_OK` / `REFLECTOR_READY` / `MEDIA_PASS` distinctions.
- [x] **First A2 checksum-only comparison, October 3:** exact merged runner and saved/effective A2 PASS; 60 real WAN Hellos, 120 preceding zero16 fakes with correct post-NAT UDP checksums, zero replies/media, both peers Reconnecting, exit 1. A2 is `WIRE_OK / NO_REPLY_UNKNOWN`, not `MEDIA_PASS`. Earlier A2-pending tasks above are superseded by this measured result. [Proof](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md).
- [x] Design one guarded, read-only same-endpoint **control-path inventory** from existing OPNsense→TNAS SSH with one private archive, no experimental host-route edits, Docker execution, GUI/PFIL changes or assumption that external TCP parent carries UDP. [Control architecture and runner](architecture/TELEGRAM_VOICE_INDEPENDENT_CONTROL.md).
- [ ] **Optional causal diagnostic only:** existing read-only inventory helper is available if a specific later hypothesis requires route/tool information; it is NOT the next mandatory run or a reason to build a new UDP exit.

- [x] Record October 5 topology/source review: shared LAN does not make reflector-mode media local; local P2P smoke and external UDP oracle have different scope; A2 TTL=63 did not test limited fake TTL; CLI exit 0 alone is weaker than the project's media gate. [Analysis and sources](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md).
- [x] Audit October 7 documentation/source consistency: retain topology and measured outcomes; correct whole-helper toggling, intentional fake checksum semantics and unproven audio-transport attribution. [Audit](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md#проверка-документации-7-октября).
- [x] Make `telegram_voice` an explicit controlled component of every experiment: freeze ON, managed Telegram target set, all-port capture and fixed STUN zero16/repeats=2; distinguish these from the variable GUI `unknown` action. Document native commands, parameter ownership and the mandatory old/new record for any future helper change. [Helper runbook](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) · [test matrix and pre/post contract](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#telegram_voice-controls-for-every-trial). This documentation contract is not a claim that the existing runner implements all new checks.
- [ ] **Retained research tooling, after the selected page/migration baseline:** extend the existing one-command Docker runner with RTC logs, bounded correlated ICMP, strict saved/effective candidate and fixed-helper checks (source/full profile/target content/actual process and semantic pre/post state), and verified owned remote-process/container cleanup. Baseline drift stops acquisition; helper recovery is a separate recorded operation. Expected result: one complete private evidence bundle with separately verified restoration, qualified tooling through PR/CI; no live bypass claim.
- [ ] **Next experimental hypothesis, not an accepted strategy:** prepare a limited-fake-TTL comparison against A2, changing only fake `ip_ttl`. Commit the exact candidate, at most four initial TTL values, expected wire output and stop/restore contract after path/source checks; seek the first library-accepted reflector response, then both-peer media. The campaign specifies expected results and branches for WAN-only reply, client rejection, partial connection and full silence. [Detailed campaign plan](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#next-experiment-limited-fake-ttl-planned-not-run). Independent controls remain optional; old `.140` stays retired.
- [ ] For a Docker media-positive candidate, apply the campaign's three-successful-fresh-run and action-only control plan, keeping Voice-helper ON; preserve failed runs and distinguish repeatability from causality. Then perform one bounded real-client connection/UDP test followed by two-way sound, with the actual client endpoint/profile verified.

- [ ] Correlate existing September 22 positive CLI evidence if recoverable; otherwise choose one bounded source-guided experiment that resolves a specific remaining hypothesis for the *current* non-STUN reflector transport. Do not restart completed fragmentation-position sweeps by inertia.
- [ ] Freeze source/runtime/profile identity, endpoint, route, hook order and capture boundaries per experiment; preserve exact pre-test state and prove complete restoration.
- [ ] **Optional separate causal control, not the next screening task:** capture a successful Windows/Android call over the alternate `192.168.3.140` gateway with matching TCP+UDP/ICE and frozen application settings, *if* later needed to locate a path difference. Do not delay the next qualified same-ISP Docker experiment or repeatedly request human calls as candidate screens.
- [ ] Repeat successful current-oracle `MEDIA_PASS` through OPNsense: both peers `Established`, stats and non-zero BWE on both, exit 0, and correlated UDP LAN/WAN packets. Missing replies without a fresh independent working control remain `NO_REPLY_UNKNOWN`, not a proven DPI diagnosis.

### Stage 2 — real Telegram client acceptance

- [ ] A remote Windows → Android P2P-disabled audible call **already occurred** on October 2, ahead of Stage 1 completion. Before marking `CALL_PASS`, explicitly verify sustained bidirectional UDP and sound in each direction; the supplied UDP captures contain **no Telegram UDP replies**. If needed, repeat a bounded call with simultaneous TCP/UDP metadata capture to identify the actual media route and distinguish fallback. Preserve the validated October 2 observation without treating it as Stage 2 completion.
- [ ] Repeat the positive case and preserve exact qualified strategy and scope for the eventual product.

### Stage 3 — qualify a proven Telegram Voice configuration for the plugin

- [ ] After the Telegram media gates, record the exact validated strategy, protocol/endpoint coverage and repeatability as a qualified configuration/preset for the new page plus any ordinary non-STUN strategy. Do not label the initial zero16 example a working default.
- [ ] Retain the configuration/lifecycle/boot acceptance from the immediate implementation track; rerun relevant checks only where the qualified strategy changes behavior. No hard-coded lab addresses or packaging of the Docker oracle.

The page/persistence implementation has moved **ahead** of these research gates by the October 8 owner decision. TCP/proxy/SOCKS feature integration and blanket console proxying remain outside the approved product. Independent lab TCP/persistence checks remain required; TNAS routes and Docker stay manual. The old unpublished `_4` fragment branch remains paused, not the new page's implementation base.

Current [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md), [laboratory operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [Voice implementation specification](architecture/VOICE_TRANSMISSION_GUI.md).

## Remaining regression / future backlog

These rows remain useful coverage or future product directions. They are **not** silently release debt for the completed stable `v0.5.0` release.

- [ ] cancellation/internal-failure containment regression
- [ ] circular lifecycle start/stop/TTL and stale-session recovery
- [ ] broader Diagnostics persistence/reload regression
- [ ] retention/cleanup boundary regression
- [ ] reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up as new evidence requires
- [ ] package/runtime version visibility follow-up
- [ ] RU/EN review beyond explicitly selected localization defects
- [ ] IPv6 Laboratory target support — requires a separate explicit architecture scope
- [ ] Additional BLOB repository GUI — wait for owner-supplied/approved technical contract

## Deferred research — do not reactivate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only for a concrete defect or explicit owner selection

## Current priority

**Implement the approved «Передача голоса» page and persistent Voice lifecycle next**, following [the complete specification](architecture/VOICE_TRANSMISSION_GUI.md). The native layout, five service fields/shared IPSETs, single-engine capture/profile separation, no LAN/local/boot toggles and migration are fixed scope. After configuration/boot qualification, resume the retained RTC/ICMP/limited-fake-TTL research on a recorded baseline; repeated MEDIA_PASS and real UDP CALL_PASS qualify a working strategy, not permission to create the page. Preserve existing TCP/proxy and manual TNAS/Docker operations. No blind repetition of completed fragments/A1/A2 or retired alternate route.

Release notes for the current stable release: [`releases/v0.5.0.md`](releases/v0.5.0.md).

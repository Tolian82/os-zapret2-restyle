# os-zapret2-restyle — Current state for `v0.5.x`

**v0.5.1_8 — read-only live Config/runtime fingerprint witness (2026-10-10):** Added an unwired `voice_native_file_observer.py` that uses no-follow, descriptor-anchored `dir_fd` traversal to hash the current OPNsense Config and runtime tree into the **same** two canonical fingerprints as the private pre-cutover snapshot, without writing any files. It rejects symlinks/hardlinks/special files, foreign ownership, oversized/deep trees, replaced descriptors and changes between two complete scans. New Linux and FreeBSD 15 CI tests verify snapshot parity, changed Config/runtime, mode/empty-directory differences, unsafe trees, oversized inputs and mid-observation races. There is still no real lifecycle-lock call site, engine/supervisor restart, boot replay, IPFW mutation or Voice Apply. No installed appliance changes; former Telegram PoC remains intact.


**CI infrastructure retry (v0.5.1_7, docs/CI-only, 2026-10-09):** Both initial and job-only rerun of exact-head CI failed before PHP lint because anonymous Docker Hub returned `toomanyrequests` for `php:8.2-cli`. The CI PHP step now prefers already installed runner PHP **only if it is version >=8.2 and <9**, executing the same source lint and five PHP validation scripts. Otherwise it retains the original pinned php:8.2-cli Docker fallback. This is an external-runner availability fix, not a PHP source change, so PLUGIN_REVISION remains **7** under DEV-033. All other Voice/FreeBSD 15 gates and packaging remain unchanged; require CI success on the new exact HEAD.


**v0.5.1_7 — native read-only IPFW kernel witness (Draft, 2026-10-09):** An unwired `voice_native_ipfw_ownership.py` now interrogates the current IPFW plugin-owned numeric range and every active/stage table through `FreeBSDIPFWAdapter(allow_mutations=False)`, then proves that live rules and IPv4 table sets match the owner-private durable IPFW ledger. Only an exact match returns the *ledger canonical manifest* SHA256; orphan stages, missing/foreign/mutated rules or tables, unsafe ownership, and changing ledger state block with no IPFW modifications. `voice_cutover_full_recovery` also converts a native observer RuntimeError into non-authorizing blocked evidence. This remains separate from production native Apply and boot recovery and does not certify the desired committed state. Offline Linux/FreeBSD 15 CI tests; active OPNsense and Telegram PoC unaffected.


**v0.5.1_6 — read-only five-resource restart attestation (Draft, 2026-10-09):** `voice_cutover_full_recovery.py` correlates the existing sealed old Config/runtime snapshot, the independent saved engine/supervisor process evidence and both durable IPFW/whole-cutover journals with a strictly typed, repeated, injected five-resource observation. It rejects missing/corrupt/unstable/foreign state, treats schema-2 committed target as **unprovable** without four additional desired hashes, and never authorizes automatic recovery, mutation or finish-intent. This is an offline staging contract, *not* a trusted FreeBSD live resource observer or boot adapter; existing Telegram PoC and OPNsense remain unchanged. The same code increment also reconciles GH-014/DEV rule-reference tables after the exact-head v0.5.1_5 repository-hygiene CI failure.


**v0.5.1_5 — corrective FreeBSD ps inventory parsing (2026-10-09):** The native read-only process adapter now ignores empty/whitespace-only rows in ps output while still rejecting nonempty malformed process lines. The error was established by the failed v0.5.1_4 Voice CI fixture for a clean stopped state; added a regression for malformed nonempty listings. The project ROADMAP current-candidate marker also follows the revised package identity so the Strategy Lab corrective matrix can verify the same version as VERSION/Makefile. No service mutation, process restart or Voice Apply. Recheck all exact-head Linux and FreeBSD 15 CI.


**v0.5.1_4 — native read-only process inventory adapter (2026-10-09):** `voice_native_process_probe.py` uses no shell and performs only bounded native FreeBSD `/bin/ps` reads plus no-follow, checked owner PID-file reads. It requires one exact engine process, one matching supervisor daemon and one monitor, checks immutable PID+process-start observation, catches foreign/orphan/duplicate processes and refuses inferred OFF if matching processes remain without PID files. The adapter is *not called* from production lifecycle, GUI or boot, and has no stop/start/IPFW method. Mock ps + real temporary PID-file regression runs on Linux and FreeBSD 15; the complete live FreeBSD argv/start-time process behavior still needs owner-device qualification. Previous snapshot v0.5.1_3 is preserved; Voice Apply remains absent.


**v0.5.1_3 — offline engine/supervisor recovery evidence (2026-10-09):** New staging-only `voice_process_recovery_evidence.py` captures an injected read-only double/triple process probe for exactly one dvtws2 engine and daemon+supervisor monitor. It requires coherent running/stopped topology, distinct PID/start identity and fixed trusted executable paths, and binds the engine's saved `dvtws.args` SHA to the sealed runtime backup. Published private 0600 evidence produces separate engine/supervisor hashes for the whole-cutover journal; reopening checks hashes and trusted bytes again. There is no production probe implementation, kernel read, process mutation, automatic boot recovery or Voice Apply. Linux+FreeBSD 15 tests cover corruption, PID collisions, torn captures, foreign identity, stale runtime, and destination conflicts.


**Revision correction v0.5.1_2 (2026-10-09):** Draft PR #328 incorrectly kept packaged code changes under `_1`. Corrected `Makefile` forward to `_2`, preserving immutable history. New GitHub verification checks every historical commit against its own VERSION/PLUGIN_REVISION, while PR title matches HEAD. Prospective `.github/REVISION_GUARD` enforces one-step `_N` bumps on all future packaged-code commits; docs/governance/CI-only commits retain revision. No Voice Apply, installation or release authorized.


**Voice isolated restore stage (Draft PR #328, 2026-10-09):** added `voice_cutover_restore_stage.py` to produce an independently inspectable private copy of sealed previous Config/runtime bytes, checked against durable journal previous fingerprints, per-file hashes, full manifest and source reinspection. No live destination or process is touched, and no automatic rollback/Voice Apply is enabled. New Linux/FreeBSD 15 offline regression covers tamper/symlinks/faults/destination conflicts. A real restorer still needs lock-held kernel/dvtws2/supervisor adapters and boot qualification.


**Voice draft UI decision (2026-10-09):** As explicitly requested, the disabled `voiceApply` **settings** button is removed from the Voice page rather than displayed as a misleading action. The independent `voiceReleaseApply` repository-package installation control, Voice Validate, read-only diagnostics and service controls are preserved. No voice settings persistence or activation endpoint is exposed; `VoiceApplyCandidate` remains a pure read-only validation/normalization helper. Future transactional activation requires a separate approved implementation. This change does not remove the old Telegram PoC or affect installed OPNsense.


**Voice recovery v2 boundary:** Draft PR #328 stages an explicit schema-2 desired IPFW ownership digest, retaining schema-1 read compatibility. The recovery preflight independently correlates previous immutable Config/runtime bytes with the whole journal and both previous/desired canonical IPFW manifests with the separate ledger. Phase and crash-restart tests include actual distinct targets and reject orphan/foreign/premature/mismatched ownership. Regressions establish that both native read-only inspector and boot lifecycle guard still block on v2 pending intent. These do not read the live FreeBSD kernel, recover the engine/supervisor, expose Voice Apply or authorize automatic reboot replay. Stable installed OPNsense and legacy Telegram PoC remain unchanged; exact-head Linux and FreeBSD CI required.


**Strategy Lab lifecycle regression root-cause corrected:** an integration fixture creates a fully mocked SERVICE_BACKEND and lacked the newly mandatory Voice guard file. The fixture now models guard success/pending through a test-only Python file and checks both parent-before-worker rejection (69) and inherited-lock internal stop rejection (69); neither case may stop the prior service. The real production journal guard remains fail closed. Separate versioned Python portability fix still applies to non-installed Linux source trees. Last-head full project/FreeBSD CI remains the release gate.


**Voice guard corrective checkpoint:** a Linux-only Strategy Lab corrective matrix failure was traced to the absolute FreeBSD Python interpreter used by the actual lifecycle guard (exit 69), not to Voice validation. The guard now resolves Python 3.13 from PATH only for non-installed source/test BACKEND_DIR when the fixed interpreter is missing; on installed FreeBSD it stays absolute and cannot be disabled. Internal Strategy Lab start/stop actions own inherited lockf and had bypassed the guard; both now call the same read-only fail-closed preflight before mutating. Exact-head complete CI including FreeBSD must be checked before qualification.


**Snapshot-to-journal link:** read-only `bound_resource_fingerprints` now ties persisted previous Config and runtime bytes to the two corresponding whole-cutover journal fingerprints; regression checks the journal record and rejects mismatched/corrupted runtime content. Actual old engine/firewall/supervisor snapshot adapters are still absent.


**Durable old Config/runtime bytes staged (Draft):** `voice_cutover_backup.py` now captures previous config.xml and regular-only runtime-v2 contents into a private write-once fsync'd directory with sealed manifest and per-file SHA256. Source re-hashing detects torn Config/runtime snapshots, read-only inspector rejects corruption/foreign files. It is disconnected from GUI and service and does not yet capture kernel IPFW, running engine/supervisor or verify actual installed runtime symlinks. Full native cutover adapter and crash recovery remain OPEN.


**Runtime rollback fault tolerance:** shared atomic_restore_tree parks the current release before installing a verified previous backup, reverses the park on failed second rename, and rejects existing unknown parked trees. New injected-rename regression verifies live candidate and backup survive without loss. No claim of crash-atomic rollback; full native cutover and cold reboot reconciliation remain unfinished.


**Rollback safety (draft):** the shared real `atomic_restore_tree` no longer removes current active runtime before proving a requested rollback backup exists as a non-symlink directory. A missing/symlinked backup is rejected without destroying the candidate, and good backup restores normally. Linux/FreeBSD regression covers both cases. This stabilizes existing Strategies rollback and is a dependency for future Voice cutover, not full durable recovery.


**Native legacy-lifecycle interruption guard (Draft):** a read-only Python boot guard now executes inside the existing zapret_service.sh lockf scope before start/stop/reconfigure/legacy Telegram PoC and runtime-failure paths. Pending whole-runtime or IPFW intents, committed native ownership and corrupt private ledgers all block old dispatcher; missing clean journals leave prior Strategies behavior. Distinct return code 69 avoids lockf busy 75 confusion. No real native dvtws2/IPFW Apply or automated recovery; this is a preservation guard until explicit ownership routing exists.


**Voice diagnostic integration:** current read-only configd inspector checks the full durable cutover journal before IPFW. Any prepared/mutating/committed unfinished intent blocks positive readiness; GUI shows localized stage explanations. This does NOT mean that normal boot or full native cutover is implemented: production adapters remain disconnected, Apply disabled, legacy PoC unchanged. Real recovery must coordinate the whole-runtime and IPFW journals under the shared lock.


**Voice next milestone (draft, mock-only):** whole-system `voice_cutover_coordinator.py` now models full Config, one dvtws2, supervisor and IPFW transition, verifies trusted previous state before any intent, runs fault-injected rollback, and never claims success if a partial failure remains. `voice_cutover_journal.py` is a separate private fsync'd prepared/mutating/committed intent with read-only boot classification, integrated with the simulated coordinator in tests. Both modules are packaged, but neither is connected to production startup, configd or GUI Apply. Must coordinate with per-IPFW ledger, migrate legacy marker, qualify installed engine and validate recovery on real OPNsense. Latest head CI pending independent verification.


**Voice draft handoff integrity:** new non-mutating bundle verifier checks candidate profile hashes, target hashes, derived native IPFW capture/rules, original ordinary port selectors against production ports.sh, WAN and exactly one generated dvtws2 divert socket. No access to a running OPNsense occurs; output explicitly disallows activation. FreeBSD-only unversioned-python3 test harness failure fixed by a private interpreter shim, not a production change. Pending: exact-head full FreeBSD CI, durable single-engine runtime cutover, config.xml persistence, removal of old Telegram PoC and boot recovery.


**Voice shared Target compatibility:** staged test now drives all five IPSET services through the real production `targets_prepare_managed()` followed by native Voice compilation; dedup/order/canonical CIDR match or fail closed, including an invalid prefix test. This is offline only and is not a live traffic claim.

**Voice PR #328 latest checkpoint:** native Voice persisted ON is rejected at the service entry *before firewall_prepare* and in orchestrator START *before cleanup or the complete-runtime shortcut*; global Zapret OFF can still stop the service. Offline candidate integration now exercises the actual production generator.sh and a consistent scoped IPFW plan. Staging snapshots source XML/managed targets/ordinary traffic twice, records hashes and refuses changes/symlinks. Tests cover torn-input races and fake cleanup; no live Voice Apply, single-engine cutover or automatic reboot recovery has been deployed. Last exact-head CI must be checked before merge.


**Voice native Apply remains blocked:** a pure `VoiceApplyCandidate` now shares code between future commit preparation and current validate-only GUI, detects independent WAN, canonicalizes enabled IPSET and preserves disabled drafts and unrelated settings. Generated OPNsense template exposes all five native Voice enable flags, and legacy `orchestrator_build_release` explicitly refuses persisted ON rather than silently disregarding it. This is fail-closed staging, not activation/boot recovery. Target real one-engine cutover, legacy migration, restored runtime/ownership on failure and owner-live acceptance remain OPEN.


**Voice GUI state (draft):** read-only native load now returns model and optimistic digest atomically under Config lock. Syntax-only Validate checks the baseline again, rejects concurrent edits in general/strategy/voice/hostlist, and never changes config or runtime. CI includes stubbed API concurrency and GUI token tests. This does NOT implement persistent Apply, PoC migration, real FreeBSD lifecycle or boot restore.


**Voice form validation staging:** new read-only VoiceCandidateValidator/VoiceController.validateAction plus RU/EN native GUI Validate button, syntax/target overlap guard, and PHP/Python differential CI tests. Last-stage CI run must be checked against exact head. This is validation of unsaved GUI data only: no config write, no Apply, no dvtws2, no live IPFW change; existing temporary Telegram PoC still not removed. The primary remaining implementation boundary is safe native lifecycle cutover, persistent Apply and boot recovery.


**Legacy Telegram Voice migration:** a read-only model/marker/active-state assessment and six negative/upgrade regression scenarios are staged. Ambiguous legacy status blocks new activation; old PoC must not be deleted before successful one-engine cutover, native lock integration and rollback. No package is published.


**Voice Draft PR #328 latest staging:** FreeBSD IPFW adapter is read-only by default with narrow bounded commands and parsing, a dedicated configd/API read-only Voice status is visible in RU/EN GUI, and native table equality is order-independent. Advanced fake TTL/checksum/fragment/range syntax is still parser-only pending installed engine qualification. Runtime cutover, persisted Apply, PoC removal, cold-boot recovery, FreeBSD owner-live acceptance remain OPEN. No new package has been published.


**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-10-09
State-line scope: **`v0.5.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- rule books: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md), [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md), [`CHAT_RULES.md`](CHAT_RULES.md), [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology: [`history/current/v0.5.x.md`](history/current/v0.5.x.md);
- completed `v0.4.x` archive: [`history/archive/v0.4.x.md`](history/archive/v0.4.x.md).

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and release facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.5.1` (**unmerged Draft PR #328**);
- current source candidate revision: `_8` (**development only**);
- package candidate: `os-zapret2-restyle-0.5.1_8.pkg` (**not published, do not install**);
- published testing candidate: `os-zapret2-restyle-0.5.0_3.pkg` / `v0.5.0_3`;
- testing source/tag target: `34adca978b3b6769972591872209c166ec9c6eb6`;
- testing package SHA-256: `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`;
- testing publication workflow: `33536081824`, PASS on attempt 2;
- last owner-live accepted package revision: `_2`;
- owner-live accepted testing corrective: `os-zapret2-restyle-0.5.0_2.pkg` / `v0.5.0_2`;
- current stable Web/pkg release/tag remains `v0.5.0`;
- current stable package remains `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable release-preparation merge/tag target: `d5afa6b1f4cfd7bc00e8e95d6896af8a1456fb24`;
- stable full release workflow: `31916256043`, PASS;
- stable GitHub Pages/pkg repository remains the `v0.5.0_1` release repository;
- internal service key: `zapret`.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_3.md`](verification/evidence/testing-publications/v0.5.0_3.md).

Owner-live `_2` evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked product facts carried into `v0.5.x`

- DNS is working; historical DNS timeout investigation is closed absent fresh evidence.
- Model C is the only normal production Stage-60 Strategy Lab runtime.
- Automatic Model-B/Model-A production fallback remains removed.
- Lua/BLOB/discovery/readiness optimization questions closed by accepted measurements remain closed for the current architecture.
- Strategy Lab supports domains and canonical IPv4 targets; IPv6 Laboratory target input remains deferred.
- IPv4 targets may use separate optional Host/SNI while traffic stays pinned to the entered IP.
- Working fixed-IP profiles use `--ipset-ip=<target>` and exact final replay.
- HTTP application `4xx`/`5xx` does not erase otherwise valid authenticated/intercepted DPI-path evidence.
- Bare-IP TLS identity failure reports `PARTIAL` + Host/SNI guidance.
- Bare-IP QUIC without Host/SNI is skipped before candidate execution; Host/SNI QUIC performs real fixed-IP hostname verification.
- Generic UDP remains independent of Host/SNI and QUIC.
- Enable QUIC is explicit, persisted, defaults OFF, and its reload/revisit persistence is owner-live accepted.
- Strategy Lab cleanup/restoration remains mandatory and selected live jobs preserve exact initial service state.
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted.
- The native OPNsense Laboratory layout and deterministic Strategy Lab RU/EN text localization contract remain accepted.
- Strategy Lab owns the visible Generic UDP file-picker labels; browser/OS-native file-input chrome is not exposed.
- Owner-live verification confirms the `_2` RU/EN file-picker presentation and selected-filename/file-selection path work as intended.
- `v0.5.0` remains the stable Web/pkg release; neither the owner-live accepted `_2` corrective nor the published-but-unaccepted `_3` candidate promoted the stable Pages/pkg repository.

## Completed `v0.5.0_2` corrective

The post-release file-picker localization defect is closed.

Completed boundary:

- browser-native visible file-input chrome identified as the localization leak;
- Laboratory-owned EN `Choose file` / `No file selected` and RU `Выбрать файл` / `Файл не выбран` presentation implemented;
- actual selected filename remains visible;
- FileReader/Base64 staging, 1–4096-byte validation, busy-state behavior and Generic UDP API semantics preserved;
- regression coverage added;
- exact-head source CI and FreeBSD-15 package qualification passed in run `31917466421`;
- source PR `#269` squash-merged as `1ae952185dbae80ec34c0a89b441feddbe8b403a`;
- prerelease `v0.5.0_2` published and verified with SHA-256 `d89bc45162ca760320cf59e4a861b2b8ef7bc30bcb05f4338b2078c57b4980f5`;
- publication-record reconciliation completed through PR `#270` and its evidence-state closure;
- owner confirmed the live `_2` result works as intended.

No further package correction belongs to this scope.

## Development handoff: `v0.5.1_8` native Voice GUI (Draft PR #328)

Work is staged at [PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328), branched from `main` `3f9951c928ac2521c3551c8311d58ed755947007`. New native MVC page, five default-OFF fields, bilingual guidance, common service control and shared IPSET model are present. Registry, storage and managed target generation for Discord/X/SIP/Custom are staged; a read-only native config.xml Voice exporter, fail-closed STUN compiler, inert release-bundle consistency gate, one-engine traffic merge helper, IPFW capture-plan validator, an adapter-injected mock-tested IPFW transaction core, retryable postcommit cleanup, and private durable ownership/intent journal with read-only restart triage plus mock-only activation ordering and verified abort (all not production-wired) and per-service scope conflict checks have also been added (not wired to Apply/runtime); Strategies Apply now limits its POST to Strategies-owned fields (Strategies-side shared Telegram-IPSET optimistic lock active in source; Voice-side payload/freshness helper staged, future Voice Apply endpoint not yet implemented); the existing Telegram hostlist data is reused. **Voice Apply is disabled** until complete validation and lifecycle migration are implemented. This draft has not replaced the temporary Telegram Voice PoC or qualified boot restoration, dual-WAN behavior, or media. The existing published and stable `0.5.0` packages are unchanged. See [design and implementation status](architecture/VOICE_TRANSMISSION_GUI.md).

## Telegram Voice UDP: current product scope and measured state

**October 8 superseding design decision:** implement the native **«Передача голоса»** configuration page now, between Strategies and Laboratory, in the same native design. Five services: Telegram / Discord / X (Twitter) / SIP (VoIP) / Custom, per-service checkbox and multiline parameters, separate shared IPSET fields, Voice WAN at top. No LAN/local-UDP/boot toggles; matching local UDP is always included and saved state must restore through the normal single-engine lifecycle. Non-STUN stays in Strategies. [Complete implementation specification](architecture/VOICE_TRANSMISSION_GUI.md), [requirements](REQUIREMENTS.md), [next task](START_HERE.md), [roadmap](ROADMAP.md). This replaces the former GUI-only-after-media/one-checkbox restriction; the Telegram `MEDIA_PASS` then real UDP `CALL_PASS` gates still qualify a claimed working strategy.

The current package still has the hard-coded transient `telegram_voice` helper and one common WAN; **none of the newly approved page, configurable service profiles, independent Voice WAN or persistent preference is implemented**. Telegram helper and ordinary Strategies already share `hostlist.telegramips`. The new design replaces PoC authority rather than adding another daemon or second IPSET copy. Technical native input/migration/WAN isolation decisions and tests belong to the implementation specification; no present source/runtime change or new voice success is claimed.

**Two separately owned goals coexist.** The new Voice feature remains **UDP/STUN configuration only**; Squid, sing-box, external parent, PF proxy rules, SOCKS and TNAS routes stay outside its product implementation. **The laboratory, however, retains the entire three-origin LAN/router-local/SOCKS Telegram TCP-versus-UDP policy and must preserve or recover its selected functional state after OPNsense and TNAS reboot.** Its TCP/TLS traffic is intended to reach the experimental external parent, Telegram UDP the selected Zapret2 treatment, and the TNAS voice path OPNsense. Prefer verified native OPNsense GUI/services for lab persistence, and a supported documented mechanism if a requirement is not exposed in GUI. Router-local Telegram-specific selection is a lab goal, not a blanket automatic proxy for all console applications. All **plugin** source, configuration-model, GUI and lifecycle changes are made **only through GitHub**; laboratory settings are maintained separately. The complete TCP/proxy architecture and clean-install TCP delivery are not approved additional product stages; the `tgcalls` laboratory/controller remains outside the package. [The laboratory contract/reboot runbook](architecture/TELEGRAM_TRAFFIC_POLICY.md) owns configuration and checks.

**2026-10-03 reaffirmed mission:** local ISP DPI restricts **Telegram voice UDP** (owner-established premise). We seek **Zapret2 UDP desynchronization through existing OPNsense `192.168.1.2` and that SAME local ISP**, not a new VPN/UDP tunnel/alternate gateway or substitute provider. Telegram **TCP/TLS is ALREADY WORKING** through PF/Squid and matching sing-box→Squid, using **external `185.203.117.88:33128`, the owner's GUI-configured Squid parent**. LAN/SOCKS tests confirmed TCP parent behavior. The HTTP parent is not the UDP voice path; sing-box UDP `direct` still uses current WAN/DPI and applicable IPFW/Zapret2. Preserve the current working TCP GUI/ACL/proxy settings. WAN PCAP results alone cannot localize the exact upstream UDP loss site, distinct from the owner-provided ISP-blocking premise. [Normative requirements](REQUIREMENTS.md) · [existing live operations](architecture/TELEGRAM_LAB_OPERATIONS.md).

**Current measured stage 1 evidence:** pinned TNAS Docker `tgcalls_cli` sent 60 intact genuine 40-byte Reflector Hellos through its selected `/32 via OPNsense` in each A1 and A2 run, accompanied by 120 correctly ordered zero16 fake datagrams. A1 fake UDP checksums intentionally invalid; A2 fake checksums all valid. Both zero captured incoming pinned-reflector replies, peers Reconnecting/BWE zero, exit 1: **`WIRE_OK / NO_REPLY_UNKNOWN`, NOT `MEDIA_PASS`**. A1→A2 checksum change alone insufficient. Prior fragment families and historical observations stay recorded separately. [A1](verification/evidence/2026-10-03-docker-a1-wire-pass-no-reflector-reply.md) · [A2](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md).

**October 5 source/topology conclusions:** owner confirms TNAS and OPNsense share one LAN/virtual switch. In pinned CLI reflector mode both local clients use the external UDP reflector through OPNsense; signaling alone is in-process, P2P is disabled and the configured reflector is not TCP. The local P2P smoke does not test provider DPI. A2's measured WAN TTL=63 for all genuine/fake packets is not a limited-TTL experiment. Separate fake packets, explicit TTL expiry, bad UDP checksums and genuine IP-fragment reassembly must not be conflated. The CLI's shared `establishedAt` can be set by either peer; exit 0 alone does not implement the project's stronger both-peer and bidirectional-UDP gate. [Source-grounded discussion, primary references and original-versus-later Desktop log distinction](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md).

**October 7 documentation audit:** the external-reflector topology, A1/A2 negative outcomes and limited-TTL hypothesis remain supported. Corrected the old real-call helper-OFF comparison, the overly broad `WIRE_OK` checksum wording and the claim that unobserved UDP proves TCP fallback. The current runner still needs RTC/ICMP collection, strict saved/effective profile validation and owned remote-process cleanup checks before a TTL trial. This is a documentation/source result, not a new live result. [Audit details](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md#проверка-документации-7-октября).

**October 7 measured reboot and manual recovery:** at 16:20:00 UTC Voice was ON/table14 with cumulative rule19000 counters60/4080; at 16:44:23 UTC, 399 seconds after the new boot, Voice was OFF and its table/marker/profile absent. Saved GUI A2, resolved GUI profile, managed target set, ordinary UDP/596–599 capture, PF NAT/redirects and measured IPFW→PF output-hook order survived. The owner's subsequent native enable/status output restored ON/table14/rule19000 with counters0/0. That last output does not include a full post-enable process/profile/target-content snapshot, fresh parent-proxy probes, TNAS measurements or a media run. [Exact three-phase evidence, private input hashes and limits](verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md). Manual restoration is verified at native status/rule level; automatic recovery remains unimplemented and unaccepted.

**Helper is an explicit experimental control:** A1 and A2 both used helper ON with the same STUN-only zero16/repeats=2 profile and Telegram all-port UDP capture. The GUI `unknown` action changed; helper parameters did not. Keep that helper baseline fixed for the next series, verify it before/after each trial and record any later helper change as a separate experiment. [Commands and configuration ownership](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md#configuration-commands-and-parameter-ownership) · [per-trial matrix and recording rules](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#telegram_voice-controls-for-every-trial).

**Next boundary:** [START_HERE](START_HERE.md) selects strict helper/candidate baseline verification and RTC/ICMP observability in the existing runner, then a bounded limited-fake-TTL hypothesis relative to A2 on the same OPNsense/ISP route. This changes only the experimental GUI fake action, not the fixed STUN helper. This is planned and untested; no numeric TTL, new runner or appliance change is delivered by this documentation update. Per-step expected results, bounded trial/repeatability criteria and outcome-dependent next actions belong to the [Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md#next-experiment-limited-fake-ttl-planned-not-run). Same-endpoint healthy-route control remains optional causal diagnosis, not a mandatory new exit; existing inventory helper is optional. Repeated Docker media success precedes real-call connection/UDP/sound acceptance and eventual UDP-only integration. Preserve working TCP and the retired status of `192.168.1.140`.

### Durable evidence and current uncertainty

- Historical September 5 `MEDIA_PASS` through the now-retired `192.168.1.140` route belongs to the old laboratory binary/epoch, not the current OPNsense provider path. No current independent working control exists; the third-party upstream `192.168.80.1` is inaccessible.
- The owner reported a fixed-reflector CLI call established through OPNsense `192.168.1.2` on September 22, but positive CLI output and full strategy-to-flow correlation remain unavailable. Do not erase the report or attribute it definitively to reverse fragmentation.
- The qualified current tgcalls source is `efd330ca04f74706024a5abdfb5b41f4e4dd1065`; binary SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; local P2P smoke passed. Later fully correlated reverse and combined fake-fragment runs had correct on-wire output but no reflector replies/media; fakefrag8+original instead had documented local PF real-packet loss.
- **October 2 real Windows → remote Android call:** both clients P2P disabled; owner reported clear, uninterrupted sound. Concurrent owner-supplied UDP-only LAN/WAN PCAPs and before/after counters show 90 identical non-STUN 40-byte UDP requests to one Telegram endpoint, 9 STUN requests to another, all 99 originals byte-identical across NAT, 18 additional zero16 WAN fakes and *zero inbound Telegram UDP*. Voice rule `19000` 0/0→99/6624, exactly 90×68 + 9×56 IPv4 bytes. Current outbound PFIL IPFW→PF confirmed; no hook changes. Actual audible media transport unproven (possibly TCP, not captured). Record **REAL_CALL_AUDIO_REPORTED_GOOD / VOICE_IPFW_CAPTURE_PASS / UDP_MEDIA_NOT_OBSERVED**, NOT `CALL_PASS` or source attribution. [Full owner-PCAP hashes and correlated analysis](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md). The separate TNAS `MEDIA_PASS` gate remains open. The owner's later clarification establishes that Windows **did not use OPNsense as its system-wide default gateway**; it was configured as proxy. Subsequent direct LAN Ethernet frame inspection nevertheless confirms all 99 observed Telegram UDP datagrams were sent to OPNsense's LAN MAC (independently identified using DNS replies from `192.168.1.2`) and forwarded/NATed by its WAN. The audible transport of that early call remains unmeasured. The subsequent seven controlled calls below completed the historical route/capture follow-up; no new per-candidate human call is requested.
- **October 2 seven-call controlled route follow-up:** Windows `192.168.1.107` used **only default IPv4 gateway `192.168.1.2`**; owner reports Telegram itself connected but all seven voice calls (#2–#8) failed. Fourteen independent LAN/WAN TCP+UDP PCAPs show **390 original outbound Telegram UDP datagrams** (345 repeated non-STUN 40-byte reflector Hellos, 45 STUN requests), all matched by payload byte-for-byte after OPNsense NAT, **90** extra 16-byte STUN fakes and **zero inbound Telegram UDP** in these capture windows. Concurrent LAN TCP differed (direct Telegram TCP/80 in #2–4; local Squid :3128 in #5; local SOCKS :1080 in #6–8), while WAN parent TCP remained active. The specific client application/proxy attribution of these TCP flows was not independently captured. Restoring the **other preferred Windows default `192.168.3.140`** led to **owner-reported established voice calls**, but no paired *successful-route PCAP* or exact per-call Telegram proxy setting was included; do not conclude UDP media/pass or a provider-specific root cause. [Exact A/B route transcript, counts, timestamps and private-PCAP hashes](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md). **Optional causal diagnostic:** capture a successful alternate-gateway call only if separately needed; the separate fixed-reflector `MEDIA_PASS` and formal UDP `CALL_PASS` remain open.
- **Checksums independently validated for the October 2 seven-call WAN captures:** all **390 matched UDP originals** and all **90 16-byte WAN STUN fakes** have **valid recorded IPv4 header and UDP post-NAT pseudoheader checksums** (480/480 for each). The original LAN datagrams were also valid. No captured local UDP checksum corruption explains these **unfragmented** failed attempts; this neither proves upstream delivery nor settles why Telegram replies are absent. [Complete per-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- **October 2 newer, independently timed Windows Telegram Desktop WebRTC debug attempt:** owner reports OPNsense `192.168.1.2` exclusively as default gateway, no Telegram app proxy, voice call still did not establish an encrypted connection. Private `last_call_log` covers **16:16:44–16:17:04**, demonstrates received bidirectional app signaling and remote relay candidates, correct-NIC reflector probes/TURN request dispatch **without any confirmed usable ICE pair/remote DTLS handshake**, then `NativeNetworkingImpl timeout 20011 ms`. Failures `10051`/`10049` occur on secondary Windows TnasOnline and iSCSI NIC candidates, not the correct NIC; do not confuse `DTLS setup complete` during remote configuration with actual secured media. The separately uploaded later main-log copy used by that report starts only **16:27** and cannot be combined with the earlier call timeline. An original earlier copy matching the 16:16 attempt is separately identified by SHA-256 in the October 5 source review above. [Sanitized event sequence and original private SHA-256s](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). The absence of matching same-call PCAP means this strengthens, but cannot be byte-correlated to, the earlier seven-call zero-reply signature. Alternate-route capture is optional for separate causal analysis, not the next strategy-screening task; approved UDP gates remain open.
- October 1 `telegram_voice` was ON with 14 managed table entries and STUN-only `stun-zero-fake-repeats-2`. It intercepted 60 packets, emitted 60 valid unchanged non-STUN 40-byte Reflector Hellos, received no WAN replies, and the reflector CLI returned exit 1 with both peers `Reconnecting`. The current helper does not transform this Hello; voice success is **not** verified.
- September 30 and October 1 LAN HTTPS and SOCKS5 HTTP/HTTPS tests passed through Squid to external parent `185.203.117.88:33128`. Additional October 1 owner verification after the TNAS HTTPS route correction again obtained `HTTP=200` and a matching Squid `FIRSTUP_PARENT` tunnel. These are lab-only TCP facts. The retained TNAS reflector/HTTPS routes through `192.168.1.2` are lab routes, not product defaults.

Detailed protocol research and current oracle: [Telegram UDP research](research/TELEGRAM_VOICE_UDP.md), [Telegram Voice emulation architecture](architecture/TELEGRAM_VOICE_EMULATION_LAB.md). Current testbed TCP/route recovery: [laboratory traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md). Results and archive identities: [September 23–October 1 evidence](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md); [original positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md). Preserve the successfully applied lab configuration and backup artifacts; do not change running TCP services merely to align the documentation.

**2026-10-01 owner-live lab inventory closed for the currently measured configuration.** [The operations runbook](architecture/TELEGRAM_LAB_OPERATIONS.md) records GUI and effective file ownership, Squid/sing-box RC/configd startup, the complete OPNsense→TNAS SSH setup, verified manual route script and precise commands, and the Voice ON-after-reboot failure mode. [The dated measurements](verification/evidence/2026-10-01-telegram-lab-owner-live-inventory.md) preserve full owner-provided sing-box GUI JSON and current file fingerprints. The OPNsense console is **csh**, and the local SSH binary is **`/usr/local/bin/ssh`**; default console commands must respect this. The owner deliberately rejected TNAS route Cron/configd and Docker autostart: both routes are checked/restored **manually** through the tested OPNsense SSH script after a TNAS reboot, and the container is started on demand. At this epoch Telegram Voice is **requested=on/effective=on**, 14 entries/rule 19000, but this experimental state is ephemeral and reverts to OFF after an OPNsense reboot unless explicitly re-enabled. Native Zapret boot startup alone does **not** preserve Voice ON.

**Latest owner source-audit/boot decision:** [GUI versus helper, IPFW capture and PF/NAT order](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) are now documented. Helper Voice and GUI use the **same dvtws2 process and managed Telegram dataset**, but the separate Voice rule matches all UDP ports **to Telegram IPs**; ordinary GUI port rules match listed ports **to any WAN IP**, and adding `--filter-udp=*` in GUI cannot produce equivalent capture under current numerical-only extractor. No repeated encryption; current STUN-only Voice does not transform non-STUN Reflector Hello. The owner explicitly forbids **Cron/periodic telegram-voice-enable**: any lab workaround must be **once at OPNsense startup after normal Zapret2 is ready**, and the October 8 approved native persistent-page redesign is now the selected implementation path. The October 7 before/after snapshots again show IPv4 output IPFW→PF unchanged; the measured reboot/manual restoration is recorded above. **No automatic boot fix has been deployed or tested by this documentation change.**

**Lab permanence is an approved requirement but not a verified result.** October 1 LAN HTTPS and SOCKS TCP parent checks passed, but router-origin Telegram automatic selection, SOCKS UDP, Squid/sing-box regenerated state, **automatic OPNsense Voice-helper ON recovery**, alias synchronization and **the selected manual route-script procedure after an actual TNAS reboot** have not been jointly accepted after reboot. TNAS route auto-recovery and Docker autostart are **not** required by the owner. Manual recovery commands are a contingency, not successful automatic reboot acceptance. Retain the working TCP configuration while making supported lab persistence changes in a separately controlled test.

Published Telegram PoC identity stays `VERSION=0.5.0`, `PLUGIN_REVISION=3`; Draft PR #328 introduces the separate unreleased `0.5.1_1` development identity. Remote `_4` remains unpublished and paused. The owner-approved product behavior is **planned**, not yet implemented or qualified.

**2026-10-03 A2 superseding outcome:** The owner's first Docker A2 run passed unique saved/effective A2, Voice ON/table14, owner TNAS route guard and pinned host-network Docker. Independent LAN/WAN PCAP analysis: 60 genuine 40-byte Hello preserved after NAT; 120 zero16 fakes with **120/120 valid UDP checksums** precede every original in exact 60/60 triplets; no pinned reflector replies on either interface, zero capture drops. Both peers Reconnecting, BWE zero, CLI exit 1. **A2 CONFIG_PASS/WIRE_OK/NO_REPLY_UNKNOWN; MEDIA_PASS OPEN**. Relative to A1, removing only `:badsum` proved insufficient in this epoch; do not infer provider drop stage or reflector readiness. [Measured A2 evidence](verification/evidence/2026-10-03-docker-a2-valid-checksum-fakes-no-reflector-reply.md). A fresh healthy same-endpoint control is optional causal diagnostic; it is not an independent-UDP-exit prerequisite before any further controlled same-ISP Zapret2 research. Retired `.140` prohibited; keep TCP/proxy and A2 lab baseline unchanged.
## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)
- [`v0.4.x archive`](history/archive/v0.4.x.md)

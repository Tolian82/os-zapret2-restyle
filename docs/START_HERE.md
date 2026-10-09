# os-zapret2-restyle — START HERE

**Voice full cutover mock (не runtime):** `voice_cutover_coordinator.py` моделирует фазы checked old state → durable prepared/mutating → one-engine/tree/IPFW/supervisor → Config save → committed → verified cleanup или полный rollback; по умолчанию блокирует выполнение, работает только с injected test adapters. `voice_cutover_journal.py` отдельно пишет ограниченный, приватный, fsync'ed whole-runtime intent и при перерыве выдаёт manual review без автоматических kernel-команд. Тесты проверяют отказные точки и actual on-disk journal, Linux/FreeBSD CI и package contents. **НЕ включать GUI Apply и не публиковать пакет по этому факту:** реальный Config/lifecycle/PoC/boot переход ещё не подключён.


**Voice one-engine handoff preflight (draft):** `voice_handoff_preflight.py` сопоставляет Voice/ordinary/реальный `dvtws.args`/IPFW-plan в памяти, проверяет SHA256, managed targets, ровно один divert, портовый вывод production `ports.sh`, WAN и отсутствие старого PoC. CI Linux и FreeBSD 15 проверяет реальные `generator.sh`/`ports.sh` с sandbox-артефактами; никаких live-мутаций. FreeBSD python3 alias используется только в test-private PATH. Apply остаётся disabled, изоляция legacy и crash rollback ещё не реализованы.


**Voice Targets interoperability:** `test-voice-targets-integration.py` теперь проверяет пять реальных managed IPSET через штатный `targets_prepare_managed()` и Voice compiler с отрицательным случаем для CIDR host bits. Это offline regression, не интеграция Apply или медиатест.

**Voice staging safety:** в Draft PR #328 Voice ON теперь отклоняется до `firewall_prepare` в сервисном входе и до `orchestrator_cleanup_runtime` при старте. Глобальный OFF остаётся допустим. Реальный `generator.sh` протестирован вместе с offline Voice+Strategies+IPFW планом (без запуска службы); source XML/managed IPSET/ordinary traffic повторно сверяются по SHA256 до публикации кандидата и не могут быть symlink. Тесты `test-voice-staged-runtime-guard.sh`, `test-voice-generator-interop.py`, `test-voice-release-stage.py` включены в CI. Native Voice Apply всё ещё disabled; legacy PoC и live runtime не заменены.


**Voice Apply preparation (Draft PR #328):** `Api/VoiceApplyCandidate.php` строит только нормализованный будущий Voice overlay, сохраняя OFF-черновики и все unrelated поля. Он используется уже в read-only Validate, но не пишет config.xml и не запускает runtime. До live cutover пять generated `VOICE_*_REQUESTED` проходят через `config_voice_staged_only_guard`: сохранённое ON или невалидное значение вызывает раннюю ошибку legacy build, а OFF оставляет обычные Strategies. При окончательном cutover временный guard заменить общей транзакцией, не выпускать его как готовую поддержку Voice.


**Voice GUI concurrency update:** Draft PR #328 содержит `VoiceController.loadAction`, возвращающий модель и fingerprint из одного чтения под Config lock. `VoiceController.validateAction` требует тот же fingerprint, отвергает stale Voice/Strategies/shared IPSET, проверяет whitelist и native STUN. Применение/сохранение не включено; в дальнейшем Apply обязан повторить проверку под lock перед live-транзакцией. CI включает PHP model-stub проверку и GUI контракт.


**Voice GUI Validate staged:** в PR #328 добавлен read-only endpoint `/api/zapret/voice/validate`, отдельная кнопка Validate и RU/EN локализация ошибок. Он проверяет несохранённую конфигурацию (IPSET, STUN, пересечения), не пишет `config.xml` и не меняет dvtws2/IPFW. PHP-проверки и сопоставление с авторитетным Python compiler добавлены в CI. Кнопка Apply остаётся disabled: cross-runtime rollback/legacy migration/boot/owner-live ещё OPEN. Не устанавливать как production voice feature только на основании CI.


**Migration staging:** a separate read-only `voice_migration_plan.py` distinguishes clean install, explicit native ON/OFF, still-running old PoC, lost `/var/run` marker and ambiguous legacy state. No automatic promotion of temporary ON to persistent ON; old builder/marker/runtime is not removed until verified cutover. The read-only Voice IPFW status is available in RU/EN GUI, but the save/apply endpoint is still absent.


**Draft PR #328 дополнен:** native FreeBSD IPFW adapter (read-only by default), read-only Voice status/configd/API in RU/EN GUI, unordered IPv4 table comparison, extended bounded fake parser, FreeBSD package regression. **Это не рабочий Voice Apply**: orchestration, старая PoC-миграция, lock-held journal/live runtime и reboot acceptance ещё впереди. Сначала смотреть exact-head CI, затем проверять безопасный one-engine cutover без второго пути ON.


- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules:** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules:** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules:** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules:** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-10-09
**Current handoff identity:** `v0.5.1_1` — active Draft PR #328 for «Передача голоса»; model/GUI/shared target generation staged, Apply and runtime migration incomplete, media gates open.

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.5.1` (**Draft PR #328, not merged**);
- `PLUGIN_REVISION=1` (**development candidate, not published**);
- published testing candidate: `v0.5.0_3` / `os-zapret2-restyle-0.5.0_3.pkg`;
- testing source/tag target: `34adca978b3b6769972591872209c166ec9c6eb6`;
- testing package SHA-256: `b88accee3fc7510e3b54ed65bb525be65c79aba8e5e02193435b431a3a4c253f`;
- testing publication workflow: `33536081824`, PASS on attempt 2;
- last owner-live accepted testing corrective: `v0.5.0_2` / `os-zapret2-restyle-0.5.0_2.pkg`;
- current stable Web/pkg release remains `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- stable package SHA-256: `38777bdf59f93e6cee596e431d01fef4b3a73a41842d93e809ba94fd310a5bce`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository remains on `_1`; neither `_2` nor `_3` promoted it.

Testing publication evidence: [`verification/evidence/testing-publications/v0.5.0_3.md`](verification/evidence/testing-publications/v0.5.0_3.md).

Historical 2026-09-02 Zapret2 runtime pin: [`verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md`](verification/evidence/2026-09-02-telegram-voice-ipfrag-runtime-pin.md).

Phase C companion build/runtime evidence: [`verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md`](verification/evidence/2026-09-04-telegram-voice-companion-build-runtime-pass.md).

Historical 2026-09-05 fixed-reflector control and host-topology evidence: [`verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md`](verification/evidence/2026-09-05-telegram-voice-fixed-reflector-control-pass.md).

Owner-live corrective evidence: [`verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md`](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md).

Stable release evidence: [`verification/evidence/2026-08-16-v0.5.0-release-publication.md`](verification/evidence/2026-08-16-v0.5.0-release-publication.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted product boundary

The completed `v0.4.x` line and the post-release `_2` corrective are accepted owner-live unless fresh evidence contradicts them.

Key facts include:

- Model C is the only normal production Stage-60 runtime;
- Strategy Lab supports domain and canonical IPv4 targets;
- optional Host/SNI keeps service identity separate from a fixed IPv4 destination;
- fixed-IP final profiles include `--ipset-ip=<target>` and exact replay;
- authenticated/intercepted HTTP `4xx`/`5xx` remains valid DPI-path evidence;
- bare IPv4 TLS identity failure reports `PARTIAL` + Host/SNI guidance;
- bare-IP QUIC without Host/SNI is skipped before execution;
- Host/SNI QUIC performs real fixed-IP hostname-verified attempts;
- Generic UDP remains independent;
- Enable QUIC defaults OFF, is explicit/persisted, and its reload/revisit persistence is owner-live accepted;
- Strategy Lab cleanup/restoration remains mandatory;
- Settings Apply validation/guards and post-Apply service-state correctness remain accepted;
- Strategy Lab owns its visible Generic UDP file-picker labels, so RU/EN presentation follows OPNsense language rather than browser/OS native file-input chrome;
- the owner verified the `_2` localized picker and file-selection path on the live appliance.

## Closed `v0.5.0_2` corrective

The English localization leak (`Выбор файла` / `Не выбран ни один файл` rendered by the browser/OS) was corrected by hiding the visible native file-input chrome and rendering Laboratory-owned picker text.

The source correction, full CI/FreeBSD-15 qualification, testing-package publication, publication-record tail and focused owner-live check are complete. The owner confirmed that `v0.5.0_2` works as intended. No further source change belongs to this scope.

## Telegram Voice UDP — current owner-approved goal

The October 8 owner decision approves implementation of a native **«Передача голоса»** page now: menu **«Стратегии» → «Передача голоса» → «Лаборатория»**, existing Strategies visual design, WAN at top, five service checkboxes/parameter textareas and separate shared IPSET fields for Telegram / Discord / X (Twitter) / SIP (VoIP) / Custom. No LAN selector, local-UDP checkbox or boot-restore checkbox. Local matching UDP is always in scope; saved selected state always restores through normal Zapret2 startup, respecting global service OFF. Non-STUN stays in Strategies; one dvtws2.

**Primary implementation specification:** [VOICE_TRANSMISSION_GUI.md](architecture/VOICE_TRANSMISSION_GUI.md). It owns layout, current-versus-target behavior, native parameter contract, shared data, WAN limitations, migration/dismantling, source map and acceptance steps. [REQUIREMENTS](REQUIREMENTS.md) and [ROADMAP](ROADMAP.md) now distinguish configuration development from qualification of a working voice strategy. The old restriction delaying a separate page until MEDIA_PASS/CALL_PASS is superseded; those gates still qualify a claimed working Telegram preset.

The practical goal remains reproducible real Telegram connection through OPNsense `192.168.1.2` and the SAME ISP, then sound. Preserve existing PF/Squid/sing-box TCP/TLS → parent `185.203.117.88:33128`. These proxies, PF redirects/NAT, routes and the Docker oracle remain independent laboratory infrastructure. No TCP/proxy integration, alternate UDP exit or embedded voice-testing controller is approved.

The current helper is still transient and hard-coded. The [helper runbook](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md) is mandatory current-implementation reading. October 7 measured ON→OFF after OPNsense reboot, then manual ON/table14/rule recovery; GUI A2 survived. New persistent behavior is not deployed. Until migration is qualified, use the existing measured recovery/preflight, not assumed GUI persistence. [Evidence](verification/evidence/2026-10-07-telegram-voice-reboot-and-manual-recovery.md).

The [operations runbook](architecture/TELEGRAM_LAB_OPERATIONS.md) owns live Squid/sing-box/SSH and manual TNAS routes. TNAS route restoration remains manual via the existing OPNsense SSH script; Docker is on-demand with `restart=no`. No Cron or Docker autostart. The [three-origin policy](architecture/TELEGRAM_TRAFFIC_POLICY.md) retains unresolved router-local TCP selection, SOCKS UDP and full laboratory reboot qualification; this page does not silently close those gaps.

## Verified evidence and limitations

- The historical September 5 `MEDIA_PASS` used the old binary and now-retired `192.168.1.140` route, **not** OPNsense; do not restore that route as a control.
- The owner reported an established reflector CLI call through OPNsense on September 22. Its positive CLI output and exact matching strategy/profile/flow are not yet correlated. Keep the positive observation without declaring reverse8 proven.
- Existing ordered8, reverse8/16/24/32 and fakefrag8+reverse24 local wire experiments emitted their documented correct packets but did not deliver a correlated current `MEDIA_PASS`. Do not repeat the completed fragment sweep by inertia. The fakefrag8+original run had a separate local PF real-packet loss; tee changed ordering.
- The latest October 1 ON-helper control intercepted 60 Telegram UDP packets and sent 60 valid 40-byte **non-STUN** Reflector Hellos through the WAN with zero observed replies. Both peers stayed `Reconnecting`, BWE was zero, exit 1. The current STUN-only `stun-zero-fake-repeats-2` helper does not modify that Hello; ON/interception is not voice success.
- **October 2: real P2P-disabled Windows → remote Android call had good owner-reported sound, but two correlated owner-supplied UDP captures show 90 unchanged 40-byte Hello + 9 STUN originals outbound, 18 extra zero16 fakes on WAN, and *zero inbound Telegram UDP*. IPFW Voice rule counters increased exactly 99 packets / 6624 bytes matching those originals. This is a successful audible user observation and verified Voice *interception*, NOT proven UDP voice or formal `CALL_PASS`. TCP/media transport was not captured. [Full dated PCAP/hash analysis](verification/evidence/2026-10-02-real-telegram-windows-android-p2p-disabled-call.md).** **Owner's gateway correction and independent PCAP recheck:** Windows default gateway was **not** OPNsense (configured as proxy), but all 99 observed Telegram UDP Ethernet frames went to the exact MAC that answered from `192.168.1.2`, then exited OPNsense WAN. Do not infer the route of unobserved media/TCP or assume all Telegram UDP was forced through OPNsense. That historical follow-up was completed by the seven controlled calls below; it is not a new per-candidate real-call instruction.
- **October 2 follow-up: owner controlled Windows' IPv4 default via OPNsense `192.168.1.2`; seven real voice calls (#2–#8) connected to Telegram but did not establish.** Independently parsed 14 concurrent TCP+UDP LAN/WAN PCAPs show **345 unchanged non-STUN 40-byte Hellos + 45 STUN originals**, all **390** NAT-forwarded on OPNsense WAN; **90** extra zero16 fakes and **zero captured incoming Telegram UDP** across all seven. LAN concurrently showed direct Telegram TCP/80 (calls 2–4), local Squid :3128 TCP (call 5) and local sing-box SOCKS :1080 TCP (calls 6–8); WAN Squid parent was active. These patterns alone do not identify per-process media or the source of any filtering. After returning Windows' preferred IPv4 default to `192.168.3.140`, the **owner reported calls established**; this positive route control lacks a captured successful-call media trace and may differ in app proxy settings. [Full dated seven-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md).
- **Follow-up packet-integrity check of calls #2–#8:** independent IPv4-header and post-NAT UDP-pseudoheader checksum validation passed for **all 480 captured outbound Telegram UDP datagrams** (390 originals + 90 fakes); there is no observed WAN checksum corruption in these **unfragmented** real-call packets. This does not prove packets reached Telegram or explain missing replies; use the [dated seven-call evidence](verification/evidence/2026-10-02-seven-real-calls-opnsense-versus-other-gateway.md), not September's fragment checksum behavior, when assessing this series.
- **October 2 newer standalone Telegram Desktop debug call (16:16) over the reported OPNsense-only default with no Telegram proxy:** private WebRTC log confirms *bidirectional app signaling/Opus/remote ICE candidate reception* but only outbound TURN/Reflector attempts on the intended `192.168.1.x` NIC, no established usable ICE/media path logged and `NativeNetworkingImpl timeout 20011 ms`. Windows also exposed TnasOnline and 192.168.192.x candidates, whose failed TURN sends are secondary-adapter errors, not evidence the proper NIC failed locally. A separately uploaded Telegram main startup log begins **11 minutes later**, not the same call. [Dated sanitized evidence/2 private-log hashes](verification/evidence/2026-10-02-telegram-desktop-webrtc-ice-timeout-on-opnsense-gateway.md). No matched same-call PCAP; preserve earlier packet-level diagnosis. A successful alternate-route capture is optional causal diagnosis, not the current next task. The original earlier main-log copy is distinguished in the October 5 source review below.
- October 1 LAN HTTPS and SOCKS5 TCP/443 via Squid and the external parent have passed. Additional owner verification on October 1 again confirmed transparent TNAS HTTPS `HTTP=200` and Squid `FIRSTUP_PARENT`. These are **retained lab facts**, not new plugin requirements or proof of UDP voice.

Evidence: [September 22 positive observation](verification/evidence/2026-09-22-telegram-voice-reverse8-call-observation.md), [September 23–October 1 results](verification/evidence/2026-10-01-telegram-traffic-policy-and-voice-control.md), [current media oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [current laboratory proxy and route recovery](architecture/TELEGRAM_TRAFFIC_POLICY.md), and [protocol research](research/TELEGRAM_VOICE_UDP.md).

## Draft implementation progress (PR #328)

The new menu/controller/form/view/model and RU/EN guidance are staged, with all five service switches default OFF. The shared Telegram IPSET remains `hostlist.telegramips`; four additional datasets now have staged backend registry/storage/normalizer/template entries. A read-only persistent Voice config.xml exporter, fail-closed STUN profile compiler, inert candidate-release staging with exact managed IPSET/WAN checks, single-engine traffic merge helper, declarative IPFW capture planner plus a mock-tested IPFW ownership/rollback core and durable private ownership/intent ledger and mock-only activation ordering with read-only restart triage exist (production adapter, lifecycle lock integration, automatic recovery and boot remain unwired) with a temporary narrow, tested option allowlist and rejects a different WAN until true one-engine isolation is proven. **Strategies Apply is now explicitly scoped and rejects a stale shared Telegram IPSET baseline (Voice side still pending). No Voice configuration Apply, runtime multi-service generator, replacement of old PoC marker, destination-scoped IPFW, migration or boot recovery is qualified.** Continue on this same Draft PR. Current stable remains `v0.5.0_1`; latest published experimental testing candidate remains `v0.5.0_3`. Do not install or merge WIP `v0.5.1_1`.

## Actual current assignment — implement the approved Voice page

After the mandatory Level-1 documents, read [the complete Voice page specification](architecture/VOICE_TRANSMISSION_GUI.md) and [current helper implementation/reference](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). For live operation or laboratory migration also read the operations/campaign documents linked above; do not reconstruct old experiments before starting the page.

1. Resolve current `main`, inspect the named MVC/model/API/backend files, and define the concrete model/native allowlist/shared IPSET and migration contract. Verify the independent-WAN boundary with the single divert engine; never silently change the ordinary WAN.
2. Build the native page and menu, then replace PoC-only request/profile generation with persistent service profiles and transactional scoped IPFW lifecycle. Keep compatible Telegram configctl actions on the same authority; preserve ordinary non-STUN strategies.
3. Qualify input validation, overlapping profiles, one-engine operation, local/forwarded UDP, failure/rollback, saved OFF/global OFF and reboot restoration. Complete GitHub/CI/package work under the normal project rules; owner-live results are a separate gate.

The prior `0.5.0_3` handoff saved documentation only. Development is now on `0.5.1_1` in a Draft PR. No new Voice Apply, complete boot behavior or media PASS is claimed; no owner appliance settings were changed. Do not merge the old unpublished `_4` fragment branch as this feature.

**Retained research queue:** [the Docker-first campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md) still requires RTC/ICMP/full-profile/cleanup tooling before a distinct limited-fake-TTL series (at most four initial values; none selected yet). This does not block implementing the page. Migration starts a documented new baseline; historical A1/A2 kept helper ON/fixed and both remain `WIRE_OK / NO_REPLY_UNKNOWN`. Do not repeat their unchanged negative tests or the closed fragment sweep by inertia. Candidate-action OFF is not whole-helper disable.

After a qualified new baseline, seek a library-accepted reflector reply, both-peer sustained UDP `MEDIA_PASS`, repeatability/action-only control, then one real remote P2P-disabled Windows/Android `CALL_PASS`. Actual client destinations/profiles must be checked. Retired `192.168.1.140` remains excluded, and access to third-party `192.168.80.1` is not required. No alternate-egress prerequisite or per-candidate human calls.

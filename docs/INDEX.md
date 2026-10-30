# os-zapret2-restyle — индекс текущей работы и истории

## Level 1 — обязательное восстановление контекста

Читать по порядку через EOF:

1. [AGENTS](../AGENTS.md)
2. [START_HERE](START_HERE.md)
3. [PROJECT_STATE](PROJECT_STATE.md)
4. [DOCUMENTATION_RULES](DOCUMENTATION_RULES.md)
5. [PROJECT_PRINCIPLES](PROJECT_PRINCIPLES.md)
6. [CHAT_RULES](CHAT_RULES.md)
7. [GITHUB_PUBLICATION](GITHUB_PUBLICATION.md)
8. [ROADMAP](ROADMAP.md)
9. Этот INDEX, затем только документы текущей задачи из START_HERE.

Уже прочитанные неизменные документы повторно не загружаются в рамках одного состояния repository; применяются существующие правила чтения. Архивы и lab runbooks не включены в автоматический cold start.

## Level 2 — FIRST PRIORITY: global Exclude IPSet and IPv4/IPv6 dual-stack

- [Approved current technical specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md) — 24 binding requirements and 24 acceptance criteria, one global IP exclusion for Strategies/Voice, domain-only Exclude Domains, and strict `/0` prohibition for all user IP lists including Voice.
- [Current staged, per-file implementation plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md) — stages 0–8, 160 file assignments covering 132 unique paths, entry/exit gates, Stages 1–5 source/CI qualified; Stage 5 installed FreeBSD15 IPFW acceptance OPEN. Voice/P2P redesign remains deferred.
- [Current handoff](START_HERE.md) and [current state](PROJECT_STATE.md) — published and owner-installed testing `v0.6.1_12`; running shared runtime and all eight profile Exclude references are confirmed, while installed packet-level A07/A08, IPv6 WAN and Voice media remain OPEN. Python interpreter unification is **cancelled in the current dual-stack technical specification** and requires a new, separate future technical specification; stable `v0.6.0_1` unchanged.

- [v0.6.1 development-stage candidate record](releases/v0.6.1.md) — historical testing-package records and publication evidence for the ongoing development line; current owner-installed identity is `_12`, with no stable `v0.6.1` release authorization.

- [Published `v0.6.1_8` GUI correction testing package evidence](verification/evidence/testing-publications/v0.6.1_8.md) — exact source/tag, SHA-256, FreeBSD15 package and no stable repo promotion; owner GUI acceptance pending.
- [Published `v0.6.1_7` correction testing package evidence](verification/evidence/testing-publications/v0.6.1_7.md) — exact tag/source, FreeBSD15 asset, SHA-256 and no stable repo promotion; owner-installed service startup still OPEN.
- [Published `v0.6.1_6` corrective testing package evidence](verification/evidence/testing-publications/v0.6.1_6.md) — SHA-256, immutable source, FreeBSD15 asset and no stable repo promotion; `_6` owner-installed service startup pending.
- [Published `v0.6.1_5` testing package evidence](verification/evidence/testing-publications/v0.6.1_5.md) — source/tag, asset URL, SHA-256, FreeBSD15 manifest and no stable repo promotion.
- [Stage 5 reviewed single owner baseline checkpoint](verification/STAGE5_WAN_OWNER_REVIEW_CHECKPOINT.md) — one separately authorized pinned IPv4 Ethernet baseline was captured and analyzed on the owner appliance; no actual Lua modification or Exclude effect was proven, the trial authorization is consumed, A07/A08 OPEN.
- [Stage 5 single-phase owner-gated baseline capture lifecycle](verification/STAGE5_WAN_SINGLE_BASELINE_CAPTURE.md) — explicit live opt-in, native owner/route/source-port/DLT/readiness guards, hard deadline and cleanup; no automatic Exclude Apply, no installed A07/A08 PASS.
- [Stage 5 bounded WAN A/B acquisition plan (no execution)](verification/STAGE5_WAN_ACQUISITION_PLAN.md) — two-phase pinned TCP five-tuple filters, explicit source-port and constrained HTTPS argv as **unexecuted** JSON, 13 no-network tests, owner consent and rollback gates still OPEN.
- [Stage 5 offline WAN TCP PCAP five-tuple attribution](verification/STAGE5_WAN_OFFLINE_PCAP_ATTRIBUTION.md) — bounded read-only existing captures, synthetic IPv4/IPv6 tests, exact flow metadata and non-proof classification; no capture, Apply or live Stage-5 acceptance.
- [Read-only Stage 5 WAN A07 target selector](verification/STAGE5_WAN_TARGET_READONLY.md) — existing native inspector, final-profile parser, five Voice IPSET/global Exclude bounds, DNS-only/FIB lookup, potential-only output; actual on-wire A07/A08 and source port remain OPEN.
- [Stage 5 A07 offline A/B/restoration readiness review](verification/STAGE5_WAN_AB_READINESS.md) — read-only review of trusted pinned plan, existing IPv4/IPv6 TCP PCAPs, native owner snapshots and byte-identical restored managed Exclude; eight no-network regression tests; never authorizes GUI Apply or claims installed A07 PASS.
- [Stage 5 native selected-Strategy TCP byte attribution](verification/STAGE5_NATIVE_STRATEGY_ATTRIBUTION.md) — actual upstream HTTP `http_hostcase` IPv4/IPv6 loopback receiver-byte test for baseline, nonmatching/matching Exclude; isolated FreeBSD15.1 only, not owner WAN TLS acceptance.
- [Stage 5 native TLS fake packet attribution](verification/STAGE5_TLS_NATIVE_FAKE_PACKET.md) — upstream fake/badsum, native IPv4/IPv6 exact flow PCAP with global Exclude A/N/B in disposable FreeBSD15.1 CI only, not installed fake/split identity or WAN acceptance.
- [Stage 5 native TLS ClientHello IP-header attribution](verification/STAGE5_TLS_NATIVE_HEADER_ATTRIBUTION.md) — real OpenSSL ClientHello / upstream `pktmod` / native FreeBSD IPv4 TTL+IPv6 Hop Limit on lo0 with exact Exclude control, not WAN approval.
- [v0.6.1_15 isolated native TLS header evidence](verification/evidence/2026-10-30-v0.6.1_15-native-tls-header.md) — exact FreeBSD15.1 CI run and PASS markers, strict owner-installed A07/A08 OPEN boundary.
- [Stage 5 sanitized effective TLS Lua-action profile signatures](../scripts/stage5-tls-profile-signature.py) — source/offline-only production-parser inherited actions and SHA-256 fingerprints for eligible profiles; never selected runtime or A07/A08.
- [Stage 5 non-executing Phase-A TLS eligibility binder](../scripts/stage5-tls-phase-a-offline.py) — accepts existing offline native owner/final argv/HOSTLIST/IPSET/PCAP evidence; never asserts executed Strategy, WAN mutation or installed A07/A08.
- [Stage 5 installed TLS Strategy Phase-A identity and packet-provenance plan](verification/STAGE5_INSTALLED_TLS_PHASE_A_PLAN.md) — read-only source-based four-witness design for actual effective TLS profile, engine selection, flow provenance and proven mutation; NOT a live probe, not A07/A08 or phase-B consent.\n- [Stage 5 installed WAN same-endpoint Exclude A/B acceptance protocol](verification/STAGE5_INSTALLED_WAN_AB_PROTOCOL.md) — designed but **not executed**; separate A07/A08, same pinned endpoint/Host/SNI/flow, packet-level proof, owner-approved normal GUI Apply/restore, fail-closed and no silent Config/IPFW mutation.
- [Stage 5 installed OPNsense read-only evidence procedure](verification/STAGE5_INSTALLED_OPNSENSE_READONLY.md) — current owner-installed `0.6.1_12` one-shot read-only IPv6 eligibility preflight, existing native Voice inspector and historic two-snapshot counter comparison. Neither can close actual WAN packet or Voice acceptance.

## Level 2 — current v0.6.x full release

- [v0.6.0 full release plan](releases/v0.6.0.md) — authorized second-component rollover and package/Pages gates.
- [v0.6.x current ledger](history/current/v0.6.x.md) — current chronology.
- [v0.5.x archived final-state snapshot](history/archive/v0.5.x.md) — prior state preserved.

## Level 2 — historical v0.5.x Remove Additional Resources

- [Approved remove specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) — 26 October binding revision: actual native Strategies+Voice GUI checks, Stop→temporary quarantine→real common Apply/Start→success or rollback; Exclude Domains untouched and no Jail.
- [Approved staged remove plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md) — owner closed Stage 11 with bounded evidence; Stage 12 README, then separately authorized Stage 13 stable release.
- [Owner-console native Remove acceptance protocol](verification/REMOVE_NATIVE_OWNER_ACCEPTANCE.md) — historical R0–R4 and `_44` API removal evidence; concrete Stage 7 `_45` RU/EN/Advanced/F5/no-op/real Remove acceptance checklist (owner tests pending).
- [Owner-live R0/R1 Remove evidence on v0.5.9_37](verification/evidence/2026-10-26-v0.5.9_37-remove-r0-r1-owner-live.md) — exact installed package/HEAD, 73-resource witness, real Stop/quarantine error, preserved inode metadata and SHA-256, restored IPFW/Config/status.
- [Owner-live R2 Remove interruption/recovery](verification/evidence/2026-10-26-v0.5.9_37-remove-r2-owner-live.md) — 130, `restarting`, guarded `RESTORED`, exact inode/Config/Git/IPFW parity; uncovered GUI status versus inventory inconsistency.
- [Installed `_44` production Remove negative API evidence](verification/evidence/2026-10-27-v0.5.9_44-owner-negative-api-r3.md) — three HTTP 200 structured rejections, 73 extra Lua/BIN intact, service running, saved Config unchanged; positive Remove still gated.
- [Installed `_44` positive production Remove acceptance](verification/evidence/2026-10-27-v0.5.9_44-owner-positive-api-r4.md) — owner-approved real removal of 73 files, correlated worker completion, zero-extra plan, new native owner healthy, saved Config and scoped IPFW unchanged.
- [Owner `_45` GUI dual-spinner defect](verification/evidence/2026-10-27-v0.5.9_45-gui-remove-spinners-r5.md) — GUI Install/Remove reported successful; Install spinner incorrectly spins during Remove; `_46` candidate fixes UI only.
- [Published `_46` testing package evidence](verification/evidence/testing-publications/v0.5.9_46.md) — verified FreeBSD 15 asset, source/tag, SHA-256 and publisher workflow, no stable repo promotion.
- [Installed `_46` owner GUI Install→Remove R6](verification/evidence/2026-10-27-v0.5.9_46-owner-gui-remove-r6.md) — new operation/native owner, 0 resources, RUNNING, unchanged Config/firewall; Stage 8 separately pending.
- [Owner `_46` Stage 8 cache/Full Help and Job inventories R7](verification/evidence/2026-10-27-v0.5.9_46-stage8-inventories-r7.md) — 6/46 current upstream-only, 25/100 historical preserved snapshots, service running; repeat Install pending.
- [Owner `_46` Stage 8 repeat Install R8](verification/evidence/2026-10-27-v0.5.9_46-stage8-repeat-install-r8.md) — optional 19 Lua/54 BIN restored, cached 25/100 provenance correct, native owner/Config/IPFW unchanged; visual Full Help colors pending.
- [Owner `_46` Stage 8 restored Full Help R9](verification/evidence/2026-10-27-v0.5.9_46-stage8-restored-full-help-r9.md) — owner confirms green upstream and blue optional filenames in Lua/BIN columns; core Stage 8 happy path accepted.
- [Stage 9 v0.5.9_46 source/fault-path audit](verification/evidence/2026-10-27-v0.5.9_46-stage9-fault-path-audit.md) — existing regression matrix documented; stale Help cache after successful mutation and failed refresh identified for bounded fail-closed repair.
- [Stage 9 `_47` fail-closed Help cache source](verification/evidence/2026-10-27-v0.5.9_47-cache-invalidation-source.md) — pre-actor cache retirement; native workflow unchanged; source CI and owner acceptance are separate.
- [Verified published `_47` testing package](verification/evidence/testing-publications/v0.5.9_47.md) — exact merged source/tag, FreeBSD 15 asset checksum and temporary publisher record; owner-installed read-only R10 PASS; separate GUI/live fault gate pending.
- [Installed `_47` owner read-only baseline R10](verification/evidence/2026-10-27-v0.5.9_47-owner-installed-read-only-r10.md) — 19/54 resources and cache 25/100, native RUNNING with previous owner and 4 identical Config/firewall fingerprints; no post-upgrade resource transaction.
- [Owner `_47` Strategies Full Help F5 persistence R11](verification/evidence/2026-10-27-v0.5.9_47-owner-full-help-f5-r11.md) — Help remains after browser refresh on installed `_47`; color/columns and live mutation fault are separate proof gates.
- [Owner `_47` Full Help color/column R12 and Stage 11 evidence review](verification/evidence/2026-10-27-v0.5.9_47-owner-help-colors-stage11-review-r12.md) — after F5, left Lua/right BIN and green upstream/blue extra confirmed; unrun negative live scenarios identified without new mutation.
- [Owner final Stage 11 acceptance R13](verification/evidence/2026-10-27-v0.5.9_47-stage11-owner-final-acceptance.md) — explicit closure with named unrun-live limitations; authorizes README Stage 12 but not stable release.
- [Published `_45` testing-package evidence](verification/evidence/testing-publications/v0.5.9_45.md) — immutable exact source/tag, FreeBSD 15 amd64 `.pkg`, SHA-256 and GitHub publisher; stable repo not promoted.

## Level 2 — active M0–M7 completion and acceptance

- [Owner-approved completion plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) — bounded milestones, acceptance gates, and no speculative Git provenance expansion.
- [Additional Resources normative technical specification](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) — normal update, exact-set reconciliation and preserved fail-closed recovery; new clean-reinstall tooling explicitly cancelled.
- [Single acceptance board](verification/EXTRA_RESOURCES_ACCEPTANCE.md) — actual candidate, evidence, pass/fail status, blocker and next action.
- [Final owner acceptance and stable release authorization](verification/evidence/2026-10-24-v0.5.8-owner-acceptance-and-release-authorization.md) — accepted H1; M6 owner-closed without a cold boot; M7 exact delivery authorization.
- [v0.5.8 stable release preparation and verification](releases/v0.5.8.md) — exact `0.5.8_1` candidate, included features and bounded release checks.
- [Historical cancelled clean-plugin repair proposal](verification/EXTRA_RESOURCES_CLEAN_REPAIR_GATE.md) — superseded by owner decision 24 October 2026; not active or required for release.

## Level 2 — urgent owner-proven cold-IPFW lifecycle correction

- Source `v0.5.7_30`: safe cold IPFW module loading with `kenv` default-allow staged and verified **before** `kldload ipfw`; strict cold owner inspector process/module evidence. Prior installed stable `_1` rescue achieved RUNNING after manual safe IPFW/ipdivert bring-up via hypervisor console; not evidence of `_30` installed boot acceptance. No new release approved. See [handoff](START_HERE.md) and [current state](PROJECT_STATE.md).

## Level 2 — current owner-directed implementation: Additional Resources

- Stage 4/GUI/upstream gate `v0.5.7_29`: dynamic BIN/Lua, correlated GUI receipts and durable upstream checkpoint. Manual `recover-prepared` clears only fully attested pre-mutation snapshots without Stop/Start/IPFW, preserving suspicious or `mutating` evidence. Saved managed-resource bytes can now be attested after a mutating checkout removed/changed live files; prepared-phase cleanup still requires intact live and saved bytes. New schema-2 snapshots seal and verify binary SHA-256 inventory and managed-manifest identity before runtime mutation; prepared-only cleanup and immediate rollback reject tampered saved proof. Explicit operator-only schema-2 recovery of an attested, fully STOPPED native owner is implemented under setup.lock→original FD9; RUNNING/INCOMPLETE/foreign cases fail closed. Installed OPNsense acceptance and old `_10` cold-IPFW package upgrade remain pending. `_29` hardens future PRE_DEINSTALL against unverified native status 2 before Stop (the published `_10` hook remains unchanged); pinned old-hook regression prevents a false migration claim. ECH-off and IPFW package gate remain based on `_15`.


- Installed `_10` read-only [cold-IPFW preflight](verification/LEGACY_COLD_IPFW_PREFLIGHT.md): self-contained script [source](../scripts/legacy-cold-ipfw-preflight.sh), not a repair or package upgrade authorization.

- Historical defect (owner restored stable `_1` manually on 23 October 2026): testing package `v0.5.7_10` owner-installed lifecycle failed;
  absent IPFW/ipdivert made stopped common owner appear foreign. The
  `v0.5.7_15` source candidate explicitly retains ECH-off and repairs
  only the attested cold-kernel case; CI/owner-live result still pending.

- [Approved Additional Resources implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) — external catalog Stage 1 verified; plugin Stage 2 read-only immutable-revision source preflight and isolated transaction/rollback engine added in source through v0.5.7_9 with source-wired native Stop→Start, shared upstream preservation guard, fail-closed direct-install/pending-rollback protection and bilingual manual Settings-page GUI; installed GUI acceptance still pending.
- [Additional Resources normative specification](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) — manual GUI, transaction/restart and fully dynamic new-Job candidate generation; not yet implemented in the plugin.

## Published stable v0.5.7 (historical release)

- [Strategy Lab target requirements](REQUIREMENTS.md) — `BH-01`–`BH-12`, three independent positive signals (target TLS handshake, target QUIC handshake or genuine HTTP response), FreeBSD `latest` without pin.
- [Detailed English Chrome TLS/QUIC/HTTP plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — implementation stages 1–6, integration points and acceptance evidence; Stages 1–6 accepted by owner within bounded installed `_17` evidence, the earlier `v0.5.7_1` full release was published with two focused GUI fixes.
- [Состояние реализации](PROJECT_STATE.md) и [единственный следующий шаг](START_HERE.md).

### Поставка и доказательства завершённых работ

- [v0.5.7 stable release and FreeBSD15 Pages/pkg](releases/v0.5.7.md) — published 22 Oct 2026 with `0.5.7_1`, immutable tag and GitHub/Pages CI evidence. [Publication evidence](verification/evidence/2026-10-22-v0.5.7-full-release-publication.md) records commit, asset SHA-256 and owner-installed limits.

Записи ниже сохраняют историю предыдущей кампании; описанные в них старые следующие эксперименты не являются активной очередью.

- [Stage 2 owner GUI Standard failure and pending logs](verification/evidence/2026-10-21-v0.5.6_5-owner-gui-worker-disappeared.md) — stages 00–85 skipped, worker not verified, Stage 90/99 RESTORE_FAILED; requires read-only runtime diagnosis before rerun.
- [Stage 2 v0.5.6_5 testing publication](verification/evidence/testing-publications/v0.5.6_5.md) — Chrome Standard/Model C source passed FreeBSD15 CI; installed Stage 2 acceptance pending.
- [Stage 1 owner-live Chrome HTTPS and QUIC HTTP/3 verification](verification/evidence/2026-10-21-v0.5.6_3-owner-live-chrome-tls-quic.md) — real HTTP/2 200 and HTTP/3 204, plus explicit TLS1.2 HTTP/2 200, all with valid certificates; Stage 1 V1 PASS.
- [Stage 1 v0.5.6_3 CA correction testing publication](verification/evidence/testing-publications/v0.5.6_3.md) — signed prerelease and FreeBSD15 CI PASS; installed TLS/QUIC acceptance pending.
- [Stage 1 v0.5.6_2 testing publication](verification/evidence/testing-publications/v0.5.6_2.md) — FreeBSD15 CI PASS, current signed latest Chrome binary, persistent GitHub pkg, installed TLS/QUIC acceptance pending.
- [Фактическая публикация full Web/pkg v0.5.6](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md) — CI/FreeBSD15 и Pages PASS, pkg SHA256, owner GUI upgrade pending.
- [Завершение Telegram Voice испытаний, pfSense VPN и release v0.5.6](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md) — MEDIA/CALL не прошли на прямом OPNsense UDP, pfSense `ovpnc6` VPN маршрут; кампания закрыта.
- [Релиз v0.5.6](releases/v0.5.6.md) — полный Web/pkg stage без новых алгоритмов и без обещания Telegram MEDIA.
- [GOST UDP ASSOCIATE, STUN через SOCKS5, два новых direct lab calls и pfSense hypothesis](verification/evidence/2026-10-20-gost-udp-associate-socks-stun-and-repeated-tgvoice-direct-routes.md) — eth2 6×64+20 через :1070, no RX; OPNsense/OpenWrt call=no, route RESTORE PASS; последующая кампания закрыта, новых capture не назначено.
- [OPNsense no-fake Reflector A/B и восстановление; исправленная схема SOCKS5](verification/evidence/2026-10-20-opnsense-reflector-fake-off-restored-socks-architecture.md) — 60 UDP40 без fake, ответа нет; `.1.140` direct-media не эквивалент Telegram через GOST SOCKS5.
- [Подтверждённый STUN fake OpenWrt на WAN: 6×UDP64 + STUN20](verification/evidence/2026-10-20-openwrt-stun-eth2-6x64-wire-proof.md) — фактическая последовательность на eth2 Out, без STUN-ответа и без проверки Telegram Call.
- [Обновлённый OpenWrt — UDP NFQUEUE/Podkop TPROXY](verification/evidence/2026-10-20-openwrt-upgraded-nfqueue-podkop-nft.md) — Podkop 0.7.24, sing-box 1.14.3, queue 537=453 UDP, Podkop TPROXY UDP=0, исходная причина предупреждения mangle counters.
- [Проверенная работа Podkop/sing-box и netfilter на OpenWrt](verification/evidence/2026-10-20-openwrt-podkop-running-runtime.md) — GUI DNS/nft/outbound успешны несмотря на `podkop status not running`; UDP 180 пакетов не привязан к звонку.
- [Схема закрытой кампании OpenWrt / GOST / Podkop / youtubeUnblock](architecture/TELEGRAM_OPENWRT_PROXY_UDP_REFERENCE.md) — отдельно TCP/TLS, STUN и non-STUN Reflector, **автоматический STUN + CLI без собеседника**, ограничения для реального Telegram SOCKS UDP.
- [OpenWrt VM .1.236 / Podkop / youtubeUnblock](verification/evidence/2026-10-20-openwrt-236-youtubeunblock-topology.md) — новая топология владельца, реальные настройки STUN 6×64, отличие от non-STUN reflector, план прямого контроля.
- [Положительный контроль Telegram через 192.168.1.140](verification/evidence/2026-10-20-tgvoice-gateway-140-positive-control.md) — тот же pinned reflector и binary, Established/Media, RESTORE PASS; .4.1 пока не испытан.
- [TTL7 vs исходная Strategy #4, live A/B](verification/evidence/2026-10-20-telegram-ttl7-vs-no-ttl-control.md) — 120+60 на WAN в обоих вариантах, без входящего UDP; актуальный официальный список и системный HTTP-прокси.
- [Рефлекторный протокол pinned tgcalls](verification/evidence/2026-10-20-tgcalls-reflector-protocol-readonly.md) — исходники Hello/12-byte peer tag, штатный список серверов, отсутствие live-квалификации старого адреса.
- [TTL7 WAN trial на установленном `0.5.5_7`](verification/evidence/2026-10-20-telegram-ttl7-wan-owner-live.md) — fake TTL=7, original TTL=63, UDP RX=0, Restore PASS; отличие от media/call.
- [Owner-live приёмка `0.5.5_7` Strategies Apply](verification/evidence/2026-10-20-v0.5.5_7-strategies-apply-owner-acceptance.md) — успешное применение неизменённой и изменённой стратегии на OPNsense; границы проверки.
- [Native Voice TNAS lab — runbook закрытой кампании](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md) — доступ, маршрут, безопасные тесты A0–A5 и приёмка.
- [Первый native reflector опыт](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md) — факт 60/4080 и незавершённый звонок.
- [A2 LAN/WAN capture на установленной 0.5.5_1](verification/evidence/2026-10-19-native-voice-a2-lan-wan-capture.md) — одновременные PCAP, WAN pattern, отсутствие подтверждённого ответа, офлайн next step.
- [Публикация v0.5.4](verification/evidence/2026-10-19-v0.5.4-full-release-publication.md) — immutable tag/CI/pkg/Pages evidence.
- [Полный релиз v0.5.5](releases/v0.5.5.md) — предыдущая стабильная поставка и UI-приёмка.
- [Публикация v0.5.5](verification/evidence/2026-10-19-v0.5.5-full-release-publication.md) — exact tag/PR/CI/pkg SHA-256/Pages evidence.
- [Принятая Voice GUI/меню локализация](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md) — owner-live закрытие UI дефектов.
- [Полный релиз v0.5.4](releases/v0.5.4.md) — история предыдущей стабильной поставки.
- [Приёмка Voice](VOICE_CODE_COMPLETION_GATE.md) — текущая независимая цепочка GUI/Config/IPFW/STUN/media/call.
- [Полное ТЗ «Передача голоса»](architecture/VOICE_TRANSMISSION_GUI.md) — пять сервисов, GUI и общий backend.
- [Исторический план v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) и [история v0.5.3](releases/v0.5.3.md).
- [ARCHITECTURE](ARCHITECTURE.md), [REQUIREMENTS](REQUIREMENTS.md), [Zapret2 Service](architecture/ZAPRET2_SERVICE.md) — общие контракты.
- [Previous v0.5.x ledger](history/current/v0.5.x.md) — historical chronology; [current v0.6.x ledger](history/current/v0.6.x.md).

## Specialist routes по задаче

- Laboratory: [English Chrome TLS/QUIC/HTTP plan (Stage 1 bundled/owner verified; production migration pending)](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md), [main architecture](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [Enable QUIC](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [finalist publishing](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [Generic UDP](architecture/STRATEGY_LAB_UDP_INPUT.md), [user guide](USER_GUIDE_STRATEGY_LAB.md), [live matrix](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).
- Историческая Telegram PoC laboratory (**НЕ native entrypoint**): [operations/SSH/ручные маршруты](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md), [helper reference](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md).
- Точечное исследование: [UDP research](research/TELEGRAM_VOICE_UDP.md), [topology/TTL](research/TELEGRAM_VOICE_DPI_TOPOLOGY_AND_TTL.md), [optional independent control](architecture/TELEGRAM_VOICE_INDEPENDENT_CONTROL.md).
- Общая навигация: [architecture/](architecture/), [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md).

Эти маршруты читаются только когда нужны для конкретного изменения/проверки. Наиболее подробные указатели прежних измерений сохранены в [историческом INDEX](history/stages/v0.5.1/INDEX.md).

## Level 3 — архивы и доказательства

- [Архив этапа v0.5.1](history/stages/v0.5.1/README.md) — восемь полных снимков, старые планы/private отчёты; не активная очередь.
- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)
- [v0.5.x archive](history/archive/v0.5.x.md)
- [DECISIONS](DECISIONS.md) / [decisions/](decisions/), [AUDIT](AUDIT.md) / [audit/](audit/), [DEVLOG](DEVLOG.md) / [devlog/](devlog/).
- [patches/](patches/), [verification/](verification/), [verification/evidence/](verification/evidence/), [releases/](releases/), [CHANGELOG](CHANGELOG.md).

Исторические records сохраняют rationale/chronology/proof. Текущие требования и следующий шаг задаются активными документами; наличие старого «next step» не открывает закрытую работу заново.

## Вход для пользователя и contributors

[README](../README.md) · [LICENSE](../LICENSE) · [NOTICE](../NOTICE).

INDEX — карта, не devlog. Локальные ссылки, anchors и канонические references проверяются существующими integrity checks.

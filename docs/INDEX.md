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

## Level 2 — активное ТЗ по полной чистой установке (8 ноября 2026)

- [Восстановление полного жизненного цикла после чистой установки — ТЗ v1.2](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md) — новое утверждённое пользовательское поведение; первая задача: безопасный автономный purge-скрипт, затем исправления GUI/uninstall/bootstrap/WAN/пустых стратегий/Strategy Lab. Реализация пока открыта.
- [Поэтапный план восстановления G01–G11](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_PLAN.md) — единственная текущая последовательность реализации: сначала безопасный full-purge, затем обычный GUI uninstall, первая runtime-install, утверждённые 10 доменов + TCP/QUIC, WAN/empty/Voice, RU/EN GUI/Lab, real native/owner-live acceptance. Результаты не подтверждены созданием документа.
- [G01 — guide to independent full purge](verification/G01_STANDALONE_PURGE_GUIDE.md) — отдельный деструктивный скрипт после обычного удаления пакета; исходник, backup/dry-run, подтверждение, сценарии отказа и границы disposable-native приёмки. До прохождения G01 запрещена автоматическая трактовка source-тестов как полной проверки.
- [G02 — ordinary GUI uninstall verification](verification/G02_NORMAL_GUI_UNINSTALL.md) — merged source and disposable-native firmware remove/reinstall, owner-live pending.
- [G03 — first upstream runtime setup verification](verification/G03_FIRST_UPSTREAM_SETUP.md) — clean GUI upper Apply, scoped first-install transaction, fail/retry/recovery and single targeted native witness; owner-browser acceptance remains G11.
- [G04 — saved Config and native TCP/QUIC/HTTPS Apply acceptance](verification/G04_INITIAL_NATIVE_CONFIG.md) — native initial Config, real v1.0.7 Start/Stop and authenticated first Strategies HTTPS Apply have installed-CI PASS through PR #984; owner browser/real WAN NOT TESTED.
- [G05 — native WAN-only Save, RUNNING/STOPPED full Apply and rollback](verification/G05_WAN_ONLY_NATIVE.md) — cold WAN Save, four full WAN Apply, `_16` post-activation rollback [native PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42621283599); `_17` real assigned TUN/OPT [native PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42627567617), [PR #991](https://github.com/Tolian82/os-zapret2-restyle/pull/991); `_18` cold WAN-first/engine-second GUI/configd/Voice/Lab [native S2 PASS #42640788056](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42640788056), [PR #992](https://github.com/Tolian82/os-zapret2-restyle/pull/992) merge pending scoped CI budget correction. Existing WAN resolver unchanged, owner browser/real VPN/IPsec OPEN.
- [G06 — native empty Strategy/Voice-only acceptance](verification/G06_NO_ACTION_NATIVE.md) — `_19` upstream no-action real packet PASS, `_21` source/CI PASS, `_22` installed Voice-only/no-action [S2 PASS #42669040205](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42669040205), `_23` post-activation Voice-only rollback [S2 PASS #42670658248](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42670658248), [PR #997](https://github.com/Tolian82/os-zapret2-restyle/pull/997) merged; owner-live and unmodified GUI fault separately OPEN.
- [G07 — five GUI statuses, native Start/Apply and RU/EN](verification/G07_LIFECYCLE_STATUS.md) — `_24` [PR #998](https://github.com/Tolian82/os-zapret2-restyle/pull/998) merged; `_25` native HTTPS first Apply/Stop/Start/Restart/ordinary Add/Remove [PASS #42678641429](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42678641429), [PR #999](https://github.com/Tolian82/os-zapret2-restyle/pull/999) merged; owner-live browser and real media separately OPEN.
- [G08 — real Standard/Extended before first normal Start](verification/G08_PRESTART_LAB_NATIVE.md) — `_26` genuine HTTPS jobs + STOPPED restore native S2 PASS [#42681458370](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42681458370); accessible control skips Stage50.
- [G09 — real native Stage50→60 negative control](verification/G09_STAGE60_NATIVE.md) — `_27` genuine installed job, no-family search, strict STOPPED restore; S2 PENDING and NOT a DPI bypass proof.
- [Дефекты опубликованного v0.6.3_1](https://github.com/Tolian82/os-zapret2-restyle/issues/970) — #970–#973, подтверждённые owner-live; исходный стабильный пакет неизменен.

## Level 2 — активное ТЗ и нативная интеграция (5 ноября 2026)

- [ТЗ: OPNsense native packaging and unified compatibility v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) — утверждённые требования к штатным pkg, зависимостям, Python и сервису, зафиксированные номера IPFW.
- [Конкретный план завершения v1.5](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_PLAN.md) — действующий штатный pkg/configd/сервис и нативные тесты Stage 5; `_137` cleanup уже завершён, новые механизмы внешнего допуска отменены.
- [START_HERE](START_HERE.md), [PROJECT_STATE](PROJECT_STATE.md), [ROADMAP](ROADMAP.md) — единая текущая задача, факты и последовательность работ.
- [ARCHITECTURE](ARCHITECTURE.md), [REQUIREMENTS](REQUIREMENTS.md), [README](../README.md) — действующие архитектура и требования.
- [v0.6.3 — разрешённый полный release candidate](releases/v0.6.3.md) — точный `0.6.3_1.pkg`, заметки и границы приёмки; [предыдущий v0.6.2](releases/v0.6.2.md) — неизменяемый `0.6.2_1.pkg`; [v0.6.x ledger](history/current/v0.6.x.md) — прошлые экспериментальные результаты, **не** release gates.
- [Stage 5 — финальная матрица AC-01–AC-11](verification/STAGE5_FINAL_ACCEPTANCE_MATRIX.md) — отдельные статусы PASS/PARTIAL/NOT TESTED, реальные native SHA, оставшиеся браузер/WAN/IPv6/media и owner approval; НЕ разрешение на публикацию.
- [PR completion watchdog](GITHUB_PR_COMPLETION_WATCHDOG.md) — независимая GitHub-проверка CI/PR, **не** авторизация пакетов.

**Отменены и исключены из активной навигации:** SQLite-свидетели и approval-gateway, криптографические одноразовые разрешения, внешний сервер подтверждений, OPNsense-specific pfilctl, IPFW shaper-flush мониторинг и новые IPFW collision/foreign-rule audits. Код/CI отменённой архитектуры вычищены в историческом `_137` и слиты после нативных проверок; исторические доказательства остаются в Git и архиве.

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

## Level 3 — historical M0–M7 completion and acceptance

- [Owner-approved completion plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) — bounded milestones, acceptance gates, and no speculative Git provenance expansion.
- [Additional Resources normative technical specification](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) — normal update, exact-set reconciliation and preserved fail-closed recovery; new clean-reinstall tooling explicitly cancelled.
- [Single acceptance board](verification/EXTRA_RESOURCES_ACCEPTANCE.md) — actual candidate, evidence, pass/fail status, blocker and next action.
- [Final owner acceptance and stable release authorization](verification/evidence/2026-10-24-v0.5.8-owner-acceptance-and-release-authorization.md) — accepted H1; M6 owner-closed without a cold boot; M7 exact delivery authorization.
- [v0.5.8 stable release preparation and verification](releases/v0.5.8.md) — exact `0.5.8_1` candidate, included features and bounded release checks.
- [Historical cancelled clean-plugin repair proposal](verification/EXTRA_RESOURCES_CLEAN_REPAIR_GATE.md) — superseded by owner decision 24 October 2026; not active or required for release.

## Level 3 — historical cold-IPFW lifecycle correction

- Source `v0.5.7_30`: safe cold IPFW module loading with `kenv` default-allow staged and verified **before** `kldload ipfw`; strict cold owner inspector process/module evidence. Prior installed stable `_1` rescue achieved RUNNING after manual safe IPFW/ipdivert bring-up via hypervisor console; not evidence of `_30` installed boot acceptance. No new release approved. See [handoff](START_HERE.md) and [current state](PROJECT_STATE.md).

## Level 3 — historical Additional Resources implementation

- Stage 4/GUI/upstream gate `v0.5.7_29`: dynamic BIN/Lua, correlated GUI receipts and durable upstream checkpoint. Manual `recover-prepared` clears only fully attested pre-mutation snapshots without Stop/Start/IPFW, preserving suspicious or `mutating` evidence. Saved managed-resource bytes can now be attested after a mutating checkout removed/changed live files; prepared-phase cleanup still requires intact live and saved bytes. New schema-2 snapshots seal and verify binary SHA-256 inventory and managed-manifest identity before runtime mutation; prepared-only cleanup and immediate rollback reject tampered saved proof. Explicit operator-only schema-2 recovery of an attested, fully STOPPED native owner is implemented under setup.lock→original FD9; RUNNING/INCOMPLETE/foreign cases fail closed. Installed OPNsense acceptance and old `_10` cold-IPFW package upgrade remain pending. `_29` hardens future PRE_DEINSTALL against unverified native status 2 before Stop (the published `_10` hook remains unchanged); pinned old-hook regression prevents a false migration claim. ECH-off and IPFW package gate remain based on `_15`.


- Installed `_10` read-only [cold-IPFW preflight](verification/LEGACY_COLD_IPFW_PREFLIGHT.md): self-contained script [source](../scripts/legacy-cold-ipfw-preflight.sh), not a repair or package upgrade authorization.

- Historical defect (owner restored stable `_1` manually on 23 October 2026): testing package `v0.5.7_10` owner-installed lifecycle failed;
  absent IPFW/ipdivert made stopped common owner appear foreign. The
  `v0.5.7_15` source candidate explicitly retains ECH-off and repairs
  only the attested cold-kernel case; CI/owner-live result still pending.

- [Approved Additional Resources implementation plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) — external catalog Stage 1 verified; plugin Stage 2 read-only immutable-revision source preflight and isolated transaction/rollback engine added in source through v0.5.7_9 with source-wired native Stop→Start, shared upstream preservation guard, fail-closed direct-install/pending-rollback protection and bilingual manual Settings-page GUI; installed GUI acceptance still pending.
- [Additional Resources normative specification](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) — owner-approved manual GUI, transactional backend and dynamic new-Job candidate generation are implemented in source; positive installed native HTTPS Install is accepted on exact-main `_162`; real unchanged repeat Install and positive Remove all 73 are accepted on `_164` [two-guest Stage 5](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42227947387). Physical browser and live owner/WAN acceptance remain separate gates.

## Published stable v0.5.7 (historical release)

- [Strategy Lab target requirements](REQUIREMENTS.md) — `BH-01`–`BH-12`, three independent positive signals (target TLS handshake, target QUIC handshake or genuine HTTP response); historical exploratory FreeBSD `latest` acquisition, with a separate mandatory pinned source/ELF gate for release candidates.
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

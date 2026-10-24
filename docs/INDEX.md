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

## Level 2 — active development: safe removal of extra resources

- [Approved remove specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) — physically retain only installed upstream HEAD Lua/BIN, block on incompatible saved Strategies or Voice (including meaningful OFF drafts), protect native lifecycle/rollback, and provide Advanced-only bilingual Remove UI.
- [Approved staged remove plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md) — 13 bounded stages including the late README and separately authorized stable release; Stage 1 source/FreeBSD15 checks qualified, Stage 2 upstream-only view source/CI qualified (PR #578), native Strategies pipeline fixture `v0.5.9_3` in progress; no testing package or release authorized.

## Level 2 — active M0–M7 completion and acceptance

- [Owner-approved completion plan](architecture/ZAPRET2_EXTRA_RESOURCES_IMPLEMENTATION_PLAN.md) — bounded milestones, acceptance gates, and no speculative Git provenance expansion.
- [Additional Resources normative TЗ](architecture/ZAPRET2_EXTRA_RESOURCES_GUI.md) — normal update, exact-set reconciliation and preserved fail-closed recovery; new clean-reinstall tooling explicitly cancelled.
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
- [Рабочий ledger v0.5.x](history/current/v0.5.x.md) — история, а не текущий handoff.

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
- [DECISIONS](DECISIONS.md) / [decisions/](decisions/), [AUDIT](AUDIT.md) / [audit/](audit/), [DEVLOG](DEVLOG.md) / [devlog/](devlog/).
- [patches/](patches/), [verification/](verification/), [verification/evidence/](verification/evidence/), [releases/](releases/), [CHANGELOG](CHANGELOG.md).

Исторические records сохраняют rationale/chronology/proof. Текущие требования и следующий шаг задаются активными документами; наличие старого «next step» не открывает закрытую работу заново.

## Вход для пользователя и contributors

[README](../README.md) · [LICENSE](../LICENSE) · [NOTICE](../NOTICE).

INDEX — карта, не devlog. Локальные ссылки, anchors и канонические references проверяются существующими integrity checks.

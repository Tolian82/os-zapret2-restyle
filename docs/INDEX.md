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

## Level 2 — текущая линия v0.5.x, этап v0.5.6

- [Завершение Telegram Voice испытаний, pfSense VPN и release v0.5.6](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md) — MEDIA/CALL не прошли на прямом OPNsense UDP, pfSense `ovpnc6` VPN маршрут; кампания закрыта.
- [Релиз v0.5.6](releases/v0.5.6.md) — полный Web/pkg stage без новых алгоритмов и без обещания Telegram MEDIA.
- [GOST UDP ASSOCIATE, STUN через SOCKS5, два новых direct lab calls и pfSense hypothesis](verification/evidence/2026-10-20-gost-udp-associate-socks-stun-and-repeated-tgvoice-direct-routes.md) — eth2 6×64+20 через :1070, no RX; OPNsense/OpenWrt call=no, route RESTORE PASS; pfSense LAN/WAN capture next.
- [OPNsense no-fake Reflector A/B и восстановление; исправленная схема SOCKS5](verification/evidence/2026-10-20-opnsense-reflector-fake-off-restored-socks-architecture.md) — 60 UDP40 без fake, ответа нет; `.1.140` direct-media не эквивалент Telegram через GOST SOCKS5.
- [Подтверждённый STUN fake OpenWrt на WAN: 6×UDP64 + STUN20](verification/evidence/2026-10-20-openwrt-stun-eth2-6x64-wire-proof.md) — фактическая последовательность на eth2 Out, без STUN-ответа и без проверки Telegram Call.
- [Обновлённый OpenWrt — UDP NFQUEUE/Podkop TPROXY](verification/evidence/2026-10-20-openwrt-upgraded-nfqueue-podkop-nft.md) — Podkop 0.7.24, sing-box 1.14.3, queue 537=453 UDP, Podkop TPROXY UDP=0, исходная причина предупреждения mangle counters.
- [Проверенная работа Podkop/sing-box и netfilter на OpenWrt](verification/evidence/2026-10-20-openwrt-podkop-running-runtime.md) — GUI DNS/nft/outbound успешны несмотря на `podkop status not running`; UDP 180 пакетов не привязан к звонку.
- [Актуальная схема OpenWrt / GOST / Podkop / youtubeUnblock](architecture/TELEGRAM_OPENWRT_PROXY_UDP_REFERENCE.md) — отдельно TCP/TLS, STUN и non-STUN Reflector, **автоматический STUN + CLI без собеседника**, ограничения для реального Telegram SOCKS UDP.
- [OpenWrt VM .1.236 / Podkop / youtubeUnblock](verification/evidence/2026-10-20-openwrt-236-youtubeunblock-topology.md) — новая топология владельца, реальные настройки STUN 6×64, отличие от non-STUN reflector, план прямого контроля.
- [Положительный контроль Telegram через 192.168.1.140](verification/evidence/2026-10-20-tgvoice-gateway-140-positive-control.md) — тот же pinned reflector и binary, Established/Media, RESTORE PASS; .4.1 пока не испытан.
- [TTL7 vs исходная Strategy #4, live A/B](verification/evidence/2026-10-20-telegram-ttl7-vs-no-ttl-control.md) — 120+60 на WAN в обоих вариантах, без входящего UDP; актуальный официальный список и системный HTTP-прокси.
- [Рефлекторный протокол pinned tgcalls](verification/evidence/2026-10-20-tgcalls-reflector-protocol-readonly.md) — исходники Hello/12-byte peer tag, штатный список серверов, отсутствие live-квалификации старого адреса.
- [TTL7 WAN trial на установленном `0.5.5_7`](verification/evidence/2026-10-20-telegram-ttl7-wan-owner-live.md) — fake TTL=7, original TTL=63, UDP RX=0, Restore PASS; отличие от media/call.
- [Owner-live приёмка `0.5.5_7` Strategies Apply](verification/evidence/2026-10-20-v0.5.5_7-strategies-apply-owner-acceptance.md) — успешное применение неизменённой и изменённой стратегии на OPNsense; границы проверки.
- [Native Voice TNAS lab — текущий runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md) — доступ, маршрут, безопасные тесты A0–A5 и приёмка.
- [Первый native reflector опыт](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md) — факт 60/4080 и незавершённый звонок.
- [A2 LAN/WAN capture на установленной 0.5.5_1](verification/evidence/2026-10-19-native-voice-a2-lan-wan-capture.md) — одновременные PCAP, WAN pattern, отсутствие подтверждённого ответа, офлайн next step.
- [Публикация v0.5.4](verification/evidence/2026-10-19-v0.5.4-full-release-publication.md) — immutable tag/CI/pkg/Pages evidence.
- [Полный релиз v0.5.5](releases/v0.5.5.md) — текущая стабильная идентичность, UI-приёмка и граница поставки.
- [Публикация v0.5.5](verification/evidence/2026-10-19-v0.5.5-full-release-publication.md) — exact tag/PR/CI/pkg SHA-256/Pages evidence.
- [Принятая Voice GUI/меню локализация](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md) — owner-live закрытие UI дефектов.
- [Полный релиз v0.5.4](releases/v0.5.4.md) — история предыдущей стабильной поставки.
- [Приёмка Voice](VOICE_CODE_COMPLETION_GATE.md) — текущая независимая цепочка GUI/Config/IPFW/STUN/media/call.
- [Полное ТЗ «Передача голоса»](architecture/VOICE_TRANSMISSION_GUI.md) — пять сервисов, GUI и общий backend.
- [Исторический план v0.5.3](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) и [история v0.5.3](releases/v0.5.3.md).
- [ARCHITECTURE](ARCHITECTURE.md), [REQUIREMENTS](REQUIREMENTS.md), [Zapret2 Service](architecture/ZAPRET2_SERVICE.md) — общие контракты.
- [Рабочий ledger v0.5.x](history/current/v0.5.x.md) — история, а не текущий handoff.

## Specialist routes по задаче

- Laboratory: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [Enable QUIC](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [Generic UDP](architecture/STRATEGY_LAB_UDP_INPUT.md), [user guide](USER_GUIDE_STRATEGY_LAB.md), [live matrix](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).
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

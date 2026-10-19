# os-zapret2-restyle — краткий master plan

## Текущий приоритет — v0.5.5: безопасный отказ Strategies Apply, затем Telegram non-STUN TTL7

На установленной `0.5.3_28` успешно завершился Telegram ON Apply: Config сохранён, общая транзакция `committed`, engine/supervisor/IPFW `ready`. Владелец подтвердил доступ к TNAS, маршрут `91.108.13.10` через OPNsense и Docker host laboratory. Первый 15-секундный `tgcalls_cli` reflector test дал **60/4080 на IPFW rule 19000**, но `Call established: no`; это не proof of UDP response, STUN processing или media.

1. **Выполнено:** full Web/pkg `v0.5.5_1` установлен владельцем; приняты [Voice UI / RU меню](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md), без заявления CALL_PASS.
2. **A2 выполнен:** [LAN/WAN packet evidence](verification/evidence/2026-10-19-native-voice-a2-lan-wan-capture.md) установило WAN egress 60 non-STUN Reflector Hello +120 zero16, 0 ответов; merged профили показали, что работает ordinary Strategy №4 `unknown` UDP/596–599, **не** Voice STUN №1.
3. **A3a STUN outbound PASS:** на установленной `_1` профиль №1 отдельно обработал валидный STUN20 на UDP/3478 и выпустил 2 zero16 fake. [Evidence](verification/evidence/2026-10-19-native-voice-a3a-stun-outbound.md). STUN_RX с заведомым responder открыт, но случайный Telegram IP:3478 не квалифицирован как responder.
4. **Блокер TTL7 Apply выявлен:** GUI `_1` ошибочно считает безмутационные preflight-отказы неопределённым результатом; source candidate `_2` классифицирует стадийные receipt и pre-dispatch exception, оставляя post-dispatch requires-review. Только после CI/выпуска тестового пакета и owner-live проверки — один ещё не запущенный fake-TTL **7** кандидат ordinary №4 UDP/596–599, штатный GUI Apply и возврат после WAN/ICMP измерения; [trace и ограниченный план](verification/evidence/2026-10-19-reflector-hop-trace-ttl7-first-candidate.md). Позиция DPI неизвестна; уже испытанный A1/A2/A3a/fragment sweep не повторять. Полный A5 Telegram caller/callee + звук обязателен для `CALL_PASS`.

Текущие факты — [PROJECT_STATE](PROJECT_STATE.md), одно следующее действие — [START_HERE](START_HERE.md), исторический v0.5.3 UI/root-FD9 completion plan — [здесь](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md). Не делать новую архитектурную переделку или запускать старый PoC runner ради «зелёного» счётчика.

## Основной завершённый путь

- Независимый native OPNsense plugin, обычный runtime/service lifecycle, Traffic Strategy и HOSTLIST/IPSET.
- Zapret2 Service GUI для upstream install/update/reinstall/downgrade; Diagnostics и asynchronous Strategy Lab.
- Python orchestration, adaptive search и finite budgets; выбор Model C, source-port attribution/leasing и readiness.
- Generic UDP exact bytes, наблюдаемый QUIC и persisted Enable QUIC; domain/IPv4 + optional Host/SNI, truthful results и точный fixed-IP replay.
- Owner-live закрытие линии v0.4.x; stable [v0.5.0](releases/v0.5.0.md), принятый file-picker corrective `_2` и опубликованный testing `_3`.
- Форма/модель Voice и PoC начинались в v0.5.1; общий page/lifecycle реализован в feature-коде v0.5.2, но owner-live приёмка ещё не выполнена. [Архив](history/stages/v0.5.1/README.md).

## Отдельная Telegram media campaign после page/migration baseline

- Продолжать на одной записанной базе через OPNsense/того же ISP, существующий current-oracle Docker runner и один меняемый параметр. Уже измеренные A1/A2, standalone fragment positions и старые отрицательные опыты не повторять без нового основания.
- Завершить retained runner tooling: RTC logs, bounded ICMP, saved/effective/source/target/process checks, semantic pre/post state и owned remote cleanup. Drift останавливает опыт; восстановление подтверждается отдельно.
- Проверить ограниченную fake-TTL гипотезу по [campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md): не более четырёх начальных значений, фиксированные endpoint/runtime/route, точный stop/restore contract. Это гипотеза, не принятый preset.
- Для media-positive кандидата — три свежих успешных повторения и action-only control, затем реальный клиент с проверенным endpoint, двусторонним UDP и звуком. После MEDIA_PASS/CALL_PASS зафиксировать квалифицированный preset; configuration PASS не заменяет их.
- Если восстанавливаемо, сопоставить September 22 positive CLI evidence. Иначе выбирать один ограниченный опыт по текущему transport, не возобновлять fragment sweep.
- Same-endpoint read-only inventory и alternate-gateway successful-call capture остаются optional causal diagnostics. Не делать обязательный новый UDP exit и не использовать человеческие звонки для каждого кандидата.

## Независимая лаборатория и persistence

- Сохранять документированную LAN/router-local/SOCKS базу: отдельные TCP/TLS parent и UDP/Zapret2 пути. Router-local без explicit SOCKS и SOCKS UDP ASSOCIATE требуют отдельной квалификации.
- Предпочитать штатный OPNsense GUI/persistence; проверить сохранность non-GUI sing-box/ACL/alias/snapshot при regeneration и reboot. Уже рабочие LAN/SOCKS TCP-parent пути сохраняются.
- Persistence выбранного Voice теперь реализуется общей native страницей; дополнительный hook/Cron enable не создаётся. После reboot проверить effective profiles, процессы/правила, LAN/SOCKS/router-local TCP и релевантный UDP до ручного исправления.
- Ручные OPNsense→TNAS SSH/два host-route repair проверены; после реального TNAS reboot остаётся owner-manual проверка восстановления. Без route Cron/configd/boot scheduling и Docker autostart.

Факты и команды находятся в [operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md) и [helper reference](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Эти задачи не добавляют TCP/proxy/routes в plugin.

## Сохранённый будущий backlog

- Cancellation/internal-failure containment; circular start/stop/TTL и stale-session recovery.
- Diagnostics persistence/reload; retention/cleanup; reboot/residue regression.
- Runtime/service reliability и package/runtime visibility при новом основании; дальнейший RU/EN review выбранных дефектов.
- IPv6 Laboratory target support — отдельная архитектурная задача.
- Дополнительный BLOB repository GUI — только после согласованного технического контракта владельца.

Эти направления не становятся автоматически долгом страницы или уже опубликованного v0.5.0.

## Отложенные исследования

Candidate parallel width выше трёх, endpoint parallelism, cross-batch keep-warm, BLOB/Lua/discovery optimization и Model-C timeout/deadline audit открываются только при новом конкретном дефекте/потребности, материальном изменении архитектуры либо выборе владельца. Завершённые измерения сохранены в истории.

Текущая граница — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [working ledger](history/current/v0.5.x.md). Roadmap не накапливает ревизионные отчёты.

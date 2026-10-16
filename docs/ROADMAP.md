# os-zapret2-restyle — краткий master plan

## Текущий приоритет — v0.5.2: завершение Voice

Полное [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) и внешний вид пяти Voice-сервисов не меняются. [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328); никакого релиза до кодовой готовности.

| Этап из [плана](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) | Фактический статус |
|---|---|
| 1. Общий Voice + ordinary generator | Реализован в коде и isolated tests |
| 2. Общий scoped STUN/IPFW | Реализован, включая точную сверку engine/UDP/IPSET/WAN/divert |
| 3. Единый Apply обеих страниц | Реализован: FD9, Config save, rollback, commit |
| 4. Lifecycle и legacy миграция | Normal Stop/Start/boot реализованы; имена Telegram enable/disable/status уже идут через native Config/Apply/inspect. По новому решению владельца legacy миграция отменена, native clean baseline |
| 5. Фактические статусы | Реализованы и уточнены в `_138–_140` |
| 6. Удаление дублирования | Завершено в коде и проверено CI/FreeBSD: удалён private PoC recovery/rollback/IPFW/process graph и его entrypoints; единый shared Apply сохранён |
| 7. Завершение и приёмка | Пять сервисов, общий Apply, native lifecycle и GUI status реализованы в коде. Проверка текущего HEAD и обязательный README/release gate предшествуют полноценному Web/pkg релизу; owner-live GUI/CONFIG/BOOT/STUN/MEDIA/CALL выполняется **после** него. |

**Остаточный рубеж:** квалифицировать текущий точный HEAD, завершить только воспроизводимые ошибки GUI/Apply, затем оценить кодовую готовность ТЗ к полноценному релизу перед будущей owner-live приёмкой. Уже реализованную STUN→common dvtws2→IPFW→Apply цепочку не строить повторно. **Точное следующее действие принадлежит [START_HERE](START_HERE.md)**, подтверждённые факты — [PROJECT_STATE](PROJECT_STATE.md), критерии — [контролю](VOICE_CODE_COMPLETION_GATE.md). ROADMAP не хранит `_N` и последние логи CI.

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

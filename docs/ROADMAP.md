# os-zapret2-restyle — краткий master plan

## Текущий приоритет — v0.5.2

**`v0.5.2_46`: общий backend «Стратегии» / «Передача голоса».** Этап открыт 13.10.2026 по поручению владельца без релиза. Архитектура утверждена, [подробный проект плана и контроля](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) принят к выполнению поручением владельца начать программирование. Frontend и все пять сервисов по [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) сохраняются.

| Предложенный этап | Конечный результат |
|---|---|
| 1. Общий generator | Полный Voice + ordinary candidate из одной модели |
| 2. Общий firewall | Пять scoped таблиц/правил, ownership и rollback |
| 3. Общий Apply | Полная форма обеих страниц, все пять сервисов, native save и no lost update |
| 4. Lifecycle/миграция | Start/stop/reconfigure/boot, interrupted Apply, ограниченный импорт PoC |
| 5. Статусы | Фактические per-service результаты в существующей форме |
| 6. Удаление дублирования | Один поставляемый backend и необходимые общие проверки |
| 7. Полная приёмка | Все обязательные GUI/CONFIG/BOOT проверки, пакет/CI и owner-live |

Детальные файлы, зависимости, переходы и проверки живут только в плане. Этап 1 реализован: полный detached common runtime; этап 2 реализован в общем firewall adapter с проверенным изолированным циклом; этап 3 начат общим PHP candidate/dependency boundary в `_4`; внутреннее переключение runtime/IPFW реализовано в `_5`; в `_12` добавлена durable общая operation record и lifecycle guard; в `_13` создана единая detached source+template+release подготовка, в `_14`–`_17` реализован и тестируется один внутренний FD9 executor с native Config save/IPFW commit, fail-closed legacy boot protection и fault injection. В `_18`–`_21` реализованы seal и common boot для committed journal через original FD9, сохранённый Config и старый общий runtime adapter. В `_21` добавлено автоматическое восстановление исключительно `prepared` без live мутаций. Следующий рубеж — проверяемое power-cut recovery фаз с возможными live изменениями, native stop/restart, обе штатные кнопки в коде переключены на native FD9 в `_27`–`_28`, но ещё нужны FreeBSD owner-live и end-to-end приёмка. Public Apply ещё не готов. Public Apply и live приёмка ещё открыты. Новая private цепочка WAL/receipt и один профиль вместо полной страницы не являются очередью.

## Основной завершённый путь

- Независимый native OPNsense plugin, обычный runtime/service lifecycle, Traffic Strategy и HOSTLIST/IPSET.
- Zapret2 Service GUI для upstream install/update/reinstall/downgrade; Diagnostics и asynchronous Strategy Lab.
- Python orchestration, adaptive search и finite budgets; выбор Model C, source-port attribution/leasing и readiness.
- Generic UDP exact bytes, наблюдаемый QUIC и persisted Enable QUIC; domain/IPv4 + optional Host/SNI, truthful results и точный fixed-IP replay.
- Owner-live закрытие линии v0.4.x; stable [v0.5.0](releases/v0.5.0.md), принятый file-picker corrective `_2` и опубликованный testing `_3`.
- В прежнем этапе v0.5.1 подготовлены форма/модель Voice и private helpers; полный page/lifecycle результат не принят. [Архив этапа](history/stages/v0.5.1/README.md).

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

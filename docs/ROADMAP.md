# os-zapret2-restyle — краткий master plan

## Текущий приоритет — модернизация Strategy Lab через curl-impersonate

The [target requirements](REQUIREMENTS.md) and [detailed English plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) include the owner's 21 October 2026 correction: **a verified target TLS handshake OR QUIC handshake OR genuine final HTTP response individually proves reachability**. HTTP/1.1 and HTTP/2 are equally positive when observed; 4xx/5xx replies count as accessible. Get the current FreeBSD `latest` curl-impersonate at each build per ugorur, with lexiforest as upstream reference, no version pin, and one supported Chrome profile. Direct HTTPS success by handshake or response skips QUIC.

Последовательность принятых этапов:

1. Поставка готового клиента FreeBSD `latest` без закреплённой версии и выбор доступного Chrome-профиля.
2. Migrate Standard/Model C and finalists to the handshake **OR** authentic HTTP-response classifier.
3. Extended TLS 1.2/cleartext HTTP and target QUIC handshake **OR** genuine HTTP/3 response (no mandatory HTTP3 GET).
4. Ограниченное расширение QUIC-каталога в конечном бюджете.
5. Достоверные результаты, RU/EN и совместимость сохранённых заданий.
6. Поставка и приёмка установленного пакета.

The owner authorized implementation. Stage 1 packaging integration is under CI qualification; stages 2–6 have not started. No Firefox, ordinary curl fallback, mandatory HTTP body, upstream version pin, Python/Model C replacement or new recovery architecture. No change to published v0.5.6 and no automatic stable release.

## Основной завершённый путь

- Независимый native OPNsense plugin, обычный runtime/service lifecycle, Traffic Strategy и HOSTLIST/IPSET.
- Zapret2 Service GUI для upstream install/update/reinstall/downgrade; Diagnostics и asynchronous Strategy Lab.
- Python orchestration, adaptive search, конечные бюджеты, Model C, source-port attribution/leasing и readiness.
- Generic UDP exact bytes, persisted Enable QUIC и QUIC candidate search; domain/IPv4 + optional Host/SNI, truthful results и fixed-IP replay.
- Owner-live закрытие выбранных сценариев линии v0.4.x и стабильная поставка [v0.5.0](releases/v0.5.0.md).
- Общий backend Voice/Strategies, подтверждённый Voice Apply, сохранность Voice-конфигурации и принятый GUI/RU/EN; подтверждённый Strategies Apply после исправления большого неизменённого запроса. Границы доказательств — в [PROJECT_STATE](PROJECT_STATE.md).
- Полный [v0.5.6](releases/v0.5.6.md) опубликован через GitHub/FreeBSD15/Pages. Установка владельцем через GUI остаётся неподтверждённой, без повторного открытия завершённой разработки.

## Telegram Voice — закрытая кампания

Владелец завершил исследования 20.10.2026 с отрицательным результатом на прямом UDP OPNsense. Положительный pfSense-контроль оказался связан с VPN-маршрутом; он не доказывает Zapret2-обход того же прямого провайдера. `MEDIA_PASS=false`, `CALL_PASS=false`; точная причина потери ответа не установлена. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

Старые предложения capture, fake/TTL, SOCKS/UDP и реальных звонков не являются активной очередью. Возобновление требует нового явного задания владельца. GUI/Config/Apply и действующие профили сохраняются.

## Независимая лаборатория и persistence

Сохранённое направление вне текущей HTTP-модернизации: штатная OPNsense persistence и квалификация LAN/router-local/SOCKS при конкретном новом задании. Рабочие TCP/TLS parent-пути и отдельный UDP/Zapret2 тракт не объединяются. Non-GUI sing-box/ACL/alias/snapshot и фактический reboot проверяются только в относящемся к ним сценарии.

Ручные OPNsense→TNAS SSH/host-route repair остаются ручными; route Cron/configd/boot scheduling и Docker autostart не планируются. Старые Telegram-проверки из runbooks не возобновляются автоматически. Исторические факты и команды: [operations](architecture/TELEGRAM_LAB_OPERATIONS.md), [traffic policy](architecture/TELEGRAM_TRAFFIC_POLICY.md), [oracle](architecture/TELEGRAM_VOICE_EMULATION_LAB.md), [helper](architecture/TELEGRAM_VOICE_LAB_BOOT_RECOVERY.md). Эти направления не добавляют TCP/proxy/routes в плагин.

## Сохранённый будущий backlog

- Cancellation/internal-failure containment; circular start/stop/TTL и stale-session recovery при конкретном основании.
- Diagnostics persistence/reload; retention/cleanup; reboot/residue regression.
- Runtime/service reliability и package/runtime visibility; дальнейшие точечные RU/EN исправления.
- IPv6 Laboratory target support — отдельная архитектурная задача.
- Дополнительный BLOB repository GUI — после согласованного технического контракта владельца.

Эти направления не превращаются в обязательные блокеры текущей HTTP-модернизации или прежних релизов без конкретного затронутого сценария.

## Отложенные исследования

Candidate parallel width выше трёх, endpoint parallelism, cross-batch keep-warm, BLOB/Lua/discovery optimization и Model-C timeout/deadline audit открываются только при новом конкретном дефекте/потребности, материальном изменении архитектуры либо выборе владельца. Завершённые измерения сохранены в истории.

Текущая граница — [START_HERE](START_HERE.md), факты — [PROJECT_STATE](PROJECT_STATE.md), хронология — [ledger](history/current/v0.5.x.md). Roadmap не накапливает ревизионные отчёты.

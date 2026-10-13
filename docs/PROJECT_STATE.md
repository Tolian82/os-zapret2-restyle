# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.2_3`**, открыт владельцем 13.10.2026 без релиза. Поток состояния: `START_HERE -> PROJECT_STATE -> version-line archive`; смена третьего компонента не закрывает линию `v0.5.x`.

## Версия и поставка

- repository: `Tolian82/os-zapret2-restyle`; primary branch: `main`; internal service key: `zapret`;
- `VERSION=0.5.2`, `PLUGIN_REVISION=3` — только незавершённая feature branch / Draft PR [#328](https://github.com/Tolian82/os-zapret2-restyle/pull/328);
- package candidate: `os-zapret2-restyle-0.5.2_3.pkg` — имя кандидата, пакет не опубликован;
- stable Web/pkg: `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`;
- опубликованный testing: `v0.5.0_3` / `os-zapret2-restyle-0.5.0_3.pkg`;
- последний owner-live принятый corrective: `v0.5.0_2`;
- поддерживаемая пакетная база: `FreeBSD:15:amd64`, Python 3.13.

Stable и testing подтверждены чтением GitHub Releases при открытии этапа. Детали поставок находятся в [stable evidence](verification/evidence/2026-08-16-v0.5.0-release-publication.md), [testing evidence](verification/evidence/testing-publications/v0.5.0_3.md) и [owner-live corrective evidence](verification/evidence/2026-08-16-v0.5.0_2-file-picker-owner-live-pass.md). Точный `main`/PR HEAD проверяется при выполнении, не берётся из старого отчёта.

## Установленные факты Voice

1. В feature branch существуют native форма/меню, пять ON/OFF/args полей, shared IPSET, validators/compiler/capture-plan и большой private cutover/recovery набор прежней реализации.
2. Общий backend со «Стратегиями» утверждён: одна постоянная модель, полный generator, один Apply/lifecycle/rollback и один нормальный `dvtws2`. [Нормативный контракт — раздел 12 ТЗ](architecture/VOICE_TRANSMISSION_GUI.md#12-общий-backend-со-стратегиями-утверждено-13102026).
3. [Подробный семиэтапный проект плана](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) подготовлен и перенесён в `v0.5.2`; план и контроль приняты к выполнению прямым поручением владельца начать программирование согласно плану.
4. Полный public Voice ON/OFF/edit/repeat Apply, normal boot, миграция и достоверные per-service статусы пока не завершены. В `_2` общий генератор создал полный detached runtime пяти сервисов; в `_3` добавлен общий firewall install/rollback/commit/verify из release artifacts. Публичное применение и lifecycle ещё не подключены.
5. «Стратегии» пока используют прежний save-then-reconfigure путь. Его rollback/concurrency разрывы устраняются общим Apply на этапе 3, а не объявляются уже исправленными.
6. Полное ТЗ и frontend сохраняются. Разный Voice/Strategies WAN до доказанной изоляции явно отклоняется; WAN-перехват не меняет маршрут. Non-STUN принадлежит ordinary Strategies.

## Что изменилось при открытии v0.5.2

Версия сброшена на новый этап `_1` по поручению владельца. Из активных handoff/state/roadmap/index/ТЗ убраны повторённые отчёты старых ревизий; полные снимки сохранены в [архиве этапа v0.5.1](history/stages/v0.5.1/README.md). Общая линия/канонические правила сохраняются. При переходе на `_1` менялись только metadata/docs. В `_2` изменён общий candidate build, в `_3` подключён общий firewall adapter без отдельного ledger. Проверки install/update/all-OFF/Stop/rollback выполнены с подставным IPFW; native CLI защищён исходным FD9. Frontend, установленный appliance и публичные пакеты сохраняются.

Следующую задачу определяет только [START_HERE](START_HERE.md). Хронология — в [working ledger](history/current/v0.5.x.md); прежние private указания не являются активной очередью.

## Сохраняемая продуктовая база

- DNS считается исправным; старое расследование закрыто до нового воспроизводимого отказа.
- Model C — единственный normal production Stage 60; автоматический A/B fallback удалён. Закрытые измерения Lua/BLOB/discovery/readiness не повторяются без нового основания.
- Strategy Lab поддерживает domain и canonical IPv4 с optional Host/SNI; трафик остаётся привязан к введённому IP, итоговый fixed-IP replay сохраняется. Bare-IP TLS даёт PARTIAL с guidance, bare-IP QUIC без Host/SNI пропускается; Generic UDP независим от Host/SNI/QUIC.
- Enable QUIC сохраняется, defaults OFF; ON/OFF execution и reload/revisit owner-live приняты. Generic UDP сохраняет exact bytes и принятый RU/EN file-picker путь.
- Model-C source-port attribution, конечные бюджеты, cleanup/cancel и Stage-90 восстановление исходной службы сохраняются. Общая архитектура Voice не меняет Laboratory.
- Нормальная служба использует один engine и общий lifecycle lock; Start/Apply/Reconfigure не устанавливают upstream engine автоматически. Его acquisition принадлежит setup/service-manager пути.
- IPv6 Laboratory и дополнительный BLOB GUI остаются отдельным будущим scope, не долгом этой страницы.

## Лаборатория и границы доказательств

Цель Telegram — воспроизводимые UDP-звонки через OPNsense `192.168.1.2` и того же провайдера. Старый UDP-маршрут через `.140` не является действующей базой. Рабочий лабораторный TCP/TLS через внешний Squid parent `185.203.117.88:33128` сохраняется отдельно; HTTP parent не переносит voice UDP.

A1/A2 дали проверенный WAN fake output без ответа/медиа; текущий рабочий Telegram preset и UDP CALL_PASS не доказаны. GUI/CONFIG/BOOT принимаются отдельно от MEDIA_PASS/CALL_PASS. После page/migration baseline продолжается [ограниченная Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).

Squid/sing-box/PF/TCP, маршруты, TNAS и Docker не входят в продуктовую переделку. Ручные TNAS host routes и запуск Docker сохраняются; route Cron/autostart не добавляется. При работе с appliance читать [операционный runbook](architecture/TELEGRAM_LAB_OPERATIONS.md), а не переносить его команды в plugin по умолчанию.

## Completed version-line archives

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)

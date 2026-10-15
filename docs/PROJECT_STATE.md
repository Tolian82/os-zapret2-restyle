# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.2_156`** (feature branch, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328)). Не выпускался и не установлен на OPNsense. Точный следующий шаг и последний CI — [START_HERE](START_HERE.md). Хронология — [working ledger](history/current/v0.5.x.md). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Версия и поставка

- Repository `Tolian82/os-zapret2-restyle`, `main`; service key `zapret`.
- `VERSION=0.5.2`, `PLUGIN_REVISION=156` — пакет только в feature branch.
- package candidate: `os-zapret2-restyle-0.5.2_156.pkg` — **не опубликован**.
- Stable `v0.5.0` / `os-zapret2-restyle-0.5.0_1.pkg`; опубликованный testing `v0.5.0_3`.
- Target platform FreeBSD 15 amd64 / Python 3.13. Последние CI/FreeBSD результаты по точному HEAD находятся в [START_HERE](START_HERE.md), не копируются сюда. `SKIPPED`, offline-only и owner-live непроверенные результаты не считаются PASS.

## Фактическая реализация Voice

1. Форма и единая Config-модель поддерживают Telegram, Discord, X, SIP, Custom, ON/OFF/args, Voice WAN и общие IPv4 IPSET, с RU/EN/help и защитой от устаревших snapshot. `_144` исправила XML-подсказки, `_145` — ошибочную API/RU фразу «активация недоступна» при попытке сохранить ON через all-OFF draft; теперь указан общий Apply, без изменения запрета чернового ON.
2. `backend/orchestrator.sh`, `voice_release_stage.py` и `voice_profile_compiler.py` создают единый Voice+ordinary `traffic.conf`, `dvtws.args`, managed IPSET и port files. `voice_ipfw_adapter._verify_shared_voice_engine` до kernel mutation проверяет точный engine-профиль, порядок, UDP/IPSET/WAN, divert socket и manifest IPFW.
3. `VoiceController::applyAction` и `SettingsController::applyAction` идут через один `zapret shared_apply`, FD9 + штатный Config worker, sealed candidate, native save/readback, rollback и commit. Отдельный normal Voice writer/dvtws2 не добавлен.
4. В `zapret_service.sh` и `apply_runtime.sh` реализованы normal Stop/Start/boot и проверки installed release/процессов/IPFW. `voice_live_inspect.py` и `voice.volt` используют независимые свидетельства; `_138–_140` убрали ложный зелёный статус и проверяют пять профилей.
5. `_146–_147` направили исторический Telegram configctl в общий Config/FD9/Apply/inspect и устранили stale owner. `_148` добавил реальные IPFW rules/counters в read-only native inspector; `_149` безопасно передаёт их через API в существующую RU/EN GUI-строку всех пяти сервисов. Unknown/oversized counters не считаются доказательством MEDIA/CALL; старый Phase-B требует явной миграции.
6. `_152–_156` закрыли отдельный mutating Voice Apply route и старые operator PREPARED commands. FreeBSD package теперь исключает три obsolete private модуля: `voice_native_prepare_route.py`, `voice_native_apply_route.py` и `voice_native_forward_apply.py`; последний больше не имеет установленных production callers. Legacy credentials и sealed PREPARED handoff перенесены в сохранённые read-only helpers. Общий FD9 Apply/Telegram compatibility/read-only inspection не менялись. Остальная old инфраструктура ещё требует caller-driven сокращения.
7. Изолированные проверки находятся в `test-voice-common-runtime.py`, `test-shared-apply-{run,execute,stop,boot}.sh`, `test-voice-gui-contract.py`. **Owner-live GUI/CONFIG/BOOT, UDP/STUN/MEDIA/CALL не подтверждены**. Старый PoC остаётся только объектом ограниченного cleanup/совместимость-аудита.

Границы: неизменное [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), один обычный dvtws2, общий lifecycle и конфигурация; отдельный TCP Squid/sing-box, маршруты и Docker остаются вне plugin. Выбор несовместимого Voice WAN отвергается; не делать глобальный UDP-to-any. Не развивать прежний recovery без конкретного нового дефекта.

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

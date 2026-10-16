# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.2_194`** (published full release `v0.5.2`), main source [1896122](https://github.com/Tolian82/os-zapret2-restyle/commit/18961229801011a201bff1dae22db96692074648). State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`. Publication verified in [release evidence](verification/evidence/2026-10-16-v0.5.2-release-publication.md); owner-live GUI/CONFIG/BOOT/STUN/MEDIA/CALL pending. [START_HERE](START_HERE.md) owns the next task.

`_194` candidate [CI #38955078719](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38955078719) Voice/Project/FreeBSD PASS; [post-merge main #38956106794](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956106794), [trigger #38956106955](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956106955), [full release #38956132121](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956132121) all PASS. The initial `_193` release-preparation failure was corrected in forward-only `_194`; no history or tag rewriting.

## Версия и поставка

- Repository `Tolian82/os-zapret2-restyle`, `main`; service key `zapret`.
- `VERSION=0.5.2`, `PLUGIN_REVISION=194` — exact published stable package source.
- package candidate: `os-zapret2-restyle-0.5.2_194.pkg` — **now published full stable package**: [`os-zapret2-restyle-0.5.2_194.pkg`](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.2/os-zapret2-restyle-0.5.2_194.pkg), release SHA256 and Pages/pkg repository verified by workflow.
- Former stable `v0.5.0` / `0.5.0_1` and testing `0.5.0_3` are historical.
- Target platform FreeBSD 15 amd64 / Python 3.13. Последние CI/FreeBSD результаты по точному HEAD находятся в [START_HERE](START_HERE.md), не копируются сюда. `SKIPPED`, offline-only и owner-live непроверенные результаты не считаются PASS.

## Фактическая реализация Voice

1. Форма и единая Config-модель поддерживают Telegram, Discord, X, SIP, Custom, ON/OFF/args, Voice WAN и общие IPv4 IPSET, с RU/EN/help и защитой от устаревших snapshot. `_144` исправила XML-подсказки, `_145` — ошибочную API/RU фразу «активация недоступна» при попытке сохранить ON через all-OFF draft; теперь указан общий Apply, без изменения запрета чернового ON.
2. `backend/orchestrator.sh`, `voice_release_stage.py` и `voice_profile_compiler.py` создают единый Voice+ordinary `traffic.conf`, `dvtws.args`, managed IPSET и port files. `voice_ipfw_adapter._verify_shared_voice_engine` до kernel mutation проверяет точный engine-профиль, порядок, UDP/IPSET/WAN, divert socket и manifest IPFW.
3. `VoiceController::applyAction` и `SettingsController::applyAction` идут через один `zapret shared_apply`, FD9 + штатный Config worker, sealed candidate, native save/readback, rollback и commit. Отдельный normal Voice writer/dvtws2 не добавлен.
4. В `zapret_service.sh` и `apply_runtime.sh` реализованы normal Stop/Start/boot и проверки installed release/процессов/IPFW. `voice_live_inspect.py` и `voice.volt` используют независимые свидетельства; `_138–_140` убрали ложный зелёный статус и проверяют пять профилей.
5. `_146–_147` направили исторический Telegram configctl в общий Config/FD9/Apply/inspect и устранили stale owner. `_148` добавил реальные IPFW rules/counters в read-only native inspector; `_149` безопасно передаёт их через API в существующую RU/EN GUI-строку всех пяти сервисов. Unknown/oversized counters не считаются доказательством MEDIA/CALL; старый Phase-B выводится из проекта.
6. `_168` — решение владельца: отказаться от всей предыдущей manual legacy Telegram PoC rollback/migration системы и поддержки исторических journal/marker/WAL/receipt как задачи разработки. Удалены private `voice_native_legacy_*` recovery executors, их старый status GUI/API/configd и тестовые пути. Сохранены пять профилей и единая штатная Voice+Strategies FD9/Config Apply архитектура. `_169` удаляет Phase-B prepend, marker activation и отдельные Telegram IPFW-таблицу/правило из штатного runtime. `_170` синхронизирует build-wire тест и ревизию документации. `_171` снимает устаревшее boot-test требование блокировки native Apply по PoC marker/table. `_172` переключает штатный FD9 предконтроль на единственный shared_apply_operation native-gate, без чтения прежних PoC WAL/marker; восстановление и защита уже существующего общего Apply остаются. Исправлены ссылки на удалённый Phase-B source. `_173` удаляет obsolete old predecessor phases/rollback methods в общем durable журнале. `_174` исключает cutover/ledger fallback из штатного Voice-status; historical PoC больше не может дать READY. `_175` отвязывает saved Voice lifecycle/candidate router от старого cutover и IPFW executor, удаляет legacy-poc-preflight CLI. `_176` снимает старые cutover/quiescence/IPFW-runtime импорты с рабочего GUI preview, удаляет test-only private candidate publisher, сохраняя read-only validation. `_177` удаляет все `voice_cutover_*` и старые private executors/их CI-тесты, оставляя только текущий shared Apply, GUI и core STUN/IPFW. Отсутствие старых файлов проверяется и в FreeBSD pkg. `_178` переключает оставшиеся фикстуры общего Apply с PoC-гейта на единственный `preflight_shared_apply_journal` и `native_lifecycle_gate`. `_179` приводит к этому же контракту остаточные saved/activated recovery и render регрессии. `_180` устраняет ещё один устаревший тестовый поиск удалённой `native-voice-checkpoint` рядом с Telegram status в FD9. `_180` [CI #38907807528](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38907807528) полностью квалифицирована, включая FreeBSD 15. `_181` удаляет неиспользуемый частный shell-исполнитель `voice_native_process_lifecycle.sh` и запрещает его возвращение в пакет; штатный общий Stop/Start/Boot остаётся. `_181` [CI #38913309729](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38913309729) Voice/Project/FreeBSD 15 PASS. `_182` заменяет неверные сообщения о старом cutover в актуальном GUI на реальные фазы единого shared Apply и убирает несуществующую процедуру миграции из RU/EN справки. `_182` [CI #38920675327](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38920675327) полностью прошла Voice/Project/FreeBSD. `_183` устраняет подавление ошибок STUN-аргументов из-за предшествующей ошибки IPSET/другого сервиса в PHP GUI precheck и [CI #38924849815](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38924849815) проходит полностью. `_184` устраняет ложное `ready/stopped` в Voice API без аттестованного native-common owner; ответ теперь interrupted, согласован с действующим GUI. `_184` [CI #38932040367](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38932040367) обнаружила старую фикстуру, ожидавшую у API `ready` без подтверждённого владельца. `_185` синхронизирует concurrency test с новой семантикой; production API unchanged.
7. Изолированные проверки находятся в `test-voice-common-runtime.py`, `test-shared-apply-{run,execute,stop,boot}.sh`, `test-voice-gui-contract.py`. **Owner-live GUI/CONFIG/BOOT, UDP/STUN/MEDIA/CALL не подтверждены**. Старый PoC и обратная миграция более не поддерживаются; baseline разработки — новая Config-модель.

Границы: неизменное [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), один обычный dvtws2, общий lifecycle и конфигурация; отдельный TCP Squid/sing-box, маршруты и Docker остаются вне plugin. Выбор несовместимого Voice WAN отвергается; не делать глобальный UDP-to-any. Не сохранять прежний PoC/recovery/rollback-код или legacy совместимость.

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

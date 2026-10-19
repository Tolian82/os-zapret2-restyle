# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.5_1`. `VERSION=0.5.5`, `PLUGIN_REVISION=1`. Владелец 19.10.2026 подтвердил на OPNsense исправленную компоновку наблюдений Voice и корректную RU-локализацию трёх пунктов меню, закрыл обе UI-задачи и прямо поручил полный Web/pkg релиз `v0.5.5_1` (`DEV-034`, `DEV-039`, `CHAT-017`). Успешный GUI не означает подтверждённый Telegram-звонок.

## Подтверждено на установленной `0.5.3_28`

- На OPNsense `192.168.1.2` настоящий Voice Apply сохранил `Telegram ON`, journal `committed`, `voice_inspect.state=ready`, общий `dvtws2` и supervisor verified; таблица `zapret2_voice_telegram` содержит 14 CIDR, правило `19000` на WAN `vtnet1`.
- TNAS `192.168.1.100` доступен SSH на порту `9222`, `tgvoice-lab` running/host, локальный `/results/tgcalls_cli` имеет SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; `route get 91.108.13.10` вернул `via 192.168.1.2 dev ovs_eth1`.
- Один 15-секундный тест рефлектора `91.108.13.10:596` поднял IPFW 19000 с `0/0` до **60 UDP packets / 4080 bytes**. Но оба локальных `tgcalls_cli` клиента закончили `Reconnecting`, `Call established=no`, `BWE non-zero=no`, `TGCALLS_EXIT=1`. Это **PASS только IPFW interception, не MEDIA_PASS**. Прямого доказательства WAN RX, STUN match и ответного Telegram UDP нет.
- Применённый профиль `--filter-l7=stun --payload=stun` не равен предыдущему reflector Hello; нельзя на основании UDP-счётчика заключать, что профиль отправил fake/STUN обработку. Старый `run-a1-opnsense.sh` рассчитан на `zapret2_tgvoice`, не на native `zapret2_voice_telegram`.

**Источник технических деталей и актуальные команды:** [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md); [неизменяемая запись первого live опыта](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md). Подробная история `v0.5.3_1..28` — [old stage release record](releases/v0.5.3.md) и [current-line ledger](history/current/v0.5.x.md). Полный [v0.5.4](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4) опубликован из source `b3c57106`, pkg SHA256 `3cf80db941a701024c15936371ee2d30fb7ef12c0b5209608ff633ba2f9d6bb9`; [workflow](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39172936035) подтвердил GitHub Release и Pages/pkg. Предыдущий v0.5.3 остаётся историческим релизом.

## Нынешняя граница `v0.5.5_1`

**Полный Web/pkg релиз разрешён владельцем; выпуск ожидает CI, тег, GitHub Release и публикацию Pages/pkg.** Состав кандидата сохраняет общий Voice/Strategies Apply, существующий runtime/IPFW и принятые исправления меню/компоновки, без нового функционального изменения. На установленном тестовом пакете пользователь подтвердил постоянное расположение статусов всех пяти профилей под флажками независимо от «справки» и правильные RU-названия «Стратегия», «Передача голоса», «Лаборатория» при загрузке/переключении страниц. [Протокол приёмки](verification/evidence/2026-10-19-v0.5.4_5-voice-ui-menu-owner-acceptance.md). Сохранение конфигурации после обновления до `_1` подтверждено [отдельно](verification/evidence/2026-10-19-v0.5.4_1-voice-upgrade-config-persistence.md). STUN response, media и CALL_PASS по-прежнему не доказаны.

**Единственное следующее техническое действие после релиза:** A2 из [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md): синхронные read-only LAN/WAN PCAP UDP `91.108.13.10:596` для различения ingress, WAN TX/RX, fake и ответов без изменения IPFW/PFIL/Config. Затем A3 валидный STUN responder и A5 реальный двусторонний звонок. Результат публикации `v0.5.5` фиксируется отдельно после выполнения release workflow.

## Минимальное чтение

[Lab runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md) · [Live evidence](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md) · [приёмка Voice](VOICE_CODE_COMPLETION_GATE.md) · [полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [state](PROJECT_STATE.md). Правила `DEV-007`, `DEV-011`, `DEV-034`, `DEV-039`, `CHAT-003` и `GH-039`–`GH-052`.

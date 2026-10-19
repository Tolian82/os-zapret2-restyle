# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.4_1`. `VERSION=0.5.4`, `PLUGIN_REVISION=1`. Владелец 19.10.2026 прямо поручил зафиксировать TNAS/OPNsense laboratory, маршруты и план дальнейших автоматизированных тестов, затем выпустить **полный** релиз `v0.5.4_1`. Это отдельный новый этап разработки (`DEV-034`, `CHAT-017`), не объявление успешного Telegram-звонка.

## Подтверждено на установленной `0.5.3_28`

- На OPNsense `192.168.1.2` настоящий Voice Apply сохранил `Telegram ON`, journal `committed`, `voice_inspect.state=ready`, общий `dvtws2` и supervisor verified; таблица `zapret2_voice_telegram` содержит 14 CIDR, правило `19000` на WAN `vtnet1`.
- TNAS `192.168.1.100` доступен SSH на порту `9222`, `tgvoice-lab` running/host, локальный `/results/tgcalls_cli` имеет SHA-256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`; `route get 91.108.13.10` вернул `via 192.168.1.2 dev ovs_eth1`.
- Один 15-секундный тест рефлектора `91.108.13.10:596` поднял IPFW 19000 с `0/0` до **60 UDP packets / 4080 bytes**. Но оба локальных `tgcalls_cli` клиента закончили `Reconnecting`, `Call established=no`, `BWE non-zero=no`, `TGCALLS_EXIT=1`. Это **PASS только IPFW interception, не MEDIA_PASS**. Прямого доказательства WAN RX, STUN match и ответного Telegram UDP нет.
- Применённый профиль `--filter-l7=stun --payload=stun` не равен предыдущему reflector Hello; нельзя на основании UDP-счётчика заключать, что профиль отправил fake/STUN обработку. Старый `run-a1-opnsense.sh` рассчитан на `zapret2_tgvoice`, не на native `zapret2_voice_telegram`.

**Источник технических деталей и актуальные команды:** [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md); [неизменяемая запись первого live опыта](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md). Подробная история `v0.5.3_1..28` — [old stage release record](releases/v0.5.3.md) и [current-line ledger](history/current/v0.5.x.md). Полный [v0.5.4](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.4) опубликован из source `b3c57106`, pkg SHA256 `3cf80db941a701024c15936371ee2d30fb7ef12c0b5209608ff633ba2f9d6bb9`; [workflow](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39172936035) подтвердил GitHub Release и Pages/pkg. Предыдущий v0.5.3 остаётся историческим релизом.

## Нынешняя граница `v0.5.4_1`

**Код runtime/IPFW/Voice Apply не меняется.** Изменяются VERSION/PLUGIN_REVISION, текущая документация лаборатории, release notes и README. В полном релизе явно указать: подтверждены Config/общий Apply/IPFW interception на устройстве, но не получены рефлекторный ответ, двусторонняя media или CALL_PASS. Данные сайта/пакета, CI и Live — три разных уровня доказательства.

**Единственное следующее действие:** A2 из [native TNAS runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md): синхронно снять read-only LAN/WAN PCAP UDP `91.108.13.10:596`, отличить LAN ingress, WAN TX/RX, fake и наличие ответов; не изменять IPFW/PFIL/Config. Затем A3 валидный STUN packet/responder и A5 реальный двусторонний звонок. Установка/обновление через GUI до v0.5.4_1 и сохранность всех настроек Voice Transmission подтверждены владельцем 19.10.2026 ([evidence](verification/evidence/2026-10-19-v0.5.4_1-voice-upgrade-config-persistence.md)); проверка runtime/IPFW после обновления и CALL_PASS остаются открыты.

## Минимальное чтение

[Lab runbook](architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md) · [Live evidence](verification/evidence/2026-10-19-native-voice-tnas-reflector-first-run.md) · [приёмка Voice](VOICE_CODE_COMPLETION_GATE.md) · [полное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [state](PROJECT_STATE.md). Правила `DEV-007`, `DEV-011`, `DEV-034`, `DEV-039`, `CHAT-003` и `GH-039`–`GH-052`.

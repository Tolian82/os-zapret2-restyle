# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_149`. `VERSION=0.5.2`; `PLUGIN_REVISION=149`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить код по ТЗ, затем один testing release и живые испытания; пока **без релиза и установки на OPNsense**.

## Текущее состояние и доказательства

**Уже реализовано в production code**, не назначать повторно: форма/модель пяти Voice-сервисов и shared IPSET; full Voice+ordinary `traffic.conf`, `dvtws.args`, port files и managed targets через `orchestrator_build_release`; проверка соответствия STUN/ports/IPSET/WAN/divert и scoped IPFW через `voice_ipfw_adapter._verify_shared_voice_engine`; один общий FD9/Config Apply для Voice и Strategies (`shared_apply_run_service`, `shared_apply_execute_service`); normal Stop/Start/boot, read-only native inspect, парное согласование статуса GUI и пяти сервисов. Предыдущий GUI commit [`6ad05b9`](https://github.com/Tolian82/os-zapret2-restyle/commit/6ad05b9113c429b2f2743da7affcef5c0581dec7) (`_140`); [`f6825bf`](https://github.com/Tolian82/os-zapret2-restyle/commit/f6825bf08347f40095a202a7897715623b545623) — только metadata/docs.

Существующие `test-voice-common-runtime.py` и `test-shared-apply-{run,execute,stop,boot}.sh` проверяют указанный общий путь изолированно. Кодовая реализация и CI не означают успешную owner-live установку, GUI/CONFIG/BOOT, STUN/MEDIA_PASS или CALL_PASS.

## Точный следующий шаг и уровень доказательств

**Подтверждение `_148`:** HEAD `f4da990` прошёл [Validate Project, Validate Voice candidates и FreeBSD 15 package build SUCCESS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38776094281). Это CI и пакет, а не работа звонка на OPNsense.

**Функциональный `_149`:** при _148 native inspector и historical Telegram configctl уже знали точные IPFW rule/packet/byte counters, но `VoiceController::inspectAction` отбрасывал их для всех пяти профилей, а страница не могла их показать. Теперь API безопасно передаёт номер проверенного правила (только у реально running ON), проверяет допустимый диапазон/уникальность, принимает только неотрицательные JS-safe integer counters; другие значения скрываются, а не округляются. Существующие RU/EN подсказки каждой галочки дополняются конкретным rule и доступными счетчиками; при stopped/per-profile OFF правила нет, неизвестные packets не подменяют MEDIA/CALL PASS. Компоновка и ТЗ прежние, backend/IPFW/FD9 не менялись.

**Следующее действие:** полный CI и FreeBSD package на итоговом `_149` HEAD, затем только доказанные незакрытые требования. Один testing release после кодовой готовности, старый Phase-B не мигрирует автоматически, owner-live STUN/MEDIA/CALL ещё не проводились.

## Минимальное чтение

После AGENTS и Level-1 rule books: [контроль завершения](VOICE_CODE_COMPLETION_GATE.md), [семиэтапный план и критерии](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [утверждённое ТЗ, включая раздел 12](architecture/VOICE_TRANSMISSION_GUI.md). Текущие факты — [PROJECT_STATE](PROJECT_STATE.md), вся ревизионная хронология — [working ledger](history/current/v0.5.x.md). Старые «next steps» из истории не имеют силы актуальной очереди.

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_149` не опубликована.

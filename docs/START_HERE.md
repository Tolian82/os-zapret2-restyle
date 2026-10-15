# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_144`. `VERSION=0.5.2`; `PLUGIN_REVISION=144`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить код по ТЗ, затем один testing release и живые испытания; пока **без релиза и установки на OPNsense**.

## Текущее состояние и доказательства

**Уже реализовано в production code**, не назначать повторно: форма/модель пяти Voice-сервисов и shared IPSET; full Voice+ordinary `traffic.conf`, `dvtws.args`, port files и managed targets через `orchestrator_build_release`; проверка соответствия STUN/ports/IPSET/WAN/divert и scoped IPFW через `voice_ipfw_adapter._verify_shared_voice_engine`; один общий FD9/Config Apply для Voice и Strategies (`shared_apply_run_service`, `shared_apply_execute_service`); normal Stop/Start/boot, read-only native inspect, парное согласование статуса GUI и пяти сервисов. Предыдущий GUI commit [`6ad05b9`](https://github.com/Tolian82/os-zapret2-restyle/commit/6ad05b9113c429b2f2743da7affcef5c0581dec7) (`_140`); [`f6825bf`](https://github.com/Tolian82/os-zapret2-restyle/commit/f6825bf08347f40095a202a7897715623b545623) — только metadata/docs.

Существующие `test-voice-common-runtime.py` и `test-shared-apply-{run,execute,stop,boot}.sh` проверяют указанный общий путь изолированно. Кодовая реализация и CI не означают успешную owner-live установку, GUI/CONFIG/BOOT, STUN/MEDIA_PASS или CALL_PASS.

## Точный следующий шаг и уровень доказательств

**Предыдущий HEAD `39f771f` (`_143`):** [Validate Project, Voice candidates и FreeBSD 15 package build — SUCCESS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38747912361). Это не owner-live.

**Изменено в `_144`:** в native OPNsense `forms/voice.xml` исправлена устаревшая справка пяти checkbox и info. Теперь она различает Validate (проверка без сохранения), Save inactive draft (только все OFF, без рестарта) и Apply (ON/OFF через общий Config/runtime/IPFW), вместо ошибочной «future activation». Уже существовавшие RU/EN тексты `voice.volt` этому соответствуют. Старый GUI contract проверяет оба представления; комментарий draft-only контроллера уточнён. Компоновка/ТЗ/backend не менялись.

**Следующее действие:** latest-HEAD CI и FreeBSD 15 для `_144`; затем только фактические GUI/API/runtime/package разрывы до единого testing release. Существующие STUN/IPFW/Apply и legacy recovery не переписывать. MEDIA/CALL и owner-live не подтверждены.

## Минимальное чтение

После AGENTS и Level-1 rule books: [контроль завершения](VOICE_CODE_COMPLETION_GATE.md), [семиэтапный план и критерии](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [утверждённое ТЗ, включая раздел 12](architecture/VOICE_TRANSMISSION_GUI.md). Текущие факты — [PROJECT_STATE](PROJECT_STATE.md), вся ревизионная хронология — [working ledger](history/current/v0.5.x.md). Старые «next steps» из истории не имеют силы актуальной очереди.

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_144` не опубликована.

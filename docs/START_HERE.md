# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_141`. `VERSION=0.5.2`; `PLUGIN_REVISION=141`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить код по ТЗ, затем один testing release и живые испытания; пока **без релиза и установки на OPNsense**.

## Текущее состояние и доказательства

**Уже реализовано в production code**, не назначать повторно: форма/модель пяти Voice-сервисов и shared IPSET; full Voice+ordinary `traffic.conf`, `dvtws.args`, port files и managed targets через `orchestrator_build_release`; проверка соответствия STUN/ports/IPSET/WAN/divert и scoped IPFW через `voice_ipfw_adapter._verify_shared_voice_engine`; один общий FD9/Config Apply для Voice и Strategies (`shared_apply_run_service`, `shared_apply_execute_service`); normal Stop/Start/boot, read-only native inspect, парное согласование статуса GUI и пяти сервисов. Предыдущий GUI commit [`6ad05b9`](https://github.com/Tolian82/os-zapret2-restyle/commit/6ad05b9113c429b2f2743da7affcef5c0581dec7) (`_140`); [`f6825bf`](https://github.com/Tolian82/os-zapret2-restyle/commit/f6825bf08347f40095a202a7897715623b545623) — только metadata/docs.

Существующие `test-voice-common-runtime.py` и `test-shared-apply-{run,execute,stop,boot}.sh` проверяют указанный общий путь изолированно. Кодовая реализация и CI не означают успешную owner-live установку, GUI/CONFIG/BOOT, STUN/MEDIA_PASS или CALL_PASS.

## Точный следующий шаг и уровень доказательств

**Реализовано в `_141`:** под исходным FD9 старые mutating `telegram-voice-enable/disable` теперь не заходят в старый reconfigure при committed/pending native shared Apply или установленном native `voice-plan.json` без журнала. Реальные legacy режимы и read-only status сохранены; добавлена регрессия к существующему shared boot/lifecycle тесту.

**Следующее действие:** проверить latest-HEAD общий CI и настоящий FreeBSD 15 package build, затем целенаправленно проверить ещё установленные и используемые legacy PoC entrypoints и package content. Только доказанные остатки удалять с сохранением совместимости. Общий STUN/dvtws2/IPFW/Apply не переписывать.

**Последний CI до изменения:** HEAD `efec440`: [Validate Voice candidates SUCCESS, Validate Project FAILURE](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38734179205), `test-repository-hygiene.sh` требует `START_HERE -> PROJECT_STATE -> version-line archive` в state; FreeBSD SKIPPED. Это документальное требование исправлено; новый HEAD пока не объявлять PASS. Source / CI / owner-live доказательства различать.

## Минимальное чтение

После AGENTS и Level-1 rule books: [контроль завершения](VOICE_CODE_COMPLETION_GATE.md), [семиэтапный план и критерии](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [утверждённое ТЗ, включая раздел 12](architecture/VOICE_TRANSMISSION_GUI.md). Текущие факты — [PROJECT_STATE](PROJECT_STATE.md), вся ревизионная хронология `_1…_140` — [working ledger](history/current/v0.5.x.md). Старые «next steps» из истории не имеют силы актуальной очереди.

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_141` не опубликована.

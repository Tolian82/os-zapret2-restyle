# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_155`. `VERSION=0.5.2`; `PLUGIN_REVISION=155`. Branch `feature/v0.5.1_1-voice-transmission`, [Draft PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328). Решение владельца 15.10.2026: сначала завершить код всех пяти Voice-сервисов по неизменному ТЗ, затем **одна testing-поставка** и owner-live испытания. Без релиза и установки на OPNsense.

## Подтверждённые факты

Уже реализовано в коде, не начинать повторно: единый Voice+Strategies runtime/`dvtws2`, пять Voice-профилей, managed IPv4 IPSET, scoped UDP/STUN/WAN/IPFW, общий FD9/Config Apply, normal Start/Stop/boot и read-only GUI native rule/counters/attestation. CI не доказывает фактический STUN/MEDIA/CALL.

**Последний полностью успешный HEAD:** `_153` `db20ef0`, [CI #38786982877](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38786982877) — Validate Voice candidates, Validate Project, FreeBSD 15 package **SUCCESS**. Для `_154` HEAD `ade226e`, [CI #38790543857](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38790543857): Voice candidates SUCCESS, Project FAIL (`scripts/build-pkg.sh` утратил executable git bit), package SKIPPED. Это точное основание исправления, а не ошибка Voice runtime.

## Текущий рубеж: этап 6

**`_155`:** восстановлен `100755` для `scripts/build-pkg.sh` и штатного `zapret_service.sh`. После проверки import-зависимостей old `voice_native_apply_route.py` больше не нужен в OPNsense package: используемый `sealed_prepared_handoff` перенесён в уже поставляемый `voice_native_forward_stage_prepare.py`; старый source-only CLI сохраняется для изолированных legacy regression tests, но в FreeBSD package staging он удаляется рядом с ранее исключённым `voice_native_prepare_route.py`. Отрицательная проверка package tar contents встроена в существующий FreeBSD CI. Нет нового recovery coordinator, public Apply/GUI/IPFW не меняются.

**Точное следующее действие:** проверить полный CI и реальный FreeBSD 15 package на точном HEAD `_155`, включая отсутствие обоих old operator route файлов в tar. Далее продолжить caller/keep/fold/delete этап 6 для оставшегося legacy code, только после этого testing-поставка. Ошибки устранять по конкретным job logs; owner-live ещё не выполнялся.

## Минимальное чтение

После AGENTS и Level-1 rule books: [completion gate](VOICE_CODE_COMPLETION_GATE.md), [план 6–7](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md), [неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md), [ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_155` не опубликована.

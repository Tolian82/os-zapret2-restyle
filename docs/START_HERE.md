# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_194`. `VERSION=0.5.2`; `PLUGIN_REVISION=194`. Branch `fix/v0.5.2_194-release-check` from `main` `ff32abdb`, release correction PR. [PR #328](https://github.com/Tolian82/os-zapret2-restyle/pull/328) was squash-merged into `main` without publishing a release. Решение владельца: завершить весь код по ТЗ пяти Voice-сервисов, затем полноценный релиз и только после него реальные испытания. Без релиза и установки на OPNsense.

## Последняя подтверждённая квалификация

`_193` HEAD `c0bf8bb`, [CI #38953354911](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38953354911): Voice/Project/FreeBSD 15 **PASS**, [delivery #38953355212](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38953355212) — PASS. Merge `ff32abd` integrated all five services, but post-merge [CI #38954679986](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38954679986) failed on a trailing blank line in the Python helper and [release trigger #38954680028](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38954680028) refused a non-_1 initial `0.5.0 -> 0.5.2_193` version transition. No release tag, assets or Pages for v0.5.2.

## Окончательное решение владельца — 16.10.2026

**Ведётся разработка конечного решения по ТЗ, без сохранения старого Telegram PoC, пятиресурсного rollback, reverse migration, исторических recovery WAL/receipt и их тестов.** Не поддерживать совместимость с отменённым private backend. Удалять ненужные подграфы целиком, без многомесячного последовательного дублирования legacy схем. Корректная обработка ошибок действующего единого Apply остаётся частью штатной архитектуры, но не поводом сохранять старый PoC.

## Текущая граница: релиз после программной готовности

**Последнее решение владельца 16.10.2026:** завершить всё программирование по неизменному ТЗ пяти Voice-сервисов, затем **выпустить полноценный релиз**, и лишь после него проводить owner-live GUI/CONFIG/BOOT/STUN/MEDIA/CALL испытания. Ни промежуточных установок, ни live-тестов до релиза; релиз при известных критических дефектах также недопустим. Исправления в рабочем коде и exact-HEAD CI остаются обязательными до выпуска.

**`_194` — release correction on immutable `main`:** `PR #328` has merged and must never be rebased/reset. The initial merge from `0.5.0` to `0.5.2_193` did not satisfy the `_1` transition gate; this is preserved as historical failed release-trigger evidence. The release tag was NOT created. The next merge keeps `VERSION=0.5.2` (no new transition), increments the package revision to `194` for the packaged Python trailing-blank-line correction, and uses the exact permitted release subject `v0.5.2_194: Prepare release v0.5.2`. It may trigger publication **only after** exact-HEAD Voice/Project/FreeBSD CI and post-merge `main` checks pass. No history rewrite or bypass of guards.

**Точное следующее действие:** проверить CI correction PR `_194`, затем squash-merge с `expected_head_sha` и указанным release subject, проверить `main` integrity + release trigger и фактический tag/asset/checksum/Pages pkg-repo. Если публикация снова откажет — сначала читать exact-job logs и исправлять только доказанную причину. Никаких owner-live до полной публикации.

Старый Telegram PoC, Phase-B migration, marker и private recovery исключены решением владельца; удаление завершено ранее. Полная история ревизий находится только в [current ledger](history/current/v0.5.x.md).

## Минимальное чтение

[Completion gate](VOICE_CODE_COMPLETION_GATE.md) · [План завершения](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) · [Неизменное ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Current ledger](history/current/v0.5.x.md).

Stable `v0.5.0`, опубликованный testing `v0.5.0_3`; `v0.5.2_194` не опубликована.

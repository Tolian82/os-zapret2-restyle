# os-zapret2-restyle — текущее состояние v0.6.x

State-line scope: **`v0.6.x`**.

Текущий этап — **`v0.6.0_1`**, package candidate: `os-zapret2-restyle-0.6.0_1.pkg`; `VERSION=0.6.0`, `PLUGIN_REVISION=1`. Владелец прямо разрешил полноценный релиз v0.6.0 и переход документации v0.5.x → v0.6.x. **Публикация ещё не подтверждена**: сначала CI и squash merge `v0.6.0_1: Prepare release v0.6.0`, затем immutable tag, FreeBSD15 GitHub Release package/SHA256SUMS и Pages/pkg. [Release plan](releases/v0.6.0.md).

## Унаследованные проверенные функции

- Native OPNsense Zapret2 `dvtws2`: общий Strategies/Voice Config/Apply, native service/IPFW, Strategy Lab и сохранённые настройки. При смене версии реализация не меняется.
- Ручная установка Lua/BIN из [дополнительного каталога](https://github.com/Tolian82/zapret2-extra-resources) и Advanced-only Remove с точным локальным Git HEAD списком стандартных файлов, подтверждением количества, сохранением Config и проверкой реального Stop→quarantine→общего Apply/Start или отката.
- На предыдущих точных пакетах наблюдались native ошибки/восстановления, GUI Install→Remove→upstream-only Job→repeat Install. На установленном `v0.5.9_47` подтверждены native RUNNING и неизменный Config/IPFW, справка после F5, Lua слева/BIN справа, штатные зелёные/дополнительные синие. [Формально принятое владельцем закрытие Stage 11 с ограничениями](verification/evidence/2026-10-27-v0.5.9_47-stage11-owner-final-acceptance.md).
- Особые live-случаи (F5 во время удаления, потеря ответа, ошибка записи кэша на устройстве, OFF draft, медиа Voice и установка собственно `v0.6.0_1`) не проверены и не называются PASS. Stage 12 README/CI был закрыт [PR #672](https://github.com/Tolian82/os-zapret2-restyle/pull/672).
- Предыдущий полный stable [v0.5.8](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.8). Новая версия должна быть действительно опубликована, а не только размечена тегом.

## Архитектура и навигация

[Remove specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) · [Remove plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md) · [Voice](architecture/VOICE_TRANSMISSION_GUI.md) · [Strategy Lab](architecture/STRATEGY_LAB.md) · [current v0.6.x ledger](history/current/v0.6.x.md) · [v0.5.x frozen ledger](history/current/v0.5.x.md). Exclude Domains не изменяются; `--ipset-exclude`, Jail и отменённый clean repair не возвращаются.

## Архивы завершённых линий

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)
- [v0.5.x archive](history/archive/v0.5.x.md)

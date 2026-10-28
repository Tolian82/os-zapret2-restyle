# os-zapret2-restyle — текущее состояние v0.6.x

State-line scope: **`v0.6.x`**. Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

Текущий этап — **`v0.6.1_1`**; `VERSION=0.6.1`, `PLUGIN_REVISION=1`; package candidate: `os-zapret2-restyle-0.6.1_1.pkg` (**development identity only; not published or installed**). The already published stable package remains `os-zapret2-restyle-0.6.0_1.pkg`. Владелец прямо разрешил полноценный релиз v0.6.0 и переход документации v0.5.x → v0.6.x. **Полный стабильный релиз опубликован:** [v0.6.0](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.0), точный [FreeBSD15 пакет](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.6.0/os-zapret2-restyle-0.6.0_1.pkg) SHA-256 `7bd6f9099efe09755bc1c2d4c9c228bcc51ae2a2a8478c949636c2527bb064a9`, immutable tag на релизном коммите `0d9c9490049f4c0cfae1201f1c3981649ae024a8`. Полный [workflow #40578282190](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40578282190) завершился успешно, включая pkg и GitHub Pages; независимая HTTP-проверка Pages и Web-установка на устройстве не выполнялись. [Факты публикации](verification/evidence/2026-10-27-v0.6.0-full-release-publication.md).

## Унаследованные проверенные функции

- Native OPNsense Zapret2 `dvtws2`: общий Strategies/Voice Config/Apply, native service/IPFW, Strategy Lab и сохранённые настройки. При смене версии реализация не меняется.
- Ручная установка Lua/BIN из [дополнительного каталога](https://github.com/Tolian82/zapret2-extra-resources) и Advanced-only Remove с точным локальным Git HEAD списком стандартных файлов, подтверждением количества, сохранением Config и проверкой реального Stop→quarantine→общего Apply/Start или отката.
- На предыдущих точных пакетах наблюдались native ошибки/восстановления, GUI Install→Remove→upstream-only Job→repeat Install. На установленном `v0.5.9_47` подтверждены native RUNNING и неизменный Config/IPFW, справка после F5, Lua слева/BIN справа, штатные зелёные/дополнительные синие. [Формально принятое владельцем закрытие Stage 11 с ограничениями](verification/evidence/2026-10-27-v0.5.9_47-stage11-owner-final-acceptance.md).
- Особые live-случаи (F5 во время удаления, потеря ответа, ошибка записи кэша на устройстве, OFF draft, медиа Voice и установка собственно `v0.6.0_1`) не проверены и не называются PASS. Stage 12 README/CI был закрыт [PR #672](https://github.com/Tolian82/os-zapret2-restyle/pull/672).
- Предыдущий стабильный релиз — [v0.5.8](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.8). Текущий стабильный — [v0.6.0](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.6.0); установка владельцем пакета `v0.6.0_1` отдельно ещё не проверена.

## Архитектура и навигация

[Remove specification](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_SPEC.md) · [Remove plan](architecture/ZAPRET2_EXTRA_RESOURCES_REMOVE_PLAN.md) · [Voice](architecture/VOICE_TRANSMISSION_GUI.md) · [Strategy Lab](architecture/STRATEGY_LAB.md) · [current v0.6.x ledger](history/current/v0.6.x.md) · [v0.5.x frozen ledger](history/current/v0.5.x.md). Historical Remove did not modify Exclude Domains or `--ipset-exclude`; this was **scope-specific**, not a veto of the subsequently approved independent Exclude IPSet/dual-stack task. Jail and the cancelled clean-repair feature remain out of scope.

## Current first-priority approved development (28 October 2026)

[Global Exclude IPSet and IPv4/IPv6 specification](architecture/ZAPRET2_EXCLUDE_IPSET_SPEC.md) is the **current product target**; its [nine-stage, 160-row per-file plan](architecture/ZAPRET2_EXCLUDE_IPSET_PLAN.md) is the execution authority. Stage 0 recorded the approved scope. **Stage 1 source/CI qualification is complete:** [PR #681](https://github.com/Tolian82/os-zapret2-restyle/pull/681) merged as [merged main 02fa191](https://github.com/Tolian82/os-zapret2-restyle/commit/02fa191436da2d22100ba20c0ac236d8ff531a72); [successful source/FreeBSD CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/40648449795) passed real Targets integration, Voice/Strategies runtime contracts, the project matrix and FreeBSD 15 package build. Post-merge main CI also passed. Six-list compiler and deterministic manifest are now in main. This is **not** installed IPv6 acceptance or a published package. Other Voice and GUI validation paths remain IPv4-oriented; no native global exclusion semantics or installed IPv6 behavior have been qualified; FreeBSD CI package evidence is not a published package. The approved contract bans explicit/effective `/0` in every user-controlled include/exclude IP list (including Voice), applies IP exclusion to every Strategies/Voice profile, and keeps Exclude Domains domain-only without DNS conversion or Voice/STUN injection. Stage 6 additionally includes the **approved Strategy Lab-only** default-OFF IPv6 checkbox beneath Mode and authoritative Standard 150/200-second, Extended 270/350-second one-job budgets for single/eligible dual-family tests; this has not yet been implemented. New **Voice-page** P2P UDP-port fields, its separate proposed checkbox, any-destination capture and media behavior remain **deferred** in [DECISIONS](DECISIONS.md). Preserve one OPNsense Config and the shared `zapret` runtime/IPFW lifecycle; source tests, CI/package results and installed FreeBSD15 proof remain separate gates. The current immutable published package identity is still `0.6.0_1`.

## Архивы завершённых линий

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)
- [v0.5.x archive](history/archive/v0.5.x.md)

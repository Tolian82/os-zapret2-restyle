# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.2_194`. Published full release `v0.5.2`, package `os-zapret2-restyle-0.5.2_194.pkg`. `VERSION=0.5.2`, `PLUGIN_REVISION=194`. Exact immutable release-preparation main merge [1896122](https://github.com/Tolian82/os-zapret2-restyle/commit/18961229801011a201bff1dae22db96692074648) from PR #329 after implementation PR #328.

## Последняя подтверждённая квалификация

[Candidate CI #38955078719](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38955078719): Voice/Project/FreeBSD PASS. [Main integrity #38956106794](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956106794): PASS. [Release trigger #38956106955](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956106955): PASS. [Full release #38956132121](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956132121): all four jobs PASS. Annotated tag `v0.5.2` points to exact main release merge. [Publication evidence](verification/evidence/2026-10-16-v0.5.2-release-publication.md).

## Точное следующее действие

Владелец установил порядок: **завершить код → полноценный релиз → реальные тесты на OPNsense**. Код и релиз выполнены. **Теперь требуется owner-live приёмка опубликованного `v0.5.2_194`:** GUI/CONFIG/BOOT и сохранённые профили, затем WAN/UDP/STUN, отдельно MEDIA/CALL. Ни один из этих реальных результатов пока не помечать PASS; CI/IPFW counters не доказывают успешный звонок.

Пять сервисов Telegram/Discord/X/SIP/Custom и неизменный frontend ТЗ сохранены, общий native Config/FD9/один dvtws2/IPFW реализованы. Старый Telegram PoC, marker, private rollback/reverse migration не восстанавливать. Исторические main/release-trigger ошибки первой попытки и forward-only исправление зафиксированы в [current ledger](history/current/v0.5.x.md).

## Минимальное чтение

[Voice acceptance](VOICE_CODE_COMPLETION_GATE.md) · [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [Release evidence](verification/evidence/2026-10-16-v0.5.2-release-publication.md) · [PROJECT_STATE](PROJECT_STATE.md).

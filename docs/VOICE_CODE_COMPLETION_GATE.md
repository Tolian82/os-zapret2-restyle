# «Передача голоса» — послерелизная функциональная приёмка

Опубликован [полный релиз v0.5.2](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.2), FreeBSD 15 amd64 package `0.5.2_194`; [publication evidence](verification/evidence/2026-10-16-v0.5.2-release-publication.md). Решение владельца 16.10.2026: код → полный релиз → реальные тесты. Первые два этапа завершены.

## Подтверждено кодом и CI

Все пять Voice-сервисов Telegram/Discord/X/SIP/Custom, RU/EN/help, shared IPSET/Config, FD9 Apply, один dvtws2, scoped UDP/IPFW/WAN, обычный Start/Stop/boot и GUI status реализованы. [CI #38955078719](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38955078719) Voice/Project/FreeBSD PASS; [release #38956132121](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/38956132121) validates and publishes exact package/assets/Pages. CI не доказывает STUN/MEDIA/CALL.

## Следующий этап: owner-live PENDING

1. GUI/CONFIG: установить опубликованный пакет; проверить RU/EN, пять сервисов, обе страницы, ON/OFF, shared IPSET и stale-form guards.
2. Runtime/BOOT: один dvtws2, точные IPFW rules/tables/WAN/ports, Start/Stop и сохранённые профили после reboot без ручного enable.
3. UDP/STUN: отдельные подтверждения local/forwarded capture, IPSET/WAN scope и реального STUN.
4. MEDIA/CALL: повторяемое двустороннее медиа и настоящий звонок, без ложного PASS от одних счётчиков.

Реальные испытания **не проводились**. Старый Telegram PoC/marker/private recovery не возвращать. TCP/proxy/TNAS/Docker вне нового плагинного lifecycle. [ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) · [START_HERE](START_HERE.md).

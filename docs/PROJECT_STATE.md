# os-zapret2-restyle — текущее состояние v0.5.x

State-line scope: **`v0.5.x`**. Текущий этап — **`v0.5.3_1`**: исправление поставки и наблюдаемая приёмка Voice. State-flow: `START_HERE -> PROJECT_STATE -> version-line archive`. [START_HERE](START_HERE.md) задаёт следующее действие; [план](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) — порядок и критерии.

## Версия и поставка

- `VERSION=0.5.3`, `PLUGIN_REVISION=1`; package candidate: `os-zapret2-restyle-0.5.3_1.pkg`. Этап открыт прямым решением владельца 17.10.2026. Пакет/релиз v0.5.3 ещё не опубликован; исходники GUI на этой границе не исправлены.
- Последняя опубликованная версия — `v0.5.2`, пакет `0.5.2_194`, source `18961229801011a201bff1dae22db96692074648`. [Публикация и её CI](verification/evidence/2026-10-16-v0.5.2-release-publication.md) подтверждены; владелец подтвердил установку через GUI.
- Целевая платформа — OPNsense 26.7 / FreeBSD 15 amd64 / Python 3.13. Наблюдённая система владельца — OPNsense 26.7.3_8.

## Подтверждённый отказ и граница доказательств

| Сценарий | Факт |
|---|---|
| Открытие `/ui/zapret/voice` из меню в `_194` | Отказ: «Страница не найдена», сообщение и снимок владельца от 17.10.2026 |
| Причина в исходниках | В UI namespace отсутствует `VoiceController.php`; `voiceAction` находится в `IndexController`. API VoiceController не обслуживает `/ui/` |
| CI предыдущего пакета | Проверки исходников, симуляции и FreeBSD-сборка выполнены; не подтверждают открытие страницы |
| Новая поставка | Пока только утверждённые правила/план и переход версии; исправление и проверки ожидаются |
| Полное GUI/CONFIG/BOOT/STUN/MEDIA/CALL | Не принято; открытие GUI имеет подтверждённый отказ, остальные живые сценарии не подтверждены |

## Сохраняемая реализация и ограничения

В исходниках уже существуют пять профилей Telegram/Discord/X/SIP/Custom, формы RU/EN/help и shared IPSET, единая Config-модель, общий FD9 Apply обеих страниц, один dvtws2, scoped UDP/IPFW/WAN и normal Start/Stop/boot. Эти исходники являются базой исправления, а не доказательством готового установленного продукта. Проверки compiler/runtime/lifecycle сохраняются; следующий объём определяется найденным дефектом.

[ТЗ](architecture/VOICE_TRANSMISSION_GUI.md) и общая архитектура остаются прежними. Старый Telegram PoC, marker, private rollback/migration не возвращаются. TCP/Squid/sing-box/PF/NAT, маршруты, TNAS и Docker вне текущей правки. Несовместимый Voice WAN явно отклоняется; глобальный UDP-to-any не допускается.

Уточнены существующие `DEV-007`, `DEV-011`, `DEV-018` и `CHAT-003`: каждый участок имеет наблюдаемый результат; блокер исправляется до перехода дальше; отчёт явно разделяет изменение, выполненную проверку и неподтверждённое. Новая переделка архитектуры найденным дефектом не обоснована.

## Сохраняемая продуктовая база

- DNS считается исправным; старое расследование закрыто до нового воспроизводимого отказа.
- Model C — единственный normal production Stage 60; автоматический A/B fallback удалён. Закрытые измерения Lua/BLOB/discovery/readiness не повторяются без нового основания.
- Strategy Lab поддерживает domain и canonical IPv4 с optional Host/SNI; трафик остаётся привязан к введённому IP, итоговый fixed-IP replay сохраняется. Bare-IP TLS даёт PARTIAL с guidance, bare-IP QUIC без Host/SNI пропускается; Generic UDP независим от Host/SNI/QUIC.
- Enable QUIC сохраняется, defaults OFF; ON/OFF execution и reload/revisit owner-live приняты. Generic UDP сохраняет exact bytes и принятый RU/EN file-picker путь.
- Model-C source-port attribution, конечные бюджеты, cleanup/cancel и Stage-90 восстановление исходной службы сохраняются. Общая архитектура Voice не меняет Laboratory.
- Нормальная служба использует один engine и общий lifecycle lock; Start/Apply/Reconfigure не устанавливают upstream engine автоматически. Его acquisition принадлежит setup/service-manager пути.
- IPv6 Laboratory и дополнительный BLOB GUI остаются отдельным будущим scope, не долгом этой страницы.

## Лаборатория и границы доказательств

Цель Telegram — воспроизводимые UDP-звонки через OPNsense `192.168.1.2` и того же провайдера. Старый UDP-маршрут через `.140` не является действующей базой. Рабочий лабораторный TCP/TLS через внешний Squid parent `185.203.117.88:33128` сохраняется отдельно; HTTP parent не переносит voice UDP.

A1/A2 дали проверенный WAN fake output без ответа/медиа; текущий рабочий Telegram preset и UDP CALL_PASS не доказаны. GUI/CONFIG/BOOT принимаются отдельно от MEDIA_PASS/CALL_PASS. После page/migration baseline продолжается [ограниченная Docker campaign](architecture/TELEGRAM_VOICE_DOCKER_STRATEGY_CAMPAIGN.md).

Squid/sing-box/PF/TCP, маршруты, TNAS и Docker не входят в продуктовую переделку. Ручные TNAS host routes и запуск Docker сохраняются; route Cron/autostart не добавляется. При работе с appliance читать [операционный runbook](architecture/TELEGRAM_LAB_OPERATIONS.md), а не переносить его команды в plugin по умолчанию.

## Completed version-line archives

- [v0.1.x archive](history/archive/v0.1.x.md)
- [v0.2.x archive](history/archive/v0.2.x.md)
- [v0.3.x archive](history/archive/v0.3.x.md)
- [v0.4.x archive](history/archive/v0.4.x.md)

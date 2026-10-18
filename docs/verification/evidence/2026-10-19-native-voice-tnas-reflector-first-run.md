# 2026-10-19 — установленная v0.5.3_28, native Voice / TNAS reflector

**Источник:** точный owner-live вывод CLI OPNsense + TNAS SSH/Docker, скрин GUI в переписке; эти результаты не являются частью CI и не означают ответ сервера.

## Согласованный базис

- `pkg info -x os-zapret2-restyle` ранее подтвердил `0.5.3_28`.
- GUI Telegram включён, Config `saved_voice_on=true`; общий Apply `committed`, `voice_inspect.state=ready`, `engine_verified=true`, `supervisor_verified=true`, `telegram.capture_verified=true`, `telegram.media_verified=false`.
- GUI Telegram Parameters: `--filter-udp=*`, `--filter-l7=stun`, `--payload=stun`, `--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2`. Эти параметры ориентированы на STUN, а фиксированный рефлектор использует другой UDP payload.
- IPFW `19000 0 0 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1` до опыта.
- `ipfw table zapret2_voice_telegram list`: 14 CIDR; `91.108.12.0/22` содержит `91.108.13.10`. `udp_ports=1-65535`.
- OPNsense SSH → TNAS успешно, `route get` точно `91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1`.
- Docker `tgvoice-lab` running=true, network=host; `tgcalls_cli` SHA256 `7ad8a2eef607e92056e8e8311519d36616c45ca19f1403601bbed8e8db01f3dc`.

## One-shot измерение

Команда в контейнере:

```text
timeout -k 5 60 docker exec tgvoice-lab /results/tgcalls_cli --mode reflector --reflector 91.108.13.10:596 --duration 15
```

Полученный owner-live результат:

```text
Caller: created (version 13.0.0)
Callee: created (version 13.0.0)
Caller state: Reconnecting
Callee state: Reconnecting
Duration: 15s
Mode: reflector (91.108.13.10:596)
Call established: no
BWE non-zero: no
Errors: none
TGCALLS_EXIT=1
```

После опыта:

```text
19000 60 4080 divert 989 udp from any to table(zapret2_voice_telegram) out not diverted not sockarg xmit vtnet1
```

`configctl zapret voice_inspect`: `ready`, `telegram.rule_packets=60`, `telegram.rule_bytes=4080`, `capture_verified=true`, `media_verified=false`, `runtime.call_verified=false`. Состояние службы и общего движка осталось подтверждённым.

## Закрыто / не закрыто

- **Подтверждено на устройстве:** сохранённый native Telegram ON, Config+common Apply, single dvtws2/supervisor, IPFW/table, маршрут TNAS через OPNsense, наличие и запускаемость tgcalls в Docker, счётчик захвата +60/+4080.
- **Не подтверждено:** что каждый пакет прошёл WAN, что `dvtws2` сгенерировал fake, что reflector вообще обязан отвечать на этот payload, что пришли UDP ответы, корректное STUN-согласование, аудио, настоящий звонок.
- **Негативный конкретный результат:** `tgcalls_cli` остался Reconnecting и завершился `1`. Не переписывать как `MEDIA_PASS` или `CALL_PASS`.
- **Следующий опыт:** A2 синхронный LAN/WAN PCAP/UDP RX, затем отдельный STUN-aware A3 в [current runbook](../../architecture/TELEGRAM_NATIVE_VOICE_TNAS_LAB.md).

Граница публичности: не хранить реальные credentials, приватные ключи, пользовательские идентификаторы вызовов или чувствительный PCAP в репозитории.

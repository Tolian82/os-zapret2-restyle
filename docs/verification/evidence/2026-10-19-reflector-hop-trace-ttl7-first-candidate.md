# 2026-10-19 — Telegram reflector ICMP hop trace; proposed first fake-TTL trial

**Proof level:** OWNER-LIVE for read-only hop trace on installed `os-zapret2-restyle-0.5.5_1`. **TTL=7 is a proposed, unexecuted candidate, not a measured fix.** A2 proved UDP WAN transmission without inbound UDP reply; A3a separately proved native STUN/fake outbound to unvalidated UDP/3478; both remain distinct from non-STUN reflector/media.

## Observed ICMP trace

Executed on OPNsense through same WAN `vtnet1`, explicitly from `192.168.80.251`:

```sh
/usr/sbin/traceroute -n -I -i vtnet1 -s 192.168.80.251 -m 12 -q 1 -w 1 91.108.13.10
```

| Hop | Observed reply | RTT |
|---:|---|---:|
| 1 | `192.168.80.1` | 1.130 ms |
| 2 | `95.165.0.1` | 4.862 ms |
| 3 | `212.188.6.45` | 6.429 ms |
| 4 | `*` | none |
| 5 | `195.34.53.206` | 4.132 ms |
| 6 | `139.45.225.162` | 4.479 ms |
| 7 | `87.245.232.206` | 159.810 ms |
| 8–11 | `*` | none |
| 12 | `91.108.13.10` | 149.613 ms |

Hop limit 12 yielded an ICMP response from the target. The unknown hops do not prove loss, and ICMP path behavior is not proof of reachable UDP/596, of reflector protocol response, or DPI location.

## Selected one-variable, one-run candidate (NOT YET EXECUTED)

- **Target:** existing Telegram Reflector Hello `91.108.13.10:596` through TNAS→OPNsense→unchanged upstream; engine 13 `tgcalls_cli`, existing container/route/native Telegram Voice.
- **Modified profile:** **ordinary Traffic Strategy profile 4 only**, IPv4, existing Telegram managed IPSET, UDP 596–599, `--payload=unknown`. Do not change native Voice STUN profile 1.
- **Only changed parameter:** `ip_ttl=7` inside the existing two-repeat zero16 `fake` action, keeping payload, original forwarding, checksum, endpoint, repetitions, NAT, TCP/proxy and process mode unchanged.
- **Original exact action:** `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`.
- **Single test action:** `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2:ip_ttl=7`.
- **Basis:** hop 7 is visible, target was seen at hop 12 with ICMP. TTL 7 may expire substantially before the target and could cross an earlier DPI. It could also expire **before** DPI or take a different path. Neither the hop where DPI sits nor the result is known. The `ip_ttl=N` mechanism is supported by upstream Zapret2 Lua `apply_fooling` and example config; actual installed behavior must be qualified on WAN.
- **Scope of next run:** one fresh 15-second existing Docker reflector run after GUI Save/Apply of *only* Strategy profile 4, short WAN PCAP showing 16-byte fake and 40-byte original UDP TTL/valid checksums and scoped ICMP Type 11/3. Never use the obsolete `run-a1-opnsense.sh`. PASS of controlled mutation requires short fake TTL in WAN capture, normal original TTL ≈63, valid original payload, and no alteration of native Voice profile.
- **Stop/classify:** if all wire invariants hold, classify receipt/reconnect/media; no UDP reply remains NO_REPLY_UNKNOWN, not disproof of any DPI arrangement. If TTL is not selectively modified, treat as configuration/engine experiment failure and do not advance. Max one candidate before evaluating; no automatic sweep or modification of other services.
- **Owner restoration:** after this single trial, return exactly to original Strategy 4 action via GUI Save/Apply, verify active `traffic.conf` contains the original line without `:ip_ttl=7`, and Voice Telegram profile 1 still unchanged. Save the original GUI text before the change. No manual writes to active `runtime-v2` files.

This is a plan plus ICMP evidence only; no TTL=7 GUI change or reflector media result is claimed at this point.

## Owner-live follow-up: first GUI Apply blocked, no TTL7 wire run


**19.10.2026 — TTL7 GUI Apply BLOCKED (без сетевого опыта):** владелец попытался заменить `fake ... repeats=2` на `...:ip_ttl=7` **в обычном поле «Стратегии»**; GUI ответил `Результат применения неизвестен`. Последующее root **read-only** наблюдение: journal phase `committed`, `page=voice`, changed_fields `voice.telegram.enabled` (без новой committed Strategies-операции); `/conf/config.xml` Strategy `SAVED_OLD_EXACT=1`, `SAVED_TTL7_EXACT=0`, active `runtime-v2/traffic.conf` `ACTIVE_OLD_EXACT=1`, `ACTIVE_TTL7_EXACT=0`; `SPLIT_LUA=false` в обоих **сохранённых** текстах, service `running`; `/var/run/zapret2-execution.status` по-прежнему `8|8|ready|ok|2026-10-19T15:34:03+0300|release build is ready`. **Новый сетевой тест с TTL7 не проводился и не разрешён до выяснения причины Apply.** Скриншот прежнего Voice `Telegram Parameters` с `fake:payload=unknown` относится к другой странице и запрещён штатным STUN валидатором, его не следует изменять. Точная исходная причина сбоя Strategies Apply пока неизвестна. В установленном PHP `SettingsController::applyAction` не различает returned `preflight-rejected=...` и послеоперационную неопределённость, а catch `Throwable` может маркировать и pre-dispatch отказ как requires_review. **Следующая точка:** посмотреть только последние приватные `shared-work` кандидат-артефакты (наличие, флаги без XML секретов) и сообщения об ошибках в configd/PHP логах, **не повторяя Apply**, затем исправить конкретный blocker/диагностику кода, если подтверждён.

This changes the previously *proposed* run status to **BLOCKED**. The saved and active Strategy 4 did not change; the older common Voice journal entry remained terminal committed. No media result or source-code fix is inferred.

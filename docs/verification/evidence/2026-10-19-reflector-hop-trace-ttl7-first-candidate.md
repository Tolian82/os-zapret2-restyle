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

## 19 October 2026 — owner correction: stop proposed TTL7 Apply, do not bypass validation

The owner identified the plugin's established strategy syntax protection as the likely reason the proposed `fake:...:ip_ttl=7` did not pass and challenged the assumption that an Apply defect was responsible. The PHP GUI only displayed `result uncertain`; without an exact engine/stage rejection, **neither an invalid Lua expression nor a broken GUI validator has been proven as the root cause**. Saved and active Strategy4 remain original, no TTL7 packet trial took place.

Upstream bol-van/zapret2 does document `ip_ttl=N` as an argument to `fake` (see `lua/zapret-antidpi.lua` `function fake` calling `rawsend_payload_segmented`, `lua/zapret-lib.lua` `desync_opts` and `apply_fooling`, and `docs/readme.md` example `--lua-desync=fake:blob=0x00000000:ip_ttl=5`). Upstream **also** has a *separate* `--lua-desync=pktmod:ip_ttl=N` option affecting the current/real packet; this is **not semantically interchangeable** with modifying fake TTL. These upstream facts do not prove exact installed engine acceptance or the project's strategy validation contract. `validator_validate_engine_mapped` explicitly notes `--dry-run` **does not validate Lua execution**.

**Operational decision:** reclassify prior `ip_ttl=7` GUI recipe as an **unexecuted, suspended hypothesis, NOT an approved action**. Do not install testing `0.5.5_3` *solely* to retry the same unqualified expression, or weaken/bypass the syntax guard. That testing package improves error classification, not the parser/validator behavior or proof of the original rejection. Next bounded step: read-only inspect the installed Lua/engine compatibility and locate the actual preflight reason before designing any new strategy candidate. No new network tests until then.

## 2026-10-19 — owner read-only installed Lua capabilities verified

- Installed upstream Git short SHA: `6b6c63e3385f`; installed tag: `v1.0.5.2`, matching GitHub exact tag target full commit `6b6c63e3385fa73f8af3be4a69171e947f5a319d`.
- Owner supplied local SHA256 prefixes: `dvtws2` `310e931cf0741ffd`, `zapret-antidpi.lua` `31c9dd75b0bd55e9`, `zapret-lib.lua` `b67a470f23b00a8d` (record only prefixes; not asserted equivalent to GitHub blob SHA or upstream release digest).
- Installed Lua structural checks ALL YES: `FAKE_FUNCTION`, `DESYNC_OPTIONS`, `SEGMENT_FOOLING`, `TTL_IMPLEMENTATION`. Exact upstream 1.0.5.2 has the same supported `fake`/`ip_ttl` composition and repeats option, so the explanation that fake TTL requires a *different* Lua function is not supported for this version.
- GUI refusal cause **still unknown**: user saw generic status; archived Config/runtime show original profile only; no TTL7 run. `--dry-run` validates engine CLI/parameters but does not execute Lua. Next uniquely informative, isolated read-only-in-effect test is one in-memory candidate argv substitution against installed binary with `--dry-run`, **not** an Apply or network experiment.

## 2026-10-19 — owner-live in-memory installed dvtws2 TTL7 dry-run: PASS

Executed on the installed OPNsense host with `/usr/local/bin/python3.13` (no config/runtime/file writes): read active `/usr/local/etc/zapret2/runtime-v2/dvtws.args`, confirm **exactly one** match of `--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:repeats=2`, create a Python in-memory argv copy with only that token appended `:ip_ttl=7`, invoke `/usr/local/etc/zapret2/binaries/my/dvtws2` with `--dry-run`. Owner supplied:

- `EXACT_PROFILE_MATCHES: 1`, `CHANGED_ARGUMENTS: 1 (in memory only)`.
- `DRY_RUN_EXIT: 0`, `STDERR: (empty)`, `command line parameters verified`.
- Engine reported `self-built version Oct 2 2026 17:42:03 lua_compat_ver 6`, **5** user-defined desync profiles; Telegram IPSET **14** entries; other hostlists loaded.
- No on-disk Config, GUI or active runtime alteration, no IPFW or network side effect, no Telegram reflector traffic.

**Narrow verdict:** engine command-line validation accepts combined `fake:...:repeats=2:ip_ttl=7` with the other active arguments. The installed Lua sources also support the path. This does **not** demonstrate runtime Lua execution; `--dry-run` explicitly does not. **Original GUI fault attribution remains unresolved**: the UI has an AJAX `.fail()` branch that presents generic uncertain error on HTTP/network exceptions, and an API `requires_review` branch that presents the same generic warning. Without the captured HTTP response/stage receipt from the original failed Apply, neither one can be inferred. Do not repeat prior A0-A3a or perform an unobserved retry; the next diagnostic should focus on the GUI-to-API response boundary using available existing logs or an explicitly agreed single instrumented attempt later.

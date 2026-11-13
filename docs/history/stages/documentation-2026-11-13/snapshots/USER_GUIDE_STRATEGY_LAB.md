# Historical source — docs/USER_GUIDE_STRATEGY_LAB.md

**ARCHIVED / LEVEL 3.** Original text at `277ef0536b217841ab6728ae9561dbc4792fef01` (`v0.6.5_14`), relocated during the 13 November 2026 documentation review. Its dated statuses, commands, proposed work and duplicated rules are historical, not current instructions. Local links are rebased; original prose is preserved. Current authority: [documentation index](/docs/INDEX.md).

# Using Strategy Lab

This guide describes the current packaged client. The approved [Chrome HTTP development plan](../../browser-http-2026-10-22/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) is not implemented yet; its future behavior must not be inferred from an old QUIC result.

Open **Services → Zapret2 → Diagnostics**.

Enter a domain that your ISP blocks. Use **Standard** for the primary TLS 1.3 search, with a finite adaptive budget whose configured Standard base is 150 seconds. Use **Extended** when TLS 1.2, plain HTTP, optional QUIC bypass testing, or a configured request-response UDP check is also needed; Extended has a configured additional 120-second base; actual finite budgets depend on eligible work.

## Enable QUIC

Extended mode shows **Enable QUIC** directly below **Generic UDP (optional)**.

- It is unchecked by default.
- Its checked/unchecked state is saved and survives a page reload.
- Unchecked means QUIC candidates are not tested.
- Checked means QUIC candidates are tested even when the Stage-30 control probe reports ordinary QUIC/IPv4 as blocked.

If every required endpoint already passes the direct HTTPS baseline, the job finishes without candidate or Extended testing, including QUIC. A bare IPv4 target requires Host/SNI for QUIC.

The control probe remains diagnostic information only. It no longer decides whether QUIC testing runs. This allows Strategy Lab to search for a QUIC bypass specifically when the provider blocks ordinary QUIC.

## Generic UDP

Generic UDP is optional and available only in Extended mode. To enable it for a job, provide both:

- a destination UDP port from `1` to `65535`;
- a payload file containing `1..4096` bytes.

Both values are required together. A file larger than 4096 bytes is rejected with a visible validation message before a new job starts; multi-megabyte files are intentionally not accepted as request payloads.

The page shows State, Outcome, and stages 00–99 and retains completed evidence. **Stop** persists cancellation, terminates the active bounded runner, and still completes cleanup and Zapret2 restoration before another lifecycle operation can run. Reloading Diagnostics recovers the active or newest completed job.

The stable-candidate table shows up to three candidates. Candidate number one is the default recommendation, but Strategy Lab never writes it to Settings automatically.

The compact green two-rectangle icon beside `Job: job.XXXX` copies exactly that displayed Job ID to the clipboard; it does not start or modify a job. Use it to reopen a saved result.

**Temporary circular validation** is offered only after a completed successful domain job has a valid three-to-five-item shortlist and verified restoration. It starts one temporary target-scoped profile for browser or application testing. Stop it when testing is complete (there is also a 300-second safety limit). It temporarily runs a separate dvtws2 and IPFW interception for matching TLS/TCP443 target addresses; the rules may affect other LAN clients accessing those addresses during the test. It cycles 3–5 eligible TLS 1.3 finalists rather than installing a permanent configuration. The saved Traffic Strategy remains unchanged, and Zapret2 state is restored on successful cleanup.

## Transferring a verified result safely (P4)

Read the final replay evidence for each *specific* port, protocol and endpoint before copying anything. Compare the recommended result with the already saved Traffic Strategy: first-match profile order, `--filter-tcp`/`--filter-udp`, `--filter-l7`, and the selected HOSTLIST/IPSET all matter. If a new Lua handler targets the same profile, place its `--payload`, `--in-range` and `--out-range` filters followed by the `--lua-desync` action **inside that profile**. Those in-profile filters affect subsequent Lua instances until changed. Use `--new` only for a separate profile and check whether an earlier profile would already select the same traffic. Keep unrelated profiles and user data unchanged. HTTP/TLS success never automatically proves QUIC/UDP, STUN/WireGuard or Voice media. Neither native `--dry-run` nor a Lab candidate is a general guarantee of ISP DPI bypass.

## Безопасный перенос результата в Стратегии (P4)

Сначала изучите итоговое подтверждение для **конкретного** порта, протокола и конечной точки. Сравните результат с сохранённой стратегией: порядок профилей и первое совпадение, `--filter-tcp`/`--filter-udp`, `--filter-l7`, HOSTLIST/IPSET. Если нужен дополнительный Lua-обработчик внутри того же профиля, разместите подходящие `--payload`, `--in-range` и `--out-range` перед его `--lua-desync` **внутри этого профиля**. Эти фильтры действуют на следующие Lua-вызовы до переопределения. Самостоятельный профиль добавляйте через `--new`, проверив приоритет уже существующих профилей. Не заменяйте несвязанные профили и не меняйте пользовательские значения. Успех HTTP/TLS сам по себе не подтверждает QUIC/UDP, STUN/WireGuard и Voice media; `--dry-run` и результат лаборатории не гарантируют обход DPI.

**A17 candidate note (source revision `v0.6.4_35`):** The Lab's button copies the complete profile only; it does **not** save/apply it. Final `profile_replay.verified` is retained per displayed row so that a saved/unverified candidate cannot receive the verified-success message. Compare transport/port, L7, payload, range and Lua actions with the existing first-match profile before a manual edit. Insert a matching additional handler inside its profile; create an independent profile only with `--new`. Other profiles and Voice must remain untouched. The installed RU/EN GUI test and owner A17 remain pending until evidenced.

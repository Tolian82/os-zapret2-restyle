# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.6_1`; `VERSION=0.5.6`, `PLUGIN_REVISION=1`. Documentation-only update; no change to the published package.

## Current task — approved Strategy Lab modernization

The [detailed English development plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) and [requirements](REQUIREMENTS.md) (`BH-01`–`BH-12`) now specify an explicit independent-OR reachability rule: **verified target TLS handshake OR verified target QUIC handshake OR genuine final target HTTP response is sufficient**. An HTTP response counts as accessible, including 4xx/5xx and without requiring a complete body; a separate handshake report is not necessary if the response is genuine. Stages 1–6, Model C, attribution and Stage 90 remain unchanged.

Chrome-default TLS 1.2/1.3 is allowed; HTTP/1.1 and HTTP/2 are equally acceptable. Direct HTTPS success by **either TLS handshake or real HTTPS response** skips QUIC. Forced TLS 1.2 stays in Extended. For every build, fetch the available FreeBSD `latest` package using ugorur's approach, referencing lexiforest; do not pin or select by version. Use one Chrome profile supported by the actual binary. These decisions are settled.

**Implementation boundary:** No new client, probe migration or newly specified QUIC checks have been implemented yet. Source audit is not installed OPNsense acceptance. See [PROJECT_STATE](PROJECT_STATE.md).

## Single next action

**After a separate owner instruction to start implementation, begin Stage 1:** bundle the current FreeBSD `latest` curl-impersonate privately, select one supported Chrome profile, and verify real target TLS/QUIC signals. The genuine HTTP-response success path is a cross-cutting Stage 2/3 requirement. Keep `v0.5.6_1` for this documentation-only change; no stable release is authorized.

Stage 1 outcome: executable client and licenses in pkg, CA, Chrome profile, final pkg SHA-256, real FreeBSD 15 TLS/QUIC signals; any genuine HTTP response is positive reachability evidence, not merely diagnostics. No pin/check on upstream version. Cross-cutting source migration is Stage 2; stable release is not scheduled.

## Minimum stage-specific reading

1. [REQUIREMENTS](REQUIREMENTS.md) — разделы Strategy Lab и `BH-01`–`BH-12`.
2. [Подробный план](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — аудит, технические решения и этап 1.
3. Для изменения поиска: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).
4. Для Extended/результатов: [QUIC control](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [unified shortlist](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [прежняя live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

## Сохранённые границы

- Полный [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; GitHub/FreeBSD15/Pages проверены, установка `0.5.6_1` через GUI владельцем не подтверждена. Это не блокирует документационную работу. [Запись публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Telegram Voice-исследования закрыты владельцем с отрицательным результатом в его прямом тракте. Новые звонки, STUN/capture, TTL/fake и маршрутные опыты не входят в текущую работу. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

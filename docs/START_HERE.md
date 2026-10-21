# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.6_3`. `VERSION=0.5.6`, `PLUGIN_REVISION=3`. Stage 1 CA trust failure confirmed on installed `v0.5.6_2`; the explicit-CA private Chrome launcher and truthful local-readiness check are now included in the published FreeBSD 15 testing package `_3`. Owner-live TLS/QUIC acceptance for `_3` remains pending.

## Current task — approved Strategy Lab modernization

The [detailed English development plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) and [requirements](REQUIREMENTS.md) (`BH-01`–`BH-12`) now specify an explicit independent-OR reachability rule: **verified target TLS handshake OR verified target QUIC handshake OR genuine final target HTTP response is sufficient**. An HTTP response counts as accessible, including 4xx/5xx and without requiring a complete body; a separate handshake report is not necessary if the response is genuine. Stages 1–6, Model C, attribution and Stage 90 remain unchanged.

Chrome-default TLS 1.2/1.3 is allowed; HTTP/1.1 and HTTP/2 are equally acceptable. Direct HTTPS success by **either TLS handshake or real HTTPS response** skips QUIC. Forced TLS 1.2 stays in Extended. For every build, fetch the available FreeBSD `latest` package using ugorur's approach, referencing lexiforest; do not pin or select by version. Use one Chrome profile supported by the actual binary. These decisions are settled.

**Stage 1 earlier `_2` evidence:** [CI run 39583956850](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39583956850) qualified the FreeBSD 15 package and ran the actual private binary under FreeBSD 15.0. The [testing prerelease v0.5.6_2](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_2) is tied to source `4166a38d6653e7faa560c86205af25519895e989` and [publication evidence](verification/evidence/testing-publications/v0.5.6_2.md). Its bundled Chrome profile is `chrome150` (upstream `2.2.3_1` was observed, **not pinned**). Owner confirmed `pkg info -x os-zapret2-restyle` -> `os-zapret2-restyle-0.5.6_2` and the read-only check -> `CURL_IMPERSONATE_READY profile=chrome150` on OPNsense on 21 October 2026 ([evidence](verification/evidence/2026-10-21-v0.5.6_2-private-curl-readiness-owner.md)). Network TLS/QUIC handshakes have NOT been reported. Stage 2/3 production probe migration is not implemented. Source audit is not installed OPNsense acceptance. See [PROJECT_STATE](PROJECT_STATE.md).

**Stage 1 `_3` delivery:** [FreeBSD15 CI PASS](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/39588528210), [testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.6_3/os-zapret2-restyle-0.5.6_3.pkg) with selected Chrome client, explicit CA launcher, and local-only status. Publisher verified signed release/tag/digest; no on-appliance CA selection or TLS/QUIC handshake has yet been observed.

## Single next action

**Single next action:** install the verified [v0.5.6_3 testing package](https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.5.6_3/os-zapret2-restyle-0.5.6_3.pkg) on OPNsense and use its `run-curl-impersonate.sh` for certificate-verified TLS and `--http3-only` QUIC. The launcher selects an existing OPNsense/FreeBSD trusted PEM bundle, fails clearly when absent, and never disables peer verification. The updated checker confirms **local** readiness only, not network reachability. Stay on Stage 1 until live handshake/HTTP response evidence is obtained. The genuine HTTP-response success path is a cross-cutting Stage 2/3 requirement. The `v0.5.6_2` test package remains published but its TLS/QUIC probes failed with curl(77) loading trust anchors. `v0.5.6_3` has been [published for testing](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6_3), SHA-256 `923f488ded4cd2c4bcbabadc14a566bb9536d19b88793e2f83db20483e96d027`, source/tag `6d2c67aa9a5f7291a5a8319e6779f9464787f2cb` ([evidence](verification/evidence/testing-publications/v0.5.6_3.md)). The stable Pages/pkg release remains unchanged.

Stage 1 package evidence: private executable, licenses, Chrome profile, source pkg digest, FreeBSD15 ABI and package SHA-256 `e3d79a7a519b1d09ae755d0df9873b38b1adbe58bff7cf8eb8bb7001ec24acf2` are known. The owner reported `TLS_EXIT=77` and `QUIC_EXIT=77` while loading `/etc/ssl/cert.pem`; neither handshake nor HTTP response was verified. [Live defect evidence](verification/evidence/2026-10-21-v0.5.6_2-ca-trust-failure.md). Any genuine target HTTP response will be positive evidence as specified in the approved requirements. No pin/check on upstream version. Cross-cutting source migration is Stage 2; stable release is not scheduled.

## Minimum stage-specific reading

1. [REQUIREMENTS](REQUIREMENTS.md) — разделы Strategy Lab и `BH-01`–`BH-12`.
2. [Подробный план](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md) — аудит, технические решения и этап 1.
3. Для изменения поиска: [основная архитектура](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).
4. Для Extended/результатов: [QUIC control](architecture/STRATEGY_LAB_QUIC_CONTROL.md), [unified shortlist](architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md), [прежняя live-матрица](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

## Сохранённые границы

- Полный [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) опубликован из `b319aafe748c1363712f5d7d6cbaaf40396bb64c`; GitHub/FreeBSD15/Pages проверены, установка `0.5.6_1` через GUI владельцем не подтверждена. Это не блокирует документационную работу. [Запись публикации](verification/evidence/2026-10-20-v0.5.6-full-release-publication.md).
- Telegram Voice-исследования закрыты владельцем с отрицательным результатом в его прямом тракте. Новые звонки, STUN/capture, TTL/fake и маршрутные опыты не входят в текущую работу. [Заключение](verification/evidence/2026-10-20-telegram-native-voice-provider-blocked-final-closure.md).

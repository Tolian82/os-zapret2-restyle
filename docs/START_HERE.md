# os-zapret2-restyle — START HERE

[PROJECT_STATE.md](PROJECT_STATE.md) · [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md) · [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) · [CHAT_RULES.md](CHAT_RULES.md) · [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) · [ROADMAP.md](ROADMAP.md) · [INDEX.md](INDEX.md).

**Current handoff identity:** `v0.5.7_2`. `VERSION=0.5.7`, `PLUGIN_REVISION=2`. This is the new Stage-1 source candidate, not a stable release.

## Current work — Stage 1 of Strategy Lab modernization

The owner authorized implementation of the [six-stage English plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md). The first implementation scope bundles signed, prebuilt FreeBSD `latest` `curl-impersonate` privately, without pinning its upstream version; it discovers one existing plain Chrome profile from the acquired package's wrapper set. Its own shared library and licenses are included and the system curl is unchanged.

Stage-1 source paths: `scripts/build-private-curl-impersonate.sh` called by `scripts/build-pkg.sh`; the package's private entrypoint is `/usr/local/libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate`, with `PROFILE` and `PROVENANCE`. The standalone Python read-only readiness API is `strategy_lab_py/browser_client.py:check_ready`. **Stage 1 does not switch production Strategy Lab HTTP requests** or introduce a new service lifecycle. The actual Stage-00 call of the readiness API is part of the Stage-2 migration before stopping Zapret2. Do not claim Chrome probing is active in an installed plugin yet.

The accepted endpoint accessibility rule for future Stage 2/3 is independent OR: verified target TLS handshake **or** verified target QUIC handshake **or** a genuine final target HTTP response. HTTP 2xx–5xx count and a full body is unnecessary; all target identity, certificate and required attribution checks still apply. Standard HTTP/1.1 and HTTP/2 are equal, and direct HTTPS success skips QUIC.

## Single next action

**Finish Stage-1 candidate qualification and persistent GitHub testing-package publication for `v0.5.7_2`; then begin Stage 2 on a new versioned candidate.** Qualification requires a successful FreeBSD 15 package build containing the private client/lib/licenses and the selected Chrome profile, a runnable binary, CA readiness, and available direct TLS/QUIC evidence. If real target handshake evidence has not been obtained, explicitly leave that acceptance item unverified; do not claim FreeBSD package existence proves wire behavior. Stable release requires a separate owner order.

## Required specialist reading

1. [Stage plan](architecture/STRATEGY_LAB_BROWSER_HTTP_PLAN.md), especially Stage 1 and the Stage-2 boundary.
2. [BH-01–BH-12 requirements](REQUIREMENTS.md).
3. `scripts/build-pkg.sh`, `scripts/build-private-curl-impersonate.sh` and the FreeBSD package job in `.github/workflows/ci.yml`.
4. For actual probe migration later: [Strategy Lab architecture](architecture/STRATEGY_LAB.md), [Model C](architecture/STRATEGY_LAB_MODEL_C.md), [adaptive search](architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md), [budgets](architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md).

## Preserved boundaries

The published stable [v0.5.6](https://github.com/Tolian82/os-zapret2-restyle/releases/tag/v0.5.6) and its stable OPNsense package feed are unchanged. The Stage-1 test package does not authorize full release. The closed Telegram Voice provider experiment remains closed.

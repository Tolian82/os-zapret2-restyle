# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-15
**Current handoff identity:** published testing `v0.4.1_19`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=19`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_19.pkg` / `v0.4.1_19`;
- `_19` testing-package SHA-256: `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`;
- `_19` source merge/testing-tag target: `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`;
- `_19` publication workflow run: `31892344832`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by testing `_N`: **no**.

Machine `_19` publication evidence: [`verification/evidence/testing-publications/v0.4.1_19.md`](verification/evidence/testing-publications/v0.4.1_19.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Accepted current live boundary

Do not repeat accepted Model-C, QUIC-ON, QUIC-OFF execution, Generic UDP, already-accessible-target, or Settings Apply work without fresh contradictory evidence.

Accepted owner-live/product facts include:

- Generic UDP exact-byte path on `_16` with `udp-140.bin`, port `53`, all three current UDP candidates and truthful no-reply semantics;
- Enable QUIC ON with all four current QUIC candidates visible;
- Enable QUIC OFF execution semantics: OFF suppresses QUIC candidate execution while independent Generic UDP remains active;
- visible Stage-90 restoration on the tested flows;
- already-accessible-target behavior is complete by owner confirmation;
- Settings Apply validation/guards and post-Apply service-state correctness are complete by owner confirmation.

Enable QUIC OFF/default persistence across an actual reload/revisit remains a separate live acceptance row. `_19` preserves the existing model-backed default/load/save source contract.

## `_18` owner-live follow-up

The owner installed published `_18` and confirmed `Лаборатория стратегий`, `UDP порт (опционально)`, and the one-line `Заблокированный домен / IP`. The same screenshot rejected the 12 px typography workaround and field alignment and selected `_19` together with deterministic mode/status/sidebar localization.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md).

## `_19` published implementation

`_19` is now source/CI/FreeBSD/package-publication complete:

- removed the 12 px blocked-domain label workaround and restored normal UI typography;
- kept `Заблокированный домен / IP` on one line through an explicit fixed label/value-column contract;
- domain input, Generic UDP input and Enable QUIC checkbox use one common value-column x-position;
- RU mode values: `Стандартный` / `Расширенный`; EN: `Standard` / `Extended`;
- right-aligned mode label: RU `Режим:` / EN `Mode:`;
- ordinary idle: RU `ожидание` / EN `idle`;
- navigation canonical names: `Strategy` / `Laboratory`, with deterministic RU presentation `Стратегия` / `Лаборатория` on the Laboratory page;
- no Strategy Lab search/runtime semantics changed;
- circular ordinary-state and Enable QUIC persistence source contracts remain guarded.

Source patch record: [`patches/v0.4.1_19.md`](patches/v0.4.1_19.md).

## Immediate owner-live acceptance

1. verify RU normal typography, one-line blocked-domain label, and domain / UDP / QUIC alignment;
2. verify `Режим:`, `Стандартный`, `Расширенный`, `Статус: ожидание`;
3. verify sidebar `Стратегия` / `Лаборатория`;
4. verify EN `Mode:`, `Standard`, `Extended`, `Status: idle`, `Strategy` / `Laboratory` and no RU leakage;
5. separately prove Enable QUIC OFF/default persistence across reload/revisit;
6. next engineering plan: add Laboratory target support for IP addresses as well as domains;
7. continue the remaining risk-selected backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.

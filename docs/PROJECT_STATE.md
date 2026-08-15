# os-zapret2-restyle — Current state for `v0.4.x`

**Status:** CURRENT SECOND-COMPONENT STATE · LEVEL 1
**Updated:** 2026-08-15
State-line scope: **`v0.4.x`**

Direct orientation:

- exact revision handoff: [`START_HERE.md`](START_HERE.md);
- documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md);
- project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md);
- chat rules: [`CHAT_RULES.md`](CHAT_RULES.md);
- GitHub rules: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md);
- master plan: [`ROADMAP.md`](ROADMAP.md);
- current-line chronology/proof: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

Current-work state-flow: `START_HERE -> PROJECT_STATE -> version-line archive`.

## Repository and package facts

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- project version: `0.4.1`;
- current packaged revision: `_19` / `PLUGIN_REVISION=19`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_19.pkg` / `v0.4.1_19`;
- `_19` testing-package SHA-256: `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`;
- `_19` source merge/testing-tag target: `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`;
- `_19` publication workflow run: `31892344832`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_19`;
- internal service key: `zapret`.

Machine `_19` publication evidence: [`verification/evidence/testing-publications/v0.4.1_19.md`](verification/evidence/testing-publications/v0.4.1_19.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` established explicit Enable QUIC as the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability remains diagnostic only.
- `_15` owner-live QUIC ON observability remains accepted: four attempted QUIC IDs are visible while ordinary QUIC is blocked.
- `_16` Generic UDP browser-to-job path is **OWNER-LIVE PASS** with exact 140-byte payload evidence.
- `_16` Enable QUIC OFF execution semantics are **OWNER-LIVE PASS**: OFF suppresses QUIC candidates while independent UDP remains active.
- already-accessible target is **COMPLETE by owner confirmation**.
- Settings Apply validation/guards and post-Apply service-state correctness are **COMPLETE by owner confirmation**.
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_19` preserves the existing source persistence contract.

## `_18` owner-live Laboratory follow-up

Published `_18` owner-live Russian UI confirmed `Лаборатория стратегий`, `UDP порт (опционально)`, and one-line `Заблокированный домен / IP`. The owner rejected the 12 px typography workaround and resulting alignment and selected `_19` together with mode/status/sidebar localization.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md).

## `_19` source/package implementation — complete

`_19` has passed source validation, the complete Strategy Lab corrective matrix, focused Laboratory localization/layout regression, FreeBSD-15 package qualification, exact-head source merge, and persistent testing publication.

Implemented:

- normal blocked-domain label typography; `_18` 12 px override removed;
- fixed shared label/value columns for domain / Generic UDP / Enable QUIC;
- RU mode values `Стандартный` / `Расширенный`; EN `Standard` / `Extended`;
- right-aligned `Режим:` / `Mode:` adjacent to the mode selector;
- RU idle `ожидание`; EN idle `idle`;
- menu canonical names `Strategy` / `Laboratory`, plus deterministic active Laboratory-page RU `Стратегия` / `Лаборатория`;
- focused regression retains prior circular ordinary-state behavior and Enable QUIC persistence source contract;
- Strategy Lab search/runtime semantics are unchanged.

Source PR `#254` merged exact candidate source as `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`. Testing publication `v0.4.1_19` is verified with SHA-256 `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`.

Source patch record: [`patches/v0.4.1_19.md`](patches/v0.4.1_19.md).

## Current owner-live verification boundary

After `_19` install:

1. RU layout/typography/mode/idle/sidebar live check;
2. EN mode/idle/sidebar and no-language-leakage live check;
3. Enable QUIC OFF/default persistence after reload/revisit;
4. next selected engineering plan: Laboratory targets must support IP addresses as well as domains;
5. continue the remaining risk-selected backlog.

## Accepted owner-live evidence retained

- Generic UDP: [`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md)
- QUIC OFF execution/UI follow-up: [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md)

## Documentation authority note

The owner’s latest instruction is current truth. Earlier hypotheses remain historical evidence only and do not override newer controlled owner-live results.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Package-affecting source changes continue through persistent testing publication and the required publication-record tail. `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).

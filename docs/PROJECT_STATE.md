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
- current source candidate: `_19` / `PLUGIN_REVISION=19`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- `_18` testing-package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- `_18` source merge/testing-tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- `_18` publication workflow run: `31889449879`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_18`;
- internal service key: `zapret`.

Machine `_18` publication evidence: [`verification/evidence/testing-publications/v0.4.1_18.md`](verification/evidence/testing-publications/v0.4.1_18.md).

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

Published `_18` was installed and the owner supplied a live Russian-mode screenshot.

Visible PASS:

- `Лаборатория стратегий`;
- `UDP порт (опционально)`;
- one-line `Заблокированный домен / IP`.

Visible defects selecting `_19`:

- blocked-domain label typography became visibly too small because `_18` used a 12 px workaround;
- owner rejected the resulting field alignment and requires domain / UDP / QUIC controls to use one explicit shared x-position with normal typography;
- mode selector presentation still needs deterministic RU `Стандартный` / `Расширенный`, EN `Standard` / `Extended`;
- add right-aligned RU `Режим:` / EN `Mode:` directly before the selector;
- ordinary RU idle must be `ожидание`, EN remains `idle`;
- sidebar must be EN `Strategy` / `Laboratory`, RU `Стратегия` / `Лаборатория`.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md).

## `_19` source implementation

Implemented in the current source candidate:

- `PLUGIN_REVISION=19`;
- normal blocked-domain label typography; the `_18` 12 px override is removed;
- fixed shared label/value columns for domain / Generic UDP / Enable QUIC;
- RU mode values `Стандартный` / `Расширенный`; EN `Standard` / `Extended`;
- right-aligned `Режим:` / `Mode:` adjacent to the mode select;
- RU idle `ожидание`; EN idle `idle`;
- menu canonical names `Strategy` / `Laboratory`, plus deterministic active Laboratory-page RU/EN text;
- focused regression covers layout, mode/status/sidebar strings, prior circular idle behavior and Enable QUIC persistence source contract;
- Strategy Lab search/runtime semantics are unchanged.

Source patch record: [`patches/v0.4.1_19.md`](patches/v0.4.1_19.md).

## Current verification boundary

Before source merge/publication `_19` must pass:

1. focused Laboratory RU/EN/layout/persistence contract;
2. complete project + Strategy Lab corrective matrix;
3. FreeBSD-15 package build/inspection qualification;
4. exact latest-head merge;
5. persistent `v0.4.1_19` testing publication and publication-record reconciliation.

After publication/install:

1. RU layout/typography/mode/idle/sidebar live check;
2. EN mode/idle/sidebar and no-language-leakage live check;
3. Enable QUIC OFF/default persistence after reload/revisit;
4. next selected product plan: Laboratory targets must support IP addresses as well as domains;
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

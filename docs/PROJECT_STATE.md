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
- current packaged source revision: `_18` / `PLUGIN_REVISION=18`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- testing-package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- source merge/testing-tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- publication workflow run: `31889449879`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_18`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_18.md`](verification/evidence/testing-publications/v0.4.1_18.md).

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
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_18` preserves the source persistence contract guarded in `_17`.

## `_17` owner-live RU follow-up

Published `_17` was installed and the owner supplied live Russian-mode Diagnostics screenshots.

Visible PASS on the tested screen:

- domain-connectivity title/help/action;
- `Заблокированный домен / IP`;
- `Запуск`;
- `Включить QUIC`;
- translated result/stage presentation including `Полный профиль Стратегий Трафика`;
- ordinary circular idle output is localized human text instead of raw JSON braces.

Visible remaining defects selected and corrected in `_18` source:

- `Strategy Lab` was still English;
- `Generic UDP (optional)` was still English;
- `Заблокированный домен / IP` wrapped to two lines; owner requested the domain input to move slightly left and the Generic UDP value control plus Enable QUIC control to share the same new alignment.

Evidence: [`verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md).

## `_18` published implementation

Published `_18` implements the owner-selected narrow presentation/layout corrective:

- RU `Strategy Lab` -> `Лаборатория стратегий`;
- RU `Generic UDP (optional)` -> `UDP порт (опционально)`;
- EN retains `Strategy Lab` / `Generic UDP (optional)`;
- Strategy Lab domain, Generic UDP and Enable QUIC rows use one shared label/value-column contract;
- the value controls are shifted slightly left from `_17`;
- the long RU blocked-domain label is constrained to one line with a bounded 190 px / 12 px label presentation and reduced inter-cell padding;
- focused diagnostics regression asserts the new RU/EN labels and alignment while retaining circular idle and Enable QUIC persistence source contracts;
- Strategy Lab runtime/search semantics are unchanged;
- latest-head full project/corrective CI and FreeBSD-15 package qualification passed;
- exact source merge is `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- `v0.4.1_18` package/tag/asset were persistently published and verified with the digest above.

Source patch record: [`patches/v0.4.1_18.md`](patches/v0.4.1_18.md).

## Current owner-live verification boundary

1. install `_18` and verify Russian title / UDP label / one-line blocked-domain label / aligned domain-UDP-QUIC controls;
2. verify English mode and no cross-language leakage;
3. prove Enable QUIC OFF/default persistence after reload/revisit;
4. continue the next risk-selected regression from `ROADMAP.md`.

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

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
- current source candidate: `_20` / `PLUGIN_REVISION=20`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_20.pkg` / `v0.4.1_20`;
- `_20` testing-package SHA-256: `5d5fae0a79054ad807a92ca7804d5984d63782927c667962b6395d48627ab64a`;
- `_20` source merge/testing-tag target: `d732965c143563352e18ac58c209aeb30a6d4feb`;
- `_20` publication workflow run: `31896330680`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_20`;
- internal service key: `zapret`.

Machine `_20` publication evidence: [`verification/evidence/testing-publications/v0.4.1_20.md`](verification/evidence/testing-publications/v0.4.1_20.md).

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
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_20` preserves the existing source persistence contract.

## `_19` owner-live Laboratory follow-up — partial

Published `_19` was installed and directly compared with the Zapret Strategy page and a native OPNsense settings page. RU `Режим:`, `Расширенный` and `Статус: ожидание` were visible, but the owner rejected final layout acceptance because the Laboratory perimeter was too large, the field value column did not match the normal OPNsense form grid, and `Режим:` needed guaranteed typography parity with the target label.

Durable evidence: [`verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md).

## `_20` source/package implementation — complete

`_20` has passed focused Diagnostics/Laboratory layout/localization/persistence validation, the complete project + Strategy Lab corrective matrix, FreeBSD-15 package qualification, exact-head source merge, and persistent testing publication.

Implemented:

- shared native-style `25%` field-label column for both the top domain-connectivity table and Strategy Lab input table;
- target, Generic UDP and Enable QUIC use the same normal OPNsense value-column position;
- rejected `_19` fixed `250px` Laboratory label column removed;
- long RU target label remains one line at normal UI typography;
- `Режим:` / `Mode:` computed font size and line height are copied from the target field-label computed style;
- nested Laboratory page/container/row/column margin/padding is neutralized to avoid a second perimeter inset;
- `_19` RU/EN presentation, Strategy Lab search/runtime, Generic UDP, QUIC and persistence semantics remain unchanged.

Source merge/tag target: `d732965c143563352e18ac58c209aeb30a6d4feb`. Published package SHA-256: `5d5fae0a79054ad807a92ca7804d5984d63782927c667962b6395d48627ab64a`.

Source patch record: [`patches/v0.4.1_20.md`](patches/v0.4.1_20.md).

## Current verification boundary

After `_20` install:

1. one owner-live visual comparison of Laboratory against Strategy/native OPNsense perimeter and field grid;
2. confirm `Режим:` matches target-label typography;
3. no Strategy Lab execution rerun is required for this visual-only correction;
4. separately prove Enable QUIC OFF/default persistence after reload/revisit;
5. after `_20` acceptance, next selected engineering plan: Laboratory targets must support IP addresses as well as domains;
6. continue the remaining risk-selected backlog.

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

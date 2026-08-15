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
- current source candidate: `_21` / `PLUGIN_REVISION=21`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_20.pkg` / `v0.4.1_20`;
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
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_21` preserves the existing source persistence contract.

## `_20` owner-live Laboratory follow-up — perimeter/navigation rejected

The owner installed `_20` and directly compared Laboratory, Strategy and a native OPNsense page.

Confirmed defects:

- Laboratory has no normal OPNsense outer content perimeter/frame;
- Strategy/native comparison retains the normal platform spacing;
- Russian `Стратегия` / `Лаборатория` is visible while Laboratory is active but reverts to `Strategy` / `Laboratory` after navigating to Strategy.

The accepted `_20` 25% field grid and mode-label typography contract is not the rejected part. The root cause is the redundant Laboratory page wrapper plus `.page-content-main` neutralization, and navigation localization being applied only by Laboratory JavaScript.

Durable evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).

## `_21` source implementation

Current source candidate:

- `PLUGIN_REVISION=21`;
- Laboratory no longer creates or overrides `.page-content-main`; OPNsense owns the outer page perimeter;
- the two Laboratory sections render as normal `content-box` blocks inside that platform wrapper;
- accepted common `25%` Diagnostics field grid and mode-label computed typography synchronization are retained;
- canonical menu names remain `Strategy` / `Laboratory`, while both Laboratory and Strategy apply deterministic RU/EN labels from the active OPNsense HTML language;
- Strategy Lab search/runtime, Generic UDP, QUIC, circular and persistence semantics are unchanged;
- focused regression guards the corrected frame ownership and cross-page navigation localization while preserving prior accepted UI/persistence contracts.

Source patch record: [`patches/v0.4.1_21.md`](patches/v0.4.1_21.md).

## Current verification boundary

Before `_21` source merge/publication:

1. focused Diagnostics/Laboratory native-frame/localization/persistence contract;
2. applicable complete project + Strategy Lab corrective matrix;
3. FreeBSD-15 package build/inspection qualification;
4. exact latest-head merge;
5. persistent `v0.4.1_21` testing publication and publication-record reconciliation.

After `_21` install:

1. Laboratory outer perimeter matches Strategy/native OPNsense page spacing;
2. Russian navigation stays `Стратегия` / `Лаборатория` across Laboratory ↔ Strategy navigation;
3. accepted common field grid and `Режим:` typography remain intact;
4. no Strategy Lab execution rerun is required for this UI-only correction;
5. Enable QUIC OFF/default persistence reload/revisit proof remains separate;
6. after `_21` UI acceptance, next selected engineering plan: Laboratory targets must support IP addresses as well as domains;
7. continue the remaining risk-selected backlog.

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

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
- current source candidate: `_17`;
- package metadata: `PLUGIN_REVISION=17`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_17.pkg` / `v0.4.1_17`;
- testing-package SHA-256: `92d7d3320246380bef53c7d37364895315e12d55b958c8a5fd657ba9ab213dbf`;
- source merge/testing-tag target: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- publication workflow run: `31887296681`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_17`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_17.md`](verification/evidence/testing-publications/v0.4.1_17.md).

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
- Enable QUIC OFF/default persistence across an actual reload/revisit is still live-pending; `_17` preserves and regression-guards its source persistence contract.

## `_17` published implementation — automated acceptance PASS

`_17` is the owner-selected Strategy Lab / Diagnostics presentation package.

Implemented deterministic RU/EN presentation:

- circular ordinary status is human text, not raw `{"state":"idle"}` JSON; RU `Состояние: ОЖИДАНИЕ`, EN `State: IDLE`;
- `Full output (advanced)` / `Полный вывод (расширенный)`;
- HTTPS connectivity guidance EN/RU, including RU `Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.`;
- `Family` / `Семейство`;
- `Endpoints` / `Назначения`;
- `Outcome` / `Результат`;
- `Restoration` / `Восстановление`;
- `Replay` / `Ответы`;
- `Complete Traffic Strategy profile` / `Полный профиль Стратегий Трафика`;
- `Run` / `Запуск`;
- `Test Domain Connectivity` / `Тестирование соединения с доменом`;
- EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`;
- `Enable QUIC` / `Включить QUIC`.

The focused regression contract also asserts that Enable QUIC uses the model-backed settings endpoint, persists `0/1`, reloads the saved value on page open, and has model default `0` (OFF). This remains source evidence until owner-live reload/revisit proof.

Source/publication acceptance:

- source PR `#250` exact verified head `9bae088ddd0d26a131cac3fb54b17fa761963c75`;
- complete Strategy Lab corrective matrix: PASS;
- focused diagnostics localization/circular/persistence contract: PASS;
- FreeBSD-15 package build/inspection: PASS;
- exact source merge: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- publisher FreeBSD-15 build/manifest/digest verification: PASS;
- release/tag `v0.4.1_17` points exactly to the candidate-defining source merge;
- asset `os-zapret2-restyle-0.4.1_17.pkg` uploaded and verified;
- SHA-256 `92d7d3320246380bef53c7d37364895315e12d55b958c8a5fd657ba9ab213dbf`.

Source patch record: [`patches/v0.4.1_17.md`](patches/v0.4.1_17.md).

## Accepted owner-live evidence retained

- Generic UDP: [`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md)
- QUIC OFF execution/UI follow-up: [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md)

## Current owner-live boundary

After `_17` install:

1. Russian visible presentation;
2. English visible presentation and no language leakage;
3. Enable QUIC OFF/default persistence after reload/revisit;
4. continue the next risk-selected regression from `ROADMAP.md`.

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

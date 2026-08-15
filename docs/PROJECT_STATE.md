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
- packaged source revision: `_16`;
- current source candidate: `_16`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- testing-package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source merge/testing-tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publication workflow run: `31882091770`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_16`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_16.md`](verification/evidence/testing-publications/v0.4.1_16.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` established explicit Enable QUIC as the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability remains diagnostic only.
- `_15` owner-live QUIC ON observability remains accepted: four attempted QUIC IDs are visible while ordinary QUIC is blocked.
- `_16` source acceptance, exact-head merge and immutable testing-package publication are complete.
- `_16` Generic UDP browser-to-job path is **OWNER-LIVE PASS** with exact 140-byte payload evidence.
- `_16` Enable QUIC OFF **execution semantics are OWNER-LIVE PASS**: OFF suppresses QUIC candidate execution while independent UDP testing remains active.
- Enable QUIC OFF/default **persistence across reload/revisit is not yet proven** and remains pending.

## Current owner-live evidence

Generic UDP PASS:
[`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md).

QUIC OFF/UI follow-up:
[`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md).

The latest owner screenshots show both sides of the explicit QUIC gate on `www.youtube.com` in Extended mode with the same Generic UDP input:

- QUIC ON: Stage 80 runs all four current QUIC candidates;
- QUIC OFF: Stage 80 reports QUIC strategy search disabled and still runs `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`;
- the OFF run completes `SUCCESS` with stable TLS/HTTP candidates and successful Stage-90 restoration.

This closes the runtime ON/OFF behavior, but not persistence after reload/revisit.

## Selected UI/RU-EN implementation boundary

The owner selected a focused presentation cleanup. These are required implementation tasks:

### Circular idle presentation

- ordinary UI must not display the raw JSON braces `{` / `}` for the idle circular state;
- ordinary `{"state":"idle"}` must become localized text;
- RU target: `Состояние: ОЖИДАНИЕ`;
- EN target: `State: IDLE`;
- raw machine JSON may exist only under an explicitly advanced/raw presentation if retained.

### RU/EN strings to close

- `Full output (advanced)` -> RU `Полный вывод (расширенный)`;
- `Enter a domain and click Test to check HTTPS connectivity.` -> RU `Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.`;
- `Family` -> RU `Семейство`;
- `Endpoints` -> RU `Назначения`;
- `Outcome` -> RU `Результат`;
- `Restoration` -> RU `Восстановление`;
- `Replay` -> RU `Ответы`;
- `Complete Traffic Strategy profile` -> RU `Полный профиль Traffic Strategy`;
- `Run` -> RU `Запуск`;
- `Test Domain Connectivity` -> RU `Тестирование соединения с доменом`;
- `Blocked Domain` becomes EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`;
- `Enable QUIC` -> RU `Включить QUIC`.

English mode must continue to show the corresponding English strings. Final acceptance must inspect both language modes and verify no cross-language leakage.

Obvious spelling slips in the conversational request are normalized to the intended product terms (`Run`, `QUIC`, `Ответы`, `Включить`).

## Current owner-live boundary

Accepted and closed for the tested scenarios:

- Generic UDP exact-byte path;
- selected port/payload direct observation and no-reply semantics;
- real QUIC ON execution;
- QUIC OFF execution semantics;
- visible Stage-90 restoration.

Current selected work:

1. prove Enable QUIC OFF/default persistence across reload/revisit;
2. implement the circular-idle and RU/EN presentation cleanup above;
3. live-check both RU and EN after implementation;
4. continue the next risk-selected regressions from `ROADMAP.md`.

## Documentation authority note

The owner’s latest instruction is current truth. Earlier hypotheses remain historical evidence only and do not override newer controlled owner-live results.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Package-affecting source changes automatically continue through persistent testing publication and the required publication-record tail. `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).

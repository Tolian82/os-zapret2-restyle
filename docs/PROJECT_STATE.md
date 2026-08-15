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
- current source/testing package revision: `_14`;
- `_14` published package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
- `_14` package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- `_14` source/tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- internal service key: `zapret`.

The exact `main` SHA is resolved at execution time under `GH-004`.

## Current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- `_13` removed automatic normal-production Model B/A replay.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING and STOPPED behavior is accepted.
- `_13 job.TJlWoY` accepted truthful Extended TLS 1.2 and HTTP branch execution.
- `_13 job.TJlWoY` also demonstrated the old closed-QUIC capability skip. The owner superseded that behavior in `_14`.
- `_14` source acceptance, persistent testing publication and publication-record reconciliation are complete.
- `_14` is installed on the owner OPNsense and the owner has begun live Extended verification.

## `_14` implemented contract

### Explicit Enable QUIC

- Diagnostics Extended mode contains `Enable QUIC` directly below `Generic UDP (optional)`.
- It is a persisted Boolean Strategy Lab preference, default OFF.
- The selected value is copied into job-local state at launch.
- OFF means Stage 80 records QUIC skipped for `disabled` and launches no QUIC candidate.
- ON means Stage 80 runs QUIC candidates.
- Stage-30 `quic_ipv4` probing is diagnostic only.
- No measured QUIC capability value may decide whether QUIC candidates run.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP input

- Generic UDP payload remains bounded to decoded size `1..4096` bytes.
- Browser pre-validation occurs before clearing the previous result or entering running state.
- API/backend strict validation remains authoritative.
- A configured valid UDP request is expected to execute Stage-80 UDP candidates rather than be silently rewritten to `skipped`.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## Owner-live `_14` observations — current follow-up boundary

The owner supplied two Extended GUI results on the installed `_14` package:

- `telegram.org`: Enable QUIC checked; Stage 30 says the QUIC/IPv4 control probe is closed; Stage 80 reports `QUIC=not_found, UDP=skipped`; terminal result `NO_CANDIDATE`.
- `rutracker.org`: Enable QUIC checked; Stage 30 says the QUIC/IPv4 control probe is closed; Stage 80 reports `QUIC=not_found, UDP=skipped`; terminal result `SUCCESS` with one stable TLS 1.3 candidate.

These screenshots are **positive evidence that the old capability-skip presentation is gone**: enabled QUIC is not reported as skipped merely because the control probe is closed. They are **not yet sufficient evidence that real QUIC candidates executed**, because the normal GUI summary does not expose a non-zero attempt count or candidate names.

Current source inspection establishes the expected implementation path:

- the current QUIC catalog contains four candidates: `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`;
- the production Python QUIC runner appends each executed candidate result to `tested`;
- a completed enabled search sets `not_found` only after walking the catalog without a winner, unless a working candidate returns early.

Therefore the owner-live gate remains open until actual job evidence proves `tested > 0`. The next implementation should also expose attempted-count/name evidence in ordinary result presentation so this can be verified without unpacking telemetry.

The same live cycle produced new selected defects/tasks:

1. **QUIC network-state wording/localization:** Stage 30 currently presents `QUIC/IPv4 закрыт по контрольной проверке`. User-facing RU/EN output must instead state the measured QUIC condition clearly (`QUIC открыт` / `QUIC закрыт`, English equivalent) and separately state whether QUIC strategy testing is enabled. A closed control path must never read as though candidate search was disabled.
2. **Stage-80 result localization:** raw fragments such as `QUIC=not_found, UDP=skipped` must be rendered as human-readable RU/EN semantics. Machine enums remain allowed in raw/structured evidence only.
3. **Enable QUIC help localization:** `When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.` currently leaks English in the Russian UI and requires RU/EN localization.
4. **Generic UDP valid-small-file defect:** the owner reports that a nominal 140-byte payload is rejected with the `1–4096 bytes` size error. This contradicts the supported contract and must be reproduced/root-caused across browser `File.size`, Base64 transport, API decode and job-local payload creation.
5. **Generic UDP destination-port verification:** the selected port/control exchange must be measured with the supplied payload and presented truthfully. UDP silence must not be misclassified as definitive proof that a port is closed, and a failed direct exchange must not become a bypass-search gate.

The master task list for these items is `ROADMAP.md`. This task-registration update is documentation-only and does not change package identity.

## Verification boundary

Already accepted `_13` live evidence remains durable under:

- [`verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md).

Current `_14` selected live verification remains open for:

1. Enable QUIC default OFF and persistence;
2. Enable QUIC OFF → `skipped/disabled`;
3. Enable QUIC ON while control QUIC is blocked → **actual candidate evidence with `tested > 0`** and truthful `working` or `not_found`;
4. corrected RU/EN QUIC control/state and Stage-80 QUIC/UDP presentation;
5. valid small Generic UDP payload, including the owner-reported 140-byte case;
6. configured UDP control-exchange/port evidence and actual UDP candidate search;
7. lifecycle restoration and temporary resource cleanup for the above live paths.

## Documentation authority note

The owner’s latest observations and requirements are current truth. Any older text saying Stage-30 QUIC availability decides whether Stage-80 QUIC candidate testing runs is historical/superseded. Raw `_14` GUI text observed above is evidence of the current implementation, not the desired final presentation contract.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Project patch/package delivery is GitHub-native; a package-affecting source change automatically continues through persistent testing publication and the required publication-record tail. `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).

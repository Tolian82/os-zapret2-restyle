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
- current source candidate: `_15`;
- current published/owner-installed testing package remains `_14` until `_15` is merged and persistently published;
- `_14` published package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
- `_14` package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- `_14` source/tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- latest full Web/pkg release: `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- internal service key: `zapret`.

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` implemented the owner rule that Enable QUIC is the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability is diagnostic only.
- `_14` source acceptance/publication/reconciliation are complete and `_14` is installed on the owner OPNsense.

## Owner-live `_14` findings that define `_15`

Two Extended live runs (`telegram.org`, `rutracker.org`) with Enable QUIC ON showed a blocked ordinary QUIC control probe and Stage-80 `QUIC=not_found` rather than capability skip. This is positive evidence that the old capability gate is gone, but the ordinary output did not show the actual `tested` set.

The owner then selected one corrective package scope:

1. expose real QUIC candidate count/names so enabled live execution can be proven without unpacking telemetry;
2. present Stage-30 QUIC measured state and QUIC-search choice separately in natural RU/EN;
3. replace raw Stage-80 `QUIC=not_found, UDP=skipped` presentation with natural RU/EN while preserving structured machine enums;
4. localize the Enable QUIC help text in RU/EN;
5. fix the owner-reported nominal 140-byte Generic UDP rejection and add exact regression coverage;
6. verify the selected UDP destination port using the exact supplied payload, expose direct reply/no-reply evidence, and never equate silence with a closed port or use it as a bypass-search gate.

These items are now implemented in source candidate `_15` and remain subject to exact-head CI/package qualification, merge, persistent testing publication and owner-live verification.

## `_15` implementation contract

### QUIC

- `_14` execution semantics are preserved: OFF means no candidates; ON means candidate execution regardless of control-probe result.
- Stage 30 derives human presentation from structured `network.json` plus immutable job-local `quic-enabled` execution intent.
- Russian UI renders `QUIC открыт` / `QUIC закрыт`; English renders the equivalent open/blocked state.
- Stage 30 separately states whether QUIC strategy search is enabled/disabled; Standard mode explicitly says the QUIC search belongs to Extended mode.
- Stage 80 uses the actual structured `tested` array and displays candidate count and IDs.
- Current QUIC catalog remains `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`.
- Raw `working`, `not_found`, `skipped`, `disabled` remain machine evidence, not ordinary user-facing Stage-80 wording.
- Enable QUIC help text is bound through the same deterministic RU/EN UI language selection used by other Strategy Lab guidance.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP

- decoded payload contract remains `1..4096` bytes, destination port remains `1..65535`, and port/file remain an atomic pair;
- browser transport is `readAsArrayBuffer -> Uint8Array.byteLength -> Base64`, removing browser `File.size` and Data-URL parsing as validation owners;
- strict API/backend Base64 and decoded-size checks remain authoritative;
- an exact 140-byte binary payload has regression coverage through job-local decode/metadata;
- configured UDP performs a direct request/response observation against each fixed search-epoch selected IP using the exact configured port and job-local payload;
- control evidence records endpoint/IP, port, payload bytes, reply observed, timeout/return state and duration;
- no reply means only `reply_observed=false`; it never means `port closed` and never suppresses the candidate loop;
- Stage 80 exposes the selected port, payload bytes, selected endpoint/IP, control observation and actual UDP candidate count/IDs in RU/EN.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_15` verification boundary

Source acceptance requires:

1. protocol-presentation Python compile/unit contract;
2. exact 140-byte UDP binary regression;
3. browser ArrayBuffer/Base64 contract and pre-start decoded-size validation;
4. exact selected-IP/port/payload direct UDP control regression;
5. explicit non-gating UDP-silence semantics;
6. blocked-control QUIC candidate execution regression;
7. complete Strategy Lab corrective matrix;
8. FreeBSD-15 package build/inspection qualification;
9. exact verified-head merge;
10. persistent `v0.4.1_15` testing publication and bounded publication-record documentation reconciliation.

After publication, owner-live checks are limited to materially changed `_15` behavior: RU/EN help and Stage-30/80 text, QUIC `tested > 0` candidate names on Enable QUIC ON, natural disabled wording on OFF, accepted 140-byte UDP payload, direct UDP observation plus actual candidate count/names, and clean Stage-90 restoration/resource cleanup.

## Documentation authority note

The owner’s latest instruction is current truth. Historical `_14` screenshots retain their evidentiary value but do not define the desired `_15` presentation. No historical evidence is rewritten to look like the corrected package.

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

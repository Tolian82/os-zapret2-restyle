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
- packaged source revision: `_15`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_15.pkg` / `v0.4.1_15`;
- testing-package SHA-256: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`;
- source merge/testing-tag target: `a219161c901c663b56cac6757364d3bbd32766c7`;
- publication workflow run: `31879283227`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository was not promoted by `_15`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_15.md`](verification/evidence/testing-publications/v0.4.1_15.md).

The exact `main` SHA is resolved at execution time under `GH-004`.

## Locked current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- Automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence remains accepted.
- `_14` established explicit Enable QUIC as the sole QUIC candidate execution gate; Stage-30 measured QUIC reachability remains diagnostic only.
- `_15` source acceptance, exact-head merge and immutable testing-package publication are complete.

## Why `_15` was selected

Owner-live `_14` Extended runs on `telegram.org` and `rutracker.org` with Enable QUIC ON showed blocked ordinary QUIC but Stage-80 `not_found` rather than capability skip. That proved the old execution gate was gone but did not expose the actual `tested` set. The same cycle exposed raw RU/EN protocol wording, English-only help at the GUI boundary, a nominal 140-byte Generic UDP rejection, and no direct selected-port/payload UDP observation.

The owner selected one corrective package scope covering those findings. The full plan and all post-publication checks remain recorded in `ROADMAP.md`, `START_HERE.md`, both specialist contracts and the live OPNsense matrix.

## `_15` implemented contract

### QUIC

- Enable QUIC OFF means no candidates; ON means candidate execution regardless of Stage-30 control-probe result.
- Stage 30 derives human presentation from structured `network.json` plus immutable job-local `quic-enabled` intent.
- Russian renders `QUIC открыт` / `QUIC закрыт`; English renders the equivalent open/blocked state.
- Stage 30 separately states whether QUIC strategy search is enabled/disabled or belongs to Extended mode.
- Stage 80 uses the actual structured `tested` array and displays candidate count and IDs.
- Current catalog remains `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`.
- Raw `working`, `not_found`, `skipped`, `disabled` remain machine evidence rather than primary ordinary Stage-80 wording.
- Enable QUIC help uses deterministic RU/EN presentation.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP

- decoded payload remains `1..4096` bytes, port remains `1..65535`, and port/file are an atomic pair;
- browser transport is `readAsArrayBuffer -> Uint8Array.byteLength -> Base64`;
- strict API/backend Base64 and decoded-size checks remain authoritative;
- exact 140-byte binary payload has regression coverage through job-local decode/metadata;
- configured UDP performs direct request/response observation against each fixed search-epoch selected IP using the exact configured port and job-local payload;
- control evidence records endpoint/IP, port, payload bytes, reply observed, timeout/return state and duration;
- no reply means only `reply_observed=false`; it never means `port closed` and never suppresses the candidate loop;
- Stage 80 exposes selected port, payload bytes, selected endpoint/IP, control observation and actual UDP candidate count/IDs in RU/EN.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_15` automated and publication verification — PASS

- source PR `#241` exact verified head: `ecf3d5269574988e56707c68b6eb9696d936b1ca`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package qualification: PASS;
- exact-head source merge: `a219161c901c663b56cac6757364d3bbd32766c7`;
- publisher FreeBSD-15 build/manifest/digest verification: PASS;
- release/tag `v0.4.1_15` points exactly to the candidate-defining source merge;
- asset `os-zapret2-restyle-0.4.1_15.pkg` is uploaded and verified;
- SHA-256: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`.

The publisher's only failed step was automatic Draft PR creation because the repository setting forbids GitHub Actions from creating or approving pull requests. The machine-generated record branch/evidence was already pushed; Draft PR `#242` was opened through the GitHub connector to complete the same required docs-only tail. Package identity/bytes were not changed.

## Current owner-live boundary

After installing `_15`, verify only the materially changed paths rather than repeating accepted Model-C baseline work:

1. RU and EN Diagnostics show localized Enable QUIC/Generic UDP help;
2. Enable QUIC ON with ordinary QUIC blocked → Stage 30 shows blocked/closed plus search enabled; Stage 80 shows `tested > 0` and attempted IDs;
3. Enable QUIC OFF → natural localized disabled wording;
4. exact/small Generic UDP payload including a 140-byte sample starts normally;
5. configured UDP shows selected port, payload bytes, endpoint/IP, direct reply/no-reply observation and actual candidate count/IDs;
6. no-reply wording never claims the port is closed;
7. Stage-90 restoration and temporary process/firewall/socket cleanup remain PASS.

One Extended run may cover enabled QUIC and configured UDP simultaneously.

## Documentation authority note

The owner’s latest instruction is current truth. Historical `_14` screenshots retain their evidentiary value but do not define the desired `_15` presentation. Historical evidence is not rewritten to look like the corrected package.

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

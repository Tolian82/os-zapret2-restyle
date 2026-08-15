# os-zapret2-restyle — START HERE

- **Current project state:** [`PROJECT_STATE.md`](PROJECT_STATE.md)
- **Documentation rules (`DOC-*`):** [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- **Project-development rules (`DEV-*`):** [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- **Owner/assistant chat rules (`CHAT-*`):** [`CHAT_RULES.md`](CHAT_RULES.md)
- **GitHub rules (`GH-*`):** [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- **Master development plan:** [`ROADMAP.md`](ROADMAP.md)
- **Documentation/navigation index:** [`INDEX.md`](INDEX.md)

**Status:** AUTHORITATIVE REVISION HANDOFF · LEVEL 1
**Updated:** 2026-08-15
**Current handoff identity:** `v0.4.1_16`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=16`;
- current source candidate: `PLUGIN_REVISION=16` / `v0.4.1_16`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- testing-package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source merge and testing-tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publication workflow run: `31882091770`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_16.md`](verification/evidence/testing-publications/v0.4.1_16.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Why `_16` exists

Published `_15` made real QUIC execution observable and also exposed ambiguity around Generic UDP file selection. `_16` made the browser handoff explicit and observable by staging the selected bytes immediately and by adding precise backend preparation diagnostics.

The earlier owner report that Generic UDP still failed is now superseded by controlled exact-byte evidence. The owner later identified the input mistake: the repeatedly selected files were approximately **140 KiB**, while the product contract is **1..4096 bytes**.

Historical `_15` report remains preserved as chronology only:
[`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

Current accepted live evidence:
[`verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md).

## Generic UDP transport and `_16` correction

Generic UDP has no multipart upload directory. The product path is:

`local File -> browser ArrayBuffer -> Base64 in normal start POST -> PHP/API -> configd -> launcher -> private job-local udp-payload.bin/udp-port -> Python Extended`.

`_16` makes this browser handoff explicit and observable:

- file-input `change` immediately captures the selected `File`;
- `readAsArrayBuffer` and exact `1..4096` decoded-byte validation run immediately;
- validated bytes are Base64-encoded and retained in application-owned staged state;
- RU/EN UI shows filename plus exact byte count and a clear `ready to send` state;
- Run uses the staged Base64 instead of depending exclusively on native `input.files[0]` still being populated;
- a defensive Run-time fallback stages a currently visible native `File` before starting;
- browser ArrayBuffer validation no longer relies on realm-specific `instanceof ArrayBuffer`;
- job-local UDP preparation publishes precise failure classes including unavailable/not-writable job directory, temporary-file creation, decode, chmod/move and state-record failures;
- existing exact port/payload direct observation, candidate enumeration, no-reply semantics and cleanup remain unchanged.

Canonical specialist contract:
[`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_16` automated/publication acceptance — PASS

- source PR `#245` latest verified head: `f7974f21dc7340b1e1416c24f9e7dade0322f0f3`;
- focused staged-browser Generic UDP contract: PASS;
- exact 140-byte backend/job-local regression: PASS;
- explicit server preparation failure attribution: PASS;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package build/inspection qualification: PASS;
- exact-head source merge: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- prerelease `v0.4.1_16`: published and verified;
- package asset: `os-zapret2-restyle-0.4.1_16.pkg`;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- tag target: exactly the candidate-defining source merge;
- stable Pages/pkg repository: unchanged.

The publisher again could not create its Draft publication-record PR because the repository setting forbids GitHub Actions from creating or approving pull requests. PR `#246` completed the bounded docs-only publication tail without altering package identity or bytes.

## `_16` owner-live Generic UDP — PASS

Controlled owner-live verification used an exact Windows-generated `udp-140.bin` fixture whose filesystem size was verified as `140` bytes before selection.

Observed in Strategy Lab job `job.j09XUc`:

- target `rutracker.org`, Extended mode, UDP port `53`, Enable QUIC OFF;
- GUI immediately displayed `udp-140.bin, 140 байт` as ready to send;
- Stage 80 showed configured UDP on port `53` with payload `140` bytes and endpoint `172.67.182.196`;
- direct reply was not observed and the UI correctly stated that this does **not** mean the port is closed;
- three candidates actually ran: `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`;
- no working UDP candidate was found, which is a truthful negative result rather than a test failure;
- QUIC OFF was presented naturally as strategy search disabled;
- Stage 90 visibly restored Zapret2 and removed temporary processes/rules.

The earlier suspicion of an upload-folder/browser/filesystem defect is therefore not the current diagnosis for this scenario. The owner identified the actual cause of the repeated size validation failures: previous files were around **140 KiB**, not 140 bytes.

## Immediate next task

Do not repeat accepted Model-C, QUIC-ON, or Generic UDP baseline work without fresh contradictory evidence.

Next selected rows:

1. verify Enable QUIC OFF/default persistence across reload/revisit;
2. complete the remaining RU/EN presentation review;
3. then continue the risk-selected regression backlog from `ROADMAP.md`.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.

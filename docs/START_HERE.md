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
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- testing-package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source merge and testing-tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publication workflow run: `31882091770`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_16.md`](verification/evidence/testing-publications/v0.4.1_16.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Why `_16` exists

Published `_15` successfully made real QUIC execution observable, but the owner-live Generic UDP retry still failed before configured UDP execution. With port `53` entered, selecting a valid small local file did not produce a usable configured payload; the native file control appeared empty and Stage 80 reported UDP as not configured.

Durable live-failure evidence:
[`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

## Trace result

The earlier permissions theory is retained only as a possible **later-stage** failure, not the primary explanation for the observed GUI state.

Generic UDP has no multipart upload directory. The product path is:

`local File -> browser ArrayBuffer -> Base64 in normal start POST -> PHP/API -> configd -> launcher -> private job-local udp-payload.bin/udp-port -> Python Extended`.

Source tracing found that `_15` did not own the prepared browser payload. The Run handler sampled `input.files[0]` at click time and only then read/encoded it. If the native selection was cleared/lost, validation returned before API/configd/job-local storage was reached. In that state filesystem permissions cannot be the first failure because no server payload file has yet been created.

## `_16` correction

`_16` makes the browser handoff explicit and observable:

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

The publisher again could not create its Draft publication-record PR because the repository setting forbids GitHub Actions from creating or approving pull requests. The publisher had already pushed the machine evidence branch, so PR `#246` completes the same bounded docs-only tail without altering package identity or bytes.

## Immediate next task — owner-live `_16`

Do not repeat accepted Model-C or QUIC baseline work. Verify the corrected Generic UDP handoff:

1. selecting a valid file immediately shows its filename and exact decoded byte count as **ready to send**;
2. a 140-byte sample shows `140` bytes and starts a **new** configured-UDP job;
3. Stage 80 shows selected port/payload/IP, direct reply/no-reply observation and actual UDP candidate IDs;
4. if a later server-side filesystem preparation error occurs, the UI/API identifies its preparation class instead of silently treating UDP as unconfigured;
5. no-reply wording never claims the UDP port is closed;
6. Stage-90 restoration and temporary process/firewall/socket/payload cleanup remain PASS.

Remaining independent rows after that are Enable QUIC OFF/default persistence and final RU/EN presentation review.

Do not reopen closed BLOB/Lua/discovery/model-selection experiments without new architecture or fresh contradicting evidence.
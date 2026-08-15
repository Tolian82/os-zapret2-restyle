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
**Current handoff identity:** `v0.4.1_16` Generic UDP browser-to-job correction

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=16`;
- last published/owner-tested package: `os-zapret2-restyle-0.4.1_15.pkg` / `v0.4.1_15`;
- `_15` SHA-256: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`;
- `_15` candidate-defining source/tag target: `a219161c901c663b56cac6757364d3bbd32766c7`;
- required ABI: `FreeBSD:15:amd64`.

Resolve the exact current `main` SHA at execution time under `GH-004`. `_16` is a source candidate until exact-head acceptance, merge and persistent testing publication complete.

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
- job-local UDP preparation now publishes precise failure classes including unavailable/not-writable job directory, temporary-file creation, decode, chmod/move and state-record failures;
- existing exact port/payload direct observation, candidate enumeration, no-reply semantics and cleanup remain unchanged.

Canonical specialist contract:
[`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## Acceptance boundary

Before owner install:

1. focused staged-browser UDP contract PASS;
2. exact 140-byte backend/job-local regression PASS;
3. explicit job-local failure attribution PASS;
4. full Strategy Lab corrective matrix PASS;
5. FreeBSD-15 package qualification PASS;
6. exact-head merge and persistent `v0.4.1_16` testing publication;
7. bounded publication-record docs reconciliation.

Owner-live after publication:

- selecting a valid file immediately shows name and exact bytes as ready;
- 140-byte sample starts a **new** configured-UDP job;
- Stage 80 shows selected port/payload/IP, direct observation and actual UDP candidate IDs;
- any later filesystem preparation failure is explicitly attributed rather than appearing as an unexplained unconfigured request;
- Stage 90 cleanup/restoration remains PASS.

Do not repeat accepted Model-C baseline work or reopen closed BLOB/Lua/discovery/model-selection experiments.

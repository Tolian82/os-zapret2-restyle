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
- `_15` source/publication acceptance remains complete.
- `_15` owner-live QUIC observability is positively demonstrated: the normal Stage-80 UI showed all four attempted QUIC candidate IDs while ordinary QUIC remained blocked.
- `_15` Generic UDP owner-live acceptance failed: a valid selected small file did not reach configured UDP.
- `_16` source acceptance, exact-head merge and immutable testing-package publication are complete; owner-live Generic UDP correction verification is the current gate.

## Generic UDP trace result

The product does not upload the selected payload through a multipart upload directory. The actual path is:

`browser File -> ArrayBuffer -> Base64 start POST -> PHP/API -> configd -> launcher -> private job-local udp-payload.bin/udp-port -> Python Extended`.

The `_15` browser implementation had no durable application-owned prepared payload. The Run handler sampled `input.files[0]` and only then attempted `FileReader`. Therefore a lost/reset native file selection could trigger port+file validation before the API call and before any job-local file existed.

This explains why the owner's directory-permissions theory cannot be the **first** cause of the observed empty native file control/no-configured-job state. Filesystem permissions remain a valid later-stage failure mode if a payload reaches the launcher.

Durable owner-live failure evidence:
[`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

## `_16` implemented contract

### Browser-owned payload staging

- file-input `change` immediately captures the selected `File`;
- exact bytes are read immediately using `FileReader.readAsArrayBuffer`;
- decoded `Uint8Array.byteLength` remains bounded to `1..4096`;
- exact validated bytes are Base64-encoded and retained in application-owned state;
- UI displays localized filename + decoded byte count + ready-to-send state;
- Run uses staged Base64 and no longer depends exclusively on native `input.files[0]` at click time;
- if native selection exists but staging was not completed, Run stages it before start as a bounded fallback;
- ArrayBuffer validation uses the returned `byteLength` contract rather than `instanceof ArrayBuffer`.

### Server-side attribution

The API/configd transport remains Base64-in-POST. After the job directory exists, job-local preparation still creates private `udp-payload.bin` and `udp-port` with mode `0600`.

`_16` adds precise failure classes for later stages, including job directory missing/not writable, temporary file creation, invalid/decode failure, size failure, write/chmod/move failure and state-record failure. The launcher surfaces the class in its error response instead of collapsing all such failures into one generic message.

### Existing UDP search behavior retained

- exact selected port/payload direct observation remains non-gating;
- UDP silence is not proof of a closed port;
- candidate loop still runs regardless of direct no-reply;
- Stage 80 still exposes selected port/payload/endpoints, control observation and actual candidate IDs in RU/EN;
- terminal payload cleanup and Stage-90 semantic restoration remain mandatory.

Canonical specialist contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_16` automated and publication verification — PASS

- source PR `#245` exact verified head: `f7974f21dc7340b1e1416c24f9e7dade0322f0f3`;
- staged-browser Generic UDP contract: PASS;
- exact 140-byte backend/job-local regression: PASS;
- precise server preparation failure attribution: PASS;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package build/inspection qualification: PASS;
- exact-head source merge: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- publisher FreeBSD-15 build/manifest/digest verification: PASS;
- release/tag `v0.4.1_16` points exactly to the candidate-defining source merge;
- asset `os-zapret2-restyle-0.4.1_16.pkg` is uploaded and verified;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`.

The publisher's only failed step was automatic Draft PR creation because the repository setting forbids GitHub Actions from creating or approving pull requests. The machine-generated record branch/evidence was already pushed; Draft PR `#246` completes the same required docs-only tail. Package identity/bytes were not changed.

## Current owner-live boundary

After installing `_16`, verify only the materially changed Generic UDP path:

1. selecting a valid file immediately shows application-owned ready state, filename and exact decoded byte count;
2. a 140-byte sample starts a new configured-UDP job;
3. configured UDP Stage 80 shows selected port, payload bytes, endpoint/IP, direct reply/no-reply observation and actual candidate count/IDs;
4. no-reply wording never claims the port is closed;
5. if server-side permission/storage preparation fails, the UI/API exposes its preparation class;
6. Stage-90 restoration and temporary process/firewall/socket/payload cleanup remain PASS.

Remaining independent rows after Generic UDP are Enable QUIC OFF/default persistence and final RU/EN presentation review.

## Documentation authority note

The owner’s latest instruction is current truth. Historical `_15` automated assertions remain evidence of what source tests proved, but they do not count as proof of the live browser-to-job path.

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
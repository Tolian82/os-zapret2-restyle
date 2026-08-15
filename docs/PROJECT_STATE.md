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
- packaged source revision: `_14`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
- testing-package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- `_14` source merge and testing-tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- publication workflow run: `31875178597`;
- latest full Web/pkg release remains `v0.4.1` / `os-zapret2-restyle-0.4.1_1.pkg`;
- stable Pages/pkg repository was not promoted by `_14`;
- required ABI: `FreeBSD:15:amd64`;
- internal service key: `zapret`.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_14.md`](verification/evidence/testing-publications/v0.4.1_14.md).

## Current product facts

- DNS is fixed/currently working; old DNS failures are closed absent fresh direct evidence.
- Model C is the only normal production Stage-60 runtime; A/B/C selection is closed.
- automatic normal-production Model B/A replay remains removed.
- Lua initialization, BLOB lazy/common-set, GET-4K discovery and cross-batch keep-warm questions remain closed for the current architecture by accepted measured evidence.
- `_13` owner-live Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP behavior remains accepted historical evidence.
- the `_13` closed-QUIC capability skip is superseded as current product behavior by `_14`.

## Current `_14` product contract

### Explicit Enable QUIC

- Diagnostics Extended mode adds `Enable QUIC` directly below `Generic UDP (optional)`.
- It is a persisted Boolean Strategy Lab preference, default OFF.
- The resolved value is copied into immutable job-local execution intent at launch.
- OFF → Stage 80 records QUIC `skipped`, reason `disabled`, and launches no QUIC candidate.
- ON → Stage 80 runs QUIC candidates.
- Stage-30 `quic_ipv4` probing is diagnostic only.
- **No measured QUIC capability value decides whether candidates run.**
- `quic_ipv4=closed` with Enable QUIC ON still executes the QUIC catalog and truthfully returns `working` or `not_found`.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP input UX

- decoded payload bound remains `1..4096` bytes;
- port and file must be supplied together;
- browser pair/size validation happens before clearing the previous result or entering running state;
- oversized input produces an immediate visible size error;
- API/backend strict Base64/decoded-size validation remains authoritative;
- a valid configured UDP request executes Stage-80 UDP candidates and may truthfully return `working` or `not_found`.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_14` automated and publication verification — PASS

- source PR `#237` latest verified head: `b476131bdd68c51288a0f89478fddd0382c0b5c9`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package qualification: PASS;
- exact-head source merge: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- publisher run `31875178597`: FreeBSD 15 build, package manifest/digest verification, prerelease publication, release/tag/asset verification all PASS;
- release/tag `v0.4.1_14` points exactly to the candidate-defining source merge;
- asset `os-zapret2-restyle-0.4.1_14.pkg` is uploaded and verified;
- SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`.

The publisher's only failed step was automatic PR creation because the repository setting currently forbids GitHub Actions from creating or approving pull requests. The machine-generated publication-record branch/evidence was already pushed. Draft PR `#238` was opened through the GitHub connector to complete the same required docs-only tail; package identity/bytes were not changed.

## Current live boundary

Owner-live `_14` verification is now selected:

1. checkbox default OFF and persistence across reload;
2. OFF → QUIC `skipped/disabled`;
3. ON while ordinary QUIC remains ISP-blocked → QUIC candidates actually execute, with truthful `working` or `not_found`;
4. 2–3 MB UDP payload → visible `1–4096` error and no new job;
5. valid port + `1..4096` payload → actual UDP candidate execution, not unconfigured skip;
6. normal lifecycle restoration remains successful.

One Extended run can cover enabled QUIC and configured UDP simultaneously.

## Documentation authority note

The owner’s new QUIC instruction is current truth. Older language saying Stage-30 QUIC availability decides whether Stage-80 QUIC candidate testing runs is historical/superseded. Historical evidence remains unchanged as evidence of what earlier packages actually did.

## Current architecture entry points

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md)
- [`architecture/STRATEGY_LAB_MODEL_C.md`](architecture/STRATEGY_LAB_MODEL_C.md)
- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md)
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md)

## Current documentation/governance facts

The four canonical general rule books remain `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, and `GITHUB_PUBLICATION.md`. Project patch/package delivery is GitHub-native; `START_HERE.md` owns the exact revision handoff, this file owns current `v0.4.x` facts, and the version-line ledger preserves chronology.

## Completed version-line archives

- [`v0.1.x archive`](history/archive/v0.1.x.md)
- [`v0.2.x archive`](history/archive/v0.2.x.md)
- [`v0.3.x archive`](history/archive/v0.3.x.md)

Current non-archived line: [`v0.4.x working ledger`](history/current/v0.4.x.md).

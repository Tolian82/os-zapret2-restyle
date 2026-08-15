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
- current source candidate: `_14`;
- current published testing package remains `_13` until `_14` is merged and persistently published;
- `_13` published package/tag: `os-zapret2-restyle-0.4.1_13.pkg` / `v0.4.1_13`;
- `_13` package SHA-256: `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`;
- `_13` source/tag target: `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
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
- `_13 job.TJlWoY` also demonstrated the **old** closed-QUIC capability skip. The owner has now superseded that behavior: being blocked is a reason to test bypass, not a reason to suppress the test.

## Current `_14` source contract

`v0.4.1_14` is one source/UI/backend scope with two related corrections.

### Explicit Enable QUIC

- Diagnostics Extended mode adds `Enable QUIC` directly below `Generic UDP (optional)`.
- It is a persisted Boolean Strategy Lab preference, default OFF.
- The selected value is copied into job-local state at launch.
- OFF means Stage 80 records QUIC skipped for `disabled` and launches no QUIC candidate.
- ON means Stage 80 runs QUIC candidates.
- Stage-30 `quic_ipv4` probing remains diagnostic only.
- **No measured QUIC capability value may decide whether QUIC candidates run.**
- In particular, `quic_ipv4=closed` with Enable QUIC ON must still execute candidates and finish with truthful `working` or `not_found`.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP apparent no-op correction

- Generic UDP payload remains bounded to decoded size `1..4096` bytes.
- The previously attempted 2–3 MB files are invalid by design.
- The browser now validates pair/size before clearing previous result or entering running state.
- Oversized input produces an immediate visible size error.
- API/backend strict validation remains authoritative.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## Current implementation boundary

The `_14` source branch implements:

- `PLUGIN_REVISION=14`;
- model-backed `strategylab.enablequic` with default `0`;
- persistent Strategy Lab settings API;
- GUI load/save checkbox state;
- explicit `enable_quic` start parameter;
- immutable job-local `quic-enabled` execution intent;
- Stage-80 checkbox-only QUIC gate;
- removal of capability gating from both Python production and shell/reference QUIC runners;
- Stage-30 presentation that reports blocked QUIC as a control-probe fact without claiming QUIC tests were excluded;
- pre-start visible Generic UDP pair/size validation;
- focused regression tests proving blocked-control-probe QUIC still executes when enabled and oversized UDP input is rejected before UI reset.

## Verification boundary

Already accepted historical `_13` live evidence remains durable under:

- [`verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md).

Current `_14` verification is not yet complete until:

1. latest-head source CI passes;
2. FreeBSD-15 package qualification passes;
3. exact verified head is merged;
4. persistent `v0.4.1_14` testing package is published from the candidate-defining source merge;
5. publication-record docs tail is reconciled/merged;
6. owner installs `_14` and verifies the explicit QUIC and Generic UDP behaviors described in `START_HERE.md`.

## Documentation authority note

The new owner instruction is current truth. Any older text saying Stage-30 QUIC availability decides whether Stage-80 QUIC candidate testing runs is historical/superseded. The specialist `_14` QUIC contract has current authority while older historical evidence remains unchanged as evidence of what `_13` actually did.

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

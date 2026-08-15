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
**Current source-candidate identity:** `v0.4.1_14`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- source candidate: `PLUGIN_REVISION=14`;
- current published testing package remains `os-zapret2-restyle-0.4.1_13.pkg` / `v0.4.1_13` until `_14` source is merged and the testing publisher completes;
- `_13` package SHA-256: `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`;
- required ABI: `FreeBSD:15:amd64`.

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Established baseline

`v0.4.1_13` Model-C-only production and its selected owner-live gates are complete:

- normal Stage 60 uses Model C only; automatic Model B/A production replay is removed;
- Standard RUNNING paths cover exhaustive no-candidate, exhaustive success and early success;
- initial Zapret2 STOPPED behavior is owner-accepted PASS;
- Extended TLS 1.2 and HTTP branches executed truthfully on `job.TJlWoY`;
- the `_13` observation that closed QUIC was capability-skipped is retained only as historical evidence and **is superseded as product behavior by the owner’s `_14` instruction**.

Accepted evidence remains under `docs/verification/evidence/`.

## `_14` current source task — explicit Enable QUIC + Generic UDP input UX

The owner changed the Strategy Lab QUIC contract on 2026-08-15.

### Enable QUIC

The Diagnostics Strategy Lab UI must contain **Enable QUIC** directly below **Generic UDP (optional)** in Extended mode.

Current contract:

- checkbox unchecked → QUIC candidate testing is inactive;
- checkbox checked → QUIC candidate testing is active;
- default is unchecked;
- the checkbox state is persisted in OPNsense configuration and survives page reloads;
- the selected value is copied into each job at launch so an in-flight job has immutable execution intent;
- **this checkbox is the sole decision gate for running QUIC candidate tests**;
- Stage-30 `quic_ipv4` control probing may remain as diagnostic evidence, but its result must never enable, disable or skip QUIC candidate testing;
- when Enable QUIC is ON, Stage 80 runs QUIC candidates even when the control probe says QUIC/IPv4 is blocked;
- when Enable QUIC is OFF, Stage 80 reports QUIC explicitly skipped because it is disabled.

Canonical specialist contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP input UX

The Generic UDP payload contract remains intentionally bounded to **1–4096 decoded bytes**. A 2–3 MB file is invalid and must not be accepted merely to make the button react.

The `_14` requirement is instead to remove the apparent no-op:

- validate the port/file pair and payload size before clearing the previous result or entering running state;
- for a file outside 1–4096 bytes show an explicit visible size error immediately;
- retain authoritative API/backend validation against bypass attempts;
- valid Extended Generic UDP still requires both a destination port and a payload file.

Canonical input contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_14` acceptance boundary

Before `_14` can replace `_13` as the testing handoff:

1. focused QUIC/UDP/UI/backend contracts must pass;
2. the complete required project corrective matrix must pass;
3. FreeBSD 15 package qualification must pass;
4. the exact verified source head must be squash-merged;
5. persistent testing package `v0.4.1_14` must be published from the candidate-defining source merge;
6. the publisher-created publication-record tail must be reconciled and merged;
7. owner-live verification must then confirm:
   - Enable QUIC default OFF and persistence across reload;
   - OFF → QUIC skipped for `disabled`;
   - ON on the owner’s blocked-QUIC path → QUIC candidates actually execute and return truthful `working` or `not_found`, not capability skip;
   - oversized UDP payload → visible 1–4096-byte error without starting/resetting the job UI;
   - valid configured Generic UDP → Stage 80 actually executes UDP and returns truthful `working` or `not_found`.

## Current task reading

For this source task read completely:

1. [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md);
2. [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md);
3. [`architecture/STRATEGY_LAB.md`](architecture/STRATEGY_LAB.md) with the explicit rule that older capability-gating language is historical wherever it conflicts with the specialist `_14` contract;
4. [`verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

For GitHub/package delivery use `CHAT_RULES.md` and `GITHUB_PUBLICATION.md`; a package-affecting source patch automatically continues through persistent testing-package publication and its publication-record tail.

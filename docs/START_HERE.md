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
**Current handoff identity:** `v0.4.1_14`

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=14`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
- testing-package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- source merge and testing-tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- publication workflow run: `31875178597`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_14.md`](verification/evidence/testing-publications/v0.4.1_14.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## What `_14` changes

The owner changed the Strategy Lab QUIC contract on 2026-08-15.

### Enable QUIC

Diagnostics / Strategy Lab Extended mode contains **Enable QUIC** directly below **Generic UDP (optional)**.

Current contract:

- unchecked → QUIC candidate testing is inactive;
- checked → QUIC candidate testing is active;
- default is unchecked;
- the checkbox state is persisted in OPNsense configuration and survives page reloads;
- the resolved choice is copied into each job at launch;
- **the checkbox is the sole decision gate for QUIC candidate execution**;
- Stage-30 `quic_ipv4` probing remains diagnostic only and never enables/disables/skips QUIC candidate testing;
- Enable QUIC ON runs candidates even when the ordinary QUIC control probe is blocked;
- Enable QUIC OFF reports an explicit `disabled` skip.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP input UX

The Generic UDP payload remains intentionally bounded to **1–4096 decoded bytes**.

- port and file must be supplied together;
- file size is checked before the previous result is cleared or the UI enters running state;
- a 2–3 MB file is rejected immediately with a visible `1–4096` size error;
- backend Base64/decoded-size validation remains authoritative;
- valid Extended Generic UDP still requires port `1..65535` plus payload `1..4096` bytes.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_14` source/publication acceptance — PASS

- source PR `#237` latest verified head: `b476131bdd68c51288a0f89478fddd0382c0b5c9`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD 15 package build/inspection qualification: PASS;
- exact-head squash merge: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- publisher FreeBSD 15 build and manifest/digest verification: PASS;
- prerelease `v0.4.1_14`: published and verified;
- tag target: exactly `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- package asset: `os-zapret2-restyle-0.4.1_14.pkg`;
- package digest: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`.

The publisher could not create its Draft publication-record PR because the repository setting currently forbids GitHub Actions from creating/approving pull requests. It had already pushed the machine publication record. The same required Draft tail was therefore opened through the GitHub connector as PR `#238`; no package bytes or release identity were changed.

## Immediate next task — owner-live `_14`

After installing the published `_14` testing package, verify the new behavior rather than repeating the completed `_13` Model-C baseline:

1. Enable QUIC defaults OFF and persists checked/unchecked across Diagnostics reload;
2. Enable QUIC OFF → QUIC `skipped`, reason `disabled`;
3. Enable QUIC ON while the ISP blocks ordinary QUIC → Stage 80 actually tests QUIC candidates (`tested > 0`) and returns truthful `working` or `not_found`, never capability-skip;
4. selecting a 2–3 MB Generic UDP payload shows the visible `1–4096` error and starts no new job;
5. valid UDP port + `1..4096`-byte payload causes actual UDP candidate execution and truthful `working` or `not_found`.

One Extended job may cover items 3 and 5 simultaneously.

## Established baseline retained

`v0.4.1_13` remains accepted historical live evidence for Model-C-only Standard RUNNING paths, initial STOPPED restoration, and Extended TLS 1.2/HTTP execution. Its old closed-QUIC capability skip is historical evidence only and is superseded by the `_14` product contract.

For current live verification read:

1. [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md);
2. [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md);
3. [`verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md).

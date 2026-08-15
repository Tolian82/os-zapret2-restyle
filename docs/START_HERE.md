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
- current published/owner-installed testing package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
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
- valid Extended Generic UDP requires port `1..65535` plus payload `1..4096` bytes.

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

The publisher could not create its Draft publication-record PR because the repository setting currently forbids GitHub Actions from creating/approving pull requests. It had already pushed the machine publication record. The publication-record reconciliation was completed through the GitHub connector and merged without changing package bytes or release identity.

## Current owner-live `_14` observations

The owner installed `_14` and supplied Extended GUI results for `telegram.org` and `rutracker.org` with **Enable QUIC checked**.

Both runs show:

- Stage 30: ordinary QUIC/IPv4 control probe is closed;
- Stage 80: QUIC finishes as `not_found`, not as a capability-based skip;
- Stage 90 restoration: PASS.

This is positive evidence that the old Stage-30 capability gate no longer suppresses an enabled QUIC branch. It does **not yet close the live QUIC execution gate**, because the ordinary GUI output does not show whether `tested` contains real candidate attempts.

Current source inspection establishes the expected execution path:

- current QUIC catalog: `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`;
- production QUIC runner appends each executed candidate result to `tested`;
- enabled live acceptance therefore requires observable `tested > 0` (and preferably attempted candidate count/names), not merely `QUIC=not_found`.

## Immediate follow-up tasks selected by owner-live `_14`

Before calling the `_14` Extended protocol work complete, retain these tasks in the active plan:

1. **Prove real QUIC strategy enumeration:** enabled blocked-control run must show `tested > 0`; expose attempted count/names in ordinary result presentation so telemetry unpacking is not required for the basic proof.
2. **Correct QUIC state wording/localization:** user-facing Stage 30 must render measured state as natural RU/EN (`QUIC открыт` / `QUIC закрыт`, English equivalent) and separately indicate whether QUIC strategy testing is enabled. A closed control probe must not read as an execution skip.
3. **Localize Stage-80 QUIC/UDP summary:** raw fragments such as `QUIC=not_found, UDP=skipped` stay permitted in structured/advanced evidence but normal UI must render human-readable RU/EN meanings.
4. **Localize Enable QUIC help text:** the English-only `When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.` must have RU and EN presentation.
5. **Fix valid-small Generic UDP rejection:** owner reports that a nominal **140-byte** payload is rejected by the visible `1–4096 bytes` size validation even though 140 bytes is valid by contract. Reproduce and trace browser `File.size` → FileReader/Base64 → API transport/decode → job-local payload; add exact 140-byte regression coverage.
6. **Verify the selected Generic UDP port/control exchange:** use the exact validated payload against the selected destination port and surface what was actually observed. UDP silence is not definitive proof that a port is closed and must not suppress bypass candidate testing.

Canonical details are in:

- [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md);
- [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md);
- [`verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`](verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md);
- [`ROADMAP.md`](ROADMAP.md).

This follow-up registration is documentation-only and does **not** change `VERSION`, `PLUGIN_REVISION`, package bytes or testing-tag identity. A later source implementation of these findings must use a new package candidate.

## Remaining `_14` live checks

In addition to the newly selected corrective scope, the still-open owner-live checks are:

- Enable QUIC default OFF and persistence checked/unchecked across Diagnostics reload;
- Enable QUIC OFF → explicit `skipped/disabled` behavior;
- enabled blocked-control QUIC → actual candidate evidence with `tested > 0`;
- valid corrected Generic UDP input → direct/control observation plus actual UDP candidate execution;
- lifecycle restoration and temporary-resource cleanup for these paths.

## Established baseline retained

`v0.4.1_13` remains accepted historical live evidence for Model-C-only Standard RUNNING paths, initial STOPPED restoration, and Extended TLS 1.2/HTTP execution. Its old closed-QUIC capability skip is historical evidence only and is superseded by the `_14` product contract.

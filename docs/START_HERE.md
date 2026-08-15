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
**Current handoff identity:** `v0.4.1_15` owner-live Generic UDP failure investigation

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=15`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_15.pkg` / `v0.4.1_15`;
- testing-package SHA-256: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`;
- source merge and testing-tag target: `a219161c901c663b56cac6757364d3bbd32766c7`;
- publication workflow run: `31879283227`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by this testing publication: **no**.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_15.md`](verification/evidence/testing-publications/v0.4.1_15.md).

Resolve the exact current `main` SHA at execution time under `GH-004`.

## What `_15` changes

Owner-live `_14` Extended checks on `telegram.org` and `rutracker.org` proved that Enable QUIC no longer capability-skips when the ordinary control probe is blocked, but exposed four remaining product-quality gaps:

1. ordinary output did not prove how many QUIC strategies were really attempted;
2. Stage 30 and Stage 80 exposed raw/internal wording instead of clear RU/EN protocol evidence;
3. an owner-selected nominal 140-byte Generic UDP payload was rejected even though the contract allows `1..4096` decoded bytes;
4. Generic UDP did not expose a direct request/response observation for the selected destination port/payload.

`_15` implements the owner-selected corrective scope with code, regression tests and current documentation.

### QUIC execution observability

The `_14` execution rule is preserved:

- Enable QUIC OFF → no QUIC candidates;
- Enable QUIC ON → candidate enumeration runs independently of Stage-30 measured QUIC reachability;
- Stage-30 control probing remains diagnostic only.

`_15` adds ordinary user-facing evidence:

- Stage 30 says `QUIC открыт` / `QUIC закрыт` in Russian and the English equivalent;
- Stage 30 separately says whether QUIC strategy search is enabled, disabled, or belongs to Extended mode;
- Stage 80 renders candidate count and candidate IDs from the actual `tested` array;
- `working` / `not_found` / `skipped` remain structured machine states but are not primary untranslated Stage-80 UI fragments;
- Enable QUIC help has deterministic RU/EN presentation.

Current catalog remains `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP exact bytes and control observation

The payload contract remains **1–4096 decoded bytes** with port `1..65535` and port/file supplied together.

Browser transport is now:

`FileReader.readAsArrayBuffer → Uint8Array.byteLength validation → Base64 → strict API decode → private job-local udp-payload.bin`.

Consequences:

- exact 140-byte binary payload is valid and regression-tested;
- zero bytes and more than 4096 decoded bytes remain invalid;
- the UI does not clear the previous result or start a job before decoded-byte validation succeeds;
- backend strict Base64/decoded-size validation remains authoritative.

Configured Generic UDP performs a direct control exchange using the same selected endpoint IP, destination port and exact job-local payload. Evidence records endpoint/IP, port, payload byte count, reply observed/not observed, timeout and duration. Lack of a reply is explicitly **not** classified as a closed port and **does not gate** subsequent bypass candidate search.

Stage 80 reports actual UDP candidate count/IDs and winner/no-winner meaning in RU/EN.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_15` source/publication acceptance — PASS

- source PR `#241` latest verified head: `ecf3d5269574988e56707c68b6eb9696d936b1ca`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD 15 package build/inspection qualification: PASS;
- exact-head squash merge: `a219161c901c663b56cac6757364d3bbd32766c7`;
- publisher FreeBSD 15 build and manifest/digest verification: PASS;
- prerelease `v0.4.1_15`: published and verified;
- tag target: exactly `a219161c901c663b56cac6757364d3bbd32766c7`;
- package asset: `os-zapret2-restyle-0.4.1_15.pkg`;
- package digest: `e25c47519844623f6e1fcfe4d45a517960d06d0939f5cf004112a02186a5701f`.

The publisher again could not create its Draft publication-record PR because the repository setting forbids GitHub Actions from creating/approving pull requests. It had already pushed the machine publication record. The same required Draft tail was opened through the GitHub connector as PR `#242`; package identity/bytes were not changed.

## Latest owner-live `_15` finding — Generic UDP still FAIL

The owner installed `_15` and repeated an Extended `rutracker.org` check with Generic UDP port `53` and Enable QUIC ON. QUIC attempt observability worked, but Generic UDP still did not become configured: attaching a small file did not produce a usable selected/uploaded payload and Stage 80 reported UDP as not configured.

This is now a confirmed owner-live product defect. The current investigation hypothesis is that the file may not reach the backend/job-local payload path at all. Possible filesystem ownership/permissions on the Strategy Lab runtime/job directory are specifically retained as a hypothesis, **not** as a proven root cause.

Durable evidence: [`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

The next implementation decision must follow an end-to-end trace of browser selection → ArrayBuffer/Base64 → API/configd → launcher job-local `udp-payload.bin`/`udp-port` creation and permissions → Python configured-UDP detection. Do not close the 140-byte/Generic UDP row from automated tests alone.

## Remaining owner-live `_15` work

Do not repeat already accepted broad Model-C baseline work. Preserve/finish the materially changed `_15` checks:

1. RU/EN Diagnostics localization checks not yet explicitly accepted;
2. Enable QUIC OFF → natural localized disabled wording;
3. investigate and correct the confirmed Generic UDP live file-selection/upload failure before retrying 140-byte acceptance;
4. after correction, configured UDP must show selected port, payload bytes, endpoint/IP, direct reply/no-reply observation and actual candidate count/IDs;
5. no-reply UDP wording must never claim the port is closed;
6. Stage 90 restoration and temporary process/firewall/socket cleanup remain mandatory.

## Established baseline retained

- `v0.4.1_13`: accepted Model-C-only Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence.
- `v0.4.1_14`: accepted explicit Enable QUIC as the sole execution gate; owner-live blocked-control runs selected the `_15` observability/input correction.

Historical evidence remains evidence of what those packages did; it is not rewritten to look like `_15` behavior.

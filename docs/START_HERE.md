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
**Current handoff identity:** `v0.4.1_15` source candidate

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- `VERSION=0.4.1`;
- current source candidate: `PLUGIN_REVISION=15`;
- current published/owner-installed testing package remains `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14` until `_15` source acceptance, merge and persistent publication complete;
- `_14` testing-package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- `_14` source merge/testing-tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- required ABI: `FreeBSD:15:amd64`;
- stable Pages/pkg repository promoted by `_14`: **no**.

Resolve the exact current `main` SHA at execution time under `GH-004`.

## Why `_15` exists

Owner-live `_14` Extended checks on `telegram.org` and `rutracker.org` proved that Enable QUIC no longer capability-skips when the ordinary control probe is blocked, but exposed four remaining product-quality gaps:

1. ordinary output did not prove how many QUIC strategies were really attempted;
2. Stage 30 and Stage 80 exposed raw/internal wording instead of clear RU/EN protocol evidence;
3. an owner-selected nominal 140-byte Generic UDP payload was rejected even though the contract allows `1..4096` decoded bytes;
4. Generic UDP did not expose a direct request/response observation for the selected destination port/payload.

The owner selected one corrective package scope covering those findings. `_15` implements that scope together with regression tests and documentation.

## `_15` source contract

### QUIC execution observability

The `_14` execution rule is preserved:

- Enable QUIC OFF → no QUIC candidates;
- Enable QUIC ON → candidate enumeration runs independently of Stage-30 measured QUIC reachability;
- Stage-30 control probing remains diagnostic only.

`_15` adds ordinary user-facing evidence:

- Stage 30 says `QUIC открыт` / `QUIC закрыт` in Russian and the English equivalent;
- Stage 30 separately says whether QUIC strategy search is enabled, disabled, or unavailable because Standard mode is selected;
- Stage 80 renders candidate count and candidate IDs from the actual `tested` array;
- `working` / `not_found` / `skipped` remain structured machine states but are no longer exposed as untranslated raw fragments in ordinary Stage-80 text;
- the Enable QUIC help text has deterministic RU/EN presentation independent of missing gettext entries.

Current catalog remains:

- `quic-fake-1`;
- `quic-fake-2`;
- `quic-ipfrag-8`;
- `quic-ipfrag-16`.

Canonical contract: [`architecture/STRATEGY_LAB_QUIC_CONTROL.md`](architecture/STRATEGY_LAB_QUIC_CONTROL.md).

### Generic UDP exact bytes and control observation

The payload contract remains **1–4096 decoded bytes** with port `1..65535` and port/file supplied together.

`_15` changes the browser transport path from Data-URL/File.size ownership to exact binary-byte ownership:

`FileReader.readAsArrayBuffer → Uint8Array.byteLength validation → Base64 → strict API decode → private job-local udp-payload.bin`.

Consequences:

- an exact 140-byte binary payload is valid and has dedicated regression coverage;
- zero bytes and more than 4096 decoded bytes remain invalid;
- the UI does not clear the previous result or start a job before decoded-byte validation succeeds;
- backend strict Base64/decoded-size validation remains authoritative.

Before bypass candidates, configured Generic UDP performs a direct control exchange using the **same selected endpoint IP, destination port and exact job-local payload**. Evidence records endpoint/IP, port, payload byte count, reply observed/not observed, timeout and duration. Lack of a reply is explicitly **not** classified as a closed port and **does not gate** the subsequent bypass candidate search.

Stage 80 then reports the actual UDP candidate count/IDs and any working candidate in RU/EN.

Canonical contract: [`architecture/STRATEGY_LAB_UDP_INPUT.md`](architecture/STRATEGY_LAB_UDP_INPUT.md).

## `_15` automated acceptance boundary

Before merge/publication the source candidate must pass:

1. exact 140-byte UDP input regression;
2. binary ArrayBuffer/Base64 transport contract;
3. direct UDP control-exchange exact endpoint/port/payload regression;
4. UDP-silence non-gating/non-`port closed` semantics;
5. Stage-30 RU/EN QUIC state + execution-choice presentation;
6. Stage-80 RU/EN QUIC/UDP candidate count/name presentation without raw `not_found`/`skipped` UI fragments;
7. existing Enable QUIC blocked-control candidate-execution regression;
8. complete Strategy Lab corrective matrix;
9. FreeBSD 15 package build/inspection qualification;
10. exact-head merge and persistent `v0.4.1_15` testing-package publication under `GH-060/GH-061`.

Publication facts that do not exist until the immutable package is published will be reconciled in the bounded publication-record tail.

## Owner-live checks after `_15` publication

Do not repeat already accepted broad Model-C baseline work. Verify only the materially changed paths:

1. Russian and English Diagnostics show localized Enable QUIC/Generic UDP help;
2. Extended + Enable QUIC ON with ordinary QUIC blocked → Stage 30 says QUIC blocked/closed **and** strategy search enabled, while Stage 80 shows `tested > 0` plus attempted QUIC IDs;
3. Enable QUIC OFF → Stage 80 says search disabled in natural RU/EN text;
4. exact/small Generic UDP payload, including a 140-byte sample, starts normally;
5. configured UDP Stage 80 shows selected port, payload bytes, endpoint/IP, direct reply observed/not observed, actual candidate count/IDs, and truthful winner/no-winner result;
6. no-reply UDP wording never claims the port is closed;
7. Stage 90 restoration and temporary process/firewall/socket cleanup remain PASS.

## Established baseline retained

- `v0.4.1_13`: accepted Model-C-only Standard RUNNING/STOPPED and Extended TLS 1.2/HTTP evidence.
- `v0.4.1_14`: accepted source/publication behavior for explicit Enable QUIC as sole QUIC execution gate; owner-live evidence showed blocked control probe → `not_found` instead of capability skip and selected the `_15` observability/input correction.

Historical evidence remains evidence of what those packages did; it is not rewritten to look like `_15` behavior.

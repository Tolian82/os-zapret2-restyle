# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15
**Direct UDP/control-observation implementation:** `v0.4.1_15`
**Browser handoff correction published in:** `v0.4.1_16`

## Purpose

Expose Generic UDP request/response bypass testing through Diagnostics without accepting arbitrary server-side file paths, misclassifying UDP silence, or retaining payload bytes after a job ends.

The owner-live `_15` retry established that the real browser path still failed even though the backend exact-140-byte regression passed. Source tracing then identified an architectural weakness at the browser boundary: the application did not own a prepared payload. It re-read `input.files[0]` only when **Run** was pressed, so loss/reset of the native file-control selection produced the observed port+file validation failure before API/configd/job-local storage was reached.

## Important transport fact

Generic UDP does **not** use a multipart upload directory.

The selected local file is read in the browser, converted to Base64, and sent in the normal Strategy Lab start POST. Only after the API/configd launcher accepts that request is the payload decoded into the private job-local `udp-payload.bin` file.

Therefore a GUI state where the selected file is already absent and no new configured-UDP job is created cannot be caused first by permissions on `udp-payload.bin`: that filesystem boundary has not yet been reached. Permissions remain a valid later-stage failure possibility and `_16` has explicit diagnostics for that boundary.

## Supported request

Generic UDP is optional and accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port: integer `1..65535`;
- one local browser-selected payload: decoded size **`1..4096` bytes**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

An exact 140-byte file is valid. Multi-megabyte files are deliberately invalid.

## `_16` browser-owned staging

The browser owns a prepared payload state independently of the native file-input display:

`file input change -> capture File -> FileReader.readAsArrayBuffer -> Uint8Array.byteLength -> binary Base64 -> application-owned staged state -> Run -> start API`.

On every file-selection `change` event the application immediately:

1. captures the selected `File` object;
2. starts `readAsArrayBuffer` immediately rather than waiting for Run;
3. validates the exact decoded byte count `1..4096`;
4. Base64-encodes those exact bytes;
5. stores filename, decoded byte count and Base64 in application-owned state;
6. displays localized positive evidence such as `Файл подготовлен к отправке: <name>, <N> байт` / `Payload ready to send: <name>, <N> bytes`.

The Run handler uses the staged Base64 when it is ready. It no longer depends exclusively on the native control still exposing `input.files[0]` at Run time.

A defensive fallback remains: if a native `File` is present at Run but the `change` event did not finish staging, Run stages that file first and only starts the job after successful preparation.

The browser no longer uses a realm-specific `buffer instanceof ArrayBuffer` test; it validates the returned object through `byteLength`, avoiding an unnecessary cross-realm assumption.

## API/configd boundary

`StrategyLabController::startAction()` remains authoritative for:

- Extended-mode requirement when UDP input is present;
- port range;
- canonical Base64 syntax;
- strict Base64 decode;
- decoded payload size `1..4096`.

The validated Base64 is forwarded as an argument through configd together with the port and explicit Enable QUIC choice. Disabled Generic UDP uses the explicit `- -` sentinel pair.

## Job-local storage

After the job directory exists, the launcher decodes the accepted Base64 into:

- private `udp-payload.bin`;
- private `udp-port`.

Both use mode `0600`. Public `status.json` stores only `configured`, port and decoded payload byte count; raw payload/Base64 is not retained in public state.

## `_16` server-side failure attribution

The job-local preparation layer records a precise non-payload error code before returning failure. This distinguishes a later filesystem/backend failure from the earlier browser-selection failure.

Current classes include:

- `job_directory_unavailable`;
- `job_directory_not_writable`;
- `payload_temp_create_failed` / `port_temp_create_failed`;
- `base64_invalid` / `base64_decode_failed`;
- `payload_size_invalid`;
- `port_write_failed`;
- `chmod_failed`;
- `payload_move_failed` / `port_move_failed`;
- `state_record_failed`.

The launcher includes that code in its error response. Thus an owner/mode/permissions problem, if it occurs on OPNsense, is directly distinguishable instead of being collapsed into `Invalid Strategy Lab generic UDP input`.

## Direct destination-port/control observation

For a configured request, the existing `_15` logic performs a bounded direct UDP observation before bypass candidates, using the same fixed search-epoch selected IP, the selected destination port and the exact job-local payload bytes.

Structured evidence records endpoint/IP, destination port, payload byte count, reply observed/not observed, return/timeout state and duration.

### Non-gating semantics

**UDP silence is not proof that a port is closed.**

`reply_observed=false` means only that no reply was observed during the bounded control exchange. It does not suppress the bypass candidate catalog and is never translated into a definitive `port closed` claim.

## Candidate execution and Stage 80

Configured UDP candidates receive:

- `STRATEGY_LAB_UDP_PORT` = selected port;
- `STRATEGY_LAB_UDP_PAYLOAD_FILE` = private job-local payload.

Every executed candidate is appended to structured `tested`. Ordinary RU/EN Stage-80 presentation reports configured port/payload/endpoints, direct observation, actual candidate count/IDs and working/no-working result while raw machine enums remain in structured evidence.

## Cleanup

`udp-payload.bin` and `udp-port` are removed during normal restoration and error/cancel/stale-worker cleanup. Terminal evidence may retain metadata/control results but not payload bytes.

## `_16` automated/publication acceptance — PASS

Repository acceptance proves:

1. the file input has a `change` handler;
2. selection is immediately read and stored in application-owned state;
3. exact decoded-byte validation occurs before staging;
4. the normal Run path uses staged Base64 rather than depending exclusively on `input.files[0]`;
5. RU/EN ready-to-send filename/byte evidence exists;
6. exact 140-byte backend decode remains PASS;
7. missing/unwritable job-directory and other server preparation failures are attributed by explicit code;
8. direct selected-port/payload observation and non-gating UDP-silence semantics remain intact;
9. complete Strategy Lab corrective matrix PASS;
10. FreeBSD-15 package qualification PASS.

Published testing identity:

- tag: `v0.4.1_16`;
- candidate/tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- package: `os-zapret2-restyle-0.4.1_16.pkg`;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- publication workflow run: `31882091770`;
- stable Pages/pkg repository promoted: no.

Machine publication evidence: [`../verification/evidence/testing-publications/v0.4.1_16.md`](../verification/evidence/testing-publications/v0.4.1_16.md).

## Owner-live `_16` acceptance

After installing the published `_16` testing package:

- selecting a valid small payload must immediately show an application-owned `ready to send` line with the exact decoded byte count;
- a 140-byte sample must show `140` bytes and a new Strategy Lab job must start with configured UDP;
- Stage 80 must show selected port/payload bytes/endpoints, direct reply/no-reply evidence and actual UDP candidate IDs;
- no-reply wording must not claim the port is closed;
- if job-local filesystem preparation fails, the UI/API error must identify the preparation class instead of silently reverting to unconfigured UDP;
- oversized input still fails before a new job starts;
- Stage-90 restoration and temporary resource cleanup remain PASS.
# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15
**Exact-byte/control-observation implementation published in:** `v0.4.1_15`
**Current owner-live state:** file-selection/upload path FAIL — investigation required

## Purpose

Expose generic UDP request/response bypass testing through the supported Diagnostics GUI/API without accepting arbitrary server-side file paths, misclassifying UDP silence, or retaining user payload data after the job ends.

The owner-live `_13` follow-up exposed an oversized-file apparent no-op; `_14` added visible bounded validation. The first owner-live `_14` follow-up then exposed a second defect: a payload reported as **140 bytes** was rejected by the GUI despite the valid `1..4096` decoded-byte contract. `_15` corrected the intended browser transport/validation ownership and added direct destination-port observation, but the first live `_15` retry proves that the real browser-to-job file path is still not operational.

## Supported request

Generic UDP input is optional and accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port: integer `1..65535`;
- one local browser-selected payload file: decoded size **`1..4096` bytes**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

A 2–3 MB file is deliberately invalid. An exact 140-byte file is valid by contract.

## Intended browser exact-byte transport

The intended `_15` browser flow is:

`selected File -> FileReader.readAsArrayBuffer -> Uint8Array -> byteLength 1..4096 -> binary Base64 -> start API`.

Consequences required by the product contract:

- validation is against the exact bytes that will be Base64-encoded;
- a 140-byte binary file remains 140 decoded bytes through the transport contract;
- zero bytes and more than 4096 decoded bytes are rejected visibly;
- invalid decoded size is detected before `beginStart()` clears the previous result, marks the UI busy, or starts a new job;
- browser validation remains UX defense, while backend strict decode/size validation remains authoritative.

Automated source tests prove these intended code-level invariants, but they do **not** prove the complete live browser-to-job handoff.

## API and configd boundary

`StrategyLabController::startAction()` validates:

- mode is `extended` when UDP input is present;
- port is decimal and within range;
- Base64 syntax is canonical;
- decoded payload is non-empty and no larger than 4096 bytes.

The validated request is forwarded together with the explicit Strategy Lab QUIC choice. Disabled Generic UDP uses the explicit `- -` sentinel pair.

## Job-local storage

After the job directory/status document exist, the launcher is intended to:

1. decode payload into private `udp-payload.bin`;
2. write validated port into private `udp-port`;
3. set mode `0600` on both files;
4. record only `configured`, `port`, and `payload_bytes` in public `status.json`.

No raw payload or Base64 content is stored in public state. Python extended orchestration reads only these fixed job-local paths; client input cannot choose another server-side path.

## Direct destination-port/control observation

For a configured request, `_15` performs a bounded direct UDP observation **before** bypass candidates using the same immutable search-epoch bindings used by candidate execution.

For each fixed selected endpoint IP it sends:

- the exact selected destination port;
- the exact job-local payload bytes.

Structured control evidence records:

- endpoint name;
- selected IPv4 address;
- destination port;
- payload byte count;
- whether any reply bytes were observed;
- process return state/timeout;
- duration.

The aggregate result records whether any direct reply was observed.

### Non-gating semantics

**UDP silence is not proof that a port is closed.** A valid UDP service can ignore an arbitrary payload.

Therefore:

- `reply_observed=false` means only that no reply was observed in the bounded control exchange;
- ordinary RU/EN presentation explicitly says that this does not mean the port is closed;
- the control result never suppresses or short-circuits the bypass candidate catalog;
- configured UDP continues to candidate testing whether a direct reply was observed or not.

## Candidate execution

Configured UDP candidates receive the exact validated values through the unified candidate runtime:

- `STRATEGY_LAB_UDP_PORT` = selected port;
- `STRATEGY_LAB_UDP_PAYLOAD_FILE` = private job-local payload path.

Each executed candidate is appended to structured `tested`. The branch may finish:

- `working` when a candidate passes; or
- `not_found` after the catalog completes without a winner.

A valid configured request must not be silently rewritten to an unconfigured skip.

## Stage-80 RU/EN presentation

Raw machine enums remain stable in structured/advanced evidence.

Normal Stage-80 text distinguishes:

- UDP not configured;
- configured port/payload and selected endpoint IP(s);
- direct reply observed vs no reply observed;
- explicit warning that no reply does not prove port closure;
- number and IDs of actual UDP candidates in `tested`;
- working candidate ID or natural no-working-strategy wording.

Raw fragments such as `UDP=skipped` / `UDP=not_found` are not the primary normal UI explanation.

## Cleanup

Payload and port files are removed:

- during normal terminal restoration;
- after cancellation, timeout, internal error, or restoration failure;
- by stale-worker reconciliation;
- when worker launch fails.

A terminal job may retain structured UDP result/control evidence but not user payload bytes.

## Automated `_15` verification

Repository acceptance for `_15` proved:

1. exact 140-byte payload survives mocked/Base64 transport and job-local decode with `payload_bytes=140`;
2. browser source uses `readAsArrayBuffer`, `Uint8Array.byteLength`, and Base64 of the validated exact bytes;
3. browser no longer rejects by `File.size` as authoritative size owner and no longer parses Data URLs;
4. zero/>4096 backend bounds and canonical Base64 validation remain intact;
5. direct control observation uses exact selected IP, destination port and payload bytes;
6. control evidence records reply/no-reply without introducing a `port_closed` conclusion;
7. no-reply control evidence does not gate candidate execution;
8. RU/EN Stage-80 presentation exposes port/payload/endpoints, control observation, actual candidate count/IDs and winner/no-winner meaning.

Automated `_15` source acceptance and persistent testing-package publication are complete. Machine publication evidence is in [`../verification/evidence/testing-publications/v0.4.1_15.md`](../verification/evidence/testing-publications/v0.4.1_15.md).

## Owner-live `_15` failure — browser-to-job file path

The first owner-live retry on the published `_15` package still fails before configured UDP execution.

Observed/reported live state:

- Strategy Lab is in Extended mode;
- UDP port `53` is entered;
- attaching a valid small file does not produce a usable selected/uploaded payload;
- GUI evidence remains `Не выбран ни один файл` and shows the `1–4096` / port+file validation message;
- the job can still run through other protocols;
- Stage 80 reports UDP as not configured.

Therefore the live product contract is currently violated even though automated exact-byte tests pass.

Durable evidence: [`../verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](../verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

### Root cause status

Root cause is **not yet established**.

The owner's current suspicion is that the file may simply never be uploaded/saved. Filesystem ownership/permissions on the Strategy Lab runtime/job directory or payload path are specifically retained as a plausible hypothesis.

Do not encode that hypothesis as fact until live tracing proves it.

### Required investigation order

Trace the same real request end to end before changing code:

1. browser file input `change` event fires;
2. the expected selected `File` object exists after selection;
3. `readAsArrayBuffer` completes and yields the real byte count;
4. Base64 is generated and present in the actual Strategy Lab start request;
5. `StrategyLabController::startAction()` receives and accepts the payload;
6. configd/launcher receives the payload argument rather than the disabled `-` sentinel;
7. the job directory exists with expected owner/mode;
8. launcher can create/write `udp-payload.bin` and `udp-port` with mode `0600`;
9. Python sees those job-local files and marks UDP configured;
10. terminal cleanup removes payload bytes without masking earlier write/permission errors.

If live evidence identifies permissions/ownership as the failure point, fix that exact lifecycle boundary. If the failure is earlier in the browser/API path, do not add unrelated filesystem changes.

## Current owner-live acceptance

The following remains open until the file path is corrected:

- a valid small payload, including a 140-byte sample, starts as configured UDP;
- configured UDP shows the selected port, decoded payload bytes and selected endpoint/IP;
- direct control observation shows reply/no-reply truthfully;
- no-reply wording does not claim the port is closed;
- actual UDP candidate count/IDs are visible and non-zero when configured search runs;
- winner/no-winner result is human-readable in the selected RU/EN language;
- oversized input still fails before a new job starts;
- Stage-90 restoration/resource cleanup remains PASS.

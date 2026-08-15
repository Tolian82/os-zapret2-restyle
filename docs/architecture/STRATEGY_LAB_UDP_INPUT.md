# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15
**Exact-byte/control-observation implementation published in:** `v0.4.1_15`

## Purpose

Expose generic UDP request/response bypass testing through the supported Diagnostics GUI/API without accepting arbitrary server-side file paths, misclassifying UDP silence, or retaining user payload data after the job ends.

The owner-live `_13` follow-up exposed an oversized-file apparent no-op; `_14` added visible bounded validation. The first owner-live `_14` follow-up then exposed a second defect: a payload reported as **140 bytes** was rejected by the GUI despite the valid `1..4096` decoded-byte contract. `_15` corrects the browser transport/validation ownership and adds direct destination-port observation.

## Supported request

Generic UDP input is optional and accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port: integer `1..65535`;
- one local browser-selected payload file: decoded size **`1..4096` bytes**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

A 2–3 MB file is deliberately invalid. An exact 140-byte file is valid and has dedicated regression coverage.

## Browser exact-byte transport

The browser no longer treats `File.size` or Data-URL parsing as the authoritative payload contract.

Current `_15` flow is:

`selected File -> FileReader.readAsArrayBuffer -> Uint8Array -> byteLength 1..4096 -> binary Base64 -> start API`.

Consequences:

- validation is against the exact bytes that will be Base64-encoded;
- a 140-byte binary file remains 140 decoded bytes through the transport contract;
- zero bytes and more than 4096 decoded bytes are rejected visibly;
- invalid decoded size is detected before `beginStart()` clears the previous result, marks the UI busy, or starts a new job;
- browser validation remains UX defense, while backend strict decode/size validation remains authoritative.

## API and configd boundary

`StrategyLabController::startAction()` validates:

- mode is `extended` when UDP input is present;
- port is decimal and within range;
- Base64 syntax is canonical;
- decoded payload is non-empty and no larger than 4096 bytes.

The validated request is forwarded together with the explicit Strategy Lab QUIC choice. Disabled Generic UDP uses the explicit `- -` sentinel pair.

## Job-local storage

After the job directory/status document exist, the launcher:

1. decodes payload into private `udp-payload.bin`;
2. writes validated port into private `udp-port`;
3. sets mode `0600` on both files;
4. records only `configured`, `port`, and `payload_bytes` in public `status.json`.

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

Normal Stage-80 text now distinguishes:

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

## Verification

Repository acceptance for `_15` proves:

1. exact 140-byte payload survives Base64 transport and job-local decode with `payload_bytes=140`;
2. browser source uses `readAsArrayBuffer`, `Uint8Array.byteLength`, and Base64 of the validated exact bytes;
3. browser no longer rejects by `File.size` as authoritative size owner and no longer parses Data URLs;
4. zero/>4096 backend bounds and canonical Base64 validation remain intact;
5. direct control observation uses exact selected IP, destination port and payload bytes;
6. control evidence records reply/no-reply without introducing a `port_closed` conclusion;
7. no-reply control evidence does not gate candidate execution;
8. RU/EN Stage-80 presentation exposes port/payload/endpoints, control observation, actual candidate count/IDs and winner/no-winner meaning.

Automated `_15` source acceptance and persistent testing-package publication are complete. Machine publication evidence is in [`../verification/evidence/testing-publications/v0.4.1_15.md`](../verification/evidence/testing-publications/v0.4.1_15.md).

## Current owner-live `_15` acceptance

After installing the published `_15` testing package:

- a valid small payload, including a 140-byte sample, must start normally;
- configured UDP must show the selected port, decoded payload bytes and selected endpoint/IP;
- direct control observation must show reply/no-reply truthfully;
- no-reply wording must not claim the port is closed;
- actual UDP candidate count/IDs must be visible and non-zero when configured search runs;
- winner/no-winner result must be human-readable in the selected RU/EN language;
- oversized input must still fail before a new job starts;
- Stage-90 restoration/resource cleanup must remain PASS.

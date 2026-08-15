# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15

## Purpose

Expose generic UDP request-response testing through the supported Diagnostics GUI/API without accepting arbitrary server-side file paths or retaining user payload data after the job ends.

The owner-live `_13` follow-up exposed a UX defect: selecting a multi-megabyte payload and pressing Run appeared to do nothing. `_14` fixes that presentation/validation defect without weakening the bounded payload contract.

## Supported request

Generic UDP input is optional and is accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port, integer `1..65535`;
- one local payload file selected in the browser, decoded size **`1..4096` bytes**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

A 2–3 MB file is deliberately invalid. The correct behavior is an explicit visible validation error, not accepting/streaming a large arbitrary payload.

## GUI validation and no-op prevention

Before the GUI clears the previous Strategy Lab result, marks the UI busy, or starts a new request, it validates:

- port and file are either both absent or both present;
- when a file is present, browser-reported size is `1..4096` bytes.

If validation fails:

- no Strategy Lab job is started;
- the previous result is not cleared merely because Run was clicked;
- the UI shows an explicit user-visible error;
- oversized payload text states that the file must contain between 1 and 4096 bytes.

Only a valid browser-side request proceeds to file reading/Base64 encoding and asynchronous start.

Browser validation is UX only; backend validation remains authoritative.

## API and configd boundary

`StrategyLabController::startAction()` validates:

- mode is `extended` when UDP input is present;
- port is decimal and within range;
- Base64 syntax is canonical;
- decoded payload is non-empty and no larger than 4096 bytes.

The validated Generic UDP request is forwarded together with the explicit Strategy Lab QUIC choice. Disabled Generic UDP uses the explicit `- -` sentinel pair.

The launcher retains backward-compatible start forms while the current GUI/API sends the explicit QUIC flag plus the UDP pair.

## Job-local storage

After the job directory and initial status document exist, the launcher:

1. decodes the payload into `udp-payload.bin` inside that job directory;
2. writes the validated port into `udp-port`;
3. sets mode `0600` on both files;
4. records only non-sensitive metadata in `status.json`: `configured`, `port`, and `payload_bytes`.

No raw payload or Base64 content is stored in the public status document.

Python extended orchestration derives the UDP port and payload exclusively from these fixed job-local paths. Client input cannot select another server-side path.

## Stage-80 result semantics

When Generic UDP is not configured, Stage 80 may report UDP `skipped`.

When both valid inputs are configured, Stage 80 must actually execute the UDP catalog. A truthful completed UDP branch may return:

- `working`; or
- `not_found`.

A configured valid request must not be silently rewritten to an unconfigured skip.

## Cleanup

The payload and port files are removed:

- during every normal terminal worker path;
- after cancellation, timeout, internal error, or restoration failure;
- by stale-worker reconciliation;
- when worker launch fails.

A terminal Strategy Lab job therefore retains UDP result evidence but no user payload bytes.

## Verification

`test-strategy-lab-udp-input-contract.sh` verifies valid input, disabled input, private file modes, exact decoding, cleanup and rejection of:

- standard-mode UDP configuration;
- missing port or payload;
- invalid or out-of-range port;
- noncanonical Base64;
- payloads larger than 4096 bytes.

For `_14` it additionally verifies that the browser size check and visible error occur before Strategy Lab UI/job state is reset.

Owner-live `_14` verification should include both:

1. an oversized file (for example the previously attempted 2–3 MB case) producing immediate visible `1–4096` validation without starting a job; and
2. a valid `1..4096`-byte payload plus port producing actual Stage-80 UDP execution and truthful `working` or `not_found`.

# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE
**Updated:** 2026-08-15

## Purpose

Expose generic UDP request-response testing through the supported Diagnostics GUI/API without accepting arbitrary server-side file paths or retaining user payload data after the job ends.

The owner-live `_13` follow-up exposed a UX defect: selecting a multi-megabyte payload and pressing Run appeared to do nothing. `_14` fixed that presentation/validation path without weakening the bounded payload contract.

The first owner-live `_14` follow-up exposed a second defect: a payload reported as **140 bytes** is rejected by the GUI with the `1–4096 bytes` size error. That behavior contradicts this contract and is now a selected defect for reproduction and correction.

## Supported request

Generic UDP input is optional and is accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port, integer `1..65535`;
- one local payload file selected in the browser, decoded size **`1..4096` bytes**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

A 2–3 MB file is deliberately invalid. A 140-byte file is valid by size and must not be rejected merely by the size contract.

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

### Selected `_14` valid-small-file defect

The owner reports that a nominal 140-byte file currently reaches the same visible size-range error as an invalid oversized file.

The next implementation must reproduce and trace the full path rather than patching only the displayed text:

1. browser `File.size` and selected file identity;
2. FileReader result and extracted Base64 payload;
3. API field transport without accidental truncation/transformation;
4. strict Base64 decode and decoded byte count;
5. launcher/job-local payload byte count.

Regression coverage must include an exact 140-byte payload and boundary-valid payloads. The browser, API and backend must agree on the same decoded `1..4096` byte contract.

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

## Destination-port/control-exchange verification

The owner requires verification that the selected Generic UDP destination port is actually exercised rather than merely accepted syntactically.

The next implementation must perform and expose a direct/control exchange using:

- the resolved Strategy Lab target endpoint(s);
- the user-selected UDP destination port;
- the exact validated payload bytes.

The result must describe the observation truthfully, for example a response was received, no response was observed within the bounded probe, or the exchange could not be determined.

**UDP silence is not, by itself, proof that a port is closed.** Many valid UDP services do not answer arbitrary payloads. Therefore:

- do not label a port definitely closed solely because no reply arrived;
- do not use the direct/control result as a gate that suppresses UDP bypass candidate testing;
- retain the result as diagnostic/control evidence analogous to the QUIC control probe;
- when a protocol-specific response can be validated, record that stronger evidence explicitly.

## Stage-80 result semantics and localization

When Generic UDP is not configured, Stage 80 may report UDP `skipped` in structured/raw data.

When both valid inputs are configured, Stage 80 must actually execute the UDP catalog. A truthful completed UDP branch may return:

- `working`; or
- `not_found`.

A configured valid request must not be silently rewritten to an unconfigured skip.

Raw machine enums may remain stable in JSON/evidence. The normal UI must render localized RU/EN meanings rather than fragments such as `UDP=skipped`.

At minimum presentation must distinguish:

- not configured/not tested;
- configured and tested with no working strategy;
- configured and a working strategy found.

## Cleanup

The payload and port files are removed:

- during every normal terminal worker path;
- after cancellation, timeout, internal error, or restoration failure;
- by stale-worker reconciliation;
- when worker launch fails.

A terminal Strategy Lab job therefore retains UDP result evidence but no user payload bytes.

## Verification

Existing `test-strategy-lab-udp-input-contract.sh` coverage verifies valid input, disabled input, private file modes, exact decoding, cleanup and rejection of:

- standard-mode UDP configuration;
- missing port or payload;
- invalid or out-of-range port;
- noncanonical Base64;
- payloads larger than 4096 bytes.

The current follow-up must additionally verify:

1. exact 140-byte valid payload through browser/API/backend/job-local storage;
2. valid boundary sizes remain accepted;
3. oversized input still fails visibly before UI/job reset;
4. configured destination port and exact payload are used by the direct/control exchange;
5. absence of a UDP response is not misrepresented as definitive port closure and does not suppress candidate search;
6. RU/EN user-facing UDP result text does not expose raw status enums.

Owner-live follow-up should include both:

- a valid small payload plus selected port producing observable control-exchange evidence and actual Stage-80 UDP candidate execution; and
- an oversized file producing immediate visible validation without starting a job.

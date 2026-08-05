# Strategy Lab generic UDP input contract

## Purpose

Expose the already implemented generic UDP request-response branch through the supported
Diagnostics GUI and API without accepting arbitrary server-side file paths or retaining
user payload data after the job ends.

## Supported request

Generic UDP input is optional and is accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port, integer `1..65535`;
- one local payload file selected in the browser, with decoded size `1..4096` bytes.

Both values must be present together. Supplying only one value is invalid. Standard mode
must not carry generic UDP input.

The browser reads the selected file and sends canonical Base64 content. The API performs
authoritative validation and never accepts a filesystem path from the client.

## API and configd boundary

`StrategyLabController::startAction()` validates:

- mode is `extended` when UDP input is present;
- port is decimal and within range;
- Base64 syntax is canonical;
- decoded payload is non-empty and no larger than 4096 bytes.

The validated request is forwarded to `strategy_lab_start` as two additional positional
parameters. Disabled generic UDP uses the explicit `- -` sentinel pair.

The launcher keeps backward compatibility with the historical three-value start request,
which is interpreted as generic UDP disabled.

## Job-local storage

After the job directory and initial status document exist, the launcher:

1. decodes the payload into `udp-payload.bin` inside that job directory;
2. writes the validated port into `udp-port`;
3. sets mode `0600` on both files;
4. records only non-sensitive metadata in `status.json`:
   `configured`, `port`, and `payload_bytes`.

No raw payload or Base64 content is stored in the public status document.

The worker derives `STRATEGY_LAB_UDP_PORT` and
`STRATEGY_LAB_UDP_PAYLOAD_FILE` exclusively from these fixed job-local paths. Client input
cannot select another path.

## Cleanup

The payload and port files are removed:

- during every normal terminal worker path;
- after cancellation, timeout, internal error, or restoration failure;
- by stale-worker reconciliation;
- when worker launch fails.

A terminal Strategy Lab job must therefore retain UDP result evidence but no user payload
bytes.

## Verification

`test-strategy-lab-udp-input-contract.sh` dynamically verifies valid input, disabled input,
private file modes, exact decoding, worker export, cleanup, and rejection of:

- standard-mode UDP configuration;
- missing port or payload;
- invalid or out-of-range port;
- noncanonical Base64;
- payloads larger than 4096 bytes.

The test also verifies the GUI, API, configd, launcher, worker, and cleanup wiring and is
part of the mandatory domain-diagnostics contract.

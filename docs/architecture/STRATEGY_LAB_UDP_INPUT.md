# Strategy Lab generic UDP input contract

**Status:** CURRENT SPECIALIST ARCHITECTURE

## Purpose

Expose Generic UDP request/response bypass testing through Diagnostics without accepting arbitrary server-side file paths, misclassifying UDP silence, or retaining payload bytes after a job ends.

## Important transport fact

Generic UDP does **not** use a multipart upload directory.

The selected local file is read in the browser, converted to Base64, and sent in the normal Strategy Lab start POST. Only after the API/configd launcher accepts that request is the payload decoded into the private job-local `udp-payload.bin` file.

Permissions remain a valid later-stage failure possibility and `_16` has explicit diagnostics for that boundary, but the controlled owner-live PASS did not expose such a failure.

## Supported request

Generic UDP is optional and accepted only in `extended` mode.

The request consists of exactly two values:

- UDP destination port: integer `1..65535`;
- one local browser-selected payload: decoded size **`1..4096 bytes`**.

Both values must be present together. Supplying only one is invalid. Standard mode must not carry Generic UDP input.

An exact 140-byte file is valid. A 140 KiB file is deliberately invalid.

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

The job-local preparation layer records a precise non-payload error code before returning failure. This distinguishes a later filesystem/backend failure from browser-side validation.

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

## Telegram Voice boundary

Generic UDP remains a raw exact-payload request/reply tool. It is not a Telegram call oracle:

- its IPFW rule is `from me`, while the selected official tgcalls emulator runs as a forwarded LAN companion;
- it treats any non-empty UDP reply as a candidate response and does not parse/correlate a STUN transaction;
- a TURN/STUN reply does not prove Telegram reflector readiness or bidirectional WebRTC media;
- a captured 40-byte Reflector Hello cannot be blindly replayed as a valid call because its tags and peer state are per run;
- the current UDP catalog stops after a synthetic success and has no `MEDIA_PASS` state.

The Telegram Voice design may reuse Generic UDP lifecycle, fixed-endpoint epochs, profile assembly, counters, restoration and result storage, but it requires a separate runner or explicit external-probe mode with a narrowly attributed forwarded-flow rule and protocol-aware oracles. Pre/post-NAT source visibility is an explicit implementation gate. The current contract is defined in [`TELEGRAM_VOICE_EMULATION_LAB.md`](../history/stages/telegram-voice-2026-10-20/TELEGRAM_VOICE_EMULATION_LAB.md).

## Candidate execution and Stage 80

Configured UDP candidates receive:

- `STRATEGY_LAB_UDP_PORT` = selected port;
- `STRATEGY_LAB_UDP_PAYLOAD_FILE` = private job-local payload.

Every executed candidate is appended to structured `tested`. Ordinary RU/EN Stage-80 presentation reports configured port/payload/endpoints, direct observation, actual candidate count/IDs and working/no-working result while raw machine enums remain in structured evidence.

## Cleanup

`udp-payload.bin` and `udp-port` are removed during normal restoration and error/cancel/stale-worker cleanup. Terminal evidence may retain metadata/control results but not payload bytes.

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_UDP_INPUT.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.

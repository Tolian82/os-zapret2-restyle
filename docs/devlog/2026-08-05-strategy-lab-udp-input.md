# 2026-08-05 — Strategy Lab generic UDP input

## Scope

Implement the remaining UDP-input half of hardening audit finding 14.

## Result

The extended Diagnostics workflow now accepts an optional UDP destination port and local
payload file. The browser transmits file content rather than a path. The API and launcher
validate the request independently, create private current-job files, and pass only those
fixed paths to the existing UDP runner.

The public job state contains only whether UDP input was configured, the selected port,
and decoded byte count. Payload bytes are removed during every terminal or stale-worker
cleanup path.

## Safety properties

- no arbitrary server-side path input;
- no generic UDP configuration in standard mode;
- port range `1..65535`;
- canonical Base64 only;
- decoded payload size `1..4096` bytes;
- job-local files mode `0600`;
- cleanup on all completion and failure paths.

## Verification

`test-strategy-lab-udp-input-contract.sh` covers the complete GUI/API/configd/launcher/
worker boundary and the dynamic file lifecycle. It is wired into the mandatory domain
Diagnostics test suite.

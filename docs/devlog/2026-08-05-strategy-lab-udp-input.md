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

PR #86 passed the exact `v0.3.2_36:` title and commit-subject gate, complete project
validation, the mandatory domain-diagnostics and end-to-end suites, repository governance
and hygiene checks, and the FreeBSD package build.

The PR was squash-merged into `main` as
`f7ddb1ed0ca4c1f39e7196e9a919946789e2589c`. Push CI run 273 then passed the post-merge
committed-diff, title-identity, and core-identity verification. The temporary task branch
was deleted automatically. No tag, GitHub Release, release asset, or pkg-repository
publication was created.

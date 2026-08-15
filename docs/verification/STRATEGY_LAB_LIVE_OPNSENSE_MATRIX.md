# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` EXPLICIT ENABLE-QUIC + GENERIC-UDP INPUT CORRECTION IS THE CURRENT SOURCE/LIVE BOUNDARY.**

Only FreeBSD 15 amd64 packages are valid. Source tests/CI do not replace selected owner-live evidence.

## Current package/source boundary

- latest owner-tested package: `os-zapret2-restyle-0.4.1_13.pkg`;
- current published testing tag: `v0.4.1_13`;
- `_13` tag target: `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`;
- `_13` package SHA-256: `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`;
- current source candidate: `v0.4.1_14`;
- `_14` is not called published until the source merge and persistent testing-publisher workflow complete.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback is disabled from `_13`.

## Accepted `_13` baseline

### Normal Model-C-only paths

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: `NO_CANDIDATE`, Stage 60 `16/16`, `graph_exhausted`, no automatic fallback, verified RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, no automatic fallback, verified RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: `SUCCESS`, early Stage-60 stop at `7/16` / `enough_candidates`, three stable shortlist entries, verified RUNNING restoration.

### Initial permanent service STOPPED

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`.

`rutracker.org` Standard `job.5b97u9` completed `SUCCESS` with three stable strategies and left the permanent Zapret2 service STOPPED; the immediate post-job normal `dvtws2|zapret.*supervisor` query was empty. The owner accepted this observable row as sufficient and declined redundant deeper replay.

### Extended TLS 1.2 / HTTP and historical QUIC behavior

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`.

`rutracker.org` Extended `job.TJlWoY`:

- terminal `SUCCESS`, Stage 80 PASS, Stage 90 PASS;
- TLS 1.2 executed `tls12-multisplit` and `tls12-fake`; both returned truthful negative endpoint results, `working=null`;
- HTTP executed `http-multisplit` and `http-multidisorder`; both returned truthful negative endpoint results, `working=null`;
- temporary runtimes were ready/stable and produced interception/endpoint evidence;
- `_13` Stage 30 classified QUIC/IPv4 closed and Stage 80 capability-skipped QUIC;
- UDP was skipped because no valid payload file was supplied.

The `_13` QUIC skip remains accurate historical evidence of `_13`. **It is not the current desired product behavior.** The owner superseded capability gating for `_14` because a blocked QUIC path is precisely where bypass candidates need to be tested.

## `_14` selected live acceptance

Canonical QUIC contract: `docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md`.
Canonical UDP input contract: `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`.

### A. Enable QUIC preference — pending owner on published `_14`

Required:

1. default is unchecked on the new setting when no prior explicit preference exists;
2. check it, reload Diagnostics, it remains checked;
3. uncheck it, reload Diagnostics, it remains unchecked;
4. saving the preference does not restart/apply the permanent Zapret2 service.

### B. Enable QUIC OFF — pending owner on published `_14`

Use Extended mode with Enable QUIC unchecked.

Required Stage-80 QUIC evidence:

- `enabled=false`;
- `status=skipped`;
- `reason=disabled`;
- no QUIC candidate is launched.

The Stage-30 control probe may independently say `quic_ipv4=closed` or `available`; it must not be the skip reason.

### C. Enable QUIC ON with ISP-blocked ordinary QUIC — pending owner on published `_14`

Use Extended mode with Enable QUIC checked on the owner’s path where the Stage-30 control probe is expected to remain closed.

Required:

- Stage 30 may truthfully report QUIC/IPv4 blocked by the control probe;
- Stage 80 must nevertheless execute QUIC candidates;
- persisted QUIC `tested` count must be greater than zero;
- terminal QUIC result may truthfully be `working` or `not_found`;
- it must **not** be skipped because the control probe is closed;
- normal lifecycle restoration remains successful.

### D. Oversized Generic UDP payload UX — pending owner on published `_14`

Select a previously problematic multi-megabyte file with a UDP port and press Run.

Required:

- visible error states payload must be `1–4096` bytes;
- no new Strategy Lab job begins;
- previous completed result is not cleared solely because invalid Run was pressed.

A multi-megabyte request remains invalid by product contract.

### E. Configured Generic UDP — pending owner on published `_14`

Use Extended mode with:

- valid port `1..65535`;
- payload file `1..4096` bytes.

Required:

- UDP request is classified configured;
- Stage 80 actually executes UDP candidates rather than returning unconfigured `skipped`;
- truthful UDP result may be `working` or `not_found`;
- temporary UDP payload is cleaned during terminal restoration;
- normal Zapret2 lifecycle state is restored.

One Extended job may cover C and E simultaneously when Enable QUIC is ON and Generic UDP is valid.

## Scenario matrix

| # | Scenario | Result |
|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 | **PASS ON `_13`** |
| 4 | Extended HTTP | **PASS ON `_13`** |
| 5 | Historical closed-QUIC capability skip | **OBSERVED/PASS FOR `_13`; SUPERSEDED AS PRODUCT RULE** |
| 6 | Enable QUIC persistence/default | **PENDING `_14` OWNER** |
| 7 | Enable QUIC OFF → explicit disabled skip | **PENDING `_14` OWNER** |
| 8 | Enable QUIC ON while control QUIC blocked → actual candidate search | **PENDING `_14` OWNER** |
| 9 | Oversized Generic UDP input → visible pre-start error | **PENDING `_14` OWNER** |
| 10 | Valid configured Generic UDP → actual candidate search | **PENDING `_14` OWNER** |
| 11 | Target already accessible | PENDING REGRESSION |
| 12 | User cancellation after service stop | PENDING REGRESSION |
| 13 | Controlled internal failure / timeout containment | PENDING REGRESSION |
| 14 | Circular start/stop/stale recovery | PENDING REGRESSION |
| 15 | Settings Apply guards during Strategy Lab/circular | PENDING REGRESSION |
| 16 | Diagnostics persistence/reload | PENDING REGRESSION |
| 17 | RU/EN presentation | PENDING REGRESSION |
| 18 | Retention/reboot residue | PENDING REGRESSION |

## Failure policy for `_14` selected rows

The current patch fails live acceptance if any of the following occur:

- checkbox state does not persist or default OFF;
- an enabled QUIC run is suppressed because Stage 30 says QUIC closed;
- a disabled QUIC run launches candidates;
- oversized UDP input again appears to do nothing instead of showing a visible error;
- a valid configured UDP request is silently skipped as unconfigured;
- lifecycle restoration fails or temporary runtime/payload ownership is violated.

A QUIC or UDP search returning `not_found` is **not** itself a failure: the requirement is truthful execution/result semantics, not manufacturing a bypass that does not work on the measured target/path.

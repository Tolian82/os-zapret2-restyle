# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; PUBLISHED `v0.4.1_14` EXPLICIT ENABLE-QUIC + GENERIC-UDP CORRECTION IS THE CURRENT OWNER-LIVE BOUNDARY.**

Only FreeBSD 15 amd64 packages are valid. Source tests/CI do not replace selected owner-live evidence.

## Current package/source boundary

- latest owner-tested package: `os-zapret2-restyle-0.4.1_13.pkg`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_14.pkg` / `v0.4.1_14`;
- `_14` source/tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- `_14` package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- publication workflow: `31875178597`;
- stable Pages/pkg repository promoted: no;
- current source identity: `v0.4.1_14`.

Machine publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_14.md`.

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
- TLS 1.2 executed two candidates and truthfully ended `working=null`;
- HTTP executed two candidates and truthfully ended `working=null`;
- temporary runtimes were ready/stable and produced interception/endpoint evidence;
- `_13` Stage 30 classified QUIC/IPv4 closed and Stage 80 capability-skipped QUIC;
- UDP was skipped because no valid payload file was supplied.

The `_13` QUIC skip remains accurate historical evidence of `_13`. **It is superseded as current product behavior.** `_14` uses explicit Enable QUIC instead.

## `_14` automated/publication acceptance — PASS

- source PR `#237` latest verified head `b476131bdd68c51288a0f89478fddd0382c0b5c9`;
- complete Strategy Lab corrective matrix: PASS;
- FreeBSD 15 package qualification: PASS;
- candidate-defining source merge: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- testing prerelease/tag/asset: published and verified;
- package digest: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`.

## `_14` selected live acceptance

Canonical QUIC contract: `docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md`.
Canonical UDP input contract: `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`.

### A. Enable QUIC preference — pending owner

Required:

1. default is unchecked when no prior explicit preference exists;
2. check it, reload Diagnostics, it remains checked;
3. uncheck it, reload Diagnostics, it remains unchecked;
4. saving the preference does not restart/apply the permanent Zapret2 service.

### B. Enable QUIC OFF — pending owner

Use Extended mode with Enable QUIC unchecked.

Required Stage-80 QUIC evidence:

- `enabled=false`;
- `status=skipped`;
- `reason=disabled`;
- no QUIC candidate is launched.

The Stage-30 control probe may independently report `quic_ipv4=closed` or `available`; it must not be the skip reason.

### C. Enable QUIC ON with ISP-blocked ordinary QUIC — pending owner

Use Extended mode with Enable QUIC checked on the owner’s path where the Stage-30 control probe is expected to remain closed.

Required:

- Stage 30 may truthfully report QUIC/IPv4 blocked by the control probe;
- Stage 80 nevertheless executes QUIC candidates;
- persisted QUIC `tested` count is greater than zero;
- terminal QUIC result may truthfully be `working` or `not_found`;
- it is not skipped because the control probe is closed;
- normal lifecycle restoration succeeds.

### D. Oversized Generic UDP payload UX — pending owner

Select a previously problematic multi-megabyte file with a UDP port and press Run.

Required:

- visible error states payload must be `1–4096` bytes;
- no new Strategy Lab job begins;
- previous completed result is not cleared solely because invalid Run was pressed.

A multi-megabyte request remains invalid by product contract.

### E. Configured Generic UDP — pending owner

Use Extended mode with valid port `1..65535` and payload file `1..4096` bytes.

Required:

- UDP request is configured;
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
| 5 | Historical closed-QUIC capability skip | **OBSERVED ON `_13`; SUPERSEDED AS PRODUCT RULE** |
| 6 | Enable QUIC persistence/default | **PENDING OWNER ON PUBLISHED `_14`** |
| 7 | Enable QUIC OFF → explicit disabled skip | **PENDING OWNER ON PUBLISHED `_14`** |
| 8 | Enable QUIC ON while control QUIC blocked → actual candidate search | **PENDING OWNER ON PUBLISHED `_14`** |
| 9 | Oversized Generic UDP input → visible pre-start error | **PENDING OWNER ON PUBLISHED `_14`** |
| 10 | Valid configured Generic UDP → actual candidate search | **PENDING OWNER ON PUBLISHED `_14`** |
| 11 | Target already accessible | PENDING REGRESSION |
| 12 | User cancellation after service stop | PENDING REGRESSION |
| 13 | Controlled internal failure / timeout containment | PENDING REGRESSION |
| 14 | Circular start/stop/stale recovery | PENDING REGRESSION |
| 15 | Settings Apply guards during Strategy Lab/circular | PENDING REGRESSION |
| 16 | Diagnostics persistence/reload | PENDING REGRESSION |
| 17 | RU/EN presentation | PENDING REGRESSION |
| 18 | Retention/reboot residue | PENDING REGRESSION |

## Failure policy for `_14` selected rows

The current patch fails live acceptance if checkbox state does not persist/default OFF, enabled QUIC is suppressed by Stage 30, disabled QUIC launches candidates, oversized UDP input appears to do nothing, valid configured UDP is silently skipped, or lifecycle restoration/temporary payload ownership fails.

A QUIC or UDP search returning `not_found` is **not** itself a failure: the requirement is truthful execution/result semantics, not manufacturing a bypass that does not work on the measured target/path.

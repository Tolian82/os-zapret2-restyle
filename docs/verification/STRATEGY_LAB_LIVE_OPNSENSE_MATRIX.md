# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED; EXPLICIT QUIC + GENERIC UDP OWNER-LIVE FOLLOW-UP IS OPEN.**

Only FreeBSD 15 amd64 packages are valid. Source tests/CI do not replace selected owner-live evidence.

## Current package/source boundary

- latest owner-installed testing package: `os-zapret2-restyle-0.4.1_14.pkg`;
- current published testing tag: `v0.4.1_14`;
- `_14` tag target: `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`;
- `_14` package SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- `_14` source acceptance/publication record is complete.

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

The `_13` QUIC skip remains accurate historical evidence of `_13`. **It is not the current desired product behavior.**

## `_14` owner-live observations — 2026-08-15 preliminary evidence

The owner installed `_14` and supplied GUI screenshots for two Extended runs with **Enable QUIC checked**.

### `telegram.org`

Observed GUI facts:

- Enable QUIC: checked;
- Stage 30: IPv4 available, IPv6 unavailable, QUIC/IPv4 reported closed by the control probe;
- Stage 80: PASS with `QUIC=not_found, UDP=skipped`;
- Stage 90: PASS/restored;
- terminal result: `NO_CANDIDATE`.

### `rutracker.org`

Observed GUI facts:

- Enable QUIC: checked;
- Stage 30: IPv4 available, IPv6 unavailable, QUIC/IPv4 reported closed by the control probe;
- Stage 80: PASS with `QUIC=not_found, UDP=skipped`;
- Stage 90: PASS/restored;
- terminal result: `SUCCESS` with one stable TLS 1.3 `seqovl` candidate shown in the result table.

### What these two runs prove — and do not prove

They prove an important `_14` semantic change at the normal GUI boundary: **an enabled QUIC run is no longer presented as capability-skipped when the control probe is closed.**

They do **not** yet prove that real QUIC strategies were attempted. `not_found` is consistent with the intended code path, but the screenshots do not expose `tested > 0` or candidate names.

Current source inspection shows that the production QUIC catalog contains four candidates:

- `quic-fake-1`;
- `quic-fake-2`;
- `quic-ipfrag-8`;
- `quic-ipfrag-16`.

The Python QUIC runner records each executed candidate under `tested`. Therefore row C below stays open until job evidence or improved GUI output proves a non-zero tested count.

### New presentation findings

The same screenshots establish a presentation/localization follow-up:

- Russian Stage 30 currently says `QUIC/IPv4 закрыт по контрольной проверке`; desired user-facing semantics are a simple measured QUIC state (`QUIC открыт` / `QUIC закрыт`) plus a separate indication of whether QUIC strategy testing is enabled;
- Stage 80 leaks raw machine enums: `QUIC=not_found, UDP=skipped`;
- the Enable QUIC explanatory text remains English in the Russian UI: `When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.`

All three require RU/EN human-readable presentation while preserving stable raw enums in structured evidence.

### New Generic UDP defect

The owner reports selecting a payload of nominal size **140 bytes**, which should be valid under the `1..4096` contract, but the GUI rejects it with the visible size-range error.

Status: **LIVE DEFECT / NOT ACCEPTED.**

The next implementation must reproduce the exact browser/API/backend path and add a valid 140-byte regression test. The selected UDP destination port must also gain truthful direct/control-exchange evidence; lack of a UDP response cannot by itself be called definitive proof that a port is closed and must not suppress bypass candidate testing.

## `_14` selected live acceptance

Canonical QUIC contract: `docs/architecture/STRATEGY_LAB_QUIC_CONTROL.md`.
Canonical UDP input contract: `docs/architecture/STRATEGY_LAB_UDP_INPUT.md`.

### A. Enable QUIC preference — pending owner completion

Required:

1. default is unchecked on a new setting when no prior explicit preference exists;
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

The Stage-30 control probe may independently say QUIC closed or available; it must not be the skip reason.

### C. Enable QUIC ON with ISP-blocked ordinary QUIC — PARTIAL, execution proof still required

The two current owner runs satisfy the presentation-level condition that closed control QUIC does not cause a capability skip.

Still required:

- Stage 80 must expose or telemetry must prove QUIC `tested > 0`;
- attempted candidate identities/count must be attributable to the job;
- terminal QUIC result may truthfully be `working` or `not_found`;
- normal lifecycle restoration remains successful.

`QUIC=not_found` alone does not close this row.

### D. Oversized Generic UDP payload UX — pending owner completion

Select a multi-megabyte file with a UDP port and press Run.

Required:

- visible error states payload must be `1–4096` bytes;
- no new Strategy Lab job begins;
- previous completed result is not cleared solely because invalid Run was pressed.

### E. Valid configured Generic UDP — LIVE DEFECT, blocked on valid-small-file rejection

Use Extended mode with:

- valid port `1..65535`;
- payload file `1..4096` bytes.

Required after correction:

- an exact 140-byte payload is accepted by browser/API/backend size handling;
- direct/control exchange uses the selected destination port and exact payload and reports truthful observed response state;
- UDP request is classified configured;
- Stage 80 actually executes UDP candidates rather than returning unconfigured `skipped`;
- truthful UDP result may be `working` or `not_found`;
- temporary UDP payload is cleaned during terminal restoration;
- normal Zapret2 lifecycle state is restored.

One Extended job may cover C and E simultaneously when Enable QUIC is ON and Generic UDP is valid.

### F. RU/EN Extended QUIC/UDP presentation — pending corrective implementation

Required:

- measured QUIC condition is localized and unambiguous in RU and EN;
- Enable QUIC explanatory text is localized in RU and EN;
- Stage-80 QUIC/UDP statuses render human-readable localized meanings rather than raw enums;
- raw machine enums remain available in structured/advanced output for diagnostics.

## Scenario matrix

| # | Scenario | Result |
|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 | **PASS ON `_13`** |
| 4 | Extended HTTP | **PASS ON `_13`** |
| 5 | Historical closed-QUIC capability skip | **OBSERVED/PASS FOR `_13`; SUPERSEDED AS PRODUCT RULE** |
| 6 | Enable QUIC persistence/default | **PENDING `_14` OWNER COMPLETION** |
| 7 | Enable QUIC OFF → explicit disabled skip | **PENDING `_14` OWNER** |
| 8 | Enable QUIC ON while control QUIC blocked → actual candidate search | **PARTIAL `_14`: no capability skip observed; `tested > 0` NOT YET PROVEN** |
| 9 | Oversized Generic UDP input → visible pre-start error | **PENDING `_14` OWNER COMPLETION** |
| 10 | Valid small Generic UDP input / 140-byte payload | **FAIL `_14` OWNER — FALSE SIZE REJECTION REPORTED** |
| 11 | Configured Generic UDP selected-port/control exchange | **PENDING CORRECTIVE IMPLEMENTATION** |
| 12 | RU/EN QUIC state/help and Stage-80 QUIC/UDP presentation | **PENDING CORRECTIVE IMPLEMENTATION** |
| 13 | Target already accessible | PENDING REGRESSION |
| 14 | User cancellation after service stop | PENDING REGRESSION |
| 15 | Controlled internal failure / timeout containment | PENDING REGRESSION |
| 16 | Circular start/stop/stale recovery | PENDING REGRESSION |
| 17 | Settings Apply guards during Strategy Lab/circular | PENDING REGRESSION |
| 18 | Diagnostics persistence/reload | PENDING REGRESSION |
| 19 | RU/EN presentation review | PENDING REGRESSION |
| 20 | Retention/reboot residue | PENDING REGRESSION |

## Failure policy for current follow-up

The current line fails acceptance if any of the following occur:

- checkbox state does not persist or default OFF;
- an enabled QUIC run is suppressed because Stage 30 says QUIC closed;
- a disabled QUIC run launches candidates;
- enabled QUIC returns a user-facing result without any durable way to prove whether candidates were actually attempted;
- normal RU/EN UI leaks selected raw QUIC/UDP status enums or English-only new help text;
- a valid 1..4096-byte UDP payload, including the 140-byte regression case, is rejected by size handling;
- a valid configured UDP request is silently skipped as unconfigured;
- UDP silence is incorrectly asserted to mean a definitely closed port or is used to suppress bypass testing;
- lifecycle restoration fails or temporary runtime/payload ownership is violated.

A QUIC or UDP search returning no working strategy is **not** itself a failure: the requirement is truthful execution/result semantics, not manufacturing a bypass that does not work on the measured target/path.

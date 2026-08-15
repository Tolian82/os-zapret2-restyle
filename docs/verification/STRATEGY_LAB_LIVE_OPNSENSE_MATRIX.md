# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` PUBLISHED/OWNER-TESTED; QUIC OBSERVABILITY LIVE PASS, GENERIC UDP LIVE FAIL; `v0.4.1_16` PUBLISHED, OWNER-LIVE GENERIC UDP CORRECTION PENDING.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- `_16` source/tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- `_16` package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- publication workflow run: `31882091770`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: pending.

Machine publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_16.md`.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback remains disabled from `_13`.

## Accepted `_13` baseline

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: exhaustive `NO_CANDIDATE`, Stage 60 `16/16`, no fallback, clean RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, clean RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: early `SUCCESS`, `7/16`, `enough_candidates`, three stable shortlist entries.
- initial permanent service STOPPED: `rutracker.org` `job.5b97u9` `SUCCESS`, service remained STOPPED; owner accepted the observable row.
- Extended TLS 1.2/HTTP: `rutracker.org` `job.TJlWoY`, truthful executed negative protocol evidence, Stage 80/90 PASS.

## `_14` owner-live observations that selected `_15`

The owner tested Extended `telegram.org` and `rutracker.org` with Enable QUIC ON. The old capability skip disappeared but ordinary output only showed `QUIC=not_found`, which did not prove how many candidates actually ran. The same cycle exposed localization gaps and Generic UDP input problems.

## `_15` accepted source and live behavior

### QUIC tested count/IDs ordinary output

`_15` Stage 80 presents the real structured `tested` set. Current catalog:

- `quic-fake-1`;
- `quic-fake-2`;
- `quic-ipfrag-8`;
- `quic-ipfrag-16`.

Owner-live `_15` evidence is positive: the `rutracker.org` Extended screenshot with blocked ordinary QUIC shows all four attempted IDs and no working QUIC candidate. Thus QUIC tested count/IDs ordinary output is **OWNER-LIVE PASS**.

### Exact 140-byte binary input

Automated `_15` coverage proved exact 140-byte Base64 decode/job-local metadata, but owner-live file selection still failed before configured UDP. Therefore the `_15` live path is **FAIL/SUPERSEDED BY `_16` CORRECTION**.

### Selected-port/payload direct UDP observation

The implemented configured-UDP path uses the exact selected search-epoch IP, destination port and job-local payload, recording reply/no-reply and timing. Its owner-live row remains pending until `_16` proves browser payload handoff.

### No-reply does not mean closed / does not gate candidates

Automated behavior remains accepted: UDP silence is not classified as `port closed` and does not suppress the bypass candidate catalog.

## `_15` Generic UDP owner-live failure

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`.

Observed:

- Extended mode;
- destination port `53` entered;
- valid small file selection did not produce a usable configured payload;
- native UI appeared as `Не выбран ни один файл` / port+file validation;
- Stage 80 reported UDP not configured;
- QUIC path in the same page/job family remained functional.

## `_16` trace result and correction

Source tracing establishes that Generic UDP does **not** use a multipart server upload directory. The path is:

`browser File -> ArrayBuffer -> Base64 start POST -> API -> configd -> launcher -> job-local udp-payload.bin/udp-port -> Python`.

In `_15`, the application did not retain a prepared browser payload. The Run handler sampled native `input.files[0]` at click time and only then read it. Loss/reset of native selection therefore returned before API/configd/job-local storage.

`_16` changes this boundary:

- file-input `change` captures and immediately reads the `File`;
- exact `1..4096` decoded bytes are validated and Base64-encoded immediately;
- filename, decoded byte count and Base64 are retained in application-owned staged state;
- RU/EN normal UI displays ready-to-send filename/byte evidence;
- Run consumes staged Base64 even if native selection is later lost;
- Run-time fallback stages a still-present native file when needed;
- browser buffer validation no longer depends on realm-specific `instanceof ArrayBuffer`;
- later job-local failures expose explicit classes, including `job_directory_not_writable`, `payload_temp_create_failed`, decode/write/chmod/move and state-record failures.

## `_16` source/publication acceptance — PASS

1. staged browser file-selection contract PASS;
2. exact 140-byte backend/job-local regression PASS;
3. job-directory unavailable/not-writable and other preparation attribution PASS;
4. selected-port/payload direct observation regression PASS;
5. no-reply does not mean closed / does not gate candidates PASS;
6. complete Strategy Lab corrective matrix PASS;
7. FreeBSD-15 package build/inspection qualification PASS;
8. exact verified source head `f7974f21dc7340b1e1416c24f9e7dade0322f0f3` squash-merged as `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
9. persistent `v0.4.1_16` testing publication PASS;
10. package SHA-256 `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`.

Publication-record documentation tail is PR `#246`.

## Owner-live `_16` acceptance

Required after installing the published package:

- selecting a valid file immediately shows localized ready-to-send filename and exact decoded bytes;
- exact 140-byte payload starts a new configured-UDP job;
- Stage 80 shows selected port/payload/endpoints, direct observation and actual UDP candidate IDs;
- any later filesystem preparation failure identifies its failure class;
- no-reply wording never claims the port is closed;
- terminal payload cleanup and Zapret2 restoration PASS.

Remaining independent `_15/_16` rows: Enable QUIC OFF/default persistence and final RU/EN presentation review.

## Scenario matrix

| # | Scenario | Result |
|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 | **PASS ON `_13`** |
| 4 | Extended HTTP | **PASS ON `_13`** |
| 5 | Historical closed-QUIC capability skip | **OBSERVED ON `_13`; SUPERSEDED** |
| 6 | `_14` Enable QUIC ON / blocked control / no capability skip | **PASS, selected `_15` observability** |
| 7 | `_15` QUIC tested count/IDs ordinary output | **OWNER-LIVE PASS — 4 IDs** |
| 8 | `_15` exact/small Generic UDP file input | **OWNER-LIVE FAIL; SUPERSEDED** |
| 9 | `_16` application-owned staged file input | **AUTOMATED/PACKAGE PASS; OWNER-LIVE PENDING** |
| 10 | `_16` exact 140-byte configured UDP | **AUTOMATED BACKEND PASS; OWNER-LIVE PENDING** |
| 11 | selected-port/payload direct UDP observation | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 12 | no-reply does not mean closed / does not gate candidates | **AUTOMATED PASS; OWNER-LIVE PENDING** |
| 13 | terminal payload cleanup and Zapret2 restoration PASS. | **OWNER-LIVE PENDING FOR `_16` UDP PATH** |
| 14 | Enable QUIC OFF/default/persistence | PENDING |
| 15 | RU/EN presentation review | PENDING |
| 16 | Target already accessible | PENDING REGRESSION |
| 17 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 18 | Circular lifecycle | PENDING REGRESSION |
| 19 | Settings Apply guards | PENDING REGRESSION |
| 20 | Retention/reboot residue | PENDING REGRESSION |

## Failure policy for `_16`

`_16` fails owner-live acceptance if a valid selected file cannot become application-owned ready state, a 140-byte payload cannot reach configured UDP, Run again depends exclusively on native file-control retention, job-local permission/storage failure is collapsed into an unexplained unconfigured request, direct observation uses the wrong port/payload/binding, UDP silence is called a closed port, or lifecycle/payload cleanup fails.
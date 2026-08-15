# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` QUIC OBSERVABILITY OWNER-LIVE PASS; `v0.4.1_16` GENERIC UDP OWNER-LIVE PASS.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current source candidate: `v0.4.1_16`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_16.pkg` / `v0.4.1_16`;
- `_16` source/tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- `_16` package SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- publication workflow run: `31882091770`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: **PASS**.

Machine publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_16.md`.
Owner-live Generic UDP evidence: `docs/verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback remains disabled from `_13`.

## Accepted `_13` baseline

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: exhaustive `NO_CANDIDATE`, Stage 60 `16/16`, no fallback, clean RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, clean RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: early `SUCCESS`, `7/16`, `enough_candidates`, three stable shortlist entries.
- initial permanent service STOPPED: `rutracker.org` `job.5b97u9` `SUCCESS`, service remained STOPPED; owner accepted the observable row.
- Extended TLS 1.2/HTTP: `rutracker.org` `job.TJlWoY`, truthful executed negative protocol evidence, Stage 80/90 PASS.

## `_14` owner-live observations that selected `_15`

The owner tested Extended `telegram.org` and `rutracker.org` with Enable QUIC ON. The old capability skip disappeared but ordinary output only showed `QUIC=not_found`, which did not prove how many candidates actually ran. The same cycle exposed localization gaps and Generic UDP input ambiguity.

## `_15` accepted source and live behavior

### QUIC tested count/IDs ordinary output

`_15` Stage 80 presents the real structured `tested` set. Current catalog:

- `quic-fake-1`;
- `quic-fake-2`;
- `quic-ipfrag-8`;
- `quic-ipfrag-16`.

Owner-live `_15` evidence is positive: the `rutracker.org` Extended screenshot with blocked ordinary QUIC shows all four attempted IDs and no working QUIC candidate. Thus QUIC tested count/IDs ordinary output is **OWNER-LIVE PASS**.

### Exact 140-byte binary input

Automated `_15` coverage proved exact 140-byte Base64 decode/job-local metadata. The earlier owner-live file-selection report was later clarified: the files being tried were approximately 140 KiB rather than 140 bytes. The product limit is `1..4096 bytes`.

### Selected-port/payload direct UDP observation

The configured-UDP path uses the exact selected search-epoch IP, destination port and job-local payload, recording reply/no-reply and timing. `_16` owner-live evidence now proves this path in the real GUI.

### No-reply does not mean closed / does not gate candidates

Owner-live `_16` confirms the intended behavior: UDP silence is not classified as `port closed` and does not suppress the bypass candidate catalog.

## Historical `_15` Generic UDP report — superseded diagnosis

Durable chronology: `docs/verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`.

At the time, the owner reported that Generic UDP file selection did not become configured. That record is retained as historical observation, but its working assumption of a valid small payload/browser or filesystem failure is superseded by the controlled `_16` exact-byte test. The owner identified that earlier files were around 140 KiB and therefore outside the documented 4096-byte limit.

## `_16` trace result and correction

Source tracing established that Generic UDP does **not** use a multipart server upload directory. The path is:

`browser File -> ArrayBuffer -> Base64 start POST -> API -> configd -> launcher -> job-local udp-payload.bin/udp-port -> Python`.

`_16` makes the boundary explicit and observable:

- file-input `change` captures and immediately reads the `File`;
- exact `1..4096` decoded bytes are validated and Base64-encoded immediately;
- filename, decoded byte count and Base64 are retained in application-owned staged state;
- RU/EN normal UI displays ready-to-send filename/byte evidence;
- Run consumes staged Base64 even if native selection is later lost;
- Run-time fallback stages a still-present native file when needed;
- browser buffer validation does not depend on realm-specific `instanceof ArrayBuffer`;
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

## Owner-live `_16` Generic UDP acceptance — PASS

Controlled fixture and run:

- Windows fixture `udp-140.bin` verified by filesystem as exactly `140` bytes;
- target `rutracker.org`;
- Extended mode;
- Generic UDP port `53`;
- Enable QUIC OFF;
- job `job.j09XUc`;
- GUI showed `Файл подготовлен к отправке: udp-140.bin, 140 байт.` before Run;
- Stage 80 reported payload `140` bytes and endpoint `172.67.182.196`;
- direct control reply was not observed and the UI explicitly stated that this does not mean the port is closed;
- actual UDP tested set contained all three IDs: `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`;
- no working UDP strategy was found, which is a valid negative result;
- QUIC OFF presentation stated that QUIC strategy search was disabled;
- Stage 90 reported temporary processes/rules removed and original Zapret2 restored/running;
- final job outcome: `SUCCESS`.

This closes the application-owned staged file input, exact 140-byte configured UDP, selected-port/payload direct UDP observation, and no-reply candidate-execution rows for the tested `_16` scenario.

The earlier browser/upload/filesystem defect hypothesis is not confirmed. Previous repeated size errors are explained by the owner selecting approximately 140 KiB files, outside the `1..4096 bytes` contract.

Remaining independent rows: Enable QUIC OFF/default persistence across reload/revisit and final RU/EN presentation review.

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
| 8 | `_15` earlier Generic UDP owner report | **HISTORICAL; DIAGNOSIS SUPERSEDED BY EXACT-BYTE `_16` PASS** |
| 9 | `_16` application-owned staged file input | **OWNER-LIVE PASS** |
| 10 | `_16` exact 140-byte configured UDP | **OWNER-LIVE PASS — `job.j09XUc`** |
| 11 | Selected-port/payload direct UDP observation | **OWNER-LIVE PASS** |
| 12 | No-reply does not mean closed / does not gate candidates | **OWNER-LIVE PASS** |
| 13 | terminal payload cleanup and Zapret2 restoration PASS. | **STAGE-90 RESTORATION/TEMP PROCESS+RULE CLEANUP OWNER-LIVE PASS; deeper residue remains under global cleanup backlog** |
| 14 | Enable QUIC OFF/default/persistence | **OFF PRESENTATION PASS; persistence PENDING** |
| 15 | RU/EN presentation review | PENDING |
| 16 | Target already accessible | PENDING REGRESSION |
| 17 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 18 | Circular lifecycle | PENDING REGRESSION |
| 19 | Settings Apply guards | PENDING REGRESSION |
| 20 | Retention/reboot residue | PENDING REGRESSION |

## Current failure policy

Generic UDP should only be reopened if fresh evidence contradicts the accepted exact-byte path: a valid `1..4096`-byte file cannot become ready/configured, the selected port/payload/binding is wrong, candidate enumeration is suppressed incorrectly, UDP silence is called a closed port, or lifecycle restoration fails.

# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` QUIC OBSERVABILITY OWNER-LIVE PASS; `v0.4.1_16` GENERIC UDP + QUIC OFF EXECUTION OWNER-LIVE PASS; `v0.4.1_17` RU PRESENTATION OWNER-LIVE PARTIAL; `v0.4.1_18` RU LABEL/LAYOUT CORRECTIVE PUBLISHED — LIVE ACCEPTANCE PENDING.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current packaged source revision: `v0.4.1_18` / `PLUGIN_REVISION=18`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- source/tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- publication workflow run: `31889449879`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: **PASS**;
- owner-live `_16` QUIC OFF execution semantics: **PASS**;
- `_17` owner-live Russian presentation: **PARTIAL — MOST LABELS/CIRCULAR IDLE PASS; TWO ENGLISH LABELS + LAYOUT DEFECT SELECTED `_18`**;
- Enable QUIC OFF/default persistence across reload/revisit: **PENDING LIVE PROOF**;
- `_18` title/UDP-label/aligned-input corrective: **SOURCE/AUTOMATED/FREEBSD-15/PUBLICATION PASS; OWNER-LIVE RU/EN ACCEPTANCE PENDING**.

Machine `_18` publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_18.md`.
Owner-live Generic UDP evidence: `docs/verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`.
Owner-live QUIC OFF/UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`.
Owner-live `_17` RU follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`.
`_18` patch record: `docs/patches/v0.4.1_18.md`.

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

Owner-live evidence is positive: Extended runs with ordinary QUIC blocked show all four attempted IDs and no working QUIC candidate. Thus QUIC tested count/IDs ordinary output is **OWNER-LIVE PASS**.

### Exact 140-byte binary input

Automated `_15` coverage proved exact 140-byte Base64 decode/job-local metadata. The earlier owner-live file-selection report was later clarified: the files being tried were approximately 140 KiB rather than 140 bytes. The product limit is `1..4096 bytes`.

### Selected-port/payload direct UDP observation

The configured-UDP path uses the exact selected search-epoch IP, destination port and job-local payload, recording reply/no-reply and timing. `_16` owner-live evidence proves this path in the real GUI.

### No-reply does not mean closed / does not gate candidates

Owner-live `_16` confirms the intended behavior: UDP silence is not classified as `port closed` and does not suppress the bypass candidate catalog.

## `_16` Generic UDP owner-live acceptance — PASS

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

## `_16` explicit QUIC OFF execution — PASS; persistence pending

The owner supplied a later pair of Extended `www.youtube.com` screenshots using Generic UDP port `53` and `udp-140.bin`.

Observed behavior:

- with **Enable QUIC ON**, Stage 80 executes all four current QUIC candidates and the independent Generic UDP catalog;
- with **Enable QUIC OFF**, Stage 80 explicitly reports `QUIC: подбор стратегий отключён` and executes no QUIC candidate catalog;
- the same OFF run still executes all three UDP IDs: `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`;
- the OFF run completes `SUCCESS`, produces stable TLS/HTTP results, and Stage 90 reports successful Zapret2 restoration.

This is **OWNER-LIVE PASS** for the runtime OFF gate itself. It does not prove persistence because the evidence does not show the OFF value surviving a page reload/revisit. Keep persistence as a separate row.

## `_17` RU presentation owner-live follow-up — partial

The owner installed published `_17` and supplied Russian-mode Diagnostics screenshots.

Visible PASS:

- translated domain-connectivity title/help/action;
- `Заблокированный домен / IP`, `Запуск`, `Включить QUIC`;
- translated result/stage labels including `Полный профиль Стратегий Трафика`;
- ordinary circular idle output is localized text and no raw JSON braces are shown.

Visible defects that selected `_18`:

- `Strategy Lab` remained English;
- `Generic UDP (optional)` remained English;
- `Заблокированный домен / IP` wrapped to two lines;
- owner required the domain input to move slightly left and the Generic UDP value control plus Enable QUIC control to align at the same new left position.

This is not a runtime/search failure. It is a narrow presentation/layout follow-up.

## `_18` automated/publication acceptance — PASS

Published `_18` contains:

- `Strategy Lab` / RU `Лаборатория стратегий`;
- `Generic UDP (optional)` / RU `UDP порт (опционально)`;
- explicit English counterparts retained;
- one shared left-side label/value-column layout for domain / Generic UDP / Enable QUIC;
- a small value-control left shift relative to `_17`;
- one-line RU `Заблокированный домен / IP` via bounded label width/font/padding;
- focused regression coverage for these strings/layout plus preservation of the prior circular-idle and Enable QUIC persistence source contracts.

Automated/package evidence:

- source PR `#252` exact verified head `1f9d5bb8b9f9d4204777f513bedf5e2d1e479396`;
- complete project/Strategy Lab corrective matrix: PASS;
- focused diagnostics RU/EN/layout/persistence test: PASS;
- FreeBSD-15 package qualification: PASS;
- exact candidate-defining source merge/tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- published testing asset: `os-zapret2-restyle-0.4.1_18.pkg`;
- SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`.

Owner-live acceptance must now verify the Russian title/UDP label/one-line domain label/alignment and then English/no-leakage mode. Enable QUIC reload/revisit persistence remains separately pending.

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
| 14 | Enable QUIC OFF execution semantics | **OWNER-LIVE PASS** |
| 15 | Enable QUIC OFF/default persistence across reload/revisit | **SOURCE CONTRACT GUARDED; OWNER-LIVE RELOAD PROOF PENDING** |
| 16 | Circular idle ordinary presentation | **OWNER-LIVE RU PASS ON `_17`; EN LIVE CHECK PENDING** |
| 17 | `_17` RU/EN presentation review | **RU PARTIAL: MOST LABELS PASS; TWO ENGLISH LABELS/LAYOUT SELECTED `_18`** |
| 18 | `_18` Strategy Lab title / Generic UDP label / aligned controls | **PUBLISHED; OWNER-LIVE RU/EN ACCEPTANCE PENDING** |
| 19 | Target already accessible | PENDING REGRESSION |
| 20 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 21 | Circular lifecycle | PENDING REGRESSION |
| 22 | Settings Apply guards | PENDING REGRESSION |
| 23 | Retention/reboot residue | PENDING REGRESSION |

## Current failure policy

Generic UDP should only be reopened if fresh evidence contradicts the accepted exact-byte path: a valid `1..4096`-byte file cannot become ready/configured, the selected port/payload/binding is wrong, candidate enumeration is suppressed incorrectly, UDP silence is called a closed port, or lifecycle restoration fails.

QUIC OFF execution should only be reopened if fresh evidence shows that OFF still runs QUIC candidates. Persistence remains separately pending until an actual reload/revisit proves the stored setting.

The `_18` presentation row should only be reopened after acceptance if the requested Russian labels/layout regress or English mode leaks Russian text.

# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` QUIC OBSERVABILITY OWNER-LIVE PASS; `v0.4.1_16` GENERIC UDP + QUIC OFF EXECUTION OWNER-LIVE PASS; `v0.4.1_17` RU PRESENTATION OWNER-LIVE PARTIAL; `v0.4.1_18` LABEL/ONE-LINE OWNER-LIVE PARTIAL; `v0.4.1_19` TEXT/MODE/STATUS PUBLISHED + OWNER-LIVE PARTIAL; `v0.4.1_20` NATIVE LABORATORY LAYOUT SOURCE CANDIDATE.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current source candidate: `v0.4.1_20` / `PLUGIN_REVISION=20`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_19.pkg` / `v0.4.1_19`;
- `_19` source/tag target: `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`;
- `_19` package SHA-256: `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`;
- `_19` publication workflow run: `31892344832`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: **PASS**;
- owner-live `_16` QUIC OFF execution semantics: **PASS**;
- already-accessible target: **COMPLETE BY OWNER CONFIRMATION**;
- Enable QUIC OFF/default persistence across reload/revisit: **PENDING LIVE PROOF**;
- `_19` live UI: **PARTIAL — RU MODE/IDLE VISIBLE; PERIMETER/VALUE GRID/MODE FONT REJECTED; `_20` SELECTED**;
- `_20` native Laboratory layout corrective: **SOURCE IMPLEMENTED; AUTOMATED/PUBLICATION/LIVE ACCEPTANCE PENDING**.

Machine `_19` publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_19.md`.
Owner-live Generic UDP evidence: `docs/verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`.
Owner-live QUIC OFF/UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`.
Owner-live `_17` RU follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`.
Owner-live `_18` Laboratory UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`.
Owner-live `_19` layout follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md`.
`_20` patch record: `docs/patches/v0.4.1_20.md`.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback remains disabled from `_13`.

## Accepted `_13` baseline

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: exhaustive `NO_CANDIDATE`, Stage 60 `16/16`, no fallback, clean RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, clean RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: early `SUCCESS`, `7/16`, `enough_candidates`, three stable shortlist entries.
- initial permanent service STOPPED: `rutracker.org` `job.5b97u9` `SUCCESS`, service remained STOPPED; owner accepted the observable row.
- Extended TLS 1.2/HTTP: `rutracker.org` `job.TJlWoY`, truthful executed negative protocol evidence, Stage 80/90 PASS.

## `_14` owner-live observations that selected `_15`

This historical section is retained as an accepted contract anchor, not as current product direction.

### QUIC tested count/IDs ordinary output

`_15` made the real attempted QUIC set visible in ordinary Stage 80 output. Owner-live runs showed all four current IDs.

### Exact 140-byte binary input

The accepted Generic UDP input contract is `1..4096 bytes`; the later `_16` owner-live run used an exact 140-byte fixture.

### Selected-port/payload direct UDP observation

The configured UDP path uses the selected endpoint, destination port, and exact job-local payload and records the direct observation separately from candidate results.

### No-reply does not mean closed / does not gate candidates

UDP silence is not treated as proof that a port is closed and does not suppress the candidate catalog.

### application-owned staged file input

The browser stages the selected payload into application-owned state before Run; the job consumes the exact staged Base64 payload.

### terminal payload cleanup and Zapret2 restoration PASS.

The accepted `_16` owner-live flow reached Stage 90 with temporary process/rule cleanup and Zapret2 restoration visible.

## `_14` through `_16` accepted protocol/input behavior

`_14` established explicit persisted **Enable QUIC** as the execution gate. `_15` made attempted QUIC IDs visible. Owner-live Extended runs with ordinary QUIC blocked showed all four current IDs:

- `quic-fake-1`;
- `quic-fake-2`;
- `quic-ipfrag-8`;
- `quic-ipfrag-16`.

`_16` established the exact browser-to-job Generic UDP path. Owner-live `job.j09XUc`, target `rutracker.org`, Extended, UDP port `53`, Enable QUIC OFF used a filesystem-verified 140-byte `udp-140.bin`. Stage 80 reported the exact 140-byte payload, ran `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`, treated no reply truthfully, and Stage 90 restored Zapret2. Final outcome was `SUCCESS`.

A later owner-live ON/OFF pair established that Enable QUIC OFF runs no QUIC catalog while independent Generic UDP continues. Persistence after page reload/revisit remains a separate pending row.

## `_17` and `_18` presentation follow-up

`_17` owner-live Russian screenshots confirmed most deterministic translations and human-readable circular idle output, but exposed remaining title/UDP/wrapping defects. `_18` fixed `Лаборатория стратегий`, `UDP порт (опционально)` and the one-line target label. `_18` owner-live accepted those three items but rejected its 12 px workaround and alignment, selecting `_19`.

## `_19` automated/publication acceptance — PASS; owner-live partial

`_19` passed full source/Strategy Lab CI, focused presentation regression, FreeBSD-15 package qualification and persistent testing publication. It provided:

- normal target-label typography instead of `_18` 12 px;
- RU `Стандартный` / `Расширенный`; EN `Standard` / `Extended`;
- right-aligned RU `Режим:` / EN `Mode:`;
- ordinary RU `ожидание`; EN `idle`;
- canonical EN `Strategy` / `Laboratory` plus deterministic active-page RU `Стратегия` / `Лаборатория`;
- a fixed `250px` Laboratory label/value-column attempt.

Automated/package evidence:

- source PR `#254` exact final head `bb3311ddbaa9d5c054ec757a3fe8b6e1c98ce76d`;
- complete project/Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package qualification: PASS;
- exact candidate-defining source merge/tag target: `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`;
- published testing asset: `os-zapret2-restyle-0.4.1_19.pkg`;
- SHA-256: `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`;
- publication workflow run: `31892344832`.

Owner-live `_19` comparison confirms RU `Режим:`, `Расширенный` and `Статус: ожидание` are visible, but rejects the remaining layout: the Laboratory perimeter is more inset than Strategy/native OPNsense pages, the form value column is not on the normal OPNsense grid, and the mode label must be guaranteed to match target-label typography. This selected `_20`.

## `_20` source acceptance scope

The owner-selected `_20` corrective implements:

- one shared native-style `25%` label column for both the top Diagnostics domain row and Strategy Lab input rows;
- target, Generic UDP and Enable QUIC controls therefore share the normal OPNsense value-column position;
- removal of the rejected `_19` fixed `250px` Laboratory label column;
- normal one-line target-label typography retained;
- computed `Режим:` / `Mode:` font size and line height synchronized from the target field-label reference;
- nested Laboratory page/container/row/column margin/padding neutralized so it cannot create a second perimeter inset;
- `_19` localization, Strategy Lab runtime/search, Generic UDP, QUIC and Enable QUIC persistence semantics unchanged.

No Strategy Lab execution rerun is required for `_20` acceptance; the selected proof is visual comparison against Strategy/native OPNsense page layout.

## Scenario matrix

| # | Scenario | Result |
|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | **PASS ON `_13`** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | **PASS ON `_13` — OWNER ACCEPTED** |
| 3 | Extended TLS 1.2 | **PASS ON `_13`** |
| 4 | Extended HTTP | **PASS ON `_13`** |
| 5 | Historical closed-QUIC capability skip | **OBSERVED ON `_13`; SUPERSEDED** |
| 6 | `_14` Enable QUIC ON / blocked control / no capability skip | **PASS** |
| 7 | `_15` QUIC tested count/IDs ordinary output | **OWNER-LIVE PASS — 4 IDs** |
| 8 | `_16` application-owned staged file input | **OWNER-LIVE PASS** |
| 9 | `_16` exact 140-byte configured UDP | **OWNER-LIVE PASS — `job.j09XUc`** |
| 10 | Selected-port/payload direct UDP observation | **OWNER-LIVE PASS** |
| 11 | No-reply does not mean closed / does not gate candidates | **OWNER-LIVE PASS** |
| 12 | terminal payload cleanup and Zapret2 restoration PASS. | **OWNER-LIVE STAGE-90 PASS; deeper residue remains global backlog** |
| 13 | Enable QUIC OFF execution semantics | **OWNER-LIVE PASS** |
| 14 | Enable QUIC OFF/default persistence across reload/revisit | **SOURCE CONTRACT GUARDED; OWNER-LIVE RELOAD PROOF PENDING** |
| 15 | Circular idle ordinary presentation | **OWNER-LIVE RU PASS ON `_17`; later idle wording retained** |
| 16 | `_17` RU/EN presentation review | **RU PARTIAL; selected `_18`** |
| 17 | `_18` title / UDP label / one-line domain label | **OWNER-LIVE PASS FOR THESE THREE ITEMS** |
| 18 | `_18` typography/alignment | **OWNER-LIVE REJECTED; `_19` SELECTED** |
| 19 | `_19` mode/status strings | **OWNER-LIVE RU VISIBLE/PASS FOR OBSERVED ITEMS** |
| 20 | `_19` perimeter/value-grid/mode-font layout | **OWNER-LIVE REJECTED; `_20` SELECTED** |
| 21 | `_20` native perimeter/common form grid/matched mode typography | **SOURCE IMPLEMENTED; CI/PUBLICATION/LIVE ACCEPTANCE PENDING** |
| 22 | Target already accessible | **COMPLETE — OWNER CONFIRMED** |
| 23 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 24 | Circular lifecycle | PENDING REGRESSION |
| 25 | Retention/reboot residue | PENDING REGRESSION |

Settings Apply validation/guards and post-Apply service-state correctness are separately marked complete in the master roadmap by owner confirmation; they are not Strategy Lab execution rows.

## Next product plan

After `_20` UI acceptance, add **Laboratory target support for IP addresses as well as domains**.

## Current failure policy

Generic UDP should only be reopened if fresh evidence contradicts the accepted exact-byte path. QUIC OFF execution should only be reopened if fresh evidence shows OFF still runs QUIC candidates; persistence remains pending until an actual reload/revisit proves the stored setting.

After `_20` owner-live acceptance, the Laboratory presentation row should only be reopened for a concrete regression in the native perimeter/grid, requested typography, mode/status/sidebar localization, or language leakage.

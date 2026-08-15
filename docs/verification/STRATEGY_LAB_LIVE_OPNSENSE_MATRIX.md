# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` QUIC OBSERVABILITY OWNER-LIVE PASS; `v0.4.1_16` GENERIC UDP + QUIC OFF EXECUTION OWNER-LIVE PASS; `v0.4.1_17` RU PRESENTATION OWNER-LIVE PARTIAL; `v0.4.1_18` LABEL/ONE-LINE OWNER-LIVE PARTIAL; `v0.4.1_19` LABORATORY UI CORRECTIVE SOURCE CANDIDATE.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current source candidate: `v0.4.1_19` / `PLUGIN_REVISION=19`;
- last published testing package/tag: `os-zapret2-restyle-0.4.1_18.pkg` / `v0.4.1_18`;
- `_18` source/tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- `_18` package SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- `_18` publication workflow run: `31889449879`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: **PASS**;
- owner-live `_16` QUIC OFF execution semantics: **PASS**;
- already-accessible target: **COMPLETE BY OWNER CONFIRMATION**;
- Enable QUIC OFF/default persistence across reload/revisit: **PENDING LIVE PROOF**;
- `_18` live UI: **PARTIAL — TITLE/UDP/ONE-LINE LABEL PASS; TYPOGRAPHY/ALIGNMENT + MODE/STATUS/NAV SELECTED `_19`**;
- `_19` Laboratory UI corrective: **SOURCE IMPLEMENTED; AUTOMATED/PUBLICATION/LIVE ACCEPTANCE PENDING**.

Machine `_18` publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_18.md`.
Owner-live Generic UDP evidence: `docs/verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`.
Owner-live QUIC OFF/UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`.
Owner-live `_17` RU follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`.
Owner-live `_18` Laboratory UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`.
`_19` patch record: `docs/patches/v0.4.1_19.md`.

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

## `_17` RU presentation owner-live follow-up — partial

The owner installed published `_17` and supplied Russian-mode Diagnostics screenshots.

Visible PASS included translated domain-connectivity UI, `Заблокированный домен / IP`, `Запуск`, `Включить QUIC`, result/stage labels and human-readable circular idle output. Remaining `Strategy Lab`, `Generic UDP (optional)` and wrapping/alignment defects selected `_18`.

## `_18` automated/publication acceptance — PASS; owner-live partial

Published `_18` contained:

- `Strategy Lab` / RU `Лаборатория стратегий`;
- `Generic UDP (optional)` / RU `UDP порт (опционально)`;
- explicit English counterparts;
- a one-line blocked-domain label and attempted shared value-column layout;
- focused regression coverage preserving circular-idle and Enable QUIC persistence source contracts.

Automated/package evidence:

- source PR `#252` exact verified head `1f9d5bb8b9f9d4204777f513bedf5e2d1e479396`;
- complete project/Strategy Lab corrective matrix: PASS;
- FreeBSD-15 package qualification: PASS;
- exact candidate-defining source merge/tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- published testing asset: `os-zapret2-restyle-0.4.1_18.pkg`;
- SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`.

Owner-live `_18` screenshot confirms:

- `Лаборатория стратегий`: PASS;
- `UDP порт (опционально)`: PASS;
- one-line `Заблокированный домен / IP`: PASS.

The owner rejected `_18` as final UI acceptance because the forced 12 px label typography is visibly too small and the perceived domain/UDP/QUIC alignment is wrong. The same handoff selected deterministic mode/status/sidebar localization. This selected `_19`.

## `_19` source acceptance scope

The owner-selected `_19` corrective implements:

- normal UI typography; `_18` `font-size:12px` is removed;
- an explicit fixed table/label/value-column contract for domain / Generic UDP / Enable QUIC;
- RU mode values `Стандартный` / `Расширенный`; EN `Standard` / `Extended`;
- right-aligned RU `Режим:` / EN `Mode:` immediately before the selector;
- ordinary idle RU `ожидание`; EN `idle`;
- canonical menu entries EN `Strategy` / `Laboratory`, with deterministic RU `Стратегия` / `Лаборатория` on the Laboratory page;
- focused regression coverage for the new strings/layout while retaining circular ordinary-state and Enable QUIC persistence source contracts.

No Strategy Lab search/runtime semantics change in `_19`.

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
| 15 | Circular idle ordinary presentation | **OWNER-LIVE RU PASS ON `_17`; `_19` changes idle casing/wording by owner request** |
| 16 | `_17` RU/EN presentation review | **RU PARTIAL; selected `_18`** |
| 17 | `_18` title / UDP label / one-line domain label | **OWNER-LIVE PASS FOR THESE THREE ITEMS** |
| 18 | `_18` typography/alignment | **OWNER-LIVE REJECTED; `_19` SELECTED** |
| 19 | `_19` normal typography / aligned controls / mode-status-navigation RU/EN | **SOURCE IMPLEMENTED; CI/PUBLICATION/LIVE ACCEPTANCE PENDING** |
| 20 | Target already accessible | **COMPLETE — OWNER CONFIRMED** |
| 21 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 22 | Circular lifecycle | PENDING REGRESSION |
| 23 | Retention/reboot residue | PENDING REGRESSION |

Settings Apply validation/guards and post-Apply service-state correctness are separately marked complete in the master roadmap by owner confirmation; they are not Strategy Lab execution rows.

## Next product plan

After `_19` UI acceptance, add **Laboratory target support for IP addresses as well as domains**.

## Current failure policy

Generic UDP should only be reopened if fresh evidence contradicts the accepted exact-byte path. QUIC OFF execution should only be reopened if fresh evidence shows OFF still runs QUIC candidates; persistence remains pending until an actual reload/revisit proves the stored setting.

After `_19` owner-live acceptance, the Laboratory presentation row should only be reopened for a concrete regression in the requested typography/alignment, mode/status/sidebar localization, or language leakage.

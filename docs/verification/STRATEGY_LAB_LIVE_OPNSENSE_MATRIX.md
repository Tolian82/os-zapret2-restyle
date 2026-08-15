# Strategy Lab live OPNsense verification matrix

Overall status: **`v0.4.1_13` ACCEPTED BASELINE; `v0.4.1_14` PUBLISHED/INSTALLED HISTORICAL INPUT; `v0.4.1_15` QUIC OBSERVABILITY OWNER-LIVE PASS; `v0.4.1_16` GENERIC UDP + QUIC OFF EXECUTION OWNER-LIVE PASS; `v0.4.1_17` RU PRESENTATION OWNER-LIVE PARTIAL; `v0.4.1_18` LABEL/ONE-LINE OWNER-LIVE PARTIAL; `v0.4.1_19` TEXT/MODE/STATUS OWNER-LIVE PARTIAL; `v0.4.1_20` FIELD-GRID/MODE CORRECTIVE PUBLISHED BUT FRAME/NAVIGATION OWNER-LIVE REJECTED; `v0.4.1_21` NATIVE FRAME + CROSS-PAGE NAVIGATION LOCALIZATION PUBLISHED, OWNER-LIVE PENDING.**

Only FreeBSD 15 amd64 packages are valid. Source/CI does not replace selected owner-live evidence.

## Current package/source boundary

- current packaged revision: `v0.4.1_21` / `PLUGIN_REVISION=21`;
- current published testing package/tag: `os-zapret2-restyle-0.4.1_21.pkg` / `v0.4.1_21`;
- `_21` source/tag target: `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
- `_21` package SHA-256: `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
- `_21` publication workflow run: `31898795618`;
- stable Pages/pkg repository promoted: no;
- owner-live `_16` Generic UDP verification: **PASS**;
- owner-live `_16` QUIC OFF execution semantics: **PASS**;
- already-accessible target: **COMPLETE BY OWNER CONFIRMATION**;
- Enable QUIC OFF/default persistence across reload/revisit: **PENDING LIVE PROOF**;
- `_20` common 25% field grid and mode-label direction remain accepted;
- `_20` owner-live perimeter/navigation: **REJECTED — normal OPNsense outer frame missing; Russian submenu reverts to English after navigating to Strategy**;
- `_21` native-frame ownership + both-page RU/EN navigation corrective: **SOURCE/CI/FREEBSD/PUBLICATION COMPLETE; OWNER-LIVE VISUAL ACCEPTANCE PENDING**.

Machine `_21` publication evidence: `docs/verification/evidence/testing-publications/v0.4.1_21.md`.
Owner-live Generic UDP evidence: `docs/verification/evidence/2026-08-15-v0.4.1_16-generic-udp-owner-live-pass.md`.
Owner-live QUIC OFF/UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`.
Owner-live `_17` RU follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`.
Owner-live `_18` Laboratory UI follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`.
Owner-live `_19` layout follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md`.
Owner-live `_20` frame/navigation follow-up: `docs/verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`.
`_21` patch record: `docs/patches/v0.4.1_21.md`.

Normal Stage 60 remains Model C only; automatic Model B/A production fallback remains disabled from `_13`.

## Accepted `_13` baseline

Durable evidence: `docs/verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`.

- `telegram.org` `job.6RhNa1`: exhaustive `NO_CANDIDATE`, Stage 60 `16/16`, no fallback, clean RUNNING restoration.
- `rutracker.org` `job.PEEjoY`: `SUCCESS`, Stage 60 `16/16`, three stable shortlist entries, clean RUNNING restoration.
- `www.youtube.com` `job.7Kz5ro`: early `SUCCESS`, `7/16`, `enough_candidates`, three stable shortlist entries.
- initial permanent service STOPPED: `rutracker.org` `job.5b97u9` `SUCCESS`, service remained STOPPED; owner accepted the observable row.
- Extended TLS 1.2/HTTP: `rutracker.org` `job.TJlWoY`, truthful executed negative protocol evidence, Stage 80/90 PASS.

## `_14` owner-live observations that selected `_15`

This historical section remains an accepted contract anchor, not current product direction.

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

`_14` established explicit persisted **Enable QUIC** as the execution gate. `_15` made attempted QUIC IDs visible. Owner-live Extended runs with ordinary QUIC blocked showed all four current IDs: `quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`.

`_16` established the exact browser-to-job Generic UDP path. Owner-live `job.j09XUc`, target `rutracker.org`, Extended, UDP port `53`, Enable QUIC OFF used a filesystem-verified 140-byte `udp-140.bin`. Stage 80 reported the exact 140-byte payload, ran `udp-ipfrag-8`, `udp-ipfrag-16`, `udp-ipfrag-32`, treated no reply truthfully, and Stage 90 restored Zapret2. Final outcome was `SUCCESS`.

A later owner-live ON/OFF pair established that Enable QUIC OFF runs no QUIC catalog while independent Generic UDP continues. Persistence after page reload/revisit remains a separate pending row.

## `_17` through `_20` presentation follow-up

`_17` owner-live Russian screenshots confirmed most deterministic translations and human-readable circular idle output. `_18` fixed `Лаборатория стратегий`, `UDP порт (опционально)` and the one-line target label; owner-live accepted those items but rejected the 12 px workaround. `_19` restored normal typography and added RU/EN mode/status/navigation strings. Owner-live `_19` confirmed RU `Режим:`, `Расширенный` and `Статус: ожидание`, but rejected the remaining perimeter/value-grid/mode-font layout and selected `_20`.

`_20` passed automated validation, FreeBSD-15 package qualification and persistent testing publication. Its shared native-style 25% label grid, common value-column positioning and mode-label typography synchronization remain the accepted direction. Owner-live `_20` then exposed two separate presentation defects: the `.page-content-main` neutralization removed the platform-owned outer OPNsense perimeter itself, and deterministic submenu RU/EN rewriting existed only on Laboratory, so a full navigation to Strategy restored the English `Menu.xml` fallback labels.

Durable `_20` owner-live evidence: `docs/verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`.

## `_21` selected corrective — published

Published `_21` corrects the confirmed presentation root causes without reopening Strategy Lab execution behavior:

- Laboratory no longer creates or overrides its own `.page-content-main`; the OPNsense-owned page wrapper retains the normal outer perimeter;
- Laboratory sections render directly as normal `content-box` blocks inside the platform frame, matching the structural pattern used by Strategy;
- the accepted common `25%` Diagnostics field grid remains unchanged;
- computed `Режим:` / `Mode:` font size and line height remain synchronized from the target field-label reference;
- canonical `Menu.xml` names remain `Strategy` / `Laboratory` as fallback;
- both Laboratory and Strategy apply deterministic active-language submenu labels, so Russian remains `Стратегия` / `Лаборатория` across page navigation and English remains `Strategy` / `Laboratory`;
- Strategy Lab runtime/search, Generic UDP, QUIC, circular and persistence behavior is unchanged.

Delivery proof:

- focused native-frame/localization/persistence regression: complete;
- complete applicable project/Strategy Lab corrective matrix: complete;
- FreeBSD-15 package qualification: complete;
- exact-head source merge: `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
- persistent testing package: `os-zapret2-restyle-0.4.1_21.pkg`;
- package SHA-256: `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
- publication workflow: `31898795618`;
- stable Pages/pkg repository promotion: no.

No Strategy Lab execution rerun is required for owner-live `_21` acceptance because the selected changes are presentation-only.

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
| 17 | `_18` title / UDP label / one-line domain label | **OWNER-LIVE PASS FOR THESE ITEMS** |
| 18 | `_18` typography/alignment | **OWNER-LIVE REJECTED; `_19` SELECTED** |
| 19 | `_19` mode/status strings | **OWNER-LIVE RU VISIBLE/PASS FOR OBSERVED ITEMS** |
| 20 | `_19` perimeter/value-grid/mode-font layout | **OWNER-LIVE REJECTED; `_20` SELECTED** |
| 21 | `_20` common 25% field grid / mode-label typography direction | **PUBLISHED; RETAINED BY `_21`** |
| 22 | `_20` normal OPNsense outer perimeter | **OWNER-LIVE REJECTED; `_21` SELECTED** |
| 23 | `_20` Russian submenu across Laboratory → Strategy | **OWNER-LIVE REJECTED; `_21` SELECTED** |
| 24 | `_21` OPNsense-owned Laboratory perimeter | **PUBLISHED; OWNER-LIVE PENDING** |
| 25 | `_21` Russian submenu persistence across Laboratory ↔ Strategy | **PUBLISHED; OWNER-LIVE PENDING** |
| 26 | Target already accessible | **COMPLETE — OWNER CONFIRMED** |
| 27 | Cancellation/internal-failure containment | PENDING REGRESSION |
| 28 | Circular lifecycle | PENDING REGRESSION |
| 29 | Retention/reboot residue | PENDING REGRESSION |

Settings Apply validation/guards and post-Apply service-state correctness are separately marked complete in the master roadmap by owner confirmation; they are not Strategy Lab execution rows.

## Next product plan

After `_21` UI acceptance, add **Laboratory target support for IP addresses as well as domains**.

## Current failure policy

Generic UDP should only be reopened if fresh evidence contradicts the accepted exact-byte path. QUIC OFF execution should only be reopened if fresh evidence shows OFF still runs QUIC candidates; persistence remains pending until an actual reload/revisit proves the stored setting.

After `_21` owner-live acceptance, the Laboratory presentation row should only be reopened for a concrete regression in the native perimeter/grid, requested typography, mode/status/sidebar localization, or language leakage.

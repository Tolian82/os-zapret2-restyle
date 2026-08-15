# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-08-15

- Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md)
- Exact revision handoff: [`START_HERE.md`](START_HERE.md)
- Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- Project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- Current-line detail: [`history/current/v0.4.x.md`](history/current/v0.4.x.md)

## Whole-project path

- [x] Initial OPNsense plugin
- [x] Runtime/service lifecycle
- [x] Traffic Strategy / targets
- [x] Zapret2 Service GUI
- [x] Diagnostics fixes
- [x] Blockcheck redesign
- [x] Strategy Lab foundation
- [x] Strategy Lab Python migration
- [x] Adaptive candidate search
- [x] Timeout/budget containment
- [x] Model A/B/C experimentation and Model C selection
- [x] Source-port attribution/leasing
- [x] Adaptive budgets/readiness
- [x] Lua initialization measurements
- [x] BLOB startup/RSS/common-set measurements
- [x] GET-4K discovery decision
- [x] Warm/readiness repeat verification
- [x] Model-C-only production (`v0.4.1_13`)
- [x] GitHub-native patch/package delivery and publication-record tail
- [x] Documentation memory/state/governance model
- [ ] Strategy Lab risk-selected regression and protocol breadth
  - [x] initial Zapret2 STOPPED state
  - [x] Extended TLS 1.2 execution/result semantics
  - [x] Extended HTTP execution/result semantics
  - [x] historical `_13` closed-QUIC capability-skip observation
  - [x] `v0.4.1_14` explicit Enable QUIC source contract
  - [x] `v0.4.1_15` QUIC/UDP observability package published
    - [x] QUIC attempted count/IDs visible in normal Stage 80
    - [x] owner-live QUIC ON with blocked control path shows all four attempted IDs
    - [x] RU/EN protocol presentation source contract
    - [x] selected-port/payload direct UDP control observation source contract
    - [x] earlier Generic UDP owner report recorded; later superseded by exact-byte `_16` live PASS
  - [x] **`v0.4.1_16` Generic UDP browser-to-job handoff — OWNER-LIVE PASS**
    - [x] trace actual product transport: browser Base64 POST, not multipart upload directory
    - [x] stage selected file immediately on `change`
    - [x] retain filename, exact decoded byte count and Base64 in application-owned state
    - [x] display localized ready-to-send filename/byte evidence before Run
    - [x] Run consumes staged payload even if native file-control selection is later lost/reset
    - [x] retain defensive Run-time staging fallback when a native File is still present
    - [x] remove realm-specific `instanceof ArrayBuffer` assumption
    - [x] retain decoded `1..4096` **byte** and strict backend Base64 bounds
    - [x] add explicit job-local preparation error attribution including unavailable/not-writable job directory, temp-create, decode, chmod/move and state-record classes
    - [x] preserve exact port/payload control observation, no-reply semantics, candidate enumeration and cleanup
    - [x] complete Strategy Lab corrective matrix and FreeBSD-15 qualification
    - [x] persistent `v0.4.1_16` testing-package publication
    - [x] owner-live exact 140-byte configured UDP and Stage-90 restoration PASS
    - [x] owner correction: previous repeated size errors were ~140 KiB files; contract is `1..4096 bytes`
  - [x] Enable QUIC OFF execution semantics
    - [x] owner-live OFF run reports QUIC strategy search disabled
    - [x] independent Generic UDP candidate execution remains active with QUIC OFF
    - [x] tested OFF job completes SUCCESS and Stage-90 restoration PASS
  - [ ] Enable QUIC OFF/default persistence across reload/revisit — source persistence contract remains guarded; owner-live reload proof pending
  - [ ] **Strategy Lab / Laboratory RU-EN presentation completion**
    - [x] `_17` source/publication: circular idle ordinary display removes raw JSON
    - [x] `_17` source/publication: deterministic RU/EN result/stage/action labels
    - [x] `_17` latest-head full CI + FreeBSD-15 qualification
    - [x] `_17` exact-head source merge and persistent testing publication
    - [x] `_17` owner-live Russian review performed; remaining title/UDP/layout defects selected for `_18`
    - [x] `_18` source/publication: `Strategy Lab` / RU `Лаборатория стратегий`
    - [x] `_18` source/publication: `Generic UDP (optional)` / RU `UDP порт (опционально)`
    - [x] `_18` source/publication: one-line RU `Заблокированный домен / IP`
    - [x] `_18` owner-live confirms title/UDP translation and one-line blocked-domain label
    - [x] `_19` source/publication: normal label typography, mode/status/sidebar RU/EN strings, shared Laboratory value-column attempt
    - [x] `_19` owner-live confirms RU `Режим:`, `Расширенный`, `Статус: ожидание`
    - [x] `_19` owner-live rejects remaining perimeter/value-grid/mode-font layout and selects `_20`
    - [ ] `_20` native OPNsense layout corrective
      - [x] source: both Diagnostics input tables use one shared native-style `25%` field-label column
      - [x] source: target / Generic UDP / Enable QUIC use the same normal value-column position
      - [x] source: remove the rejected fixed `_19` `250px` Laboratory label column
      - [x] source: preserve one-line target label with normal UI typography
      - [x] source: synchronize `Режим:` / `Mode:` computed font size and line height from the target field label
      - [x] source: neutralize nested Laboratory page/container/row/column perimeter spacing
      - [x] focused regression preserves RU/EN, circular idle and Enable QUIC persistence source contracts
      - [ ] latest-head full CI + FreeBSD-15 package qualification
      - [ ] exact-head source merge and persistent `v0.4.1_20` testing publication
      - [ ] owner-live visual acceptance: native perimeter, common field grid, matched mode-label typography
    - [ ] owner-live EN/no-language-leakage completion if still needed after `_20`
    - [ ] owner-live Enable QUIC OFF/default persistence after reload/revisit
  - [x] already-accessible target — completed by owner confirmation
  - [ ] cancellation/internal-failure containment
- [ ] **Laboratory target support: test IP addresses as well as domains — NEXT PLAN after `_20` UI acceptance**
- [ ] Circular lifecycle coverage
  - [ ] start/stop/TTL
  - [ ] stale-session recovery
- [x] Settings Apply coverage — completed by owner confirmation
  - [x] validation/guards
  - [x] service-state correctness after Apply
- [ ] Diagnostics persistence/reload
- [ ] RU/EN presentation review beyond the current Laboratory corrective scope
- [ ] Retention/cleanup boundaries
- [ ] Reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up
- [ ] Package/runtime version visibility follow-up
- [ ] Additional BLOB repository GUI
  - [ ] wait for owner-supplied/approved technical contract

## Current priority — qualify/publish `_20`, visually verify it, then add IP targets to Laboratory

Current source candidate: `v0.4.1_20` (`PLUGIN_REVISION=20`).

Last published testing identity:

- tag: `v0.4.1_19`;
- asset: `os-zapret2-restyle-0.4.1_19.pkg`;
- SHA-256: `142ec3f3f5843d6be09d0ad34aa433c00ddf4ef82e75bbb2fd7104fdcc3eb7f8`;
- source/tag target: `6d06f0c3dfc7a76f0dc7b43ca6ba8cc0d0f83758`;
- publication workflow run: `31892344832`;
- stable Pages/pkg repository promoted: no.

`_19` automated/package acceptance is complete. Owner-live comparison selected `_20` because the Laboratory page still has a larger perimeter inset than ordinary OPNsense pages, the field value column is not on the normal platform form grid, and `Режим:` must be explicitly typography-matched to the target label.

After `_20` publication/install:

1. one visual comparison of Laboratory against Strategy/native OPNsense perimeter and field grid;
2. confirm `Режим:` typography matches the target label;
3. no Strategy Lab execution rerun is needed for this visual-only corrective;
4. Enable QUIC OFF/default persistence reload/revisit proof remains separate;
5. **next engineering plan: make Laboratory accept/test IP addresses as well as domains**;
6. continue the remaining backlog above.

Owner-live `_19` corrective evidence: [`verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md).
Machine `_19` publication evidence: [`verification/evidence/testing-publications/v0.4.1_19.md`](verification/evidence/testing-publications/v0.4.1_19.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

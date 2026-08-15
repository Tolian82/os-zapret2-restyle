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
  - [x] **`v0.4.1_16` Generic UDP browser-to-job handoff — OWNER-LIVE PASS**
  - [x] Enable QUIC OFF execution semantics
  - [ ] Enable QUIC OFF/default persistence across reload/revisit — source persistence contract remains guarded; owner-live reload proof pending
  - [ ] **Strategy Lab / Laboratory RU-EN presentation completion**
    - [x] `_17` source/publication + RU owner-live partial
    - [x] `_18` title / UDP label / one-line blocked-domain label + owner-live partial
    - [x] `_19` source/publication: normal label typography, mode/status/sidebar RU/EN strings
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
      - [x] latest-head full CI + FreeBSD-15 package qualification
      - [x] exact-head source merge and persistent `v0.4.1_20` testing publication
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

## Current priority — visually verify published `_20`, then add IP targets to Laboratory

Current source candidate: `v0.4.1_20` (`PLUGIN_REVISION=20`).

Current published testing identity:

- tag: `v0.4.1_20`;
- asset: `os-zapret2-restyle-0.4.1_20.pkg`;
- SHA-256: `5d5fae0a79054ad807a92ca7804d5984d63782927c667962b6395d48627ab64a`;
- source/tag target: `d732965c143563352e18ac58c209aeb30a6d4feb`;
- publication workflow run: `31896330680`;
- stable Pages/pkg repository promoted: no.

`_20` source, focused layout/localization/persistence test, complete corrective matrix, FreeBSD-15 qualification, exact-head source merge and persistent testing publication are complete. The remaining `_20` boundary is visual owner-live acceptance only.

After `_20` install:

1. compare Laboratory against Strategy/native OPNsense perimeter and field grid;
2. confirm `Режим:` typography matches the target label;
3. no Strategy Lab execution rerun is needed for this visual-only corrective;
4. Enable QUIC OFF/default persistence reload/revisit proof remains separate;
5. **next engineering plan: make Laboratory accept/test IP addresses as well as domains**;
6. continue the remaining backlog above.

Owner-live `_19` corrective evidence: [`verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_19-laboratory-layout-owner-live-followup.md).
Machine `_20` publication evidence: [`verification/evidence/testing-publications/v0.4.1_20.md`](verification/evidence/testing-publications/v0.4.1_20.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

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
    - [x] `_20` source/CI/FreeBSD/testing publication
      - [x] source: both Diagnostics input tables use one shared native-style `25%` field-label column
      - [x] source: target / Generic UDP / Enable QUIC use the same normal value-column position
      - [x] source: remove the rejected fixed `_19` `250px` Laboratory label column
      - [x] source: preserve one-line target label with normal UI typography
      - [x] source: synchronize `Режим:` / `Mode:` computed font size and line height from the target field label
      - [x] source: attempted nested Laboratory perimeter neutralization
      - [x] focused regression preserves RU/EN, circular idle and Enable QUIC persistence source contracts
      - [x] latest-head full CI + FreeBSD-15 package qualification
      - [x] exact-head source merge and persistent `v0.4.1_20` testing publication
      - [x] owner-live: accepted common field grid/mode text direction, but rejected missing native perimeter and cross-page navigation localization
    - [ ] `_21` native frame ownership + persistent cross-page menu localization
      - [x] source: remove redundant Laboratory `page-content-main/container-fluid/row/column` wrapper
      - [x] source: remove Laboratory `.page-content-main` margin/padding overrides
      - [x] source: render Laboratory as normal OPNsense `content-box` blocks inside the platform-owned frame
      - [x] source: preserve accepted shared 25% form grid and mode-label typography synchronization
      - [x] source: apply RU/EN `Стратегия` / `Лаборатория` navigation on Strategy as well as Laboratory
      - [x] focused regression updated for native frame ownership and both-page navigation localization
      - [x] latest-head full CI + FreeBSD-15 package qualification
      - [x] exact-head source merge and persistent `v0.4.1_21` testing publication
      - [ ] owner-live visual acceptance: native perimeter + Russian menu persistence across Laboratory ↔ Strategy
    - [ ] owner-live EN/no-language-leakage completion if still needed after `_21`
    - [ ] owner-live Enable QUIC OFF/default persistence after reload/revisit
  - [x] already-accessible target — completed by owner confirmation
  - [ ] cancellation/internal-failure containment
- [ ] **Laboratory target support: test IP addresses as well as domains — NEXT PLAN after `_21` UI acceptance**
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

## Current priority — owner-live verify published `_21`, then add IP targets to Laboratory

Current published testing identity:

- tag: `v0.4.1_21`;
- asset: `os-zapret2-restyle-0.4.1_21.pkg`;
- SHA-256: `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
- source/tag target: `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
- publication workflow run: `31898795618`;
- stable Pages/pkg repository promoted: no.

Owner-live `_20` comparison showed that the perimeter-neutralization approach removed the platform-owned OPNsense frame itself, and that Russian submenu localization was only reapplied on Laboratory. Published `_21` corrects the ownership model rather than adding another spacing workaround: OPNsense owns the page frame, while both plugin pages apply the same active-language submenu labels.

`_21` delivery status:

1. focused native-frame/localization/persistence regression — complete;
2. applicable complete corrective matrix and FreeBSD-15 package qualification — complete;
3. exact-head source merge — complete at `02cbd27d3c6a533bdaa9b44bf90e9510c8a4af29`;
4. persistent testing publication — complete, SHA-256 `17d74cfe804bdcc3984961185d0b29ef1c15329b6079dcf1ea2417ea16e3848a`;
5. bounded publication-record reconciliation — current documentation tail.

After `_21` install:

1. confirm Laboratory perimeter matches Strategy/native OPNsense;
2. switch Laboratory ↔ Strategy under Russian UI and confirm `Стратегия` / `Лаборатория` stays Russian;
3. confirm accepted common field grid and `Режим:` typography remain intact;
4. no Strategy Lab execution rerun is required for this UI-only corrective;
5. Enable QUIC OFF/default persistence reload/revisit proof remains separate;
6. **next engineering plan: make Laboratory accept/test IP addresses as well as domains**;
7. continue the remaining backlog above.

Owner-live `_20` corrective evidence: [`verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_20-laboratory-frame-menu-owner-live-followup.md).
Machine `_21` publication evidence: [`verification/evidence/testing-publications/v0.4.1_21.md`](verification/evidence/testing-publications/v0.4.1_21.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

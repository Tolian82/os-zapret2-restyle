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
  - [x] **Strategy Lab / Laboratory RU-EN presentation completion — OWNER CLOSED CURRENT SCOPE**
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
      - [x] attempted nested Laboratory perimeter neutralization
      - [x] focused regression preserves RU/EN, circular idle and Enable QUIC persistence source contracts
      - [x] latest-head full CI + FreeBSD-15 package qualification
      - [x] exact-head source merge and persistent `v0.4.1_20` testing publication
      - [x] owner-live: accepted common field grid/mode text direction, but rejected missing native perimeter and cross-page navigation localization
    - [x] `_21` native frame ownership + persistent cross-page menu localization
      - [x] source: remove redundant Laboratory `page-content-main/container-fluid/row/column` wrapper
      - [x] source: remove Laboratory `.page-content-main` margin/padding overrides
      - [x] source: render Laboratory as normal OPNsense `content-box` blocks inside the platform-owned frame
      - [x] source: preserve accepted shared 25% form grid and mode-label typography synchronization
      - [x] source: apply RU/EN `Стратегия` / `Лаборатория` navigation on Strategy as well as Laboratory
      - [x] focused regression updated for native frame ownership and both-page navigation localization
      - [x] latest-head full CI + FreeBSD-15 package qualification
      - [x] exact-head source merge and persistent `v0.4.1_21` testing publication
      - [x] owner-live visual acceptance: native perimeter + Russian menu persistence across Laboratory ↔ Strategy
    - [x] additional current-scope language acceptance not required: owner explicitly closed the Russian-presentation task after `_21`; future concrete language regressions are new defects
    - [ ] owner-live Enable QUIC OFF/default persistence after reload/revisit — separate non-presentation row
  - [x] already-accessible target — completed by owner confirmation
  - [ ] cancellation/internal-failure containment
- [ ] **Laboratory target support: test IPv4 addresses as well as domains — `_23` PUBLISHED; OWNER-LIVE CORRECTIVE VERIFICATION NEXT**
  - [x] architecture/current-source audit: feature is feasible but not a validator-only change
  - [x] confirm dormant IP scaffolding in Stage 00/40, search epoch, firewall pinning and final `--ipset-ip=` profile generation
  - [x] identify unsafe prior behavior: IPv4 TLS candidates degraded to plain TCP-connect evidence and must not create false PASS results
  - [x] select IPv4-first contract; do not silently claim IPv6 support in the first patch
  - [x] select fixed destination IP + explicit/conditional Host/SNI service identity for truthful web/TLS/QUIC validation
  - [x] implement domain-or-IPv4 API/shell target classification and per-job optional service identity
  - [x] implement IP-aware candidate target binding without changing Model-C attribution/lifecycle ownership
  - [x] make TLS/HTTP/QUIC probes preserve service hostname/SNI while pinning destination IP; bare-IP QUIC is unsupported rather than false PASS
  - [x] preserve direct-IP Generic UDP behavior
  - [x] add focused domain-regression + IPv4/SNI + bare-IP/error-semantics coverage
  - [x] latest-head complete CI + FreeBSD-15 package qualification for `_22`
  - [x] exact-head squash merge + persistent `v0.4.1_22` testing publication
  - [x] owner-live `_22` exposed result-classification corrections
  - [x] implement `_23` truthful-result corrective
  - [x] exact-head complete CI + FreeBSD-15 qualification for `_23` — run `31909623049`
  - [x] squash merge `_23` source — `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`
  - [x] persistently publish `v0.4.1_23` — run `31909994148`, SHA-256 `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`
  - [ ] owner-live `rutracker.net` Standard: stable intercepted finalist survives Stage 85 with HTTP 4xx/5xx
  - [ ] owner-live `rutracker.org` ordinary-domain regression
  - [ ] owner-live bare IPv4: certificate-identity failure reports PARTIAL + Host/SNI guidance
  - [ ] owner-live IPv4 + real Host/SNI pinned to entered destination
  - [ ] owner-live final working profile contains `--ipset-ip=<target>` and exact replay passes
  - [ ] owner-live Extended Generic UDP against IPv4 without Host/SNI
  - [ ] owner-live bare-IP QUIC is SKIPPED with zero tested candidates; QUIC with Host/SNI remains valid
  - [ ] owner-live Stage-90 restoration/residue verification after IP run
- [ ] Circular lifecycle coverage
  - [ ] start/stop/TTL
  - [ ] stale-session recovery
- [x] Settings Apply coverage — completed by owner confirmation
  - [x] validation/guards
  - [x] service-state correctness after Apply
- [ ] Diagnostics persistence/reload
- [ ] RU/EN presentation review beyond the closed current Laboratory corrective scope
- [ ] Retention/cleanup boundaries
- [ ] Reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up
- [ ] Package/runtime version visibility follow-up
- [ ] Additional BLOB repository GUI
  - [ ] wait for owner-supplied/approved technical contract

## Current priority — owner-live `v0.4.1_23` truthful-result verification

Current published testing identity:

- tag: `v0.4.1_23`;
- asset: `os-zapret2-restyle-0.4.1_23.pkg`;
- SHA-256: `37bd4c19bacc48f17aeb4e497c1058e675df067adf2ecd00334708e995bcb283`;
- source/tag target: `3cd3ecc8b9976b1ec8000e2eccfa48f6898d1e73`;
- exact-head source CI run: `31909623049`;
- publication workflow run: `31909994148`;
- stable Pages/pkg repository promoted: no.

Machine publication evidence: [`verification/evidence/testing-publications/v0.4.1_23.md`](verification/evidence/testing-publications/v0.4.1_23.md).

Owner-live `_21` remains accepted for the selected Laboratory presentation scope: the normal OPNsense outer frame is restored, the accepted shared field grid remains correct, and Russian `Стратегия` / `Лаборатория` stays localized across page navigation. The current Russian-presentation task is closed; GitHub issue `#155` is completed.

The published `_23` corrective preserves the `_22` IPv4 target contract while fixing truthful terminal/result classification selected by owner-live evidence: authenticated/intercepted HTTP 4xx/5xx no longer erases otherwise stable DPI-path evidence, bare-IPv4 QUIC is skipped before execution without Host/SNI, and bare-IPv4 TLS identity failure is reported as PARTIAL guidance rather than a misleading empty result.

The current base target contract remains:

1. the existing `Заблокированный домен / IP` field accepts either a domain or canonical IPv4;
2. domains continue through the existing behavior unchanged;
3. IPv4 skips DNS and is pinned directly for firewall/result attribution;
4. a conditional/optional `Host / SNI` field carries service identity separately from destination identity;
5. with Host/SNI, web/TLS/QUIC connect to the fixed IP while preserving hostname/SNI/certificate verification;
6. Generic UDP remains direct against the IP and does not require Host/SNI;
7. TLS candidates do not treat a successful plain TCP connection as successful TLS/DPI-bypass evidence;
8. bare-IP QUIC without hostname verification is skipped, never a false working strategy;
9. final IP recommendations and exact replay use `--ipset-ip=<target>`;
10. Model C, timeout budgets, lifecycle, cleanup/restoration and deterministic attribution remain unchanged;
11. IPv6 target support remains deferred because the current search epoch is IPv4-specific.

Source patch contracts: [`patches/v0.4.1_22.md`](patches/v0.4.1_22.md), [`patches/v0.4.1_23.md`](patches/v0.4.1_23.md).

Enable QUIC OFF/default persistence reload/revisit proof remains a separate existing backlog row and is not folded into this IP-target patch.

Owner-live `_21` evidence: [`verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_21-laboratory-frame-localization-owner-live-pass.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

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
    - [x] `_17` source/publication: circular idle ordinary display removes raw `{` / `}` / `{"state":"idle"}` JSON
    - [x] `_17` source/publication: RU `Состояние: ОЖИДАНИЕ` / EN `State: IDLE`
    - [x] `_17` source/publication: raw machine job JSON remains only under explicitly advanced output
    - [x] `_17` source/publication: deterministic RU/EN result/stage/action labels
    - [x] `_17` latest-head full CI + FreeBSD-15 qualification
    - [x] `_17` exact-head source merge and persistent testing publication
    - [x] `_17` owner-live Russian review performed; remaining title/UDP/layout defects selected for `_18`
    - [x] `_18` source/publication: `Strategy Lab` / RU `Лаборатория стратегий`
    - [x] `_18` source/publication: `Generic UDP (optional)` / RU `UDP порт (опционально)`
    - [x] `_18` source/publication: one-line RU `Заблокированный домен / IP`
    - [x] `_18` owner-live confirms title/UDP translation and one-line blocked-domain label
    - [ ] `_19` owner-selected corrective
      - [x] source: remove `_18` 12 px label workaround; restore normal UI typography
      - [x] source: explicit fixed label/value columns for domain / Generic UDP / Enable QUIC
      - [x] source: RU mode values `Стандартный` / `Расширенный`; EN `Standard` / `Extended`
      - [x] source: right-aligned `Режим:` / `Mode:` before mode selector
      - [x] source: RU idle `ожидание`; EN idle `idle`
      - [x] source: sidebar EN `Strategy` / `Laboratory`, RU `Стратегия` / `Лаборатория`
      - [x] focused regression preserves circular-idle and Enable QUIC persistence source contracts
      - [ ] latest-head full CI + FreeBSD-15 package qualification
      - [ ] exact-head source merge and persistent `v0.4.1_19` testing publication
      - [ ] owner-live RU layout/typography/mode/status/sidebar acceptance
      - [ ] owner-live EN mode/status/sidebar and no RU/EN leakage
    - [ ] owner-live Enable QUIC OFF/default persistence after reload/revisit
  - [x] already-accessible target — completed by owner confirmation
  - [ ] cancellation/internal-failure containment
- [ ] **Laboratory target support: test IP addresses as well as domains — NEXT PLAN after `_19` UI acceptance**
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

## Current priority — qualify/publish `_19`, live-check it, then add IP targets to Laboratory

Current source candidate: `v0.4.1_19` (`PLUGIN_REVISION=19`).

Last published testing identity remains `_18` until `_19` publication completes:

- tag: `v0.4.1_18`;
- asset: `os-zapret2-restyle-0.4.1_18.pkg`;
- SHA-256: `1ca82e1405c688a5429e1fd1d68da19906bea613323d8d01090bba85068b34f0`;
- source/tag target: `fa1b924a5c1d646f0daec13aff6e7406a534c6a3`;
- publication workflow run: `31889449879`;
- stable Pages/pkg repository promoted: no.

`_18` owner-live confirms the two requested labels and the one-line blocked-domain label, but rejects the 12 px typography workaround and resulting alignment. `_19` is the narrow corrective for normal typography, explicit alignment, mode/status translations and sidebar naming.

After `_19` publication/install:

1. RU live acceptance of layout/typography/mode/status/sidebar;
2. EN/no-leakage live acceptance;
3. Enable QUIC OFF/default persistence reload/revisit proof;
4. **next engineering plan: make Laboratory accept/test IP addresses as well as domains**;
5. continue the remaining backlog above.

Owner-live `_18` corrective evidence: [`verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_18-laboratory-ui-owner-live-followup.md).
Machine `_18` publication evidence: [`verification/evidence/testing-publications/v0.4.1_18.md`](verification/evidence/testing-publications/v0.4.1_18.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

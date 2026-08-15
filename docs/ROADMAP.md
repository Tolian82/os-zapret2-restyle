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
  - [ ] **Strategy Lab / Diagnostics RU-EN presentation completion**
    - [x] `_17` source/publication: circular idle ordinary display removes raw `{` / `}` / `{"state":"idle"}` JSON
    - [x] `_17` source/publication: RU `Состояние: ОЖИДАНИЕ` / EN `State: IDLE`
    - [x] `_17` source/publication: raw machine job JSON remains only under explicitly advanced output
    - [x] `_17` source/publication: `Full output (advanced)` / RU `Полный вывод (расширенный)`
    - [x] `_17` source/publication: HTTPS connectivity guidance RU/EN
    - [x] `_17` source/publication: `Family` / `Семейство`
    - [x] `_17` source/publication: `Endpoints` / `Назначения`
    - [x] `_17` source/publication: `Outcome` / `Результат`
    - [x] `_17` source/publication: `Restoration` / `Восстановление`
    - [x] `_17` source/publication: `Replay` / `Ответы`
    - [x] `_17` source/publication: `Complete Traffic Strategy profile` / `Полный профиль Стратегий Трафика`
    - [x] `_17` source/publication: `Run` / `Запуск`
    - [x] `_17` source/publication: `Test Domain Connectivity` / `Тестирование соединения с доменом`
    - [x] `_17` source/publication: EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`
    - [x] `_17` source/publication: `Enable QUIC` / RU `Включить QUIC`
    - [x] `_17` focused automated source contract covers RU/EN, circular idle, and persisted QUIC default/load/save
    - [x] `_17` latest-head full CI + FreeBSD-15 qualification
    - [x] `_17` exact-head source merge and persistent testing publication
    - [x] `_17` owner-live Russian review performed; most translations/circular idle PASS, remaining defects selected for `_18`
    - [ ] `_18` owner-selected corrective
      - [x] source: `Strategy Lab` / RU `Лаборатория стратегий`
      - [x] source: `Generic UDP (optional)` / RU `UDP порт (опционально)`
      - [x] source: one shared aligned value column for domain / Generic UDP / Enable QUIC
      - [x] source: small left shift and one-line RU `Заблокированный домен / IP`
      - [x] focused regression contract for new RU/EN labels and alignment while preserving `_17` contracts
      - [ ] latest-head full CI + FreeBSD-15 package qualification
      - [ ] exact-head source merge and persistent `v0.4.1_18` testing publication
      - [ ] owner-live RU acceptance of title/UDP label/one-line label/alignment
      - [ ] owner-live English mode and no RU/EN cross-language leakage
    - [ ] owner-live Enable QUIC OFF/default persistence after reload/revisit
  - [ ] already-accessible target
  - [ ] cancellation/internal-failure containment
- [ ] Circular lifecycle coverage
  - [ ] start/stop/TTL
  - [ ] stale-session recovery
- [ ] Settings Apply coverage
  - [ ] validation/guards
  - [ ] service-state correctness
- [ ] Diagnostics persistence/reload
- [ ] RU/EN presentation review beyond the current Strategy Lab corrective scope
- [ ] Retention/cleanup boundaries
- [ ] Reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up
- [ ] Package/runtime version visibility follow-up
- [ ] Additional BLOB repository GUI
  - [ ] wait for owner-supplied/approved technical contract

## Current priority — qualify/publish `_18`, then finish live RU/EN + persistence acceptance

Current source candidate: `v0.4.1_18` (`PLUGIN_REVISION=18`).

Last published testing identity remains `_17` until `_18` publication completes:

- tag: `v0.4.1_17`;
- asset: `os-zapret2-restyle-0.4.1_17.pkg`;
- SHA-256: `92d7d3320246380bef53c7d37364895315e12d55b958c8a5fd657ba9ab213dbf`;
- source/tag target: `ebf071122b2613c4fe56b5af4e5e9f07c99e9122`;
- publication workflow run: `31887296681`;
- stable Pages/pkg repository promoted: no.

`_17` owner-live Russian screenshots confirmed most deterministic translations and the circular-idle cleanup, but exposed the two remaining English labels plus the blocked-domain wrapping/alignment issue. `_18` closes exactly that visible scope without reopening Strategy Lab runtime/search semantics.

After `_18` publication/install, live acceptance must check the new Russian labels/layout, English/no-leakage mode, and separately prove saved Enable QUIC OFF/default persistence across reload/revisit.

Current evidence: [`verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md`](verification/evidence/2026-08-15-v0.4.1_17-ru-presentation-owner-live-followup.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

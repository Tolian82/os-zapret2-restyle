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
  - [ ] Enable QUIC OFF/default persistence across reload/revisit — source persistence contract exists; owner-live reload proof pending
  - [ ] **`v0.4.1_17` Strategy Lab / Diagnostics RU-EN presentation cleanup**
    - [x] source: circular idle ordinary display removes raw `{` and `}` / `{"state":"idle"}` JSON
    - [x] source: RU `Состояние: ОЖИДАНИЕ` / EN `State: IDLE`
    - [x] source: raw machine job JSON remains only under explicitly advanced output
    - [x] source: `Full output (advanced)` / RU `Полный вывод (расширенный)`
    - [x] source: HTTPS connectivity guidance RU/EN
    - [x] source: `Family` / `Семейство`
    - [x] source: `Endpoints` / `Назначения`
    - [x] source: `Outcome` / `Результат`
    - [x] source: `Restoration` / `Восстановление`
    - [x] source: `Replay` / `Ответы`
    - [x] source: `Complete Traffic Strategy profile` / `Полный профиль Стратегий Трафика`
    - [x] source: `Run` / `Запуск`
    - [x] source: `Test Domain Connectivity` / `Тестирование соединения с доменом`
    - [x] source: EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`
    - [x] source: `Enable QUIC` / RU `Включить QUIC`
    - [x] focused automated source contract covers RU/EN, circular idle, and persisted QUIC default/load/save
    - [ ] latest-head full CI + FreeBSD-15 package qualification
    - [ ] exact-head source merge and persistent `v0.4.1_17` testing publication
    - [ ] live acceptance in Russian mode
    - [ ] live acceptance in English mode
    - [ ] verify no RU/EN cross-language leakage
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
- [ ] RU/EN presentation review
- [ ] Retention/cleanup boundaries
- [ ] Reboot/residue verification
- [ ] OPNsense runtime/service reliability follow-up
- [ ] Package/runtime version visibility follow-up
- [ ] Additional BLOB repository GUI
  - [ ] wait for owner-supplied/approved technical contract

## Current priority — publish `_17`, then RU/EN + persistence live acceptance

Current source candidate: `v0.4.1_17` (`PLUGIN_REVISION=17`).

Last published testing identity remains `_16` until `_17` publication completes:

- tag: `v0.4.1_16`;
- asset: `os-zapret2-restyle-0.4.1_16.pkg`;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- source/tag target: `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`;
- stable Pages/pkg repository promoted: no.

Generic UDP and explicit QUIC ON/OFF execution semantics remain owner-live accepted. `_17` does not reopen them; it implements the selected visible RU/EN/circular-idle cleanup and preserves the existing persisted Enable QUIC contract.

After publication/install, live acceptance must inspect both language modes and then prove the saved OFF/default QUIC value survives reload/revisit.

Current evidence: [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

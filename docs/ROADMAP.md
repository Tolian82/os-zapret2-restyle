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
    - [x] extend focused Generic UDP regression contract
    - [x] complete Strategy Lab corrective matrix
    - [x] FreeBSD-15 package build/inspection qualification
    - [x] exact-head source merge `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`
    - [x] persistent `v0.4.1_16` testing-package publication
    - [x] publication-record evidence generated; bounded docs reconciliation in PR `#246`
    - [x] owner-live: exact `udp-140.bin` fixture verified as **140 bytes** and immediately shown ready to send
    - [x] owner-live: exact 140-byte payload starts configured-UDP job `job.j09XUc`
    - [x] owner-live: Stage 80 shows port `53`, payload `140` bytes, endpoint `172.67.182.196`, direct no-reply observation and all three UDP candidate IDs
    - [x] owner-live: no-reply text explicitly does not claim the port is closed and candidate search still runs
    - [x] owner-live: Stage-90 service restoration and temporary process/rule cleanup visibly PASS
    - [x] owner correction: previous repeated size errors were caused by selecting ~140 KiB files, not a confirmed upload/filesystem defect; contract is `1..4096 bytes`
  - [x] Enable QUIC OFF execution semantics
    - [x] owner-live OFF run reports QUIC strategy search disabled
    - [x] independent Generic UDP candidate execution remains active with QUIC OFF
    - [x] tested OFF job still completes SUCCESS and Stage-90 restoration PASS
  - [ ] Enable QUIC OFF/default persistence across reload/revisit
  - [ ] **Strategy Lab / Diagnostics RU-EN presentation cleanup — owner-selected next implementation**
    - [ ] circular idle ordinary display: remove raw `{` and `}` braces
    - [ ] circular idle ordinary display: replace raw `{"state":"idle"}` with RU `Состояние: ОЖИДАНИЕ` / EN `State: IDLE`
    - [ ] keep raw machine JSON only in explicitly advanced/raw presentation if still needed
    - [ ] localize `Full output (advanced)` / RU `Полный вывод (расширенный)`
    - [ ] localize `Enter a domain and click Test to check HTTPS connectivity.` / RU `Введите домен и нажмите «Проверка», чтобы проверить HTTPS-соединение.`
    - [ ] `Family` / RU `Семейство`
    - [ ] `Endpoints` / RU `Назначения`
    - [ ] `Outcome` / RU `Результат`
    - [ ] `Restoration` / RU `Восстановление`
    - [ ] `Replay` / RU `Ответы`
    - [ ] `Complete Traffic Strategy profile` / RU `Полный профиль Traffic Strategy`
    - [ ] `Run` / RU `Запуск`
    - [ ] `Test Domain Connectivity` / RU `Тестирование соединения с доменом`
    - [ ] `Blocked Domain` -> EN `Blocked Domain / IP`, RU `Заблокированный домен / IP`
    - [ ] `Enable QUIC` / RU `Включить QUIC`
    - [ ] live acceptance in Russian mode
    - [ ] live acceptance in English mode
    - [ ] verify no RU/EN cross-language leakage
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

## Current priority — QUIC persistence + RU/EN presentation

`v0.4.1_16` remains the current published testing package from candidate-defining source merge `1a7baa7d1afee032170e654c6840cfb4e3b55ea2`.

Published identity:

- tag: `v0.4.1_16`;
- asset: `os-zapret2-restyle-0.4.1_16.pkg`;
- SHA-256: `819498c34ab4dacd34f38cb04cf353ed9b46633dbf8fc6b85f73d8d229deb415`;
- publication workflow run: `31882091770`;
- stable Pages/pkg repository promoted: no.

Generic UDP and explicit QUIC ON/OFF execution semantics are now owner-live accepted for the tested `_16` flows. The latest OFF screenshot proves the runtime gate itself: QUIC candidate search is disabled while configured UDP still runs all three current UDP candidates and the job restores cleanly.

What is **not** yet proven is persistence of the OFF/default value across a page reload/revisit. Keep that as a separate live row.

The owner has now selected the RU/EN/circular-idle cleanup above as the next implementation scope. The implementation must be reflected in `START_HERE`, `PROJECT_STATE`, this roadmap, and live evidence/matrix, then live-checked in both language modes.

Current evidence: [`verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md`](verification/evidence/2026-08-15-v0.4.1_16-quic-off-owner-live-pass-ui-followup.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

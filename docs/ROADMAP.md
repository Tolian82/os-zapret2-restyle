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
    - [x] owner-live Generic UDP file-selection path still FAIL; durable evidence recorded
  - [ ] **`v0.4.1_16` Generic UDP browser-to-job handoff correction — current source candidate**
    - [x] trace actual product transport: browser Base64 POST, not multipart upload directory
    - [x] identify `_15` browser ownership weakness: Run sampled native `input.files[0]` instead of retaining prepared payload
    - [x] stage selected file immediately on `change`
    - [x] retain filename, exact decoded byte count and Base64 in application-owned state
    - [x] display localized ready-to-send filename/byte evidence before Run
    - [x] Run consumes staged payload even if native file-control selection is later lost/reset
    - [x] retain defensive Run-time staging fallback when a native File is still present
    - [x] remove realm-specific `instanceof ArrayBuffer` assumption
    - [x] retain decoded `1..4096` byte and strict backend Base64 bounds
    - [x] add explicit job-local preparation error attribution including unavailable/not-writable job directory, temp-create, decode, chmod/move and state-record classes
    - [x] preserve exact port/payload control observation, no-reply semantics, candidate enumeration and cleanup
    - [x] extend focused Generic UDP regression contract
    - [ ] complete Strategy Lab corrective matrix
    - [ ] FreeBSD-15 package build/inspection qualification
    - [ ] exact-head source merge
    - [ ] persistent `v0.4.1_16` testing-package publication
    - [ ] bounded publication-record docs reconciliation
    - [ ] owner-live: selecting valid file immediately shows ready state + exact byte count
    - [ ] owner-live: exact 140-byte payload starts a new configured-UDP job
    - [ ] owner-live: Stage 80 shows selected port/payload/endpoints, direct observation and actual UDP candidate IDs
    - [ ] owner-live: any later filesystem preparation failure reports its explicit class
    - [ ] owner-live: no-reply UDP text does not claim the port is closed
    - [ ] owner-live: Enable QUIC OFF shows natural disabled wording
    - [ ] owner-live: remaining RU/EN presentation checks
    - [ ] owner-live: Stage-90 restoration and temporary process/firewall/socket/payload cleanup PASS
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

## Current priority — qualify and publish `v0.4.1_16`

The `_15` live failure is no longer being treated as an unspecified “upload folder” issue. Source tracing established that there is no server upload directory at the failing point: selected bytes are supposed to be read in the browser and Base64-encoded into the ordinary start POST. `_15` did not persist a prepared browser payload; Run depended on the native file control still exposing `input.files[0]`.

`_16` corrects that boundary by staging exact validated bytes at selection time and making the prepared state visible before Run. It also adds server-side preparation error classes so a real later owner/mode/permissions failure can be distinguished if one occurs.

Current gate: full corrective matrix → FreeBSD-15 package qualification → exact-head source merge → persistent testing publication → bounded publication record. Then owner-live checks only the materially changed UDP handoff rather than repeating accepted Model-C/QUIC baseline work.

Durable `_15` failure evidence: [`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

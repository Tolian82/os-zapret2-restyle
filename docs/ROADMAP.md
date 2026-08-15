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
  - [ ] **`v0.4.1_14` explicit Enable QUIC — current source task**
    - [x] persisted checkbox in Extended GUI, default OFF
    - [x] saved checkbox state survives page reload through model-backed API
    - [x] copy resolved value into immutable job-local state at launch
    - [x] OFF → explicit `disabled` QUIC skip
    - [x] ON → run QUIC candidates regardless of Stage-30 `quic_ipv4` control result
    - [x] remove capability-based execution gate from Python production QUIC runner
    - [x] remove capability-based execution gate from shell/reference QUIC runner
    - [x] keep Stage-30 QUIC precheck as diagnostic evidence only
    - [x] focused automated regression for enabled QUIC with mocked `quic_ipv4=closed`
    - [ ] merge/publish/install `_14`
    - [ ] owner-live: default OFF + persistence
    - [ ] owner-live: OFF → `skipped/disabled`
    - [ ] owner-live: ON on blocked-QUIC ISP → candidates execute, truthful `working` or `not_found`
  - [ ] **configured Generic UDP**
    - [x] retain payload bound `1..4096` bytes
    - [x] reject missing port/file pair before start
    - [x] reject oversized browser file visibly before clearing previous result / entering running UI
    - [x] keep backend authoritative size/Base64 validation
    - [ ] owner-live: 2–3 MB file produces visible `1–4096` error and no new job
    - [ ] owner-live: valid port + `1..4096` payload executes UDP branch (`working` or `not_found`, not `skipped`)
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

## Current priority — publish and live-verify `_14`

The owner changed the QUIC product rule after `_13` proved that the old capability gate skips QUIC when the ISP blocks ordinary QUIC. The new rule is intentionally the opposite: a blocked control path is a reason to allow bypass testing when the owner enables it.

`v0.4.1_14` therefore combines one coherent Strategy Lab input/execution scope:

1. **Enable QUIC** — explicit persisted opt-in, default OFF, sole QUIC execution gate;
2. **Generic UDP input UX** — preserve the strict 1–4096-byte payload contract but turn the old apparent no-op for large files into an immediate visible validation error.

The Stage-30 QUIC control probe remains useful diagnostic evidence, but it no longer has authority over Stage-80 candidate scheduling.

Source acceptance requires focused tests, the repository corrective matrix, FreeBSD-15 package qualification, exact-head merge and persistent testing-package publication under the normal GitHub delivery contract.

After `_14` is published, one owner-live Extended cycle may cover both enabled QUIC and valid Generic UDP if both inputs are intentionally configured. Separate quick checks still verify checkbox persistence/default and oversized-file visible rejection.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

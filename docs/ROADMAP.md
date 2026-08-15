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
  - [ ] **`v0.4.1_14` explicit Enable QUIC — current owner-live task**
    - [x] persisted checkbox in Extended GUI, default OFF
    - [x] saved checkbox state survives page reload through model-backed API
    - [x] copy resolved value into immutable job-local state at launch
    - [x] OFF → explicit `disabled` QUIC skip
    - [x] ON → run QUIC candidates regardless of Stage-30 `quic_ipv4` control result
    - [x] remove capability-based execution gate from Python production QUIC runner
    - [x] remove capability-based execution gate from shell/reference QUIC runner
    - [x] keep Stage-30 QUIC precheck as diagnostic evidence only
    - [x] focused automated regression for enabled QUIC with mocked `quic_ipv4=closed`
    - [x] complete corrective matrix + FreeBSD-15 qualification
    - [x] exact-head source merge `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`
    - [x] persistent testing package `v0.4.1_14` published and verified
    - [x] machine publication evidence recorded
    - [ ] owner install `_14`
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

## Current priority — owner-live `_14`

`v0.4.1_14` is now persistently published as a FreeBSD 15 testing package from candidate-defining source merge `df20ed2ebe7f6c37c4189008e06e80700ae89ce4`.

Published identity:

- tag: `v0.4.1_14`;
- asset: `os-zapret2-restyle-0.4.1_14.pkg`;
- SHA-256: `b2df12f0af8ec6057f0df87e5289f89bc087664d7a0e2529c5e362e59db53d03`;
- stable Pages/pkg repository promoted: no.

Machine evidence: [`verification/evidence/testing-publications/v0.4.1_14.md`](verification/evidence/testing-publications/v0.4.1_14.md).

The owner’s QUIC rule is now implemented: **Enable QUIC is the sole execution gate**. Stage-30 QUIC probing remains diagnostic and cannot suppress Stage-80 bypass candidates.

Owner-live verification now needs only materially new behavior:

1. install `_14`;
2. verify checkbox default/persistence;
3. verify OFF gives `skipped/disabled`;
4. verify ON on the ISP-blocked ordinary-QUIC path actually runs candidates and gives truthful `working` or `not_found`;
5. verify a 2–3 MB Generic UDP file gives immediate visible `1–4096` validation without a new job;
6. verify a valid small Generic UDP payload actually runs the UDP branch.

One Extended run can cover enabled QUIC and valid Generic UDP simultaneously.

The publisher’s automatic Draft-PR creation was blocked by the repository setting that disallows GitHub Actions PR creation. The already-created machine publication branch/evidence was retained, and the mandatory publication-record PR was opened via the GitHub connector; this does not affect published package identity or bytes.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

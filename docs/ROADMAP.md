# os-zapret2-restyle — Master development plan

Status: **CURRENT / COMPLETE CONCISE PLAN**
Updated: 2026-08-14

Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md).
Exact revision handoff: [`START_HERE.md`](START_HERE.md).
Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).
Current-line detail: [`history/current/v0.4.x.md`](history/current/v0.4.x.md).

This file is the always-available short master plan. Every known future intention must appear here at
least once, but implementation detail, timings and proof belong in the current ledger/deep records.

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
- [x] Model A baseline
- [x] Model B testing
- [x] Model B parallel testing
- [x] Model B production integration
- [x] Model C testing
- [x] Model C production integration
- [x] Source-port attribution/leasing
- [x] Adaptive budgets/readiness
- [x] Model C selected
- [x] Lua initialization measurements
- [x] BLOB startup/RSS measurements
- [x] BLOB common-set measurements
- [x] GET-4K discovery decision
- [x] Warm/readiness repeat verification
- [x] Three-level documentation memory
- [x] Release/README authority rules
- [x] Version-aware documentation rules
- [ ] Model-C-only production
  - [ ] remove B/A production fallback (`v0.4.1_13`)
  - [ ] owner-live Model-C-only regression
- [ ] Risk-selected Strategy Lab regression coverage
  - [ ] initial Zapret2 STOPPED state
  - [ ] Extended TLS 1.2
  - [ ] Extended HTTP
  - [ ] QUIC capability gating
  - [ ] configured Generic UDP
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
- [ ] Strategy Lab protocol/capability breadth
- [ ] Package/runtime version visibility follow-up
- [ ] Additional BLOB repository GUI
  - [ ] wait for owner-supplied/approved technical contract

## Current priority — `v0.4.1_13`

**Model-C-only production finalization.** Model selection is already closed.

Implement:

- make Model C the only normal production Stage-60 runtime;
- remove automatic production fallback `C -> B -> A`;
- keep Model-C infrastructure failures explicit and bounded;
- preserve planner/CandidateSpec/ResourceInventory semantics;
- preserve source-port leasing/attribution, profile-compatible segmentation and readiness;
- preserve adaptive budgets, GET-4K discovery, cleanup/cancellation and Stage-90 restoration;
- retain Model A/B only as reference/benchmark/test tooling.

Acceptance:

- no silent production B/A replay;
- explicit bounded Model-C infrastructure failure;
- correct cleanup, attribution and segmentation;
- complete Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS;
- one owner-live normal Model-C-only regression.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

## Version-stage transitions

- ordinary same-stage patch: keep third component and increment `_N`;
- genuine next development stage: increment/change the third numeric component and reset `_N` to `_1`;
- third-component change alone: **not** a full release;
- explicitly authorized second-component change: archive current state/line and perform a full release;
- full release inside the current second-component line: allowed when explicitly requested and does not
  itself authorize a second-component change.

The second numeric component never changes automatically.

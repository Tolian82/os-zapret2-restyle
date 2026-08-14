# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-08-14

- Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md)
- Exact revision handoff: [`START_HERE.md`](START_HERE.md)
- Documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
- Project-development rules: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
- Current-line detail: [`history/current/v0.4.x.md`](history/current/v0.4.x.md)

This is the concise master plan defined by `DOC-031`–`DOC-033`. Version and release semantics remain canonical in `DEV-027`–`DEV-040`.

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
- [x] Version-aware state/handoff/archive model
- [x] Four canonical rule domains (`DOC-*`, `DEV-*`, `CHAT-*`, `GH-*`)
- [x] Permanent rule IDs and bidirectional cross-reference integrity
- [x] Rule cancellation/replacement lifecycle without ID deletion/reuse
- [x] Remove obsolete duplicate quick-reference documents after reference migration
- [x] Context-first/SHA-scoped documentation cold-start optimization
- [x] Internal Markdown link/anchor integrity validation
- [ ] Model-C-only production (`v0.4.1_13`)
  - [x] remove automatic B/A production fallback from the normal packaged Stage-60 path
  - [x] keep explicit Model B/A reference/benchmark/test overrides
  - [ ] exact-head corrective matrix + FreeBSD-15 qualification
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

## Current priority — finish `v0.4.1_13`

Model selection is closed and the source change is defined: normal production Stage 60 routes through the Model-C-only owner, while Model B/A remain explicit reference tooling.

Current gates:

- run the complete Strategy Lab corrective matrix on the exact PR head;
- run FreeBSD 15 package qualification on that same head;
- squash-merge only the verified head;
- publish a persistent `_13` testing package only when testing-package delivery is requested;
- perform one selected owner-live normal Model-C-only regression;
- verify correct result handling, explicit no-fallback behavior, Stage-90 restoration, and absence of temporary IPFW/process/socket residue.

After the selected `_13` owner-live PASS, move to the accepted risk-selected Strategy Lab regression backlog rather than reopening historical A/B/C selection or closed Lua/BLOB/discovery/lifecycle experiments.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

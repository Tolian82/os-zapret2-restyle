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
  - [x] exact-head corrective matrix + FreeBSD-15 qualification
  - [x] exact verified head squash-merged to `main`
  - [x] persistent testing package `v0.4.1_13` published and verified
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

Model selection is closed. Normal production Stage 60 is Model-C-only in source merge `45ce19f8e4b37df31ea97af8b8d7900a866f81f5`, while Model B/A remain explicit reference tooling.

Completed delivery gates:

- complete Strategy Lab corrective matrix PASS on exact PR head `8e1af17ce4ccfaad4851329167b386741d0c9ee8`;
- FreeBSD 15 package build/inspection qualification PASS on the same head;
- squash merge to `main` complete;
- source CI run `31819116248` complete successfully;
- persistent testing prerelease `v0.4.1_13` published from the exact source merge;
- publication workflow run `31838633599` complete successfully;
- package `os-zapret2-restyle-0.4.1_13.pkg` verified as `FreeBSD:15:amd64`, SHA-256 `7a2f864aa14ba2170ca378954ab5421092b76aca79b7b1765b976de2f024797b`.

Remaining live gate:

- perform one selected owner-live normal Model-C-only regression on OPNsense using the published `_13` package;
- verify correct result handling, explicit no-fallback behavior, Stage-90 restoration, and absence of temporary IPFW/process/socket residue.

After the selected `_13` owner-live PASS, move to the accepted risk-selected Strategy Lab regression backlog rather than reopening historical A/B/C selection or closed Lua/BLOB/discovery/lifecycle experiments.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

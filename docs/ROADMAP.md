# os-zapret2-restyle — Master development plan

**Status:** CURRENT · COMPLETE CONCISE PLAN
**Updated:** 2026-08-15

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
- [x] GitHub-native patch/package delivery with candidate-defining source verification and mandatory publication-record tail
- [x] Model-C-only production (`v0.4.1_13`)
  - [x] remove automatic B/A production fallback from the normal packaged Stage-60 path
  - [x] keep explicit Model B/A reference/benchmark/test overrides
  - [x] exact-head corrective matrix + FreeBSD-15 qualification
  - [x] exact verified head squash-merged to `main`
  - [x] persistent testing package `v0.4.1_13` published and verified
  - [x] owner-live Model-C-only regression
- [ ] Risk-selected Strategy Lab regression coverage
  - [x] initial Zapret2 STOPPED state
  - [ ] Extended TLS 1.2 — **current selected row together with HTTP**
  - [ ] Extended HTTP — **current selected row together with TLS 1.2**
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

## Current priority — Extended TLS 1.2 + HTTP regression

`v0.4.1_13` Model-C-only production remains complete. Risk-selected Standard lifecycle coverage now includes both initial normal-service states:

- initial RUNNING: accepted on the `_13` owner-live Model-C-only matrix;
- initial STOPPED: `rutracker.org` Standard `job.5b97u9` completed `SUCCESS` with three stable working strategies and left the permanent Zapret2 service STOPPED; the post-job normal `dvtws2|zapret.*supervisor` process query was empty.

The owner explicitly accepted `job.5b97u9` as sufficient for the STOPPED row and stated that deeper telemetry/repeat testing of that same scenario would not add useful evidence. That completed row is not to be reopened by inertia.

Durable evidence:

- [`verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md).

The next selected row is one **Extended blocked-domain run** covering both TLS 1.2 and HTTP in Stage 80. This deliberately changes the tested protocol path instead of repeating already accepted Standard lifecycle behavior.

Required acceptance:

- use the unchanged published `_13` package;
- execute one normal Extended blocked-domain Strategy Lab job;
- require a truthful terminal job result;
- require TLS 1.2 and HTTP to be exercised for available finalists or explicitly reported/skipped according to the implemented result/capability semantics;
- preserve the normal lifecycle state after completion.

This is regression coverage, not a new package candidate unless the live row exposes an actual defect.

After this row is accepted, choose the next backlog row from current risk/evidence rather than mechanically repeating equivalent paths.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it
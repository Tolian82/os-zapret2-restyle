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
  - [x] Extended TLS 1.2
  - [x] Extended HTTP
  - [x] QUIC capability gating
  - [ ] configured Generic UDP — **current selected row**
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

## Current priority — configured Generic UDP regression

`v0.4.1_13` Model-C-only production remains complete. Accepted risk-selected live coverage now includes:

- initial normal Zapret2 RUNNING;
- initial normal Zapret2 STOPPED;
- Extended TLS 1.2 execution/result semantics;
- Extended HTTP execution/result semantics;
- QUIC capability gating when QUIC/IPv4 is closed.

The Extended protocol evidence came from `rutracker.org` Extended `job.TJlWoY`:

- terminal `SUCCESS`, one stable shortlist entry;
- Stage 80 `PASS`;
- TLS 1.2 executed two candidates and truthfully persisted `working=null`;
- HTTP executed two candidates and truthfully persisted `working=null`;
- all four temporary candidate runtimes reached ready/stable state and produced interception/endpoint evidence;
- Stage 30 classified QUIC/IPv4 as closed and Stage 80 reported `QUIC=skipped`;
- Stage 90 restored the normal Zapret2 service successfully;
- `UDP=skipped` because Generic UDP was not fully configured with a request payload file.

A protocol row does not require fabricating a successful bypass where the measured target/environment has none. For TLS 1.2 and HTTP, the regression contract is satisfied by real branch execution, truthful candidate outcomes, correct runtime attribution and normal completion/restoration.

Durable evidence:

- [`verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-model-c-only-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-initial-stopped-owner-live-pass.md);
- [`verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md`](verification/evidence/2026-08-15-v0.4.1_13-extended-tcp-quic-owner-live-pass.md).

The next selected row is **configured Generic UDP**. Required acceptance:

- use the unchanged published `_13` package;
- use Extended mode;
- supply both a valid UDP port and a 1-4096-byte request payload file so the request is classified as configured;
- execute the UDP branch rather than `UDP=skipped`;
- require a truthful `working` or `not_found` result with normal candidate/runtime cleanup;
- preserve the normal Zapret2 lifecycle state after completion.

This is regression coverage, not a new package candidate unless the live row exposes an actual defect.

After this row is accepted, choose the next backlog row from current risk/evidence rather than mechanically repeating equivalent paths.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it
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
    - [x] persisted checkbox in Extended GUI, default OFF
    - [x] saved checkbox state survives page reload through model-backed API
    - [x] copy resolved value into immutable job-local state at launch
    - [x] OFF → explicit `disabled` QUIC skip
    - [x] ON → run QUIC candidates regardless of Stage-30 `quic_ipv4` control result
    - [x] remove capability-based execution gate from Python production QUIC runner
    - [x] remove capability-based execution gate from shell/reference QUIC runner
    - [x] keep Stage-30 QUIC precheck as diagnostic evidence only
    - [x] focused automated regression for enabled QUIC with mocked `quic_ipv4=closed`
    - [x] merge/publish/install `_14`
    - [ ] owner-live: default OFF + persistence
    - [ ] owner-live: OFF → disabled semantics
  - [ ] **`v0.4.1_15` QUIC/UDP observability and Generic UDP live correction — published, live defect open**
    - [x] expose actual QUIC `tested` count and candidate IDs in ordinary Stage-80 RU/EN text
    - [x] Stage-30 RU/EN: `QUIC открыт` / `QUIC закрыт` plus separate QUIC-search enabled/disabled state
    - [x] keep Stage-30 measured QUIC state diagnostic-only; never use it as execution gate
    - [x] replace raw Stage-80 `working` / `not_found` / `skipped` / `disabled` fragments with natural RU/EN presentation
    - [x] deterministic RU/EN Enable QUIC help text
    - [x] preserve raw protocol enums in structured/advanced evidence
    - [x] replace browser Data-URL/File.size validation ownership with ArrayBuffer exact-byte validation and Base64 encoding
    - [x] exact 140-byte Generic UDP automated regression through Base64 decode/job-local payload metadata
    - [x] preserve decoded payload bound `1..4096` and strict backend validation
    - [x] configured Generic UDP direct control exchange uses exact search-epoch selected IP, destination port and job-local payload
    - [x] record selected endpoint/IP, port, payload bytes, reply/no-reply, timeout/return state and duration
    - [x] never interpret UDP silence as definitive `port closed`
    - [x] direct UDP no-reply never suppresses the bypass candidate loop
    - [x] expose actual UDP candidate count/IDs and winner/no-winner meaning in Stage-80 RU/EN text
    - [x] focused automated protocol-observability coverage added
    - [x] complete Strategy Lab corrective matrix
    - [x] FreeBSD-15 package build/inspection qualification
    - [x] exact-head source merge `a219161c901c663b56cac6757364d3bbd32766c7`
    - [x] persistent `v0.4.1_15` testing-package publication
    - [x] bounded publication-record docs reconciliation merged
    - [x] owner-live: Enable QUIC ON on blocked-control path shows four attempted IDs in ordinary Stage-80 output
    - [x] owner-live: Generic UDP file path still fails to reach configured UDP — defect recorded
    - [ ] investigate browser file input/change event and selected `File` ownership
    - [ ] verify ArrayBuffer read, actual byte count and Base64 value before start request
    - [ ] verify PHP/API receives the Base64 payload and forwards it through configd
    - [ ] verify launcher creates private job-local `udp-payload.bin` and `udp-port`
    - [ ] inspect OPNsense runtime/job directory owner/mode/permissions; test the owner's permissions hypothesis
    - [ ] verify Python Extended stage sees configured UDP when the job-local files exist
    - [ ] implement the minimal correction at the proven failure point and publish the next package candidate if source changes are required
    - [ ] owner-live after correction: exact/small UDP payload including 140 bytes starts normally
    - [ ] owner-live after correction: configured UDP shows selected port/payload/endpoints, control observation and actual candidate count/IDs
    - [ ] owner-live: no-reply UDP text does not claim the port is closed
    - [ ] owner-live: Enable QUIC OFF shows natural disabled wording
    - [ ] owner-live: remaining RU/EN presentation checks
    - [ ] owner-live: Stage-90 restoration and temporary process/firewall/socket cleanup PASS for the corrected UDP path
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

## Current priority — trace the `_15` Generic UDP live failure

`v0.4.1_15` is correctly published, and the latest owner-live `rutracker.org` Extended run proves the QUIC attempt-observability portion is active: ordinary Stage 80 shows all four attempted QUIC IDs. The same live cycle proves that the Generic UDP browser-to-job path is still broken: attaching a valid small file does not produce a configured UDP request and Stage 80 reports UDP as not configured.

Do **not** guess the root cause or immediately rewrite size validation again. Trace the real path end to end:

`file input/change -> selected File -> ArrayBuffer/byteLength -> Base64 start payload -> PHP/API -> configd -> launcher -> job-local udp-payload.bin/udp-port -> filesystem ownership/mode -> Python configured-UDP detection`.

The owner's suspicion that the file may not actually be uploaded/saved, potentially because of permissions on the runtime/job directory, is an explicit investigation hypothesis. It becomes a root cause only if live evidence proves it.

Durable evidence: [`verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md`](verification/evidence/2026-08-15-v0.4.1_15-generic-udp-file-selection-owner-live-fail.md).

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

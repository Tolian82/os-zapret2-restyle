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
  - [ ] **`v0.4.1_14` explicit Enable QUIC — owner-live follow-up**
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
    - [ ] owner-live: OFF → `skipped/disabled`
    - [ ] **prove real QUIC enumeration on blocked-control path: persisted/result evidence must show `tested > 0`; `QUIC=not_found` alone is not sufficient**
    - [ ] expose enough QUIC execution evidence in GUI/result output to make attempted candidate count/names observable without unpacking telemetry
    - [ ] Stage-30 RU/EN presentation: show measured `QUIC открыт` / `QUIC закрыт` (`QUIC is open` / `QUIC is blocked`) and separately show whether QUIC strategy testing is enabled, so a closed control probe never reads as an execution skip
    - [ ] localize Enable QUIC help text in RU/EN instead of always showing `When enabled, QUIC candidates are tested even when the control probe reports QUIC as blocked.`
    - [ ] localize Stage-80 QUIC result semantics; user-facing output must not expose raw `working` / `not_found` / `skipped` / `disabled` enums
  - [ ] **configured Generic UDP**
    - [x] retain payload bound `1..4096` bytes
    - [x] reject missing port/file pair before start
    - [x] reject oversized browser file visibly before clearing previous result / entering running UI
    - [x] keep backend authoritative size/Base64 validation
    - [ ] **DEFECT: owner reports a nominal 140-byte payload is rejected with the 1–4096-byte size error; reproduce and fix browser/API/backend size-contract parity**
    - [ ] add regression coverage for valid small payloads, including an exact 140-byte file, through browser read → Base64 → API decode → job-local payload
    - [ ] verify the configured destination port with the supplied payload before/alongside candidate testing and surface the measured direct UDP response state
    - [ ] UDP port verification must be protocol-aware: absence of a UDP reply is not by itself proof that a port is closed, and a failed direct control exchange must not suppress bypass candidate testing
    - [ ] localize Stage-80 UDP result semantics; user-facing output must not expose raw `working` / `not_found` / `skipped` enums
    - [ ] owner-live: 2–3 MB file produces visible `1–4096` error and no new job
    - [ ] owner-live: valid port + `1..4096` payload executes UDP branch (`working` or `not_found`, not `skipped`)
  - [ ] **Strategy Lab Extended presentation/localization follow-up**
    - [ ] RU/EN coverage for new QUIC control text, measured QUIC state, Stage-80 QUIC/UDP summaries and related input/help text
    - [ ] preserve machine enums in structured/raw evidence while rendering human-readable localized text in the normal UI
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

## Current priority — close `_14` owner-live findings before the next protocol patch

`v0.4.1_14` is installed and the owner supplied Extended screenshots for `telegram.org` and `rutracker.org` with **Enable QUIC ON**. Both runs report Stage 30 control QUIC closed and Stage 80 `QUIC=not_found` rather than a capability skip. This is consistent with removal of the old gate, but it does **not** yet close the live execution requirement because the screenshots do not expose a non-zero QUIC attempt count.

The current QUIC catalog contains four candidates (`quic-fake-1`, `quic-fake-2`, `quic-ipfrag-8`, `quic-ipfrag-16`) and production code records each executed candidate under `tested`. The next implementation must make this execution evidence explicit enough to verify live behavior directly.

The same owner-live cycle identified two additional presentation/input defects:

1. raw English/internal QUIC and UDP status fragments still leak into the RU UI and the new Enable QUIC help text is not localized;
2. a payload reported by the owner as 140 bytes is rejected by the GUI with the size-range error even though the supported contract is 1–4096 bytes.

Generic UDP also needs an explicit destination-port/control-exchange check. Because UDP can legitimately be silent, the implementation must report what was actually observed (`response`, `no response`, or equivalent) rather than equating silence with a definitely closed port. This diagnostic must not become a gate that prevents bypass testing.

These items are now the selected follow-up boundary. A package-affecting implementation will get a new package revision; this documentation-only task registration does not change package identity.

## Deferred research — retain, do not activate by inertia

- [ ] candidate parallel width above three — only with new need/evidence
- [ ] endpoint-level parallelism — only with new need/evidence
- [ ] cross-batch keep-warm — only if accepted decision is invalidated by new evidence
- [ ] BLOB/Lua/discovery optimization — only after material architecture change/new evidence
- [ ] Model-C timeout/deadline audit — only when owner/plan selects it or a concrete defect requires it

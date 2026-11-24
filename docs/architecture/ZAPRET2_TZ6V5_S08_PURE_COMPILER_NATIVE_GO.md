# TZ6v5 S08 — pure target/resource/Voice compiler, native first-match and effective semantic diff: formal GO

**Decision 25 November 2026: S08 GO within its approved pure, nonactivating compiler/planner scope.** Exact accepted source [main `v0.6.5_195 2cb6b318`](https://github.com/Tolian82/os-zapret2-restyle/commit/2cb6b318321d024243c961422b2e79c6ed4280f2), four sequential merged PRs [#1311](https://github.com/Tolian82/os-zapret2-restyle/pull/1311), [#1312](https://github.com/Tolian82/os-zapret2-restyle/pull/1312), [#1313](https://github.com/Tolian82/os-zapret2-restyle/pull/1313), [#1314](https://github.com/Tolian82/os-zapret2-restyle/pull/1314). Current line issue [#1310](https://github.com/Tolian82/os-zapret2-restyle/issues/1310). This decision **does not** authorize Start/Stop/reload, Config, IPFW, manifest promotion, original FD9 operation or an owner-device installation.

## Acceptance evidence: actual original producers, not reimplemented engine behavior

| Accepted substep | Actual source/OPNsense evidence and boundaries |
| --- | --- |
| **S08a original target/profile parity** | [PR #1311](https://github.com/Tolian82/os-zapret2-restyle/pull/1311) exact source `v0.6.5_192`, original `target_mode.sh::target_mode_policy` and `registry.sh` with 3 modes × 4 profile cases **exact-byte parity**, canonical `profile_policy` expansion, explicit targets override defaults, no hidden `<HOSTLIST:auto>`. [CI #45482139242](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45482139242) SUCCESS. |
| **S08b authoritative prepared resources/Voice** | [PR #1312](https://github.com/Tolian82/os-zapret2-restyle/pull/1312), exact original 8-row `storage.sh` catalog + canonical `domain_policy.normalize`, `ipset_policy.parse_ipset`, `auto_detect_effective_known.compose_known`, `voice_profile_compiler.compile_candidate`. Manual empty versus independently owned Found data, missing active resource refusal, optional present-but-empty Auto, Exclude empty OFF/invalid FAIL, Voice OFF retains argument draft while prepared IPSet remains validated; Voice ON empty/invalid refuses. [CI #45485382156](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45485382156) SUCCESS. |
| **S08c actual final native args / source map / Voice IPFW / first-match** | [PR #1313](https://github.com/Tolian82/os-zapret2-restyle/pull/1313), **8 actual original** `orchestrator_build_release` products through existing P2e builder: Voice before Strategies, known YouTube/User working before eligible learning clones, exact native profile indices after Voice merge, ordinary managed IPFW **19000–19099**, canonical exclusion tails, List/All **no fabricated map**, altered argv/map/capture/identity refusal. Original `plan_learning_tier` plus independent `auto_detect_owner._valid_learning_proposal`. Important authentic RED: implicit Target Mode defaults include Telegram IPSet, so all expanded defaults are `excluded-ipset` and **must not** become known-list learning. Corrected **test expectation only**; production first-match unchanged. [CI #45489135401](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45489135401) SUCCESS. |
| **S08d deterministic structural fingerprint / semantic planner** | [PR #1314](https://github.com/Tolian82/os-zapret2-restyle/pull/1314), real **10-case original S03b** `orchestrator_build_release` outputs compared with new pure planner **within existing single disposable OPNsense 26.7 P2e VM**, no extra candidate builds. [Native P2e #45491313522](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45491313522) terminal SUCCESS with `S08D_ORIGINAL_GENERATOR_TEN_CASE_SEMANTIC_PLANNER=PASS`, `S03B_ACTUAL_OLD_GENERATOR_BASELINE=PASS`, and `S03B_RELOAD_SAFE_NATIVE_NOT_CLAIMED=1`. [CI #45491313840](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45491313840) **11 additional pure negative tests** and native official Mk build SUCCESS. |
| **Protected lifecycle/ABI regression** | Exact S08d-head [published `_107` protected native schema2→schema3 upgrade #45491313451](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45491313451) SUCCESS; Stage1 FreeBSD compatibility, PR title SUCCESS. No changed physical owner implementation. |
| **Merged main branch verified** | After S08d merge [main CI #45492640890](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45492640890) and [release classifier #45492640860](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45492640860) both terminal **SUCCESS** on exact `2cb6b318321d024243c961422b2e79c6ed4280f2`. Release trigger is classifier only, **not** public .pkg publication. |

## Observed S08d semantic matrix from the genuine original builder

| Scenario | Analytic result |
| --- | --- |
| Unchanged native candidate | `NO_CHANGE` |
| Only linked YouTube Domains content changed | `RELOAD_SAFE_CANDIDATE` |
| Only linked User Domains content changed | `RELOAD_SAFE_CANDIDATE` |
| Linked nonempty global Exclude Domains content changed | `RELOAD_SAFE_CANDIDATE` |
| Ordinary profile order changed | `RESTART_REQUIRED` |
| DPI arguments changed | `RESTART_REQUIRED` |
| Voice switched ON | `RESTART_REQUIRED` |
| Divert port changed | `RESTART_REQUIRED` |
| Target Mode `auto → list` | `RESTART_REQUIRED` **even though original native argv is byte-identical** |
| Global Exclude absent → nonempty (new native flag/ref) | `RESTART_REQUIRED` |

A separate pure test proves unlinked/disabled editor-only list changes can be `SAVE_ONLY` rather than claiming a reload. Structural SHA includes actual native argv hash, ordered original source map/selectors, mode, Voice/IPFW capture, saved and producer-resolved WAN, declared engine-version identity, exact linked refs and ordinary TCP/UDP. Mutable contents stay separate from structural identity. External/absent managed references, malformed or stale supplied proof, out-of-range IPFW and incomplete Auto source map refuse or conservatively require restart. Every result is immutable, `authorization=NONE`, `physical_transition_allowed=False`.

## Strict boundaries / carry-forward

- **Original first-match and engine syntax unchanged.** All new S08 modules are read-only detached Python projection/checkers. They neither call the original engine nor generate alternative `dvtws.args`; original `registry.sh`, `target_mode.sh`, `storage.sh`, `profile_policy`, native Voice producers, P1 destination ownership, `auto_detect_origin_map` and `auto_detect_owner` retain control.
- `RELOAD_SAFE_CANDIDATE` **is NOT** a SIGHUP, actual engine-file-reload, verified owner state or runtime operation receipt. Upstream Zapret2's documented HOSTLIST/IPSet reread/SIGHUP behavior is accepted as canon, never re-tested. **Later** original FD9/Config/epoch/PID/refs/CAS and atomic rollback must separately qualify any physical action. Found/managed live P1/CAS/ACK writes remain outside permanent immutable root content hash pins.
- The only qualified ordinary owned rule interval is **19000–19099**; Lab **19100–19131** and future comparative **19140–19200** remain separate. This stage does not claim native user-router live testing, installed production service acceptance, Traffic Strategy real provider success, S09 JSON manifest or a new root writer.
- Prospective `os-zapret2-restyle-0.6.5_195.pkg` was **built for CI qualification only**; it was **not publicly published or installed on the owner's OPNsense**. The documentation-only next `v0.6.5_196` is not an independently published package.
- Existing later work [Lab #1224](https://github.com/Tolian82/os-zapret2-restyle/issues/1224) (S15) and [Auto #1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223) (S16) is neither silently marked fixed nor included in S08. No pfSense implementation is included.

**Formal result: S08 — GO for the pure original-parity compiler + semantic planner.** The **next approved stage is S09 — root immutable JSON manifest + full attestation of generated references**, preserving single original FD9 and single Config owner, no second physical generator. [Ordered approved S00–S20](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). S09 not started at this decision.

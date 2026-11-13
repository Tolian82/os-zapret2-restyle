# P0 #1052: native Auto-detect isolation feasibility

**Status:** P0 COMPLETE within the bounded generated TCP/HTTP/IPSET/STUN feasibility scope. [Native generated run 43327217834](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43327217834), job `131562724779`, tested head `2393237a81d78ff51b9bea313acbf18aec0d280a` and tree `353d2ea0bbfd9f36f1db0a5f1a30f954d70bb0c9`; same tree merged as `b29de5ca7e9dd3e499d0b7423a8524de90259209` in [PR #1096](https://github.com/Tolian82/os-zapret2-restyle/pull/1096). [CI/native package run 43327217748](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43327217748) also passed. [Immutable execution receipt](https://github.com/Tolian82/os-zapret2-restyle/issues/1052#issuecomment-6838843832). The chronological prepared-source/failed-run descriptions below remain historical evidence, not the current stage status. No production Auto-detect or package publication.
**Authority:** [approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) and [plan P0–P5](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). The live user appliance, Config, original FD9, Voice, IPFW and Strategy Lab are not touched.

## Upstream v1.0.7 — verified source facts

- [Manual: profile ordering](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#using-multiple-profiles): first matching native profile wins. Dynamic L7/hostname information can cause re-selection.
- [Manual: lists](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#filtering-by-lists): `--hostlist-auto` causes its profile to match **any known hostname** passing other filters, regardless of the raw file contents. The engine does not apply its strategy until the hostname appears in its inclusion lists, but **after the auto append it can apply that same profile's strategy**.
- [desync.c lines 269–292](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L269-L292) implements unconditional selection of the auto-enabled profile for known hostnames; [lines 336–345](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L336-L345) implement first-match. This proves it is **unsafe to attach raw native auto detection indiscriminately to existing action profiles**, even if the file will later be rotated.
- [desync.c lines 469–489](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L469-L489): debug `adding to ...` precedes the in-memory insertion and physical append. Only confirmed raw data proves insertion. [helpers.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/helpers.c#L157-L165) appends with `fopen(filename,"at")` followed by `fclose`.
- [params.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/params.c#L332-L358) initializes an empty Lua action list, but auto retransmission TCP RST is **enabled by default**. [desync.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L395-L405) sends this RST unless disabled. [Lua dispatch](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L933-L950) is conditional on nonempty profile Lua actions.

**Source-level rejection:** Direct `--hostlist-auto` on an existing real strategy is **not passive logging** and violates explicit-only `<HOSTLIST:auto>` semantics. That implementation path is discarded before editing production.

## Current project pipeline (verified source)

[`target_mode.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/target_mode.sh) currently adds implicit `<HOSTLIST:auto>` with `auto`, as well as YouTube/User/Telegram. This must change later, but is not changed during P0. [`profile_policy.py`](../../src/opnsense/scripts/OPNsense/Zapret/backend/profile_policy.py) splits `--new` and expands multiple selectors into **ordered sequential native profiles**. [`profile_pipeline.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/profile_pipeline.sh) and [`targets.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/targets.sh) transform and resolve them; [`generator.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/generator.sh) combines them with final Voice/Extra/global exclusions. Native `--template` / `--import` can also affect effective identity. No persisted production generation-bound source/native attribution map for Auto-detect exists. The detached P0 implementation below now proves the portable capture/binding step without enabling it in production.

[`registry.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/registry.sh) resolves `<HOSTLIST:auto>` to ordinary `--hostlist` and [`storage.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/storage.sh) still uses the historic registry path `ipset/zapret-hosts-auto.txt`. The contract's **new** output `auto-domains.txt` must not be confused with that legacy path or native raw `inbox.txt`. None of these production paths are changed by this P0 probe.

## P0 candidate — **not approved implementation yet**

Investigate an **observer-only trailing profile within the same `dvtws2`**, after all legitimate action profiles, with `--hostlist-auto=<inbox.txt>`, **no `--lua-desync` options** and explicit `--hostlist-auto-retrans-reset=0`. This could collect previously unmatched hostnames without applying bypass actions after native inclusion.

This is **confirmed only for the scoped native loopback witness**, not as a general production implementation. A preceding broad profile could consume traffic first and prevent observation; moving an observer ahead could preempt an authorized profile and is forbidden. However, the GUI's `all` mode and `auto` mode are **mutually exclusive Target Mode choices**: a broad profile from `all` must **not** be projected into the default `auto` mode to manufacture a defect. Only an actual generated `auto` profile, including explicit selectors / `--new` or imported/native profiles, can establish a real coverage problem. Distinct known-list origin is established only from a **single unambiguous generation-bound mapping**, otherwise the shared fallback is mandatory. IPSET-only/mixed and Voice must not be silently included. Dynamic hostname/L7 jumps and template/import expansion also require separate P0 source/generator evidence.

## One bounded, real FreeBSD/OPNsense witness

[Native disposable test](../../scripts/test-p0-native-auto-observer.py) and [dedicated scoped workflow](../../.github/workflows/p0-native-auto-observer.yml) exercise **one** pinned upstream v1.0.7 `dvtws2` on localhost TCP/HTTP in an isolated OPNsense 26.7 guest. Required observation: legitimate first profile executes its existing Lua, unknown hostname goes to the trailing no-action observer, deliberate localhost failure generates a **real raw append plus correlated debug record**, and unknown HTTP reaches its test server unchanged both before and after native auto inclusion. Guarded bidirectional IPFW divert rules must be restored to identical initial state; the plugin must not be installed. No owner traffic or Strategy Lab operations.

**Evidence:** workflow [43302135750](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43302135750), native job `131475892342` succeeded; log reports `P0_NATIVE_AUTO_OBSERVER_SELF_TEST=PASS_SOURCE_ONLY` and `P0_NATIVE_AUTO_OBSERVER=PASS_NATIVE_LOOPBACK_OBSERVER_NON_ACTIVATING_ONLY`. The witness confirms a non-activating observer for its tested native HTTP/loopback conditions. This is not proof of full generator integration, all supported filters, real WAN bypass, a production package, or owner-appliance acceptance. Never treat `--dry-run` or an early debug line as packet-level proof. If the targeted native job fails, classify infrastructure versus genuine native behavior; do not repeatedly launch unrelated VM jobs or change production to match a test hypothesis.

## P0 source-identity audit: real accepted profiles (13 November 2026)

The actual target registry supports only `<HOSTLIST:...>` and `<IPSET:...>` selector placeholders. BLOB resources use **native** `--blob=name` shorthand and are handled later by `blobs.sh`; an isolated `<BLOB:name>` example cannot pass normal target resolution, so it must **not** be promoted as a valid broad-profile bug. No production Target Mode source change is justified by that example.

The scoped `v0.6.5_6` test extends the existing `scripts/test-profile-pipeline.sh` using the **actual parser, target_mode.sh and Python normalizer**, not a synthetic second policy: `all` preserves one broad source profile, `list` expands three permitted default selectors, and **as-is** `auto` expands four (including the still-legacy implicit ordinary `<HOSTLIST:auto>` that P3 must remove). Valid native `--blob=name` remains part of each source profile and is not a target selector.

A user-authored `--new` with explicit `<HOSTLIST:user>` bypasses default injection for **that source profile only**, and retains its position after expanded earlier profiles. Crucially, a source with **both** HOSTLIST and IPSET expands into separate final profiles; **a final HOSTLIST-only row is not proof the originating source was HOSTLIST-only**. The product must preserve generation-bound source identity when deciding whether native detection is allowed. This is actual source-pipeline evidence; full `dvtws.args`/native runtime and debug correlation remain separate P0 gates.

## P0 generation-bound attribution (13 November 2026)

This section records the prior source-only `_7` boundary; the `_8` native blocker and product correction are recorded below. The historically noninstalled [P0 implementation](p0_profile_attribution.py) (from P2d `v0.6.5_13` promoted as the single installed `backend/auto_detect_origin_map.py`, with the P0 file now a compatibility import) and [actual-generator witness](test_p0_profile_attribution.py) establish the next portable P0 boundary. Both live under `docs/verification/`; neither is packaged, called by production, or writes a service map. No production parser, Target Mode, registry, generator, Voice, GUI or Strategy Lab file changed. P2 must integrate the qualified capture with the original generator/FD9/atomic release owner only after the remaining P0 native gate passes.

**Preselected observable scenario:** a real source profile containing `<HOSTLIST:youtube>` plus `<IPSET:telegram>` reaches the original parser, Target Mode, normalizer, mapped target resolver, BLOB resolver, original Voice composer/generator and final global-exclusion pass. Its two final rows must retain the **same original source** and **IPSET ancestry**, so its apparent HOSTLIST-only row cannot acquire automatic HOSTLIST ownership. A stale generation or uncertain transformation must yield unknown/refusal, never a guessed known destination. This is an Auto-detect safety precursor, not GUI Apply or live detection acceptance.

**Executed red→green:** before the new map implementation existed, the mixed-source test completed that full pipeline and failed with `complete generator has no generation-bound attribution implementation`. With the implementation, the identical test and the focused nine-case suite pass locally in approximately six seconds:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 docs/verification/test_p0_profile_attribution.py
```

Output: `P0_GENERATION_BOUND_ATTRIBUTION=PASS_DETACHED_SOURCE_ONLY`. The CI documentation gate and the existing full-project gate execute this same suite; exact-head CI results remain separate from this recorded local result.

### Capture and fail-closed binding

- Capture original Traffic Strategy, per-source Target Mode output, Python-expanded profiles, individual resolver outputs, BLOB-resolved ordinary traffic, Voice/Extra composition, assembled and final argv **from one generation**. Use the existing canonical `profile_policy` splitter/expander and `global_exclusions` structural helpers; do not add a second profile parser or infer sources from file/domain/IP similarity.
- Check every normalization result against the originating source expansion, verify native selector substitutions against captured original registry/storage bindings and unchanged remaining arguments, and verify exact generated composition/order through the final exclusion overlay. Unexpected counts, ordering, inline native boundaries or modified artifacts refuse the map. Only exact generated HOSTLIST/IPSET exclusion tokens may move during that already-existing policy pass.
- Bind the result to a unique caller-supplied generation identity, complete final-argv SHA-256, original strategy SHA-256 and captured-stage digest. Even identical argv in a new generation receives different profile identities. Lookup refuses another generation, changed bytes, duplicate/missing numbers or invalid profile numbers.
- Preserve authored source ordinal/selectors, post-default IPSET ancestry and selected expansion branch separately. Default-injected IPSET ancestry is conservatively excluded too; this proof does not authorize any observer attachment. Two sources using the same HOSTLIST retain different identities. Global `--ipset-exclude` is an exclusion, not an including IPSET source.
- Voice/STUN are excluded; native raw list options do not acquire a guessed registry HOSTLIST. Extra Arguments before their first `--new` affect the last preceding profile and make its attribution unknown (or IPSET-excluded). New Extra profiles have no authored HOSTLIST origin. Any `--import` makes known attribution unknown because native `dp_copy` may replace targets. Template and skipped rows are nonexecutable.

### Native numbering evidence and its limit

Pinned upstream [v1.0.7 `nfq2/nfqws.c`](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/nfqws.c) establishes `IDX_NEW`/`IDX_SKIP`/`IDX_TEMPLATE`/`IDX_IMPORT` and finalization: templates are kept in a separate template list, skipped rows do not consume executable profile numbers, import copies profile state, and the engine appends its implicit low-priority `no_action` **profile 0**. The P0 map preserves those distinctions and the fixture covers a Voice prefix, template, skipped source, import, ordinary known list and named Extra boundary. Empty and Voice-only input are covered as separate cases.

This is **source-qualified numbering**, not a newly executed native engine claim. The map is conservative metadata, not a detector-eligibility or activation grant. This change does **not** claim protected production map publication, process/debug identity, raw-append correlation, safe observer placement, every native option's semantics, runtime hot reload, an installable package or owner acceptance. Those boundaries remain in the approved P0/P2 plan.

**Verification budget:** portable stage capture/map checks, the existing profile pipeline regression, documentation/identity/rule/link and CI-budget checks only. No product payload changed; no package build, extra native VM, historical laboratory matrix or stable-release publication is justified by this increment. The earlier native loopback witness is reused only for its original tested scope.

## Native-proven import blocker and bounded correction

The first generated native run [43325819019](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43325819019), job `131558044470`, reached the real pinned engine and failed at startup: `failed to register ipset .../managed/ipset-exclude.txt`. KVM, image, official package prerequisites and the native compiler succeeded; this is a demonstrated generated-argv defect, not an infrastructure failure or an observer result.

Pinned [v1.0.7 `ipset.c` registration](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/ipset.c) rejects another reference to an already registered realpath in the same collection. Native `IDX_IMPORT` copies the template collection. The original `global_exclusions.compose()` injected the generated global file into both the nonexecutable template and the final importing row, causing exactly that rejection.

The bounded repair stays in that original policy: remove the owned generated IPSET token from templates and append it once on each **executable** final row, after imports, preserving mandatory protection and unrelated user template exclusions. Domain exclusions already followed executable applicability. No second native parser, new Config/FD9/IPFW owner or observation bypass is introduced.

**Executed red→green:** the complete generated fixture's new `GENERATED_TEMPLATE_REIMPORTS_GLOBAL_IPSET_EXCLUSION` check fails on the old policy and passes with the repair. The original global-exclusion suite now checks nested imports, preserved user template filters, exactly one final generated filter, audit/idempotency and unchanged negative cases. The same real native witness must pass on the successor source; the failed run is never reclassified as PASS.

Because one shipped source file changes, the ordinary native package CI build is now required in addition to the one scoped P0 native scenario. The portable exclusion test no longer automatically launches both historical Stage 5 clean/RUNNING/reboot/resource campaigns; they retain explicit manual dispatch and genuine lifecycle triggers. This is a same-scope GH-069/072 workload correction, not removal of required native evidence. No package is published.

## P0 generated native exit gate

The [generated native witness](../../scripts/test-p0-native-generated-observer.py) reuses the existing actual-generator capture helper, original `voice_profile_compiler.compile_candidate`, canonical map and native disposable-host guard. It starts exactly one pinned engine on the final generated argv; no hand-replacement of native target/profile arguments and no installed plugin or Strategy Lab. The older two-profile native experiment is retained as historical evidence and is not repeated by this workflow.

Preselected native acceptance: actual profiles 1 (compiled Telegram STUN), 2 (known HOSTLIST), 3/4 (the same mixed source split HOSTLIST/IPSET), 5 (native import), 6 (trailing no-action observer), default 0; template/skip rows do not consume executable numbers. Separate local ports make the excluded and permitted scopes observable. Native `dp_find` hostname/L7/port search+match records must prove those selections, beyond startup banners. The Voice fixture intentionally has no Lua action; its real compiled STUN/IPSET selection and unchanged UDP request/reply are the scope, not real Telegram media acceptance.

Known/mixed/IPSET/default failing HTTP flows and the STUN exchange must leave raw discovery empty. Exactly one failed unknown HTTP connection in the observer scope must then append the raw hostname. The request must arrive unchanged before and after inclusion; the observer has no Lua/import/IPSET and explicitly disables retransmit RST. The confirmed raw record must match one native positive debug entry with observer number and actual client port, stable raw/debug dev/inodes, unchanged generated argv and the same running engine PID/start identity. Map lookup must return unknown for that observer and refuse a stale generation. Cleanup must restore exact initial IPFW rules and leave no engine.

Portable S0: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-p0-native-generated-observer.py --self-test` executes the full generated fixture; a separate non-FreeBSD invocation must refuse before mutation. These are source/host-guard proofs only. The scoped [native workflow](../../.github/workflows/p0-native-auto-observer.yml) first runs this fast gate, requires runner KVM/network readiness, then performs one bounded native scenario; workflow-only/docs/revision changes do not automatically launch it; the exact changed final-exclusion production file does because this witness qualifies its native import behavior. The workflow uses the already qualified pinned engine/OPNsense image and does not install the plugin or publish a package.

**Exit rule:** a successful exact-head native generated witness closes P0 feasibility for the bounded TCP/HTTP observation/attribution design and allows P1. A failing/skipped/infrastructure-blocked native gate keeps P0 open and blocks P1. The immutable execution receipt is recorded in [#1052](https://github.com/Tolian82/os-zapret2-restyle/issues/1052); this prepared-source section alone does not assert native PASS. Production capture/persistence, minute worker, full UDP/QUIC and GUI/package/owner acceptance remain P2/P5, without a claim of universal detection coverage.

## Status and next action

| Evidence | State |
| --- | --- |
| Upstream behavior and local generation source | **SOURCE CONFIRMED** |
| Native auto directly on an active action profile | **REJECTED AS UNSAFE** |
| Trailing no-Lua observer with RST disabled | **PASS: scoped native OPNsense loopback only** |
| Real OPNsense packet and native raw append | **PASS: workflow 43302135750, job 131475892342** |
| Detached full-generator source/selector/generation binding | **SOURCE VERIFIED: executed red→green witness; not installed** |
| Native generated-profile coverage / first-match and raw/debug attribution | **PASS: run 43327217834, job 131562724779; bounded generated TCP/HTTP/IPSET/STUN** |
| Later-stage implementation | [P1 canonical policy/source and package boundary](P1_AUTO_DETECT_DOMAIN_POLICY.md); P2–P5 open |

**Next:** follow the [current handoff](../START_HERE.md) and P1/P2 gates. P0 feasibility is complete; production observation/persistence, broader UDP/QUIC coverage, worker, GUI/restarts and final owner acceptance are not implied. No package was published.

# P0 #1052: native Auto-detect isolation feasibility

**Status:** P0 IN PROGRESS. Upstream/local source analysis and one narrowly scoped genuine OPNsense native loopback packet-level witness **PASS** (workflow [43302135750](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43302135750)); generated-profile attribution and coverage still OPEN. No product implementation or package publication. Source-only candidate `v0.6.5_6`.
**Authority:** [approved specification](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_SPEC.md) and [plan P0–P5](../architecture/ZAPRET2_NATIVE_AUTO_DETECT_TARGET_MODE_PLAN.md). The live user appliance, Config, original FD9, Voice, IPFW and Strategy Lab are not touched.

## Upstream v1.0.7 — verified source facts

- [Manual: profile ordering](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#using-multiple-profiles): first matching native profile wins. Dynamic L7/hostname information can cause re-selection.
- [Manual: lists](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md#filtering-by-lists): `--hostlist-auto` causes its profile to match **any known hostname** passing other filters, regardless of the raw file contents. The engine does not apply its strategy until the hostname appears in its inclusion lists, but **after the auto append it can apply that same profile's strategy**.
- [desync.c lines 269–292](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L269-L292) implements unconditional selection of the auto-enabled profile for known hostnames; [lines 336–345](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L336-L345) implement first-match. This proves it is **unsafe to attach raw native auto detection indiscriminately to existing action profiles**, even if the file will later be rotated.
- [desync.c lines 469–489](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L469-L489): debug `adding to ...` precedes the in-memory insertion and physical append. Only confirmed raw data proves insertion. [helpers.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/helpers.c#L157-L165) appends with `fopen(filename,"at")` followed by `fclose`.
- [params.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/params.c#L332-L358) initializes an empty Lua action list, but auto retransmission TCP RST is **enabled by default**. [desync.c](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L395-L405) sends this RST unless disabled. [Lua dispatch](https://github.com/bol-van/zapret2/blob/v1.0.7/nfq2/desync.c#L933-L950) is conditional on nonempty profile Lua actions.

**Source-level rejection:** Direct `--hostlist-auto` on an existing real strategy is **not passive logging** and violates explicit-only `<HOSTLIST:auto>` semantics. That implementation path is discarded before editing production.

## Current project pipeline (verified source)

[`target_mode.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/target_mode.sh) currently adds implicit `<HOSTLIST:auto>` with `auto`, as well as YouTube/User/Telegram. This must change later, but is not changed during P0. [`profile_policy.py`](../../src/opnsense/scripts/OPNsense/Zapret/backend/profile_policy.py) splits `--new` and expands multiple selectors into **ordered sequential native profiles**. [`profile_pipeline.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/profile_pipeline.sh) and [`targets.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/targets.sh) transform and resolve them; [`generator.sh`](../../src/opnsense/scripts/OPNsense/Zapret/backend/generator.sh) combines them with final Voice/Extra/global exclusions. Native `--template` / `--import` can also affect effective identity. No persisted generation-bound source/native attribution map for Auto-detect exists.

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

## Status and next action

| Evidence | State |
| --- | --- |
| Upstream behavior and local generation source | **SOURCE CONFIRMED** |
| Native auto directly on an active action profile | **REJECTED AS UNSAFE** |
| Trailing no-Lua observer with RST disabled | **PASS: scoped native OPNsense loopback only** |
| Real OPNsense packet and native raw append | **PASS: workflow 43302135750, job 131475892342** |
| General source-to-generated profile coverage / first-match and attribution | **P0 OPEN** |
| P1–P5 implementation | **NOT STARTED** |

**Next:** inspect actual compiled `Target Mode=auto` profiles (including preserved explicit selectors, `--new` and any import/template semantics) and source→native attribution. Do not mistake a hypothetical `all`-mode broad-first profile for an `auto` defect. Close P0 only with bounded evidence for permitted observation/known-list attribution; if a genuine generated-`auto` incompatibility exists, report that exact reproducible blocker. Production remains untouched.

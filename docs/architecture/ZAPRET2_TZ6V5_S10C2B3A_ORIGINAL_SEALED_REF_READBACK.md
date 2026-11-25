# TZ6v5 S10c2b3a — one original FD9 source-to-final-seal readback

**Scope:** [S10 #1319](https://github.com/Tolian82/os-zapret2-restyle/issues/1319), approved [TZ6v5 §4.2](TZ_6v5.md) and [S10c2 §S10](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md). Baseline [merged S10c2b2 PR #1335](https://github.com/Tolian82/os-zapret2-restyle/pull/1335) at `v0.6.5_214`. This document describes a bounded source-only step, not S10 acceptance or physical execution authorization.

## Observable problem and actual original route

The already-qualified `neutral_shared_apply_source_gate.py` verifies raw original `traffic.input`, registered HOSTLIST/IPSET sources, original managed outputs, `dvtws.args`, Voice, IPFW profile numbers and Auto source-map **before** the original `auto_detect_origin_map.py` schema3 promoter and before `shared_apply_seal.py`. That first witness must remain tied to the original nonactivating argv; treating it as proof of the **later promoted and sealed** native bytes would leave an unverified gap.

In the same `zapret_service.sh::shared_apply_prepare_service`, after one original schema3 promotion when eligible, release mode finalization and exactly one original bundle seal, call the **same** `shared_apply_original_source_gate` with a private `--sealed` mode. The existing NUL-delimited original input and the PHP-produced Auto candidate digest remain unchanged; no duplicate input snapshot is written.

## Mandatory final source checks

- Recompare the original current source/owned P1 after-image to the actual `release/managed` bytes and read back unchanged candidate XML, traffic, registered storage and original Voice/IPFW native projections.
- For promoted schema3 Auto: use actual `dvtws.original.args` for S08c parity, compare actual `dvtws.args` SHA against the S08c proposed SHA, and call the existing **original** `verify_learning_promotion()` for active native map, its original candidate SHA, profiling/order and output bytes. Do not synthesize postpromotion argv or a second source-map.
- For All/List: no original Auto source-map, no silent learner, no postpromotion old argv; reject unexpected native Auto artifacts. In unpromoted Auto, only verify nonactivating original bytes, never claim a running learner.
- Require `shared_apply_seal.verify_seal()` of the original whole bundle before/after typed checks, pinned exact `bundle-seal.json` bytes and final argv readback. Absent/tampered seal, moved original refs, unexpected sibling/second/pending root or partial promotion refuses.
- Any failure remains existing safe `preflight-rejected=seal` after the one seal, before durable Apply/Config/P1/IPFW/service mutation. Result status is explicitly nonauthorizing (`authorization=NONE`, `physical_transition_allowed=False`).

## Proof and deliberate next boundary

The existing real-P2e original generator integration test extends to All/List/Auto × Voice ON/OFF final bundle seal and actual original schema3 promotion, with source/map/ref tamper, hash, collision and absent-seal negatives. The existing shell source contract asserts the original preseal and postseal calls on both branches, and the same NUL stream without user data in argv. Run the existing affected native CI gates only; no upstream reread experiments.

**Not implemented by S10c2b3a:** no positive manifest-bound `PREPARED→ACTIVATING` transition, no root/journal writer, no old-active physical promotion, no Config save, process/IPFW action, rollback or recovery claim. The existing original `manifest-unbound` fence stays closed. The next S10c2b3 substep must bind these final readbacks to the original journal, immutable sibling root and original native preimages **under the same FD9** before executing and proving crash-safe physical state changes. Full S10 remains OPEN/NO-GO until native physical verification.

## S10c2b3b same-source typed root connection (_216 candidate)

The existing postseal gate optionally emits the native parity and effective snapshot in memory from the same actual inputs, managed bytes, original argv, source map, Voice capture and ports. The engine version is a required independently qualified caller input for that typed path, not a guessed installed fact. The original root-stage module reuses the existing sealed refs and schema3 physical refs readers against the exact original PREPARED journal and native PHP candidate SHA. The detached result has no authorization. Source integration exercises existing sibling root writer and original journal binding, then asserts the existing activation refusal. Native FD9/PHP/engine identity is not simulated as an installed PASS; test version and journal details are fixture inputs. No installed invocation, Found-journal route or physical activation added. Exact-head CI pending.

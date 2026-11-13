# P4a — Strategies and Strategy Lab safe profile/handler help

**Candidate:** `v0.6.4_25` (source-only; not released). **Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). **Normative:** [approved P4 plan](../history/stages/strategies-2026-11-12/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md).

## User-visible increment

Bilingual OPNsense-profile UI help now explains the scope of native v1.0.7 in-profile `--payload`, `--in-range`, `--out-range` filters and their effect on **subsequent** `--lua-desync` instances. A separate `--new` profile is appropriate only for an independently matched profile, not merely a second handler. The Strategy Lab guidance instructs users to compare final replay evidence, protocol, endpoints, L7, target lists and preceding first-match profiles before transferring a result, and warns that tested HTTP/TLS is not proof of QUIC, generic UDP or a completed voice call. Existing saved strategies are never overwritten by the Lab.

Canonical upstream: [bol-van/zapret2 v1.0.7 manual](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md), **In-profile filters**, **Lua desync action**, and **Multi-strategy** sections. The examples here are descriptions, not a new parser or fabricated runnable recipes.

## Acceptance/evidence boundary

S0/S1 source regression contracts: `scripts/test-strategies-i18n.py` and `scripts/test-diagnostics-guidance-localization.sh`. One scoped native S2 installed Chromium RU/EN/Full Help/F5 check is relevant because existing Strategies GUI help changes. The Lab guidance and save/runtime behavior remain separate: this change touches only UI prose, source tests and docs, not any Lab runtime, Config writer, voice, FD9 or IPFW. Native product acceptance/owner A17 remains OPEN until the P4 bilingual examples, cache-only installed resource catalog and real Lab/help evidence are accepted. The `v0.6.4_25.pkg` artifact is not published; stable `v0.6.4_1.pkg` stays immutable.

## GH-071 G03 native workload routing (same PR)

The source-only P4 bilingual help changes share `general.volt` with the G03 setup buttons. This historically triggered an unrelated **75-minute disposable first-upstream-install G03 VM** on every help-only PR synchronization. [Initial _25 G03 run #43076483262](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43076483262) did pass, but did not test a changed installer. To avoid repeating it, the G03 workflow retains its fast frontend/setup source regressions and adds a fail-closed, read-only source-diff classifier before the expensive native job.

`scripts/g03_native_scope.py` compares **exact PR base/head** and masks *only* the bounded existing P3/P4 help dictionary/info section in `general.volt`. Native G03 still runs on any actual `setup.sh`, `setup_transaction.sh`, G03 fixture/progress-test change, any executable UI difference outside the help section, missing/ambiguous help boundaries, or deliberate `workflow_dispatch`. Unit self-tests include help-only SKIP and setup/unknown REQUIRE. The fixture does not modify Config or intercept the engine; its skip is explicitly **not a G03 product PASS**. The already-qualified installed P3 Chromium RU/EN Strategies check remains the relevant S2 check for this change. The permanent GH-071 policy and `scripts/test-github-workflow-budget.py` guard this routing.

## Exact native browser assertion added before P4a acceptance

The P3 disposable installed Chromium harness now **also** checks the actual P4 help rather than accepting earlier P3 EN/RU coverage as proof of new text. For both real root-user profile languages it opens Strategies and validates the native popup/full-help cycle on Traffic Strategy (`--in-range`/`--out-range`/conntrack) with entered settings unchanged, reads the actual rendered Lab-to-Strategy transfer information, then navigates to the authenticated **Diagnostics/Laboratory** page and validates the four localized help paragraphs and protocol-scope disclaimer. The final sanitized receipt includes explicit P4 help/Lab booleans. No Lab Run, Stop, candidate, Apply, Config or runtime mutation is performed by this new check. Actual P4a installed-CI PASS is conditional on an exact-head completed browser workflow; old P3 PASS does not establish these new assertions.

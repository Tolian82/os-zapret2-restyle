# P4a — Strategies and Strategy Lab safe profile/handler help

**Candidate:** `v0.6.4_25` (source-only; not released). **Feature:** [#936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). **Normative:** [approved P4 plan](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md).

## User-visible increment

Bilingual OPNsense-profile UI help now explains the scope of native v1.0.7 in-profile `--payload`, `--in-range`, `--out-range` filters and their effect on **subsequent** `--lua-desync` instances. A separate `--new` profile is appropriate only for an independently matched profile, not merely a second handler. The Strategy Lab guidance instructs users to compare final replay evidence, protocol, endpoints, L7, target lists and preceding first-match profiles before transferring a result, and warns that tested HTTP/TLS is not proof of QUIC, generic UDP or a completed voice call. Existing saved strategies are never overwritten by the Lab.

Canonical upstream: [bol-van/zapret2 v1.0.7 manual](https://github.com/bol-van/zapret2/blob/v1.0.7/docs/manual.en.md), **In-profile filters**, **Lua desync action**, and **Multi-strategy** sections. The examples here are descriptions, not a new parser or fabricated runnable recipes.

## Acceptance/evidence boundary

S0/S1 source regression contracts: `scripts/test-strategies-i18n.py` and `scripts/test-diagnostics-guidance-localization.sh`. One scoped native S2 installed Chromium RU/EN/Full Help/F5 check is relevant because existing Strategies GUI help changes. The Lab guidance and save/runtime behavior remain separate: this change touches only UI prose, source tests and docs, not any Lab runtime, Config writer, voice, FD9 or IPFW. Native product acceptance/owner A17 remains OPEN until the P4 bilingual examples, cache-only installed resource catalog and real Lab/help evidence are accepted. The `v0.6.4_25.pkg` artifact is not published; stable `v0.6.4_1.pkg` stays immutable.

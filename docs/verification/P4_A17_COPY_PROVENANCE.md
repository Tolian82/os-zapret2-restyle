# P4 / A17 — Strategy Lab RU/EN clipboard provenance and safe manual transfer

**Source candidate:** `v0.6.4_35` (not released). **Authority:** [approved P4 plan](../architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_PLAN.md) and [A17 in #936](https://github.com/Tolian82/os-zapret2-restyle/issues/936). **Status:** source change, exact-head CI/installed disposable OPNsense Chromium RU/EN not yet qualified. Real owner A17 acceptance is separately OPEN.

## Safety gap and product change

The Laboratory's existing complete-profile table displayed protocol, port, original profile text and its final replay counts. The `Copy profile` action previously showed the same generic success message even for saved, unverified replay results; historical records with only a candidate `strategy` fragment could also be copied under a label implying a *complete* profile. Neither action changed the configuration, but the user could mistake copied bytes for verified/applicable settings.

The existing client-side view now:

1. Labels the action **Copy full profile / Копировать полный профиль**. It copies only `item.profile` supplied by the existing Python shortlist authority, without changing bytes, parsing native grammar again or silently saving/applying anything.
2. Refuses to copy an older fragment-only `item.strategy` entry when no nonempty `item.profile` exists; the control remains visible but disabled with an explicit localized tooltip. The legacy fragment may still be displayed as historical diagnostic evidence, not silently promoted into a complete profile.
3. Carries the exact existing `profile_replay.verified === true` boolean alongside each displayed row (no new backend truth authority). A verified copy explicitly says that nothing was saved or applied; an unverified copy gets a **different** RU/EN warning rather than a success claim. Every result uses `.text()`, and actual configuration writes, WAN/Voice/FD9/IPFW and runtime remain unchanged.
4. Explains in the existing four-paragraph Strategy Lab guidance that copying is not transferring a handler: compare actual selected transport port, `--filter-l7`, HOSTLIST/IPSET, `--payload`, ranges, Lua and earlier first-match profiles. If adding just another Lua action for the same profile, insert scoped filters and `--lua-desync` *inside* it; use an independent `--new` only when a separate profile really is intended.

No clipboard-to-Config action, second profile parser, automatic strategy rewrite, new API/Config writer, or background download is introduced. The existing `Copy Job ID` and saved results workflow must remain unchanged.

## Evidence and remaining gates

- **S0/S1:** existing `scripts/test-strategy-lab-structured-results.sh`, `scripts/test-diagnostics-guidance-localization.sh`, all usual source/CI gates; add guards for real complete-profile origin, verified/unverified copy messages, and nonmutating guidance.
- **Installed disposable GUI:** extend the existing bounded `stage5-native-browser-wan.yml` / `scripts/p3-browser-i18n.py` authentic OPNsense logged-in profile browser check to read both RU and EN Strategy Lab copy guidance; retain native popup/Full Help, F5, unsaved value and Voice checks. No dummy user results, no invented live job and no overriding the GUI locale.
- **Owner A17 (OPEN):** in the owner's actual installed GUI, review a genuine completed Lab result and an unverified saved result, verify copy-only feedback, then manually transfer an action versus independent `--new` while preserving all unrelated profiles and shared Voice and ensuring normal Restore/Apply. This step may require later qualified native package from P6.

**Not proved by this PR:** physical owner acceptance, real ISP DPI bypass, all L7 handlers, Voice call success, P5 read-only Preview or P6 official `.pkg` qualification. No stable `v0.6.4_1.pkg` replacement is authorized.

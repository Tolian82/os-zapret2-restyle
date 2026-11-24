# TZ6v5 S08a — pure original Target Mode/profile parity precompiler

**24 November 2026 — candidate `v0.6.5_192`, FIRST S08 substep only; S08 overall OPEN.** Accepted base is [S07 formal native GO](ZAPRET2_TZ6V5_S07_NATIVE_XML_PROJECTION_GO.md) in [main `v0.6.5_191 74816f16`](https://github.com/Tolian82/os-zapret2-restyle/commit/74816f164190d7102d458b4d35ad673c94db2fe3). [S08 issue #1310](https://github.com/Tolian82/os-zapret2-restyle/issues/1310).

## Bounded source change / result

- New import-only pure `backend/neutral_target_compiler.py` consumes the S07 immutable `RequestedConfig` / registered `SourceId`, genuine strategy input bytes and the original installed `target_mode.sh::target_mode_policy()` source bytes. It **extracts default IDs from the existing shell source**, never stores a second hardcoded registry or independently implements profile parsing.
- Reuses actual `profile_policy.split_profiles`, `validate_syntax`, `_tokens`, `_supported` and `expand_profiles`. Preserves source profile numbering and selector ordering; explicit authored targets override default policy. `all` yields no defaults; original `list` and `auto` append the same YouTube / Telegram / User identities when no explicit selector exists. `auto` does **not** implicitly inject `<HOSTLIST:auto>`; an explicit selector is retained but does NOT on its own qualify an Auto learning event.
- Returns frozen `TargetProjection` / `TargetedProfile`, source policy hash, authored/effective identities and in-memory normalized bytes with `status=SOURCE_TARGETS_ONLY`, `authorization=NONE`, `physical_transition_allowed=False`. No native final `dvtws.args`, no source-map attestation, no root manifest, no runtime application.
- Strict refusal on invalid/missing Target Mode, unauthorized or forged typed input, unknown/duplicate target registry, unknown explicit selector, foreign placeholder, malformed/oversize/NUL strategy or changed/dynamic original default policy. The original shell policy cannot be silently substituted.

## Exactly scoped verification

S0 local executed: Python syntax and four synthetic policy/parser unit cases PASS; **native original-shell parity was SKIPPED locally**, not called PASS. Exact production-source test `scripts/test-tz6v5-s08a-native-target-parity.py` is added to the existing fast PR `journey` CI on Ubuntu: **12 genuine shell transformations** (three modes × default/explicit/mixed/empty) using the original `registry_build` and `target_mode_apply_all` on disposable test-owned files, compared byte-for-byte with the pure compiler, original Python normalizer and source profile indices; negative/error and no-hidden-learner cases. Its real CI conclusion is a gate, not presumed PASS. Only fast source/PR checks and the existing path-classified package qualification if required; no unrelated extra VM matrix or engine reload/restart tests.

## Explicit S08 completion boundary

This does NOT implement full S08: storage/Found/Exclude readiness, Voice OFF-draft/ON-invalid, actual two-tier learning/known User first-match source map, genuine native `dvtws.args`/Voice/IPFW parity, structural fingerprint or semantic planner still remain. Next implement them against current original `registry.sh`, `storage.sh`, `auto_detect_origin_map.py`, Voice producers and accepted S03 ten-case baseline; do not create a second runtime writer or change original physical behavior. S08 GO only after all ordered tests, with native first-match unchanged. S09–S20 remain separate.

**Never:** call a shell, create Config/FD9/journal/manifest, change dvtws2/PID/IPFW, infer selected OPT/TUN device, claim engine reload success, publish a testing .pkg or act on the owner's firewall in this substep.

## S08a accepted after original-source checks

[PR #1311](https://github.com/Tolian82/os-zapret2-restyle/pull/1311) exact head 54198753 merged to main c6c1670b; original shell 12-case [CI #45482139242](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45482139242), native protected _107 [#45482139342](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45482139342), postmerge main [CI #45483216982](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45483216982) and [classifier #45483216934](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/45483216934) SUCCESS. S08a GO, full S08 OPEN; [S08b next](ZAPRET2_TZ6V5_S08B_RESOURCE_VOICE_PARITY.md).

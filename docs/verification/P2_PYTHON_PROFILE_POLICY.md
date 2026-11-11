# P2 — Python profile policy with compatible shell entrypoints

**Scope:** owner-approved Feature #936, P2 partial implementation. Exact baseline `v0.6.4_10` main commit `9613871f46dcda85a15537682798a81bf315b18b`. P2 A06–A09 full acceptance **NOT YET COMPLETE**. No new native .pkg has been published.

## Ownership and boundaries

**One parser/normalizer:** `src/opnsense/scripts/OPNsense/Zapret/backend/profile_policy.py` is the only implementation of the existing **plugin profile boundary/placeholder grammar**; it does not attempt to parse native `dvtws2` options, Lua or templates. It uses the official upstream manual and existing `dvtws2 --dry-run` rather than fresh experiments on the engine.

**Shell wrappers:** `backend/parser.sh` exposes its unchanged three public functions (`parser_parse`, `parser_validate_placeholder_syntax`, `parser_index_placeholders`) and `backend/profile_normalizer.sh` exposes `profile_normalizer_normalize_all`. They resolve `BACKEND_DIR`/qualified `PYTHON_RUNTIME` and delegate; no AWK parser/selector policy remains. Source fixtures may explicitly provide Python through `PYTHON_RUNTIME`; installed OPNsense defaults to the existing `python_runtime.sh` qualification wrapper.

**No lifecycle change:** `profile_pipeline.sh`, `target_mode.sh`, `targets.sh`, `generator.sh`, `validator.sh`, one shared Voice+Strategies `dvtws2`, Config, FD9, WAN-first, IPFW and existing Apply/rollback remain under their established owners.

## Exact staged-file contract

| CLI and shell API | Input | Output or failure |
| --- | --- | --- |
| `parse` / `parser_parse` | user strategy → `traffic.input` | count on stdout, `profile-1.conf…N`, `profile-count`; blank strategy yields 0, no ghost files; native `--new=name` maps to `--name=name` |
| `validate` / `parser_validate_placeholder_syntax` | number and existing profile file | validates generic `<TYPE:NAME>` (without parsing engine CLI), field/profile/line error on stderr, no user content dump |
| `index` / `parser_index_placeholders` | existing profile | first-seen unique `TYPE<TAB>NAME` rows in staged metadata output |
| `normalize` / `profile_normalizer_normalize_all` | staged profiles and count after Target Mode | expands multiple unique HOSTLIST/IPSET selectors in first-use order, copies every non-selector line verbatim (multiple `--payload` and `--lua-desync` retained), writes count |
| error and rollback | invalid `--new`, placeholder, invalid staged count/file | refuses with nonzero status; existing profiles/count not replaced; prepared temporary files cleaned |

Python prepares outputs under a private workdir temporary directory and backs up current per-profile artifacts during replacement. No saved Config or permanent runtime state is edited. Caller already owns the candidate directory, shared Apply and FD9.

## Bounded tests

- `scripts/test-profile-policy.py`: Python parser/placeholder/index, zero strategy, CRLF, native names, first-use expansion, multiple payload/Lua handlers, idempotence, and rollback.
- `scripts/test-profile-policy-shell.sh`: real shell API entrypoints and staged-file consistency.
- Existing `scripts/test-profile-normalizer.sh` and `scripts/test-profile-pipeline.sh`: unchanged test scenarios using explicit source-fixture Python runtime. These cover Target Mode, mixed IPSET/HOSTLIST, named `--new`, zero profiles, managed references, generated order and consistency.
- Exact-head CI: Python syntax/unit, shell syntax/contracts, original pipeline tests, Voice regression, source-only native package build and relevant disposable GUI as the change classifier requires. Separately record results instead of presuming they passed.

## Still outstanding in P2

1. Detect prohibited duplicate **resolved** list-file references within the same native profile, accounting for symlink/realpath identity and include/exclude/type distinction; do not reject legitimate references in distinct `--new` profiles.
2. Review `--template`/`--import` interaction and ensure existing native `dvtws2 --dry-run` remains the final validation authority.
3. Complete actual A06–A09 acceptance criteria and regression evidence. This migration is a bounded engineering increment, **not** P2 or Issue #936 final acceptance.

**Status:** Python policy migration SOURCE CANDIDATE. No native-engine semantic re-tests requested, no test package published and no owner-installed appliance acceptance claimed.

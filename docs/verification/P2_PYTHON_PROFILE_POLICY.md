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

## `v0.6.4_12`: final-argv mapped resolved-list guard

- `validator_validate_build_mapped()` invokes `validator_check_resolved_lists()` **after** the final global-exclusion rewrite and mapped reference validity checks. It uses qualified `PYTHON_RUNTIME` and the existing `profile_policy.py check-lists` CLI. This is read-only and does not touch the generator, user Config, live FD9, IPFW or shared Voice service.
- For each native `--new` / `--new=name` profile, the Python guard checks explicit `--hostlist`, `--hostlist-exclude`, `--ipset`, `--ipset-exclude` file options by resolving mapped staging paths or static-root paths. It compares `realpath` only **within the same option collection in the same profile**. Duplicates, aliases, absent/unmapped/escaping list paths fail with structured code and profile/option/position metadata. Paths are not echoed in errors.
- Distinct profiles and include/exclude collections may reuse one file; distinct files inside one profile remain legal; ordered `--payload` / `--lua-desync` pairs are not interpreted or rewritten. `--template` / `--import` expansion remains entrusted to existing native `dvtws2 --dry-run`.
- `scripts/test-profile-policy.py` includes duplicate, alias, missing/escaping path, per-profile allowlist, two-handler preservation and real shell adapter/CLI cases. Separate exact-source CI and native/installed acceptance have not yet been established by this record. No `_12.pkg` published.

## `v0.6.4_13`: mapped generator-to-validator integration regression

- `_12` exact-head [CI #42979704963](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42979704963) succeeded with Python policy, existing profile pipeline, Voice regressions and OPNsense 26.7 source-only package qualification. `main` integration [PR #1044](https://github.com/Tolian82/os-zapret2-restyle/pull/1044): `ff349d5be37da7eb387671731cbce520bf1f56bd`. These are CI/source facts, **not** physical owner acceptance or a published `_12.pkg`.
- `_13` extends `scripts/test-profile-policy.py` (already run by the normal CI) to source the **real** `common.sh`, `ports.sh`, `generator.sh` and `validator.sh`. In a private temp candidate, it invokes mapped generator and full mapped validator, checks two sequential `payload`/Lua handlers (A08), allowed same-target separate profiles and their untouched order (A07/A09), blocked direct/alias/IPSET duplicates introduced by Extra Arguments (A06), and the `--new=name` last-profile scope. Valid include/exclude across profiles are not blocked. Every case snapshots generated/staged files before validation and requires byte-identical content afterwards.
- Separate source-order contract ensures mapped validator and global exclusion audit precede existing native `dvtws2 --dry-run` / readiness. It neither runs an isolated upstream semantic probe nor claims activation rollback: final native installed/apply evidence is still needed.
- Local S0 syntax and 10-scenario compatible mock shell/Python harness passed. **Exact-source `_13` CI is not yet claimed**; mock results do not substitute it. No `_13.pkg` published.

## Still outstanding in P2

1. Establish exact-head CI and native candidate-activation refusal/rollback evidence at mapped validator plus current `dvtws2 --dry-run` boundaries, including existing Voice and generated exclude handling.
2. Confirm real `--template` / `--import` integration without implementing a second native option parser.
3. Complete and record A06–A09 evidence and owner acceptance, then proceed to P3 localization. This migration is a bounded engineering increment, **not** P2 or Issue #936 final acceptance.

**Status:** `_13` mapped-validator regression SOURCE CANDIDATE, exact-source CI pending. No extra engine semantic experiments requested, no test package published and no owner-installed appliance acceptance claimed.

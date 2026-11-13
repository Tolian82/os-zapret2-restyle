# #1052 P2e — actual original common release-builder witness

**Development source candidate:** `v0.6.5_14`. P0/P1 complete; P2a–P2d merged. This is a *verification/integration gate*, **not** production collection or completion of P2.

## The missing proof after P2d

P2d introduced a read-only `auto-detect-source-map.json` generated during original `shared-candidate` compilation; P0 synthetic full-generator samples alone do not prove it survives actual `orchestrator_build_release()` (Target Mode, per-profile resolver, managed resources, canonical Voice staging, extra and global exclusion pass, final validator, nonactivating publisher). A native OPNsense 26.7 .pkg archive successfully compiling also does not prove the map is actually emitted.

The focused `scripts/test-p2e-original-shared-build.py` therefore invokes **the existing `orchestrator_build_release()` directly, not a reimplementation**, sourcing real `common/config/parser/registry/storage/targets/target_mode/profile_normalizer/profile_pipeline/exclude/blobs/ports/generator/validator/stage/orchestrator` modules. The test constructs one disposable candidate workdir, rendered config and Voice XML and static runtime resources; the normal original compiler owns all transformations and calls the P2d publisher. The test checks exact shared generation token and SHA of the final `dvtws.args` in the resulting source map, known explicit HOSTLIST, mixed HOSTLIST+IPSET with enabled native Voice, and auto Target Mode default with no known-list guessing.

**No service/Config/IPFW/FD9 or user runtime is touched.** The offline fixture stubs only the native interface resolver to local `lo0` and intentionally provides no `dvtws2` engine. It exercises the original common **build**, *not* actual installed FD9 Apply, native dry-run, live process start or network capture. The test checks no observer, no `--hostlist-auto`, no `auto-detect-generation.json` and no inbox writer was activated.

## Scope and gates

Fast S0: one short Python integration test using the real source+shell modules, in existing fast CI. Stage 1: existing standard version/docs/native policy and full Project/Voice source suite only as dictated by path classifier. S2 when proven necessary: **one** disposable OPNsense 26.7 guest run invoking this same isolated source test (not a historical Strategy Lab campaign), preserving no-service/no-IPFW/no-Config preconditions. No package is published; stable owner-installed `0.6.5_1.pkg` unchanged.

Any missing map is a safe refusal to attribute, not evidence that production Auto-detect works. Red original-build evidence must be addressed against actual generated files, not by inventing fallback mapping from argv filenames or turning on a collector. P2c still requires a separate schema=2 map containing a genuine observer, actual raw/debug generation and current owner proof; nothing in this test can satisfy those conditions.

## Remaining P2

After qualified native real-generator output, design and qualify a trailing no-action observer and the exact schema=2 owner+generation-bound raw/debug and complete FreeBSD FD-drained event correlation; only then idempotent domain ownership journaling, pending acknowledgement, and one-minute configd/cron activation. P3 shared fallback/explicit placeholder, P4 GUI/restart, P5 installed owner acceptance follow.

**State:** source and CI validation tracked in #1052; distinguish offline builder proof from native original FD9 process/traffic acceptance.
## Recorded qualification

The scoped [native OPNsense 26.7 run #43392107224](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/43392107224) completed successfully on exact PR source `84b82a9d2c6b93d483d0afb47c94c5375a0b911f`, before the `_14` merge `277ef0536b217841ab6728ae9561dbc4792fef01`. This qualifies the same isolated original-builder/map witness on FreeBSD. It does not establish an actual running FD9 owner, observer, raw/debug collection or pending acknowledgement. The subsequent observer/schema-2 worker boundary remains open under P2; this completed native qualification is not the next task.

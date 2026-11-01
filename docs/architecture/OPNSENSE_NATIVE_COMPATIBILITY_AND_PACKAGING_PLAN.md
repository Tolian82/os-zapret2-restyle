# Native OPNsense Packaging and Unified External Compatibility — Per-File Development Plan v1.3

**Authority:** [Approved technical specification v1.3](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md).
**Origin:** updated from previously prepared *Development Plan v1.0*, keeping five stages, ordered concrete steps, file mapping and fifteen increments while applying approved v1.1/v1.2/v1.3 refinements.
**Independent document revision:** `v1.3` here is exclusively the editorial revision of this development plan; the technical specification has its own independently assigned editorial revision. Neither is a GitHub source/package version. Document revisions are independent of root `VERSION`, `PLUGIN_REVISION`, `_N` GitHub commits, tags and releases: none of those events automatically renumbers this plan or specification, and a document-revision change does not itself version or release the plugin.
**Preparation baseline:** exact `main` `8339e9ddda16f6910344c26f798c62aca4306c5e`, `VERSION=0.6.2`, `PLUGIN_REVISION=5`; re-pin current `main` before implementation.
**Status:** owner-authorized Stage 0 source/CI audit now covers steps 0.01–0.16, with 0.14–0.16 mapped in the [pinned parent `_18` source audit](../verification/evidence/2026-11-01-v0.6.2_19-stage0-test-ci-scenarios.md); the [owner-executed read-only target witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) is retained; the new [pinned official repo-trust source gate](../verification/evidence/2026-11-01-v0.6.2_21-stage0-official-repository-trust-source.md) is retained, and [exact archived stable ELF native FreeBSD15.1 runtime qualification](../verification/evidence/2026-11-01-v0.6.2_22-stage0-published-private-elf-native-runtime.md) is retained; [single owner script](../verification/evidence/2026-11-01-v0.6.2_23-stage0-owner-isolated-catalog-and-elf-plan.md) was **executed successfully** with [target PASS evidence](../verification/evidence/2026-11-01-v0.6.2_24-stage0-owner-target-trust-and-elf-acceptance.md) now recorded in source `v0.6.2_24`. Stage 0 is **OPEN**, Stage 1 **BLOCKED**: actual target ABI, generic Python owner and installed package are observed, and official source signature-template defaults are now checked, but actual configured OPNsense signed-catalog acceptance and installed ELF execution **now pass owner-live**; [owner-executed official signing root match](../verification/evidence/2026-11-01-v0.6.2_26-stage0-owner-official-26.7-signing-key-pass.md) **PASSES**: the installed OPNsense trusted key exactly matches the independent official 26.7 release PEM and pinned core SHA-256, with no extra trusted or matching revoked keys. **Stage 0.08's configured-catalog/official root trust sub-gate is now PASS**; [FreeBSD15.1 actual `pkg` phase scheduling fixture/archived-hook provenance gate](../verification/evidence/2026-11-01-v0.6.2_27-stage0-real-freebsd-pkg-phase-scheduler.md) now **PASSES real VM CI** with strict limits, and a [new original archived four-hook/body real FreeBSD15.1 FD9 runner](../verification/evidence/2026-11-01-v0.6.2_28-stage0-historical-pkg-hooks-real-fd9.md) is **CI **PASS** with real FreeBSD15.1 native FD9, mocked external service/configd**. Historical script body/FD9 VM execution PASS; original installed predecessor provenance on isolated OPNsense is prepared but NOT VERIFIED; genuine installed old service, OPNsense successor package/build and target acceptance are still NOT VERIFIED. Owner approved v1.3 lifecycle requirements on 1 November 2026.
**Immutable:** `os-zapret2-restyle` package, `PLUGIN_NAME=zapret2-restyle`, internal service/configd `zapret`, `VERSION`, `PLUGIN_REVISION` policy and separate Zapret2 engine release manager. Published stable `v0.6.2` / `0.6.2_1.pkg` remains unchanged.

## Working rules and proof levels

At each step: pin current SHA; inspect real caller/source/test; state observable behavior; update target test; make minimal change; run fast local syntax/contract checks **before PR**; run relevant exact-head CI; reconcile changed current docs; merge only accepted branch and verify main. Steps are not individually mandated PRs: group inseparable changes into one working increment, and do not merge a broken intermediate package/runtime. Follow DEV-050–DEV-052 and current DOC/GH rules.

**A:** source/consumer contracts; **B:** actual native-built package, real metadata and qualified target environment; **C:** installed qualified OPNsense; **D:** owner WAN/live appliance. A/B never imply C/D. Owner IPv4-only stand has waived live IPv6; WAN A07/A08 and Voice media are not automatically reopened.

**Authorities:** official `Mk/defaults.mk` and `Mk/plugins.mk` own build; `pkg` using qualified **target OPNsense** repositories owns system package names/versions/origins; only `compatibility.json` owns qualified product ABI, FreeBSD package ABI, architecture, Python policy and capabilities. Stage 2 native build **must precede** broad Stage 3 Python migration. Stage 2 package is a qualification artifact, not the final acceptance package.

**Source markers:** NEW = proposed file not currently tracked; CHANGE = expected edit; REVIEW = scan and edit only if necessary; TEST = relevant test; BOUNDARY = unchanged functional behavior; DOC = current-document reconciliation. All steps below describe paths relative to repository root; the prefix `src/opnsense/scripts/OPNsense/Zapret/` is implied for named backend, setup and strategy_lab runtime files.

## Stage 0 — Audit and immutable baseline

**Result:** Complete path/line inventory, exact old-package baseline and qualified OPNsense dependency/provider map; **no production change**.

| Step | Concrete file / operation and check |
|---|---|
| 0.01 | Pin actual `main` SHA, `VERSION`, `PLUGIN_REVISION`, same-scope open PRs and current CI; fully read AGENTS, current handoff, canonical rules and v1.2 specification. |
| 0.02 | Enumerate all tracked files with mode/symlink information: `src/`, `pkg/`, `scripts/`, workflows, repository, documentation and root. |
| 0.03 | Search every tracked active file for `python3.13`, `python313`, `EXPECTED_PYTHON`, `PYTHON_BIN`, versioned shebangs, executable fallbacks, ABI literals and direct `proc_open` / `subprocess` calls; record exact line and justified fixture exemptions. |
| 0.04 | Trace `GUI → PHP → configd → shell → Python` and `zapret_service.sh → backend` including Voice, Lab, Targets, Extra Resources and native Python-independent Stop/Status. |
| 0.05 | Inspect `Makefile`, `VERSION`, `scripts/build-pkg.sh`, `scripts/build-pkg-repository.sh`, `scripts/verify-release-package.sh`, `repository/zapret2-restyle.conf` for duplicated package/ABI/manifest ownership. |
| 0.06 | Trace system package installs, stock FreeBSD repository toggles and backup names in `src/opnsense/scripts/OPNsense/Zapret/setup.sh`, `setup_launcher.sh` and `setup_transaction.sh`. |
| 0.07 | Classify actual Python, PHP, git, jq, luajit, pkgconf, gmake and other tools by runtime/CI-build/test/private/optional **and execution location**; identify system/target package providers. |
| 0.08 | **PARTIAL — owner appliance observed:** [witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) confirms product ABI 26.7 / version 26.7.8_1, `FreeBSD:15:amd64`, amd64, generic `python3` owned by `opnsense` and `python313` installed from OPNsense. The [official `OPNsense`/aux source signing-template contract](../verification/evidence/2026-11-01-v0.6.2_21-stage0-official-repository-trust-source.md) also has strict negative CI checks. The [owner's executed witness](../verification/evidence/2026-11-01-v0.6.2_24-stage0-owner-target-trust-and-elf-acceptance.md) now **PASSES** configured fingerprint-signed `OPNsense` catalog in an isolated database and reports eight remote provider candidates with origins/versions. **These are catalog candidates, not necessarily installed package providers**; native `PLUGIN_PYTHON` build is still untested. The [independent official 26.7 release PEM → pinned core fingerprint derivation](../verification/evidence/2026-11-01-v0.6.2_25-stage0-independent-official-26.7-key-check.md) is now verified in source and a read-only target comparison with ten offline negative cases is prepared. The [owner's actual local official-key verifier](../verification/evidence/2026-11-01-v0.6.2_26-stage0-owner-official-26.7-signing-key-pass.md) now **PASSES** `installed_key_matches_independent_official_reference=true`, `additional_trusted_keys=false`, `official_key_found_in_revoked=false`. Combined with prior configured catalog acceptance, **on-device independent official signing trust is verified**. Still OPEN: available-vs-installed provider provenance and actual native `PLUGIN_PYTHON` build/runtime acceptance. |
| 0.09 | **PARTIAL — actual installed predecessor is now `0.6.2_1`**, not historical `0.6.1_30`; see [witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md). Public `0.6.2_1.pkg` SHA/manifest/hooks are independently archived in CI. The [new actual FreeBSD `pkg` scheduler gate](../verification/evidence/2026-11-01-v0.6.2_27-stage0-real-freebsd-pkg-phase-scheduler.md) first checks exact old package SHA/manifest 4 hook digests, then measures `pkg` scheduler using **synthetic trace-only fixtures**. Real FreeBSD15.1 CI [PASS](../verification/evidence/2026-11-01-v0.6.2_27-stage0-real-freebsd-pkg-phase-scheduler.md) reveals **`pkg add -f` invokes new PRE/POST_INSTALL but NOT old PRE/POST_DEINSTALL** for synthetic trace fixtures; explicit `pkg delete` invokes the new PRE/POST_DEINSTALL. The [original historical 0.6.2_1 hook body + native FD9 fixture](../verification/evidence/2026-11-01-v0.6.2_28-stage0-historical-pkg-hooks-real-fd9.md) **PASSED real FreeBSD15.1 VM CI**, but mocks old/new service and configd. The [new read-only installed predecessor provenance gate](../verification/evidence/2026-11-01-v0.6.2_29-stage0-installed-predecessor-provenance-gate.md) checks archive/installed four-hook body equality and installed service bytes/mode/owner in a separately qualified OPNsense guest; seven offline unit tests pass, **guest not yet run**. The [native FreeBSD15.1 synthetic pkgdb-format gate](../verification/evidence/2026-11-01-v0.6.2_30-stage0-native-pkgdb-format-qualification.md) is added to test real `pkg info -R --raw-format json`, `pkg which -q`, installed scripts and modes with a private synthetic pkg database and inert hooks; five offline tests PASS and native synthetic pkgdb [CI #41296771422](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/41296771422) PASS (actual created archive and installed script bytes, owner and 0755 mode). It never installs the immutable released package. None of these constitute actual target OPNsense replacement or old deployed service FD9 acceptance. The [`_31` fail-closed predecessor manifest integrity gate](../verification/evidence/2026-11-01-v0.6.2_31-stage0-predecessor-manifest-integrity.md) now requires immutable archive-vs-installed `arch`/`origin` equality and exactly four approved lifecycle hook keys, refusing previously unqualified metadata or extra hooks even when ABI and four bodies match; offline/real native `pkg` CI is required. Actual installed old package complete byte equality and full native OPNsense replacement still OPEN. |
| 0.10 | **PARTIAL:** owner's [installed-mode witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) confirms `zapret_service.sh` mode 0755 and `os-zapret2-restyle-0.6.2_1` package ownership, against Git 100644; old builder's stage chmod explains present success. LH-05 still requires source Git 100755, all direct entrypoints and native installed pkg proof in Stage 2. |
| 0.11 | **PARTIAL:** the [owner witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) confirms installed private ELF SHA matches archived asset, FreeBSD 15.1 amd64 ELF loader and six required base soname files exist. A new [isolated native FreeBSD15.1 published-byte runtime gate](../verification/evidence/2026-11-01-v0.6.2_22-stage0-published-private-elf-native-runtime.md) checks actual loader, six sonames, HTTPS/HTTP3 feature advertisement and Chrome/ECH-off loopback parse for immutable `0.6.2_1.pkg` upon CI PASS. The [same bounded target witness](../verification/evidence/2026-11-01-v0.6.2_23-stage0-owner-isolated-catalog-and-elf-plan.md) now includes installed ELF digest, actual `ldd`, HTTPS/HTTP3 and Chrome/ECH-off loopback. [Owner target execution](../verification/evidence/2026-11-01-v0.6.2_24-stage0-owner-target-trust-and-elf-acceptance.md) **PASSES** actual installed ELF SHA, `ldd` six sonames, HTTPS/HTTP3 and `chrome150` ECH-off localhost argument parse. Real public TLS ClientHello/HTTP3-QUIC and independently established base-library providers remain NOT VERIFIED; missing base-file `pkg which` owner is not missing-file evidence. |
| 0.12 | **NEGATIVE/REFUSAL OBSERVED:** [owner witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) finds a regular 98-byte `FreeBSD.conf` **not matching old plugin template**, with **no plugin backup**, `pkg which` unowned. Classify as **foreign/unproven**, prohibit automatic restore/overwrite/cleanup or stock FreeBSD repository enablement. Preserve foreign file and seek provenance only if manual recovery later becomes necessary. |
| 0.13 | **DONE, source-only**: [Stage 0.13 exact-HEAD audit](../verification/evidence/2026-11-01-v0.6.2_16-stage0-hook-lifecycle.md) records all four hooks, FD9, old PRE_DEINSTALL without independent retry, configd worker SIGTERM and service Git `100644`; refer to binding **LH-01–LH-07** in spec `8. The [real FreeBSD phase scheduler fixture](../verification/evidence/2026-11-01-v0.6.2_27-stage0-real-freebsd-pkg-phase-scheduler.md) now PASSES actual FreeBSD15.1 CI and documents **no old deinstall hooks on `pkg add -f`**; it does not execute historical production hooks. [Unmodified archived historical four hooks with actual FreeBSD15.1 lockf/FD9](../verification/evidence/2026-11-01-v0.6.2_28-stage0-historical-pkg-hooks-real-fd9.md) now **PASS** eight sandbox scenarios with actual FreeBSD15.1 lockf FD9, but still do not exercise real installed OPNsense service. Actual installed OPNsense old-service ownership and new package replacement/FD9 remain NOT VERIFIED |
| 0.14 | **SOURCE AUDIT COMPLETE:** [pinned test/CI map](../verification/evidence/2026-11-01-v0.6.2_19-stage0-test-ci-scenarios.md) classifies `scripts/test_freebsd15_package_ci.py`, `test-freebsd15-package-ci.sh`, `test-package-lifecycle-restart.sh`, `test-package-cold-kernel.py`, `test-setup-release-selection.sh` and all four workflows. Retired manual manifest/Python expectations remain as *future migration work*, not CI changes in Stage 0. |
| 0.15 | **SOURCE AUDIT COMPLETE:** [N01–N09 finite scenarios](../verification/evidence/2026-11-01-v0.6.2_19-stage0-test-ci-scenarios.md) define positive/negative native evidence for install, RUNNING/STOPPED replacement, callers, Python/ABI, native Stop, private ELF, owned/foreign FreeBSD.conf, worker/PID/IPFW refusal. All unobserved target outcomes remain NOT VERIFIED. |
| 0.16 | **SOURCE AUDIT COMPLETE:** [pinned `_18` exact-source path/line map](../verification/evidence/2026-11-01-v0.6.2_19-stage0-test-ci-scenarios.md), dependency owners, published predecessor/package and private ELF SHA-256, permitted literal exceptions, scenario inputs and STOP register; accompanying complete tracked-tree JSON and archive artifacts are generated by already qualified Stage 0 CI. Target qualification is still OPEN. |

**STOP gate:** Missing qualified target repository/ABI, unknown production caller, missing old package contents, or ambiguous ownership.

## Stage 1 — Single machine-readable compatibility policy

**Result:** One `compatibility.json` authority and fast negative-tested validator; existing service behavior unchanged.

| Step | Concrete file / operation and check |
|---|---|
| 1.01 | **NEW** root `compatibility.json`: schema version, OPNsense 26.7 product ABI, `FreeBSD:15:amd64` pkg ABI, amd64, native Python policy (initial qualified 3.13 branch), capabilities and bounded exceptions. |
| 1.02 | **NEW proposed** `scripts/validate-compatibility.py` (or suitable existing validator): standard-library-only JSON structural and semantic check with actionable error categories. |
| 1.03 | Explicitly separate OPNsense product/plugin ABI, FreeBSD pkg ABI and architecture; support admitted same-ABI OPNsense and Python branch patch updates by capability, not automatic new branches. |
| 1.04 | **NEW proposed** `scripts/test-compatibility.py`: supported tuple plus invalid/missing JSON, wrong schema/product/package ABI, CPU, Python branch, capabilities and contradictory exception negatives. |
| 1.05 | If runtime needs policy, stage source-derived `/usr/local/share/zapret2-restyle/compatibility.json`; assert source/staged/installed semantic equality or SHA-256. |
| 1.06 | Define Python-independent early executable check; no use of future installed manifest during `+PRE_INSTALL` and no Python required to establish that Python is missing. |
| 1.07 | Define qualified target identity (real OPNsense product ABI or explicit target attestation) and actual pkg ABI probes; reject upstream Make fallback constants as standalone qualification. |
| 1.08 | Verify real Python package name/origin and generic `python3` link in target OPNsense repositories; official `Mk/defaults.mk` owns evaluated `PLUGIN_PYTHON`. |
| 1.09 | Add narrow static prohibition against competing production version/ABI tables; classify historical documentation, golden fixtures and reproducible CI version locks. |
| 1.10 | Wire policy validation into quick checks in `.github/workflows/ci.yml`, without changing the builder yet. |
| 1.11 | Run focused source regressions confirming current `zapret`, Voice, Strategy Lab, Targets, GUI and package lifecycle remain untouched in this stage. |
| 1.12 | Record schema, positive/negative check outcomes, target provider evidence and limited exceptions before Stage 2. |

**STOP gate:** Duplicated compatibility table, unvalidated ABI fallback, circular Python bootstrap, or unsupported platform accepted.

## Stage 2 — Qualified official OPNsense packaging BEFORE Python migration

**Result:** One authentic `Mk/plugins.mk` candidate `.pkg` with real target dependencies, complete files/modes/hooks and qualified private ELF. Candidate is a **build qualification**, not final package/release.

| Step | Concrete file / operation and check |
|---|---|
| 2.01 | Define reproducible **qualified OPNsense 26.7** target build environment and its official target system pkg repositories; do not equate stock FreeBSD15 VM with OPNsense. |
| 2.02 | **NEW proposed** `scripts/bootstrap-opnsense-build.sh` or bounded code in `scripts/build-pkg.sh`: prepare pkg, BSD Make, Python package and generic link, PHP and official build tools BEFORE Makefile evaluation. |
| 2.03 | Verify actual package providers/repositories and product+pkg ABI; never fake `opnsense-version`, manually create `python3` link or force `PLUGIN_PYTHON=313`. |
| 2.04 | Acquire complete unmodified official `opnsense/plugins` at `stable/26.7` including `Mk/`, `Scripts/`, `Templates/` and requirements; pin exact upstream commit SHA. |
| 2.05 | Stage root `Makefile`, `VERSION`, `pkg-descr`, four `pkg/+...` hooks, `src/opnsense/`, `src/etc/` into temporary official `security/zapret2-restyle/`; one exact project commit, no secrets/scratch. |
| 2.06 | Verify `PLUGIN_NAME=zapret2-restyle`, package `os-zapret2-restyle` (not `-devel`), project version/revision, license/maintainer, `PLUGIN_WWW` and project `PLUGIN_HASH` independent of upstream Git. |
| 2.07 | Evaluate native `Mk/defaults.mk` using real `/usr/local/bin/python3 -V`, confirm `PLUGIN_PYTHON`/`PLUGIN_ABI` against matrix before invoking package target. |
| 2.08 | **CHANGE** `Makefile` to declare correct target OPNsense `PLUGIN_DEPENDS`: all mandatory appliance runtime and engine-build prerequisites including justified `pkgconf`, `gmake`, `luajit` (not CI-only tools). |
| 2.09 | Validate each target repo dependency's real name/version/origin from pkg; no manual name→origin table or invented `version: 0`. |
| 2.10 | Fail closed for unavailable qualified target package, missing Python generic link or unsupported ABI; stock FreeBSD **system package installation** is not a target fallback. |
| 2.11 | **LH-05:** inventory source Git direct-service/rc/configd/hook modes and ensure `zapret_service.sh` Git `100755`, verifying real native `.pkg` and installed modes; no bespoke blanket chmod |
| 2.12 | Stage `src/etc/inc/plugins.inc.d/zapret.inc`, `src/etc/rc.syshook.d/{start,stop}/20-zapret`, `src/opnsense/service/conf/actions.d/actions_zapret.conf`, MVC, backend and templates without feature rewrite. |
| 2.13 | **LH-01/LH-06/LH-07:** stage four authoritative `pkg/+...` hooks through official `scripts-manual`, reject unexpected auto-hook addition, verify phase-available old/new files and restart-marker owner |
| 2.14 | Keep `scripts/build-curl-impersonate.sh` signed FreeBSD latest **private extraction only**; stage existing private binary, libs, licenses and launchers in `libexec/zapret2-restyle` without installing FreeBSD system package. |
| 2.15 | Inspect each relevant bundled ELF executable/library for architecture, ABI loader and dynamic shared-library requirements **against actual compatible target OPNsense providers**. |
| 2.16 | Run packaged private launcher locally on qualified target OPNsense: Chrome TLS profile, ECH-off and HTTP/3/QUIC capabilities where actually used; no uncontrolled WAN requirement. |
| 2.17 | Record signed source package and private binary SHA-256; rerun ELF/provider/capability gate whenever the signed latest artifact bytes change. |
| 2.18 | **LH-05:** compare exact Git modes (including source `zapret_service.sh` `100755`), native package/installed executable modes, direct calls, symlinks, configd/rc/templates, private asset and hooks. Do not accept blanket staging chmod or syntax-only proof |
| 2.19 | **CHANGE** `scripts/build-pkg.sh` to thin validation/staging/orchestrator calling native BSD `make package` from temporary `security/zapret2-restyle`; preserve CLI and `dist/` contract. |
| 2.20 | Delete old sed-evaluated Make parser, `dep_origin()`, fake dependencies, manual plist/manifest, and own `pkg-static create` from production builder in the same packaging scope. |
| 2.21 | Track exact upstream and project commits independently; ensure `PLUGIN_HASH` refers to project and resulting `.pkg` has correct owner website/identity. |
| 2.22 | Build native candidate; extract `.pkg` manifest, real deps/versions/origins, OPNsense/package ABI and exact package SHA-256. |
| 2.23 | **LH-01/LH-02/LH-06/LH-07:** observe **real pkg hook order** on qualified isolated OPNsense for clean install, exact supported predecessor RUNNING/STOPPED, forced reinstall/removal and interrupted retry. Verify incoming PRE_INSTALL sees OLD code (no future JSON/launcher) and refuses if old PRE_DEINSTALL cannot safely prove FD9/owner |
| 2.24 | **LH-04:** exercise packaged `configctl zapret status/start/stop/restart` and direct hooks; record watcher/worker identity, safe action reload and positive readiness without mandating SIGTERM; verify negative PID/worker ownership and no global Web GUI restart |
| 2.25 | **CHANGE/TEST** `scripts/test_freebsd15_package_ci.py` and `scripts/test-freebsd15-package-ci.sh`: require native builder/real target provenance, remove assertions demanding `python313` or hand-built manifest; keep versioned CI VM fixtures. |
| 2.26 | **REVIEW/TEST** `scripts/test-package-lifecycle-restart.sh`, `scripts/test-package-cold-kernel.py`: preserve lifecycle and kernel rollback safety with new package format. |
| 2.27 | Record Stage2 native candidate SHA, provider, ELF, files/modes/hook evidence; mark **not final** until Python Stage3 rebuild. |
| 2.28 | Retire obsolete old production packaging path and its old-expectation tests in same logical scope; no two active production package engines. |

**STOP gate:** Missing target package/link, wrong origin, unqualified OPNsense ABI, missing exec mode/hook, private ELF provider error or changed IPFW/service state.

## Stage 3 — Unify Python calls, setup dependencies and safety

**Result:** One validated Python policy across real callers; native safe Stop/Status under Python loss, bounded old FreeBSD.conf handling, final native package rebuild.

| Step | Concrete file / operation and check |
|---|---|
| 3.01 | Validate installed generic `/usr/local/bin/python3` provider and single `compatibility.json`; no production minor-version selection. |
| 3.02 | Implement at most one necessary shared shell interpreter contract under `src/opnsense/scripts/OPNsense/Zapret/`; `exec` rather than persistent wrapper, no second manager. |
| 3.03 | Early Python-free existence check; full Python policy/modules check before any Start/Apply/Config/IPFW mutation; preserve CLI/API error contracts. |
| 3.04 | **LH-02:** test actual predecessor hook and service FD9 inheritance, busy/inherited lock, cold journal/Status=2, signal ownership, PID/group, argv/stdout/stderr, timeouts and no recursive lock acquisition; fail closed on unknown owner |
| 3.05 | **CHANGE** `backend/targets.sh`, `backend/generator.sh` removing local python3.13 fallback while preserving HOSTLIST/IPSET/placeholder outputs. |
| 3.06 | **CHANGE/REVIEW** `backend/firewall.sh`, `backend/apply_runtime.sh`, `backend/orchestrator.sh` and actual caller shells; preserve atomic Apply/foreign IPFW refusal/rollback. |
| 3.07 | **CHANGE** `zapret_service.sh` Python selection only where needed, preserving one `dvtws2` and `configctl zapret` interfaces. |
| 3.08 | **LH-03:** provide Python-independent truthful native Status and bounded Stop for independently verified plugin-owned `dvtws2`/IPFW despite missing/broken/wrong Python; preserve FD9/signals and reject unknown/foreign/partial ownership without mutation |
| 3.09 | Implement truthful Python-independent `Status`/degraded diagnostics where feasible; never report healthy when interpreter is unavailable or contaminate machine stdout. |
| 3.10 | Negative tests: absent/wrong interpreter blocks dependent Start/Apply before mutation but never blocks ownership-safe native Stop; later failures retain same-operation cleanup. |
| 3.11 | **CHANGE** `setup.sh`: remove temporary stock FreeBSD repo activation and independently installing system dependencies; rely on qualified OPNsense pkg owner without changing Zapret2 engine version/source/compile. |
| 3.12 | Verify appliance engine-build tools including `pkgconf`, `gmake`, `luajit` still supplied through target dependency graph even though package CI may not need them. |
| 3.13 | Read-only detect plugin's old `/usr/local/etc/pkg/repos/FreeBSD.conf` override and matching saved backup; verify exact ownership and absence of later user edits. |
| 3.14 | Restore only **proven plugin-owned intact override** from exact valid backup atomically; on ambiguous/modified/foreign config leave user file and backup untouched, produce actionable diagnostic/refusal. |
| 3.15 | **CHANGE/REVIEW** `setup_launcher.sh`, `setup_transaction.sh` to common Python policy and unchanged FD9, cancellation, transaction rollback, engine build selection. |
| 3.16 | **CHANGE** `extra_resources_launcher.sh`; **REVIEW** actual `extra_resources_*.py`/`upstream_checkout_origin.py` Python subprocesses; reuse `sys.executable` for validated parent. |
| 3.17 | Run Extra Resources Lua/BIN Install/Remove/reconcile/SHA and interrupted-operation regression tests; no extra feature rewrite. |
| 3.18 | **CHANGE** `strategy_lab_python_launcher.sh`: remove `EXPECTED_PYTHON=3.13`, use matrix contract and preserve Lab deadlines/mode selection. |
| 3.19 | **REVIEW/CHANGE** actual `strategy_lab/*.sh`, `strategy_lab_*worker.sh`, `strategy_lab_python.py`, `strategy_lab_py/*.py`: one interpreter, `sys.executable` children, FD9/signals and Stage85/90/99 cleanup. |
| 3.20 | **REVIEW/CHANGE** actual Voice shell/Python launch paths including `backend/voice_profile_compiler.py`, `backend/voice_live_inspect.py`; preserve IPv4/IPv6 Exclude/Voice IPFW. |
| 3.21 | **CHANGE** `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php`: verified common Python command; preserve JSON and distinguish unavailable runtime from user validation. |
| 3.22 | **CHANGE** `src/opnsense/service/conf/actions.d/actions_zapret.conf` direct Voice/preflight/inventory Python actions; keep configd `zapret` namespace and response shape. |
| 3.23 | **REVIEW** other API controllers (`SettingsController.php`, `StrategyLabController.php`, `VoiceController.php`) for actual direct interpreter calls only. |
| 3.24 | **LH-01/LH-02/LH-04/LH-06:** REVIEW/CHANGE four hooks for actual phase-available files/dependencies, old PRE_DEINSTALL no-FD9-retry refusal, verified configd worker/readiness (stale/reused/multiple PID tests, no unrelated signals), restart-marker lifetime and safe RUNNING/STOPPED rollback. Never require new files in incoming PRE_INSTALL |
| 3.25 | Scan production shebangs, PHP, shell, Python for direct minor-version interpreter constants and unsafe fallbacks; preserve narrow historical/CI fixture exemptions. |
| 3.26 | **LH-01–LH-07:** real shell/PHP/configd/hook/shebang/Python consumer tests for argv/JSON, FD9, PID/group/signals and PID reuse, missing Python/module/link, unknown/foreign owner, no-mutation refusal, safe native Stop/Status and interrupted package marker/rollback |
| 3.27 | Rebuild through the **single official Stage2 native path** after all Python/setup changes; retest real manifest, hooks, modes, target ELF and record **new** final candidate SHA-256. |
| 3.28 | Run bounded isolated qualified OPNsense tests for service, Apply, Lab, Voice, Extra Resources and current-package RUNNING/STOPPED replacement; separate source, package and installed proof. |
| 3.29 | **CHANGE/TEST** stale checks in `scripts/test_freebsd15_package_ci.py`, `scripts/test-setup-release-selection.sh` and affected launch tests in same scope; do not disable old assertions without replacement coverage. |
| 3.30 | Re-scan complete production tree for independent version locks, misplaced dependency owners and unexpected changes; Stage3 exit only with verified safe native Stop and one interpreter contract. |

**STOP gate:** Unsafe early mutation, FD9/process/signal drift, Python loss blocks safe native Stop, foreign IPFW or user repo overwritten, or appliance engine build fails.

## Stage 4 — CI/repository contracts and bounded final acceptance

**Result:** One official native build across all package workflows, all AC-01–AC-10 evidenced for **one exact final post-Python package SHA-256**.

| Step | Concrete file / operation and check |
|---|---|
| 4.01 | Add full-tree path/version/ABI guards in `scripts/` and `.github/workflows/ci.yml`, narrow exceptions only; fail reintroduced hardcoded Python minor. |
| 4.02 | Validate matrix schema, source/staged hash, distinct product/pkg ABI, accepted patch updates and unsupported Python/platform negatives. |
| 4.03 | Verify target OPNsense repo/bootstrap before Make evaluation, exact unmodified official `Mk/plugins.mk` commit and separate project SHA/PLUGIN_HASH. |
| 4.04 | Inspect actual built `.pkg` identity, FreeBSD ABI, `pkg query` name/version/origin, no `version: 0`, and no parallel project package engine. |
| 4.05 | **LH-05/LH-07:** compare exact Git `100755` direct service mode → extracted native `.pkg` → installed executable modes, plus old/new paths, symlinks, four manual hooks, configd/rc/templates/private binary and packaged direct calls |
| 4.06 | Enforce target OPNsense ELF/loader/shared-provider and packaged private curl Chrome/ECH-off/HTTP3-QUIC tests for actual private binary hash. |
| 4.07 | **LH-01–LH-07:** verify real package hook phase/order and actual predecessor FD9/owner refusal, configd worker PID reuse/stale signal refusal, RUNNING/STOPPED markers/rollback, and Python-loss interpreter-independent safe Stop/Status without touching foreign IPFW/processes |
| 4.08 | Test legacy FreeBSD.conf residue with valid owned override/backup and changed/foreign/ambiguous cases: exact atomic restore or read-only refusal. |
| 4.09 | Inject deliberate invalid production Python minor lock, wrong ABI, fake pkg version/origin, contradictory matrix, missing generic link and missing private shared library; assert failures. |
| 4.10 | **CHANGE** `scripts/verify-release-package.sh` to validate extracted native package metadata, SHA-256 and provenance instead of inferred Makefile claims. |
| 4.11 | **CHANGE** `scripts/build-pkg-repository.sh` and `repository/zapret2-restyle.conf` to derive/render/verify actual ABI/URL while retaining Pages package index files. |
| 4.12 | **CHANGE** `.github/workflows/{ci,testing-package-delivery-ci,publish-prerelease,release}.yml`: every testing/stable/CI package uses one native `scripts/build-pkg.sh`; publishing authorization remains separate. |
| 4.13 | Run each modified test and quick local syntax/contract checks BEFORE PR; then exact-head relevant CI and FreeBSD/target OPNsense qualification, not a pretend live proof. |
| 4.14 | Fresh install of actual package in qualified isolated OPNsense: real dependencies/generic python3 provider, executable modes, hooks and configd integration. |
| 4.15 | Bounded old-package replacement in RUNNING and STOPPED modes with retained Config, correct service/IPFW state and forced reinstall/removal semantics. |
| 4.16 | Exercise real changed entrypoint categories (PHP, configd, shell, Python, Lab, Voice, setup, Extra Resources) plus cancellation/owner cleanup. |
| 4.17 | Refuse unsupported ABI/Python/link/module/matrix/private shared provider at earliest valid boundary without unauthorized Config/IPFW/user repo mutation. |
| 4.18 | Only if isolated target proof is insufficient, ask for **one consolidated** owner-appliance batch; owner IPv4-only stand does not re-open waived IPv6/WAN/Voice media. |
| 4.19 | Bind every accepted result to exact final after-Python package SHA-256 plus upstream/project/policy/private binary SHAs; rebuilt bytes invalidate affected older evidence. |
| 4.20 | Confirm no testing package, tag or stable Pages release published without owner authority; immutable `v0.6.2`/`0.6.2_1.pkg` untouched. |
| 4.21 | Reconcile current `START_HERE`, `PROJECT_STATE`, `ROADMAP`, `INDEX`, ledger and README only if actual accepted behavior/evidence changes. |
| 4.22 | Prepare final implementation report: source/upstream/env SHA, target repo providers, manifest, modes/hooks, private ELF, Python-loss safe Stop, FreeBSD.conf owned/foreign results and CI status. |
| 4.23 | Close AC-01–AC-10 individually with actual A/B/C evidence and explicit NOT TESTED cases; green job counts alone do not equal acceptance. |
| 4.24 | Declare completion only when all required criteria concern the **final post-integration package SHA-256**; source merge alone is not installation or release. |

**STOP gate:** Any required AC unverified, wrong package SHA, missing target provider, failed safe cleanup, or package described as published without authorized delivery.

## Fifteen ordered implementation increments

These are work packages, **not reserved `_N` version numbers**. Every merged source PR follows the next actual `PLUGIN_REVISION`; independent stages may be split but never leave non-functional `main`.

| Increment | Steps | Gate |
|---|---|---|
| I-00 | 0.01–0.16 | Full-tree baseline, old package and dependency owner map |
| I-01 | 1.01–1.05 | compatibility.json and schema |
| I-02 | 1.06–1.12 | Bootstrapping, negative guards, early CI |
| I-03 | 2.01–2.07 | Qualified OPNsense target bootstrap and official upstream |
| I-04 | 2.08–2.10 | Target repository PLUGIN_DEPENDS and real pkg origins |
| I-05 | 2.11–2.18 | Required files/modes/hooks and private ELF/providers |
| I-06 | 2.19–2.22 | Thin native builder, real .pkg and manifest |
| I-07 | 2.23–2.28 | Native lifecycle and retirement of old builder |
| I-08 | 3.01–3.04 | One interpreter contract, FD9 and signals |
| I-09 | 3.05–3.10 | Backend/service and Python-loss safe Stop |
| I-10 | 3.11–3.17 | Setup native pkg, residue recovery, Extra Resources |
| I-11 | 3.18–3.25 | Lab, Voice, PHP/configd and manual hooks |
| I-12 | 3.26–3.30 | Real consumers, integration and new native package |
| I-13 | 4.01–4.12 | CI/manifest/repository/workflow policy |
| I-14 | 4.13–4.24 | Bounded target acceptance, evidence and AC closure |

## Per-file lookup

| Existing paths / future files | Steps and expected change |
|---|---|
| `Makefile`, `VERSION`; **NEW** `compatibility.json` | Stage 1 schema, Stage 2 native `PLUGIN_PYTHON` and target OPNsense dependencies; preserve version source |
| `scripts/build-pkg.sh`; optional **NEW** `scripts/bootstrap-opnsense-build.sh` | Stage 2 verified target bootstrap, temporary complete official `opnsense/plugins`, one `make package` |
| `scripts/build-curl-impersonate.sh`, `scripts/check-curl-impersonate.sh`, `scripts/run-curl-impersonate.sh` | Stage 2 signed private artifact, target ELF/shared providers, Chrome/ECH/QUIC, exact hashes |
| `pkg/+PRE_INSTALL`, `pkg/+POST_INSTALL`, `pkg/+PRE_DEINSTALL`, `pkg/+POST_DEINSTALL` | LH-01/LH-02/LH-04/LH-06/LH-07: Stage 2 manual scripts and old/new phase qualification; Stage 3 FD9/worker/rollback; Stage 4 real lifecycle |
| `src/opnsense/scripts/OPNsense/Zapret/setup.sh`, `setup_launcher.sh`, `setup_transaction.sh` | Stage 3 native pkg instead of FreeBSD repo toggling; verified owner-only `FreeBSD.conf` restore/refusal |
| `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` | LH-05 Stage 2 Git `100755` → native package → installed mode; LH-02/LH-03 Stage 3 FD9, common interpreter, Python-loss safe Status/Stop |
| `src/opnsense/scripts/OPNsense/Zapret/backend/{targets,generator,firewall,apply_runtime,orchestrator}.sh` | Stage 3 real Python caller migration, same generated config and IPFW owner |
| `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python_launcher.sh`, `strategy_lab/*.sh`, `strategy_lab_py/*.py` | Stage 3 common Python, preserve Stage85/90/99 budgets/signals |
| `src/opnsense/scripts/OPNsense/Zapret/backend/voice_*.py` | Stage 3 only actual Python spawn changes, preserve Voice IPv4/IPv6/Exclude |
| `src/opnsense/scripts/OPNsense/Zapret/extra_resources_launcher.sh`, `extra_resources_*.py` | Stage 3 no Python version forks, same Lua/BIN and upstream checks |
| `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php` | Stage 3 common verified Python, truthful API JSON/errors |
| `src/opnsense/service/conf/actions.d/actions_zapret.conf` | Stage 3 direct Python commands, unchanged `configctl zapret` |
| `src/etc/rc.syshook.d/{start,stop}/20-zapret`, `src/etc/inc/plugins.inc.d/zapret.inc` | Stage 2 required exec/registration/hook semantics |
| `scripts/test_freebsd15_package_ci.py`, `test-freebsd15-package-ci.sh`, `test-package-lifecycle-restart.sh` | Stage 2/3 replace obsolete manual-manifest and `python313` expectations |
| `scripts/verify-release-package.sh`, `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf` | Stage 4 actual ABI and package SHA-256, preserve existing Pages package repository |
| `.github/workflows/{ci,testing-package-delivery-ci,publish-prerelease,release}.yml` | Stage 4 one native build route; testing/stable publication separately authorized |
| This plan and [approved v1.3 specification](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) | Plan is subordinate; implementation updates actual current facts/evidence only |

## Required v1.3 acceptance trace

| Spec gate | Required plan evidence |
|---|---|
| AC-01 verified Python, FD9/process/signal and native safe Stop/Status | 3.01–3.10, 3.26, 4.07 |
| AC-02 no independent production Python minor lock | 0.03, 3.18–3.30, 4.01 |
| AC-03 target OPNsense `pkg`, real manifests and appliance engine-build tools | 0.07–0.08, 2.01–2.10, 3.11–3.15, 4.04 |
| AC-04 one matrix, distinct ABIs and admitted patch policy | 1.01–1.12, 4.02 |
| AC-05 all packages via official `Mk/plugins.mk` and verified bootstrap | 2.01–2.28, 4.03/4.12 |
| AC-06 GUI/Voice/Lab/service semantics, ownership cleanup and old repo residue | 2.23–2.24, 3.05–3.30, 4.07–4.18 |
| AC-07 preserve project/packaging IDs, `zapret`, engine version policy | 0.01, 2.06, 3.11–3.12, 4.20 |
| AC-08 executable modes, four hooks, target-compatible private ELF and rollback | 0.10–0.13, 2.11–2.23, 4.05–4.08 |
| AC-09 CI rejects divergence and final/authorized published asset SHA | 4.01–4.14, 4.19–4.20 |
| AC-10 current docs and honest independent proof levels | 0.16, 4.13–4.24 |
| **LH-01** phase-available old PRE_INSTALL/owner refusal | 0.13, 2.13/2.23, 3.24/3.26, 4.07 |
| **LH-02** old PRE_DEINSTALL FD9/unsafe-owner refusal | 0.13, 2.23, 3.04/3.24/3.26, 4.07 |
| **LH-03** Python-loss truthful Stop/Status / foreign IPFW | 3.08/3.26, 4.07 |
| **LH-04** configd watcher/worker identity / PID reuse | 2.24, 3.24/3.26, 4.07 |
| **LH-05** Git `100755` / native pkg / installed executable | 0.10/0.13, 2.11/2.18, 4.05 |
| **LH-06** RUNNING/STOPPED marker / interrupted rollback | 2.13/2.23, 3.24/3.26, 4.07 |
| **LH-07** actual pkg/target hook order and package SHA-256 | 2.23–2.24, 3.26–3.28, 4.05–4.07 |

**Definition of done:** all LH-01–LH-07 and AC-01–AC-10 evidenced on the actual native-built target-qualified *final post-Python* `.pkg` with correct real target `pkg` dependencies, effective file modes, four manual hooks, target-compatible private ELF, Python-independent native Stop where safe, owned-only old repository cleanup, and AC-01–AC-10 evidence **bound to one exact final package SHA-256**. This plan is not proof of implementation, installation or release.

**Next execution step:** [Stage 0.14–0.16](../verification/evidence/2026-11-01-v0.6.2_19-stage0-test-ci-scenarios.md) already records **five old test contracts and four package workflows** as Stage 2–4 migration debt. The [one-shot owner OPNsense read-only witness](../verification/evidence/2026-11-01-v0.6.2_20-stage0-owner-opnsense-target-witness.md) is now EXECUTED and recorded; **do not repeat it**. The [pinned source trust gate](../verification/evidence/2026-11-01-v0.6.2_21-stage0-official-repository-trust-source.md) validates official main/aux fingerprint-template defaults in CI, **not** actual host trust. The [new exact-published-ELF native FreeBSD15.1 gate](../verification/evidence/2026-11-01-v0.6.2_22-stage0-published-private-elf-native-runtime.md) narrows the remaining runtime problem without touching the owner host. [Owner PASS](../verification/evidence/2026-11-01-v0.6.2_24-stage0-owner-target-trust-and-elf-acceptance.md) is now recorded for configured signed OPNsense catalog and actually loaded installed ELF. **Do not repeat** `_20` or `_23` owner tests. [Owner OPNsense installed official key PASS](../verification/evidence/2026-11-01-v0.6.2_26-stage0-owner-official-26.7-signing-key-pass.md) completes the 26.7 signing-root verification; **no repeat probe**. **Next:** the [new verbatim historical archived hook/body native FreeBSD15.1 FD9 test](../verification/evidence/2026-11-01-v0.6.2_28-stage0-historical-pkg-hooks-real-fd9.md) **now passes actual native FreeBSD15.1 CI** with a bounded old-body/FD9 proof. It extracts all four hooks from SHA-checked `0.6.2_1.pkg`, runs them with **real lockf FD9** and confined fake service/configd, checking RUNNING/STOPPED/refusal/failed Stop/marker cases; **not** actual deployed old service or `pkg` transaction. Prior [actual FreeBSD pkg scheduler](../verification/evidence/2026-11-01-v0.6.2_27-stage0-real-freebsd-pkg-phase-scheduler.md) confirms force-add omits old deinstall hooks only for its synthetic fixture. Then proceed to **qualified isolated OPNsense** real installed-service FD9, genuine native successor `pkg` paths (including normal upgrade), Python-loss Stop/Status, worker PID and remaining LH-01–LH-07. No owner gateway replacement. Generic FreeBSD mocks do not prove an actual OPNsense package replacement, and the owner's live gateway is prohibited for this test. Never modify the unproven `FreeBSD.conf`. Stage 0 OPEN, Stage 1 BLOCKED. No new package or production change is implied.

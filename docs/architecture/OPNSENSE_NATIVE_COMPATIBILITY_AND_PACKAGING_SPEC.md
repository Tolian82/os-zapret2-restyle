# Native OPNsense Packaging and Unified External Compatibility — Technical Specification v1.3

**Status:** OWNER-APPROVED intended contract, NOT YET IMPLEMENTED.
**Approval:** 1 November 2026; owner-approved v1.3 lifecycle-safety clarification of the standalone native OPNsense follow-up to completed IPv4/IPv6 / Exclude IPSet work and full v0.6.2 release.
**Project:** `Tolian82/os-zapret2-restyle`.
**Next implementation deliverable:** finish Stage 0.14–0.16 audit and target qualification under per-file plan v1.3. Stage 0.13 source audit is complete; this document alone does not authorize production changes, package publication or owner-appliance experiments.

This file is revised in place from v1.2 to v1.3; previous v1.0–v1.2 revisions remain available in Git history, with no second active specification. Revision history belongs in the [current-line ledger](../history/current/v0.6.x.md).

**Independent document revision:** `v1.3` identifies only the editorial revision of this technical specification. It is **not** the GitHub project/source version, `VERSION`, `PLUGIN_REVISION`, package revision, tag or release version. Advancing any GitHub/plugin version does not automatically advance the specification revision; editing or approving the specification does not automatically change the plugin version or publish a release. The specification revision changes only when its own content/requirements are deliberately revised.

## 1. Purpose and boundaries

Use the **official OPNsense plugin build system**, FreeBSD `pkg` dependency management, a single external-compatibility manifest and one unified, validated Python execution contract. Ordinary supported updates of external interpreters/packages must not require scattered feature-code rewrites. Audit the **entire active repository**; only change files that violate the contract or require a genuine integration adjustment.

This is a NEW approved technical specification. Former [issue #732](https://github.com/Tolian82/os-zapret2-restyle/issues/732) and closed/unmerged [PR #740](https://github.com/Tolian82/os-zapret2-restyle/pull/740) were cancelled **inside the previous dual-stack work**, not silently reactivated here. Do not change prior dual-stack acceptance or reopening rules.

**Not in scope:** rewriting Strategies, Strategy Lab, Voice, Targets, HOSTLIST/IPSET, Exclude, configd, service/IPFW logic, transaction/recovery semantics, the existing separately managed Zapret2 engine version process, or speculative pfSense adaptation.

**Dependency-provisioning boundary:** auditing and replacing the system-dependency acquisition block in `setup.sh` is explicitly in scope. Keep the existing choice of Zapret2 release, engine source acquisition, compilation and lifecycle/transaction behavior. The engine-version exclusion above does not preserve independent dependency decisions or temporary activation of a stock FreeBSD system-package repository on the appliance. Section 6 governs the replacement.

## 2. Immutable identities and governance

| Item | Binding requirement |
|---|---|
| GitHub repository | `Tolian82/os-zapret2-restyle` |
| Project and installed package | `os-zapret2-restyle` |
| BSD Make variable | `PLUGIN_NAME=zapret2-restyle` |
| Internal configd/service key | **`zapret`**, not `zapret2` |
| Project version | existing root `VERSION` alone |
| Package revision | existing `PLUGIN_REVISION` governance |
| Engine versions | existing independent Zapret2 engine acquisition/upgrade mechanism, unchanged |
| Current stable release | published `v0.6.2` and immutable `0.6.2_1.pkg`, untouched |

Follow [DEV-052](../PROJECT_PRINCIPLES.md), DEV-023, DEV-025–DEV-028 and DEV-050–DEV-051, and existing documentation/GitHub governance. Do not add legacy/migration-only product branches to this experimental project. Preserve atomic same-operation recovery, native ownership and cleanup.

## 3. Single authority for every external fact

| Authority | Responsibilities |
|---|---|
| FreeBSD `pkg` using the target OPNsense repositories | system package installation/update, dependency resolution, installed package names, actual versions and origins |
| Official OPNsense `Mk/defaults.mk` / `Mk/plugins.mk` | evaluated `PLUGIN_PYTHON`/`PLUGIN_ABI` and native staging, generated plist, package hooks, dependency manifest and `.pkg` |
| One root `compatibility.json` | validated supported OPNsense product ABI, FreeBSD package ABI, architecture, Python policy and necessary capability restrictions |
| Shared Python entrypoint | one fail-closed runtime interpreter policy across shell, PHP, configd, hooks, shebangs and child Python processes |
| CI | check the policy, exact packaging artifacts, exceptions, real changed execution paths and regressions |
| `VERSION` and `PLUGIN_REVISION` | our plugin identity only |

The matrix does **not** duplicate the installed `pkg` database. Existing obligatory platform metadata may be generated from, or mechanically verified against, the authoritative policy. Never create a competing independently edited constants table.

## 4. Compatibility manifest

### 4.1. Format and placement

Use one machine-readable JSON source (`compatibility.json` at repository root), with versioned schema, static validation and negative tests. If runtime requires it, copy or generate an identical installed representation from that source during native package staging, tentatively `/usr/local/share/zapret2-restyle/compatibility.json`; compare SHA-256 or full semantic equivalence. No hand-maintained PHP/shell/Python/CI duplicates.

Early install checks cannot require Python or files which do not yet exist. Validate build-time requirements in the build environment, and runtime policy at the earliest stage where its dependencies are actually present.

### 4.2. Supported dimensions and sample

Distinguish **OPNsense product/plugin ABI** (initially `26.7`), **FreeBSD package ABI** (initially `FreeBSD:15:amd64`) and **CPU architecture** (`amd64`). A FreeBSD minor release such as 15.0 or 15.1 is allowed as a reproducible CI VM selection, not as an independent product-wide compatibility constant.

Required fields: `schema_version`, `target_product`, `supported_platforms[]`, per-platform `opnsense_product_abi`, `freebsd_pkg_abi`, `architecture`, `python.policy`, `python.entrypoint`, `python.supported`, `required_capabilities` and documented, bounded `exceptions`.

Illustrative policy **schema only**, NOT a claim that all OPNsense 26.7.x or future Python versions are qualified:

```json
{
  "schema_version": 1,
  "target_product": "OPNsense",
  "supported_platforms": [{
    "opnsense_product_abi": "26.7",
    "freebsd_pkg_abi": "FreeBSD:15:amd64",
    "architecture": "amd64",
    "python": {
      "policy": "opnsense-PLUGIN_PYTHON",
      "entrypoint": "/usr/local/bin/python3",
      "supported": ["3.13"]
    }
  }],
  "required_capabilities": [],
  "exceptions": []
}
```

Only qualified combinations are permitted. A valid FreeBSD build does not prove installed OPNsense behavior or pfSense compatibility. Unknown and contradictory policy records fail with an actionable diagnostic.

### 4.3. Supported updates and qualification records

Express support at the ABI, interpreter branch and capability boundaries actually required by the code. Patch updates within an admitted OPNsense product ABI and Python major/minor branch do not require feature-source edits or a matrix edit solely because the patch number changed, provided required capabilities and any explicit centralized restrictions still hold. This is a compatibility policy, not a claim that every patch release was individually tested. A new Python branch, product ABI or other unsupported combination requires qualification before the matrix admits it.

Keep exact observed package versions, origins and environment identities in the build/verification report; do not turn the matrix into a duplicate installed-package database. Introduce a minimum/maximum patch restriction only for an evidenced compatibility need under DEV-052.

## 5. Official native OPNsense package build

### 5.1. Temporary upstream plugin tree

Preserve our existing GitHub layout. Build a disposable complete official `opnsense/plugins` tree for the matching supported line (initially `stable/26.7`), and stage our plugin at `security/zapret2-restyle/`:

```text
work/opnsense-plugins/
├── Mk/                         # official, unmodified
├── Scripts/                    # official, unmodified
├── Templates/                  # official, unmodified
└── security/
    └── zapret2-restyle/
        ├── Makefile
        ├── VERSION
        ├── pkg-descr
        ├── +PRE_INSTALL
        ├── +POST_INSTALL
        ├── +PRE_DEINSTALL
        ├── +POST_DEINSTALL
        └── src/
            ├── opnsense/
            ├── etc/
            └── libexec/zapret2-restyle/
```

Use the **complete corresponding official infrastructure**, including any required related templates/scripts or platform dependencies; do not copy a lone `Mk/plugins.mk`, fork it or implement missing portions ourselves.

Record the upstream repository URL, branch and **exact resolved commit** for every package build. Record our own exact source commit separately; temporary upstream Git state must not corrupt `PLUGIN_HASH` or project version annotations.

#### Build-environment bootstrap

Before invoking BSD Make, prepare and verify the tools and package repository configuration of the build environment. The per-file plan must name the environment, the target OPNsense repository line and the bootstrap commands; a stock FreeBSD VM alone does not establish target compatibility. The official `defaults.mk` evaluates `PLUGIN_PYTHON` while Makefiles are read, before the `package` target installs `PLUGIN_DEPENDS`. Consequently, declaring Python in `PLUGIN_DEPENDS` cannot bootstrap a missing `/usr/local/bin/python3` for that first evaluation.

Require the real `pkg`, BSD Make and the tools used by the selected official build path, a working generic Python link and its package-provided interpreter, and PHP where required. Verify their installed providers and target-repository provenance. Establish the target product ABI from actual OPNsense identity or an explicitly identified, qualified target build environment; a fallback constant in upstream Makefiles is not qualification. Compare the evaluated Make variables, real interpreter and package ABI to the matrix before staging or building. Do not fabricate `opnsense-version`, manually create a substitute Python symlink, or force `PLUGIN_PYTHON` to make an unqualified environment pass.

### 5.2. Package inputs and staging

Stage root `Makefile`, `VERSION`, `pkg-descr`, `src/opnsense/`, `src/etc/` and all four `pkg/+...` hooks from one identified project commit. Preserve required installed file content, paths, executable modes, permissions, symlink and sample/shadow semantics. Never stage developer host configuration, downloaded engine trees, secrets, scratch archives or unrelated material.

The reference for executable permissions is actual installed-package behavior. Stage 0.13 found `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` tracked as **Git `100644`** and the old bespoke builder setting `.sh` files executable during staging. **Stage 2 must change this direct service entrypoint to Git `100755`** before official native packaging, and verify all other directly invoked script modes. Compare exact Git modes → native `.pkg` entries → actual installed modes and exercise direct configd/hook/rc calls. Never rely on blanket staging `chmod` or syntax checks as executable-delivery proof. Preserve other required symlink/sample/permissions; see LH-05 (§8).

Keep current signed FreeBSD `latest` private `curl-impersonate` retrieval and existing capability/provenance checks. Stage its binary and private launcher scripts under their established packaged `libexec/zapret2-restyle` destination. Do not turn a bundled private build artifact into a mandatory installed system package merely for convenience.

#### Private ELF binary compatibility with target OPNsense

Private extraction from a signed FreeBSD `latest` package proves origin, **not** runtime compatibility with qualified OPNsense. For each resolved private `curl-impersonate` artifact verify the actual ELF architecture/ABI, executable loader and dynamic library requirements using available target-platform facilities (for example `file`, `readelf`, `ldd`); identify actual ABI-compatible shared-library providers in the **target OPNsense** package environment. Include all binaries or libraries material to the private launcher path.

The packaged private entrypoint must execute in a qualified target environment and demonstrate relevant local capabilities used by Strategy Lab (Chrome profile, ECH-off and HTTP/3/QUIC where applicable). A successful stock FreeBSD build-VM smoke test is not target acceptance. Missing or incompatible providers cause a fail-closed diagnostic **before** use. Required libraries come only from qualified OPNsense packages or an expressly validated private-bundling policy; never install FreeBSD system packages into the appliance to satisfy them. Local smoke tests do not require uncontrolled WAN access.

Record the signed source package digest, bundled binary digest, dynamic-library providers and exact qualified environment identity; rerun the gate on every changed `latest` private binary.

The official build must retain the package identity `os-zapret2-restyle`, current project `VERSION` and `PLUGIN_REVISION`, project website (`PLUGIN_WWW=https://github.com/Tolian82/os-zapret2-restyle`), maintainer, license and valid OPNsense annotations; do not produce an unexpected `-devel` suffix or upstream-derived project version.

### 5.3. Exactly one packaging engine

Execute official BSD Make **`make package`** inside temporary `security/zapret2-restyle` using `.include "../../Mk/plugins.mk"`. Pass supported `WRKDIR`/`PKGDIR` options where needed; never modify upstream Makefiles to accommodate our project.

Retain `scripts/build-pkg.sh` only as a **thin orchestrator**: validate inputs/environment; prepare upstream tree, sources and private bundled files; invoke official build; verify output; deliver existing `dist/` artifact contract.

Remove hand-written `get_make_var()` parsing by `sed` for computed Make variables, `dep_origin()` mappings, synthetic dependency version `"0"`, custom `plist`/`+MANIFEST` generation, and parallel production package creation code that native `Mk/plugins.mk` already owns.

**All** development, testing-package and stable-release builds use the same mechanism. Publication, CI and release-authority policies remain distinct.

## 6. System dependencies: pkg and target OPNsense repositories

Classify every actual external component as `runtime`, `build-only`, `test-only`, `bundled private` or `optional`. Independently record its execution location: package-build CI, test environment or installed OPNsense. For each component identify its consuming entrypoint, package/base-system provider, permitted repository and provisioning owner. Audit at least Python, `git`, `jq`, `luajit`, `pkgconf`, `gmake`, PHP/OPNsense-provided tools, and all other executable dependencies actually reached by installed code.

Distinguish building the plugin package in CI from compiling the separately managed Zapret2 engine on the appliance. Tools required by installed setup, such as `pkgconf` in the current engine build path, are appliance requirements even if their purpose is compilation. Do not remove them from target provisioning merely because they are classified as `build-only`. Conversely, a tool used only to build or test our plugin package is not an appliance dependency.

`pkg` is the package manager, not the choice of package repository. System dependencies must come from the repository for the qualified target OPNsense line. Do not enable a stock FreeBSD repository on the appliance, including temporarily from `setup.sh`, to satisfy a missing system dependency. A missing target package requires an actionable failure and a resolved dependency plan, not an unqualified repository fallback. The existing build-time extraction of a private signed FreeBSD `latest` `curl-impersonate` artifact is the bounded exception in section 5.2; it does not authorize installing FreeBSD packages into the appliance's system dependency set.

Use official `PLUGIN_DEPENDS` for true mandatory appliance packages, including tools needed by supported installed setup operations. Explicitly document dependencies supplied by OPNsense itself and any optional component's acquisition boundary. Each dependency has one provisioning owner; remove redundant `setup.sh` package-install decisions when native package dependencies take ownership. Prefer no exact version pin unless proven necessary; trust native `pkg` for installed versions and origins. Distinguish base system tools from extra packages. Do not promote CI-only build/test dependencies to appliance dependencies merely because tests mention them.

Follow official HAProxy, ACME and ddclient Python-flavor examples using `py${PLUGIN_PYTHON}-...`, while independently verifying the **real package name and origin for the Python interpreter itself** in the target OPNsense repository. Do not assume `python${PLUGIN_PYTHON}` and `/usr/local/bin/python3` are equivalent: verify the package providing the generic link, the interpreter it resolves to and how the target dependency graph guarantees both.

The native build resolves/installs dependencies as designed and emits real `name`/`version`/`origin` through `pkg query`. No fake `+MANIFEST` entries such as `"version":"0"` and no manually curated name→origin mappings. Ordinary package hooks do not install or upgrade system dependencies. The existing separate Zapret2 engine release process stays untouched.

## 7. Unified, validated Python invocation contract

1. OPNsense `Mk/defaults.mk` obtains `PLUGIN_PYTHON` from the real system `/usr/local/bin/python3 -V`. The selected version must match the supported manifest and available verified package.
2. Do **not** manually set `PLUGIN_PYTHON=313` to bypass a missing generic Python or mismatch. Reject an unverified build environment.
3. Prefer the validated, stable `/usr/local/bin/python3` runtime path. Use at most one minimal shared launcher if actual entrypoint requirements justify it; do not invent a package manager or parallel interpreter resolver.
4. Shell, PHP `proc_open`, configd `actions_zapret.conf`, all package hooks, Python shebangs and worker entrypoints (Strategies, Strategy Lab, Voice/IPSet, extra resources) must implement the **same** policy, while keeping their native invocation interface.
5. Remove direct minor-version executables, e.g. `/usr/local/bin/python3.13`, and independent `EXPECTED_PYTHON=3.13` from production code. Version constraints belong in the matrix. Tests may explicitly select an interpreter as a declared fixture.
6. Children launched by a Python process already running under the validated interpreter use `sys.executable`.
7. Preserve CLI argv, I/O streams, environment, timeouts, exit codes, API response semantics and existing service/owner behavior.
8. A missing executable, missing generic symlink, incompatible Python, missing module or unreadable entrypoint must fail closed with meaningful diagnostics; never silently choose an arbitrary executable from `PATH`.
9. Preserve the inherited lifecycle descriptor **FD9**, process identity/group assumptions and signal delivery for Stop, cancellation and timeouts. A shared launcher transfers control through `exec`/equivalent without an extra persistent parent. Never close ownership descriptors or reacquire the same lock recursively. An incoming hook runs against **previously installed** hook/service code; if its real FD9/ownership contract cannot safely establish Status/Stop, refuse instead of assuming the incoming package repairs old installed code (LH-01/LH-02).
10. Perform every available compatibility check before the corresponding entrypoint stops the service or mutates Config, IPFW or runtime state. Define the bootstrap explicitly: check executable availability before invoking Python, then validate the installed policy and required modules using the common contract. Package-hook checks may only consume dependencies/files present at that hook phase, as required by sections 4.1 and 8. A later failure retains the existing same-operation cleanup and truthful recovery result; never infer a safe state from a failed check.
11. **Native safe Stop and truthful Status must not become dependent on unavailable Python where their underlying operations are interpreter-independent.** If `dvtws2` is active but Python is missing, incompatible or its generic link is broken, reject new Python-dependent Start/Apply/Strategy mutations; continue to allow safe native Stop and bounded cleanup of **verified plugin-owned** IPFW/process resources, with process identity, FD9, signals and ownership checks preserved. Never flush unrelated IPFW state or treat uncertain ownership as safe. Keep interpreter-independent Status and degraded-state diagnostics where feasible, without false success. This is not a substitute Python, an independent service owner or a legacy fallback.

The real caller tests must exercise FD9 inheritance, signals, process ownership, safe Stop and truthful Status when Python is unavailable, and refusal before mutation in addition to argv, streams and exit status. Diagnostics must not contaminate a machine-readable stdout/API response or misclassify an unavailable runtime as invalid user input.

A simple shebang rewrite is insufficient if a PHP, configd or shell caller still contains a versioned path; verify **real** caller-to-callee contracts.

## 8. Installed package lifecycle and four manual hooks

Official `Mk/plugins.mk` provides `scripts-manual`. Keep `pkg/+PRE_INSTALL`, `+POST_INSTALL`, `+PRE_DEINSTALL` and `+POST_DEINSTALL` as full authoritative manual package scripts; verify generated scripts are not unexpectedly appended/replaced by auto hooks.

During a package replacement, incoming `+PRE_INSTALL` can run **before new files or the new installed manifest exist**, interacting with the previously installed service/old hooks. No new pre-install dependence on an unavailable launcher/JSON/runtime file. Test actual `pkg` ordering.

Keep configd watcher/action registration, template updates, lifecycle lock/FD9, foreign/incomplete IPFW refusal, service RUNNING/STOPPED state, safe interrupted-operation recovery, transaction atomicity, restoration and extra-resources operations. No speculative old-version transition branches under DEV-050; immediate current-operation rollback and cleanup remain mandatory.

Select the exact currently supported installed package as the replacement baseline in the implementation plan. Verify replacement in both RUNNING and STOPPED states with configuration retained; this is a bounded current-package transition, not a compatibility matrix for arbitrary historical packages. If a deliberate current-format setup/Apply is required, state that consequence explicitly instead of adding a legacy product path.

### Stage 0.13 audit promoted to binding native lifecycle requirements (LH-01–LH-07)

The [exact-HEAD Stage 0.13 audit](../verification/evidence/2026-11-01-v0.6.2_16-stage0-hook-lifecycle.md) is **source evidence**, not installed acceptance. The following are future native build **requirements**, not mandatory preservation of every old implementation detail.

| ID | Mandatory native contract / acceptance |
|---|---|
| **LH-01 — phase/owner refusal** | Incoming `pkg/+PRE_INSTALL` must inspect the **previously installed** service, process/IPFW ownership and available files before Stop. No dependence on not-yet-installed launcher, JSON, manifest or dependencies. Unknown/incomplete/foreign state or missing/nonexecutable old service does not prove stopped; refuse unverified Stop. Verify real pkg order including fresh install and RUNNING/STOPPED replacement. |
| **LH-02 — old PRE_DEINSTALL/FD9** | Incoming PRE_INSTALL currently offers conditional FD9-aware read, but old `pkg/+PRE_DEINSTALL` **has no independent FD9 retry**. Qualify the exact supported installed predecessor's actual hook and service, preserve **one inherited FD9 owner**, and forbid recursive lock acquisition. With old Status=2, busy lock, cold journal, absent Python or unknown owner, allow safe verified-only behavior or refuse package replacement with a recovery diagnostic. Incoming code cannot rewrite the already installed old hook. |
| **LH-03 — missing Python Stop/Status** | On absent/broken/incompatible Python, refuse Python-dependent Start/Apply before mutation while retaining interpreter-independent **truthful Status** and bounded Stop only for verifiably plugin-owned engine/process/IPFW state. Preserve FD9 and signal ownership; foreign, partially owned or ambiguous state must remain untouched. Test real target owned vs foreign negative conditions. |
| **LH-04 — safe configd worker update** | `pkg/+POST_INSTALL` must activate updated `configctl zapret` actions, verify the selected worker belongs to the existing watcher and confirm readiness. Existing worker `SIGTERM` is **an observation, not a mandated implementation**. Never signal stale/reused PIDs, unrelated worker, watcher parent or global Web GUI; fail closed on identity ambiguity. Test correct update, stale/reused/multiple workers, missing watcher and readiness failure. |
| **LH-05 — Git/native/installed executable mode** | Change direct `zapret_service.sh` Git mode from `100644` to `100755` at Stage 2; audit all other direct hook/configd/rc entrypoints and require actual native `.pkg` and installed executable modes, with direct-call tests. No blanket staging `chmod` substitute. |
| **LH-06 — marker/rollback safety** | All four authoritative manual package hooks preserve verified RUNNING/STOPPED, Config, restart-marker ownership and interrupted retry/rollback. Restore only a proven previously running plugin; do not turn STOPPED into RUNNING or claim success after failed Stop/Start/Status/register/template. `+POST_DEINSTALL` must not restart global services. Test forced reinstall and injected failure cases. |
| **LH-07 — real target package evidence** | Official `scripts-manual` must carry four hooks intact. Observe actual incoming PRE_INSTALL / old PRE_DEINSTALL / old POST_DEINSTALL / new POST_INSTALL *pkg execution order* on qualified isolated OPNsense and bind old/new identities, FD9/process/signals, permissions and negatives to **one native package SHA-256**. Mocked hooks, static source and generic FreeBSD CI are not installed evidence; mark unverified cases NOT VERIFIED. |

**Stage allocation:** Stage 2 proves LH-01/LH-05–LH-07 native hooks, modes and real package order; Stage 3 implements LH-02–LH-04 and LH-06 verified ownership, safe Stop/Status, worker identity and rollback; Stage 4 exercises **all LH-01–LH-07** against the exact final package and qualified target. Stage 0 STOP and Stage 1 block are unaffected.

### 8.1. Bounded recovery boundary for residual old FreeBSD repository overrides

The former `setup.sh` could leave a temporary plugin-created override at `/usr/local/etc/pkg/repos/FreeBSD.conf` and a backup in the plugin state directory after interruption. While removing that old repository-mutation code, provide a bounded **read-only detection** of such residue; never assume a user's current repository file is owned by the plugin.

Only when the temporary content, matching valid backup and absence of subsequent foreign edits are all **unambiguously verified** may a scoped recovery atomically restore the exact backed-up content, retaining the backup on failure. If provenance, backup integrity or current ownership is ambiguous, do not overwrite, normalize or remove the user's file or backup; emit actionable manual recovery guidance and refuse unsafe dependency provisioning. Never automatically enable stock FreeBSD system repositories.

This is an explicitly bounded safety/cleanup responsibility for the current environment, not a permanent old-version migration framework or a general `pkg` repository editor.

## 9. OPNsense ABI, FreeBSD ABI and repository publication

Use official OPNsense product ABI discovery (e.g. `opnsense-version -a`) and actual FreeBSD `pkg`/build ABI; compare **each separately** to the matrix. Do not mistake OPNsense `PLUGIN_ABI=26.7` for `FreeBSD:15:amd64`. Do not silently trust missing-environment fallback values as proof of support.

Keep FreeBSD 15.0/15.1 VM versions only where needed as reproducible test selections, not as independent runtime locks. New Python/FreeBSD/OPNsense support requires qualification before changing the matrix.

Preserve `dist/`, signed/hashed artifact provenance, GitHub Release/Pages repo index generation and immutable existing published assets. Align `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf` and release workflows to one verified package ABI. If concrete repo URLs are required, **render/verify** them from the validated build output rather than manually maintaining a divergent constant.

Package-content and installed-package verification identify the exact final `.pkg` SHA-256. The same project commit can produce different bytes when the official build tree, target packages or private FreeBSD `latest` artifact change. A rebuild is a new artifact and must receive applicable artifact checks again; earlier source checks remain usable only within their actual scope. Record the resolved build inputs and private artifact hashes without introducing a permanent `latest` version pin. Within one publication, GitHub Release and the Pages/package repository must receive the same verified package bytes; no unverified rebuild or redownload may replace them between qualification and publication.

The same native package build path is mandatory in `.github/workflows/ci.yml`, `testing-package-delivery-ci.yml`, `publish-prerelease.yml` and `release.yml`.

## 10. Entire-repository audit, exceptions and known work groups

Before implementation, scan the **exact then-current Git tree** and provide a path/line audit, dependency classifications, allowed exemptions and a tested plan for each affected caller. The prior audit is only an investigation baseline and is **not** a complete final-file inventory.

Required groups:

| Group | At least these files and integrations |
|---|---|
| Identity/policy | `Makefile`, `VERSION`, new `compatibility.json`, schema/validator tests |
| Build | `scripts/build-pkg.sh`, target-environment bootstrap, `scripts/build-curl-impersonate.sh`, private launch scripts, target ELF/shared-library compatibility checks, effective installed modes and staging |
| Package lifecycle | four `pkg/+...` scripts and generated hooks |
| Runtime and Python | `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`, `setup.sh` dependency provisioning and bounded old FreeBSD.conf residue detection/recovery-or-refusal, `setup_transaction.sh`, `strategy_lab_python_launcher.sh`, Python entrypoints and backend modules; FD9, process and signal contracts, Python-independent native Stop/Status |
| GUI/configd | `src/opnsense/service/conf/actions.d/actions_zapret.conf`, `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php` and other actual callers |
| Publication | `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf`, `scripts/verify-release-package.sh` |
| CI/tests/docs | the four package workflows, targeted tests and fixture exceptions, `README.md` only if user-facing facts change, current docs and navigation |

Versions in historical records, golden fixtures, explicitly reproducible CI environments, GitHub Actions tags, immutable upstream resource SHA and demonstrated safety locks are permitted **only as classified, tested exceptions**. No broad exclusions that conceal live production version locks. Audit all files, **do not rewrite all files**.

## 11. Mandatory CI and regression gates

- **CI-01 Full-tree coverage:** scan active production/build/CI sources; classify every literal external version, executable and ABI; use narrow documented allowlists.
- **CI-02 Matrix:** validate schema and positive supported combination; negative invalid/missing matrix, unsupported OPNsense product ABI/FreeBSD ABI/Python, inconsistent capabilities and unsupported architecture.
- **CI-03 Python:** test actual shell, PHP, configd, package-hook, shebang and Python-child paths; preserve args, stdout/stderr, exit status, timeouts, FD9, process ownership and signals; reject absent/unsupported interpreter, wrong link and missing module before the applicable mutation boundary. With a verified owned native engine running, simulate unavailable Python and prove safe Stop/owned cleanup, truthful Status and foreign-resource refusal.
- **CI-04 Native build:** verify target-repository/environment bootstrap before Make evaluation, genuine upstream `Mk/plugins.mk`, exact upstream revision, single standard `make package` path and correct product/source identity; reject fallback ABI values as qualification evidence.
- **CI-05 Package metadata:** inspect the **real built `.pkg`** for version, name, ABI and real `pkg`-derived name/version/origin with target-repository provenance; reject fake `version: "0"`. Bind artifact results to package SHA-256 and verify identical published Release/Pages bytes when publication is authorized.
- **CI-06 Package contents and private ELF compatibility:** enforce LH-05 source Git `100755` → native `.pkg` → installed executable mode; compare old/new necessary files, rc/configd/templates, four manual hooks, private `curl-impersonate` resources and OPNsense annotations. Verify private ELF/loader architecture, required dynamic libraries and actual target OPNsense providers; locally exercise relevant capabilities through the packaged launcher. Revalidate whenever private binary bytes change. Exercise direct entrypoints from packaged files; source modes alone are insufficient. Metadata changes need not be byte-identical.
- **CI-07 Regression:** cover **LH-01–LH-07** with actual pkg hook order, old FD9 and Python-loss Stop/Status, safe configd worker identity/PID reuse, exact Git/native/installed executable modes, RUNNING/STOPPED marker/rollback and final package SHA-256. Preserve GUI/API, Start/Stop/Restart/Status, Strategies Apply, Strategy Lab, Voice/IPSet/Exclude, setup/removal, IPFW owner and restoration paths, plus owned-only old FreeBSD.conf recovery/refusal without modifying foreign settings; use bounded scenarios and existing coverage.
- **CI-08 Negative injection:** deliberately insert a forbidden hard-coded Python version, wrong ABI, fake dependency version or divergent matrix in an isolated test; each corresponding guard must refuse it.
- **CI-09 Evidence honesty:** separately report source checks, isolated FreeBSD/native package checks and actual owner-installed OPNsense evidence. Unexecuted/waived IPv6/WAN/Voice scenarios are not `PASS` and do not automatically reopen prior accepted scope.

Use DEV-051 and GH-062: run fast relevant checks on real generated/consumed artifacts **before** long CI or a product PR. Preserve ordinary project documentation, link-integrity and governance checks.

### 11.1. Bounded implementation acceptance scenarios

Before implementation, the per-file plan assigns these scenarios their exact inputs, expected outcomes and evidence level. Reuse applicable tests; do not create a new open-ended acceptance campaign.

| Scenario | Required observation |
|---|---|
| Clean target installation | The native-built package installs in an isolated supported OPNsense environment using only declared target requirements; required files are executable, manual hooks/register/configd integration work and Python has the verified provider/link |
| Current-package replacement | Replace the identified supported baseline in RUNNING and STOPPED cases; preserve Config and the required final service/ownership state, with real package-hook ordering |
| Changed entrypoints | Exercise each changed caller category and affected user operation through its real installed/consumed path, including cancellation and cleanup where launch behavior changes |
| Incompatibility refusal | Missing/wrong interpreter or link, invalid/missing policy and incompatible platform are rejected at the earliest valid boundary; verify no premature mutation and truthful same-operation recovery for later failures |
| Python-loss native Stop/Status | With verified plugin-owned `dvtws2` running but Python unavailable, safe native Stop cleans only owned resources, Status reports the actual/degraded state and foreign/ambiguous resources remain untouched |
| Private target ELF compatibility | Qualified target OPNsense resolves packaged `curl-impersonate` ELF/loader, dynamic libraries and providers and runs the private launcher/local Chrome/ECH/QUIC capabilities; missing providers fail closed |
| Interrupted old repository override | Verified plugin override plus matching untouched backup permits only atomic exact restoration; ambiguous or foreign `FreeBSD.conf` and backup must be left untouched with actionable refusal |

Automate source and isolated-environment checks wherever possible. Any genuinely necessary owner-appliance observations are one consolidated, reviewed batch rather than repeated piecemeal console requests. Report unavailable checks as unverified. Previously accepted or waived WAN/IPv6/Voice-media investigations are not reopened by this specification.

## 12. Ordered implementation stages — separately authorized

| Stage | Work | Required exit evidence |
|---|---|---|
| 0. Exact baseline | current SHA; all-file/version/entrypoint audit; dependencies by purpose and execution location; old package manifest/files/permissions, old FreeBSD.conf override/backup and bundled ELF/library inventory; exception list and finite acceptance scenarios | reproducible path/line map and baseline |
| 1. Policy | JSON schema/source, policy validator, positive/negative tests | single consistent authoritative matrix |
| 2. Minimal native packaging | qualify target-environment bootstrap; official temporary tree and evaluated `PLUGIN_PYTHON`; native deps/manual hooks, private ELF/library target compatibility, executable modes, ABI/repository alignment; retain current functional behavior while proving this build boundary | a real native-built candidate `.pkg` with verified inputs, manifest, hooks, target-compatible private binary and installed modes before broad Python caller changes |
| 3. Python integration | shared interpreter contract across all real entrypoints, remove duplicated decisions, integrate appliance dependency provisioning and bounded old FreeBSD.conf residue handling; preserve Python-independent native Stop/Status where safe, FD9/process/signal ownership | consumer-level tests including Python-loss Stop/Status, repository ownership refusal, native rebuild and unchanged required runtime behavior |
| 4. CI/acceptance | cross-tree guards, final artifact and target binary checks, safe Stop with missing Python, old repository residue/refusal, focused regressions and the bounded target-platform scenarios | applicable gates evidenced for the final package SHA-256 without false PASS |

Implementation stages must be split into minimal, testable increments and follow current project PR/version governance. Documentation acceptance does not authorize the implementation.

Stage 2 is an isolated qualification step, not a permanent second packaging engine or an automatic publication. Complete the switch to the single native build path and retire superseded production packaging code in the same logical packaging scope; broad Python-call migration follows the demonstrated native-package boundary.

## 13. Binding final acceptance criteria

| ID | Required result |
|---|---|
| AC-01 | All production Python entrypoints use one validated interpreter contract preserving FD9, process identity, signals, streams and failure semantics, without making safe native Stop or truthful Status depend on unavailable Python |
| AC-02 | No independent minor-version Python executable or path in feature code |
| AC-03 | `pkg` owns system dependencies from the qualified target OPNsense repositories; appliance-side build tools have explicit provision and the resulting `+MANIFEST` contains actual name/version/origin |
| AC-04 | One matrix defines qualified OPNsense product ABI, FreeBSD package ABI, CPU architecture and Python policy, with admitted patch updates distinguished from new unsupported branches |
| AC-05 | Official, provenance-attested `Mk/plugins.mk` / `make package` builds every package type after verified environment bootstrap |
| AC-06 | GUI, configd, service, Strategies, Strategy Lab, Voice, installation/removal and relevant recovery behavior are retained through the bounded acceptance scenarios including Python-loss Stop/Status and owned old repository cleanup/refusal |
| AC-07 | Product/package names, `zapret` service key, `VERSION`, `PLUGIN_REVISION` and separate Zapret2 engine version policy are unchanged |
| AC-08 | All required installed files, effective executable permissions, four manual hooks, target-compatible bundled ELF/shared-library providers and native state/rollback safety invariants are retained |
| AC-09 | CI rejects reintroduced fragmented version policy and inconsistent package/compatibility artifacts; package results identify exact SHA-256 and authorized Release/Pages publication uses identical verified bytes |
| AC-10 | Documentation and evidence accurately distinguish intended scope, source implementation, CI/package proof and owner-installed acceptance |

All criteria are required to close the future engineering implementation, not the current documentation PR.

## 14. Required final implementation report

Report exact source/upstream SHA, matrix schema/hash, final package SHA-256, full-tree exceptions and touched files, dependency purpose/execution location/provisioning owner, target-repository/environment bootstrap evidence, `pkg query` metadata and extracted `+MANIFEST`, private artifact hashes and target ELF/dynamic-library provenance, FreeBSD/OPNsense ABI, old/new package content/mode comparisons, Python-loss safe Stop/Status and bounded repository override/backup restoration-or-refusal evidence, actual fast checks, CI links and the bounded target/owner-appliance evidence. List skipped/unverified cases explicitly; do not attach earlier artifact results to unverified rebuilt bytes.

Publication authority follows [CHAT-015–CHAT-017 and CHAT-027](../CHAT_RULES.md), [GH-034–GH-040 and GH-060–GH-061](../GITHUB_PUBLICATION.md). An owner command to make a patch/package already includes the applicable testing-package delivery and its documentation tail when a package candidate is involved; do not request a second publication permission. Full stable release promotion requires explicit release authority. This documentation-only revision authorizes neither implementation nor package delivery; an explicit build/CI-only instruction may also stop at that requested boundary.

## 15. Explicit prohibitions

Do not create a new package/dependency manager, custom Python version manager, altered OPNsense build-system fork, parallel package builder, speculative platform adapters, legacy product fallbacks, or an indiscriminate production code rewrite. No service rename; no change to engine version ownership.

The approved specification is the normative specialist contract for this **new** scope. Its publication is **documentation only**. The separately approved per-file plan v1.3 is now current, Stage 0 source/CI audit has begun, and actual installed target acceptance remains unproven. Further implementation/delivery follows the approved plan and applicable publication rules; its testing-package authority is interpreted under section 14 without duplicate confirmation, while stable promotion remains separately owner-controlled.

## 16. Official reference implementation

- [OPNsense defaults and native Python variables](https://github.com/opnsense/plugins/blob/stable/26.7/Mk/defaults.mk).
- [OPNsense native plugin builder](https://github.com/opnsense/plugins/blob/stable/26.7/Mk/plugins.mk).
- [Official HAProxy plugin](https://github.com/opnsense/plugins/blob/stable/26.7/net/haproxy/Makefile).
- [Official ACME plugin](https://github.com/opnsense/plugins/blob/stable/26.7/security/acme-client/Makefile).
- [Official ddclient plugin](https://github.com/opnsense/plugins/blob/stable/26.7/dns/ddclient/Makefile).
- [OPNsense system package and repository policy](https://docs.opnsense.org/manual/software_included.html).
- [OPNsense ports generic Python provider](https://github.com/opnsense/ports/blob/a484faf5039260edc4a24a6a29005d0e8ff62966/lang/python3/Makefile) — inspected reference only; actual target package/link identity is verified for each qualified build environment.

**Approved architecture:** project source → isolated complete official OPNsense tree → native `PLUGIN_PYTHON`, `Mk/plugins.mk` and FreeBSD `pkg` → exact package/metadata → unified compatibility matrix and Python execution contract → CI and evidence-based acceptance.

General canonical rules remain in [PROJECT_PRINCIPLES.md](../PROJECT_PRINCIPLES.md); current priority/handoff remain in [ROADMAP.md](../ROADMAP.md) and [START_HERE.md](../START_HERE.md).

# Native OPNsense Packaging and Unified External Compatibility — Technical Specification v1.5

**Status:** owner-approved native integration scope, 5 November 2026. `_137` passed real official Mk package build and clean installation on disposable OPNsense 26.7. `_138` dependency cleanup merged after 15/15 native CI PASS. `_139` generic Python/manifest-backed exec merged after 15/15 exact-head CI PASS, including actual native OPNsense build/install. `_140` accepted Python-down verified ordinary Stop/Status (15/15 exact-head and postmerge CI). `_141` was merged after successful exact-head native CI for pkg removal and official OPNsense firmware unregister on a disposable guest. `_142` merged after 15/15 exact-head workflows confirming installed cold Start/Restart/Reconfigure refusal with healthy Python and absent engine. `_143` passed real installed ordinary Strategies Start/Stop/Restart/Reconfigure and verified Python-down Stop on isolated lo0 (PR #913, 26/26 exact-head and postmerge main CI PASS). `_144` [PR #914](https://github.com/Tolian82/os-zapret2-restyle/pull/914) merged after 26/26 exact-head and postmerge CI SUCCESS, proving installed packaged configctl Start/Stop/Restart/Reconfigure/Status. `_145` merged after 16/16 exact-head and postmerge CI SUCCESS: a real clean OPNsense reboot executed original stop/start syshooks with unchanged canonical native Config and restored scoped lo0 engine/IPFW. `_146` now has genuine installed OPNsense 26.7 guest evidence ([run #42065497016](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42065497016)) for one common Strategies/Telegram Voice owner through the existing original-FD9 configctl Apply, scoped lo0 IPFW, safe Python-down Stop refusal and native Stop/Start. Full exact-head CI and integration remain obligatory. Web GUI click, Voice media, power loss and final qualification remain separate.
**Approval:** 5 November 2026. External pkg approval and additional IPFW/PF mechanisms are cancelled.
**Project:** `Tolian82/os-zapret2-restyle`.
**Implementation boundary:** `_137` removed cancelled authorization experiments and reconciled active technical documentation; existing native Mk builder and disposable clean install passed. `_138` proved native dependency ownership; `_139` merged generic qualified Python entrypoint (incoming PRE_INSTALL remains phase-safe). `_140` accepted interpreter-independent verified ordinary native Stop/Status and cold installed smoke; not active shared-owner teardown. `_141` verified real installed stock `pkg delete` and official firmware registration removal with retained Config and no extra global autoremove. `_142` accepted actual installed cold Start/Restart/Reconfigure refusal without engine while Python is healthy. `_143` accepted the ordinary live engine lifecycle after actual native pkg replacement. `_144` qualified the installed native configctl-to-service action path on disposable OPNsense. `_145` accepted real clean shutdown/new-boot lifecycle for ordinary Strategies on lo0, retaining approved syshooks unchanged. `_146` tested the installed committed common Strategies/Voice owner with the existing service and configctl on disposable lo0, with genuine guest CI success; full exact-head PR merge and postmerge main verification remain distinct. Web GUI clicks, Voice media and final package acceptance remain separate. No appliance mutation/publication authorized.

**Accepted `_147` (unpublished source-only, installed native HTTP guest PASS in [guest run #42082770896](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42082770896); [PR #917](https://github.com/Tolian82/os-zapret2-restyle/pull/917) merged with 18/18 exact-head and postmerge main CI/Release trigger PASS):** the installed HTTPS Voice-page/API on disposable OPNsense 26.7 is exercised through a cookie-authenticated localhost session after the accepted `_146` real common owner. The exact five-profile AJAX form and current Config snapshot must refuse stale submissions before mutation; authenticated Apply modifies only Telegram's test STUN UDP 3478→3479, then reverses to 3478. Verify shared original-FD9 journal, one dvtws2, scoped lo0 IPFW, unchanged unrelated/extra-plugin XML, and restored full native model snapshot; root `Zapret` model metadata (`version` and `persisted_at`) may change after legitimate Apply, while all non-metadata extra XML attributes and fields must remain unchanged. This is an actual HTTP API user path, not a physical browser click. No WAN/Voice media or owner appliance mutation, production changes, or release publication.

This document supersedes v1.4 in place. Previous requirements remain only in Git history and are not active product gates.

**Independent document revision:** `v1.5` identifies only the editorial revision of this technical specification. It is **not** the GitHub project/source version, `VERSION`, `PLUGIN_REVISION`, package revision, tag or release version. Advancing any GitHub/plugin version does not automatically advance the specification revision; editing or approving the specification does not automatically change the plugin version or publish a release. The specification revision changes only when its own content/requirements are deliberately revised.

## 1. Purpose and boundaries

Use the **official OPNsense plugin build system**, FreeBSD `pkg` dependency management, a single external-compatibility manifest and one unified, validated Python execution contract. Ordinary supported updates of external interpreters/packages must not require scattered feature-code rewrites. Audit the **entire active repository**; only change files that violate the contract or require a genuine integration adjustment.

This is a NEW approved technical specification. Former [issue #732](https://github.com/Tolian82/os-zapret2-restyle/issues/732) and closed/unmerged [PR #740](https://github.com/Tolian82/os-zapret2-restyle/pull/740) were cancelled **inside the previous dual-stack work**, not silently reactivated here. Do not change prior dual-stack acceptance or reopening rules.

**Not in scope:** unrelated functional rewrites; proprietary pkg authorization or managed privileged updater; new IPFW collision/ownership scans, dynamic allocation, shaper-flush monitoring or recovery; OPNsense-only pfilctl conversion; immediate pfSense port. Preserve portability for future pfSense without inventing new abstractions.

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

The reference for executable permissions is actual installed-package behavior. Stage 0.13 found `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh` tracked as **Git `100644`** and the old bespoke builder setting `.sh` files executable during staging. **Stage 2 already changed this direct service entrypoint to Git `100755`** before official native packaging, and verify all other directly invoked script modes. Compare exact Git modes → native `.pkg` entries → actual installed modes and exercise direct configd/hook/rc calls. Never rely on blanket staging `chmod` or syntax checks as executable-delivery proof. Preserve other required symlink/sample/permissions; see LH-05 (§8).

Keep the existing build-time extraction of signed FreeBSD `latest` private `curl-impersonate` for exploratory development candidates, with all existing capability/provenance checks. **Before qualifying a candidate for testing/stable release publication, lock one exact signed FreeBSD source package and its extracted private ELF SHA-256** in the single authoritative machine-readable external-compatibility manifest (`compatibility.json`, extended for this source identity). The lock records the source package version, official repository/snapshot coordinates, target ABI, source package digest, ELF digest and selected supported Chrome profile; verify the resolved artifact against it, fail closed on absent/mismatched input, and do not automatically fall back to a changed `latest`. Do not mistake a Chrome profile for a product-wide pinned browser version. Reusing exactly these inputs for each release-candidate rebuild is mandatory; changing the client requires an explicit manifest revision and renewed native tests. This is an **approved future build/CI implementation requirement**, not a claim that the current floating `build-curl-impersonate.sh` already enforces the lock.

Stage the verified binary, licenses and private launcher scripts under the existing packaged `libexec/zapret2-restyle` destination. Never download the client during installation or turn it into a mandatory installed system package.

#### Private ELF binary compatibility with target OPNsense

Private extraction from a signed FreeBSD `latest` package proves origin, **not** runtime compatibility with qualified OPNsense. For each resolved private `curl-impersonate` artifact verify the actual ELF architecture/ABI, executable loader and dynamic library requirements using available target-platform facilities (for example `file`, `readelf`, `ldd`); identify actual ABI-compatible shared-library providers in the **target OPNsense** package environment. Include all binaries or libraries material to the private launcher path.

The packaged private entrypoint must execute in a qualified target environment and demonstrate relevant local capabilities used by Strategy Lab (Chrome profile, ECH-off and HTTP/3/QUIC where applicable). A successful stock FreeBSD build-VM smoke test is not target acceptance. Missing or incompatible providers cause a fail-closed diagnostic **before** use. Required libraries come only from qualified OPNsense packages or an expressly validated private-bundling policy; never install FreeBSD system packages into the appliance to satisfy them. Local smoke tests do not require uncontrolled WAN access.

Record the signed source package digest, bundled binary digest, dynamic-library providers and exact qualified environment identity. Recheck all of them for each deliberately changed private binary and for the final release candidate; the locked release input must remain byte-identical even if the FreeBSD `latest` index subsequently changes.

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

## 8. Standard native package lifecycle and the existing four hooks

Use only the official `Mk/plugins.mk` / FreeBSD `pkg` path with `pkg/+PRE_INSTALL`, `+POST_INSTALL`, `+PRE_DEINSTALL`, `+POST_DEINSTALL`. Keep hooks focused on normal registration, configd/service, settings preservation and bounded cleanup. Incoming PRE_INSTALL cannot assume new package files already exist. Observe real `pkg` scheduling without claiming universal rollback or pre-install veto.

| ID | Native lifecycle requirement |
|---|---|
| LH-01 | Fresh installation and package replacement use native `pkg`; hooks cannot depend on incoming files that do not yet exist. |
| LH-02 | Use the existing `zapret` service and normal lifecycle/FD9 locking for actual Start/Stop/Apply; test RUNNING and STOPPED replacement without a separate package-update manager. |
| LH-03 | Python-dependent operations require a qualified interpreter and return clear failure on its absence; preserve correct existing Python-independent Status/Stop where feasible. |
| LH-04 | Updated `configd` actions work through the existing OPNsense watcher without signalling unrelated processes or restarting the whole Web GUI. |
| LH-05 | Direct entrypoints (including `zapret_service.sh`) have valid Git, native archive and installed executable modes; `100755` service mode has already been corrected in source. |
| LH-06 | Standard install/update/reinstall/remove handle their own service settings and normal cleanup, without a custom system-package transaction or guarantee of universal rollback. |
| LH-07 | Test the actual four installed package hooks, settings retention, ordinary interruption and errors on a disposable target; separate source, installed, owner and publication evidence. |
| **LH-08** | **Root and stock firmware/Web/pkg remain native administrator operations.** No additional root warning, direct-pkg interceptor, separately running authorization server, SQLite witness, one-use cryptographic permissions, RSA grant, operator approval receipt, managed pre-pkg gateway or FD9-serialized pkg replacement. Native `pkg` semantics are authoritative. The reproduced `_74` incident means a failed PRE_INSTALL may not veto `pkg add -f`; it does **not** authorize or require a parallel trust infrastructure. |

### IPFW/PF scope set by the owner

- Fixed **IPFW rule numbers**, not network or divert ports: **19000–19010** for ordinary Zapret2/Strategies and **19100–19131** for Strategy Lab. Document both in README and current technical documentation.
- No new per-number collision checks, foreign-rule inventory, dynamic number allocator, ownership database, rule-manager refactor, shaper-flush listener, automatic restoration or extra standalone tests for those hypothetical scenarios.
- Retain the already existing safe cold-IPFW module-loading behavior, checked only as part of normal installed service acceptance.
- Keep existing `pfctl -d; pfctl -e` unchanged. No OPNsense-only `sync_fw_hooks.py` / `pfilctl` migration. Future pfSense port is a separate task.

### Old FreeBSD repository overrides

Remove the stock FreeBSD repository toggle from `setup.sh`. Do not overwrite an ambiguous existing administrator `FreeBSD.conf` or backup. Provide concise diagnostics/manual remediation; do not invent a repository recovery framework.

## 9. OPNsense ABI, FreeBSD ABI and repository publication

Use official OPNsense product ABI discovery (e.g. `opnsense-version -a`) and actual FreeBSD `pkg`/build ABI; compare **each separately** to the matrix. Do not mistake OPNsense `PLUGIN_ABI=26.7` for `FreeBSD:15:amd64`. Do not silently trust missing-environment fallback values as proof of support.

Keep FreeBSD 15.0/15.1 VM versions only where needed as reproducible test selections, not as independent runtime locks. New Python/FreeBSD/OPNsense support requires qualification before changing the matrix.

Preserve `dist/`, signed/hashed artifact provenance, GitHub Release/Pages repo index generation and immutable existing published assets. Align `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf` and release workflows to one verified package ABI. If concrete repo URLs are required, **render/verify** them from the validated build output rather than manually maintaining a divergent constant.

Package-content and installed-package verification identify the exact final `.pkg` SHA-256. The same project commit can produce different bytes when the official build tree, target packages or private FreeBSD `latest` artifact change. A rebuild is a new artifact and must receive applicable artifact checks again; earlier source checks remain usable only within their actual scope. Exploratory builds may continue to record resolved floating inputs. **For a release candidate**, apply the source-package/ELF lock from §5.2 and record both digests plus the actual final plugin-package SHA; a source pin reduces dependency drift but does **not** alone guarantee bit-reproducibility of independently rebuilt plugin archives. The Additional Resources Remove plan SHA is per-installation state evidence, not a package or dependency identifier, and may legitimately differ across OPNsense guests. Within one publication, GitHub Release and the Pages/package repository must receive the **same verified package bytes**; no unverified rebuild or redownload may replace them between qualification and publication. Keep the already-qualified **one physical plugin archive across clean and RUNNING guests** as a distinct mandatory acceptance gate.

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

## 11. Targeted verification

- Official native builder: `scripts/build-pkg.sh` already delegates to `scripts/native-opnsense-package.py` using `Mk/plugins.mk` / `make package`. Qualify real OPNsense repositories/ABI, manifest/dependencies, modes, four hooks and bundled private `curl-impersonate` ELF; do not start a second builder.
- Package-managed dependencies: `setup.sh` must not toggle a stock FreeBSD repository or reinstall dependencies owned by OPNsense `pkg`.
- Unified Python: test changed real shell, PHP, configd, backend, Lab, Voice, Extra Resources and hook call paths; preserve actual inputs, outputs, deadlines and errors.
- On a disposable OPNsense 26.7 target test fresh install, Start/Stop/Restart/Status/Apply, RUNNING/STOPPED upgrade from `0.6.2_1`, forced reinstall, settings retention, removal and ordinary bounded failures.
- Run only relevant Strategies, Lab, Voice, Exclude and Extra Resources regressions. Already existing cold-IPFW initialization is checked by normal service Start, not a new shaper/foreign-IPFW study.
- Remove cancelled SQLite/approval-only CI when the corresponding tools are deleted. Retain stage0/stage2 tests that really verify normal pkg, hooks, ABI, dependencies and service even if their filenames mention FD9.
- Final proof is tied to one actual native package SHA-256. Source-only CI does not prove installed behavior or a new stable release.

## 12. Five-step completion route

| Step | Concrete deliverable | Exit condition |
|---|---|---|
| 0. Reset | Remove cancelled pkg approval source/tests/workflows; **after removal, audit and reconcile the entire active technical documentation/README and CI references**. | No active dependency on the rejected architecture; relevant CI green and docs consistent with v1.5. |
| 1. Package | Finish the **existing** official Mk native builder, correcting only real build/install blockers. | Real `.pkg` installs in disposable OPNsense. |
| 2. Dependencies/Python | Native OPNsense pkg dependencies, setup FreeBSD-repo cleanup, unified qualified interpreter in real consumers. | Target install supplies dependencies and changed functions work. |
| 3. Service/hooks | Existing configd/rc, four hooks, RUNNING/STOPPED update, ordinary reinstall/remove and Config retention. | Native lifecycle functional in disposable guest. |
| 4. CI/acceptance | One native CI/testing/release build path, bounded full-function tests and one final package SHA. | AC-01–AC-11 genuinely checked; any owner-device changes or publication separately approved. |

No further speculative Stage 3.xx or PF/IPFW research subprojects. Small changes, real verification, minimal effort.

## 13. Final acceptance criteria

| ID | Required result |
|---|---|
| AC-01 | One qualified Python invocation contract across real consumers, with appropriate working Status/Stop under Python failure. |
| AC-02 | No scattered hard-coded production Python minor-version executable paths. |
| AC-03 | Real system dependencies are owned by target OPNsense `pkg`; `setup.sh` no longer enables stock FreeBSD repositories. |
| AC-04 | The existing single compatibility matrix covers supported OPNsense/FreeBSD ABI, CPU and Python without duplicating installed versions. |
| AC-05 | All package types use official `Mk/plugins.mk` / `make package` through the existing single builder. |
| AC-06 | GUI, configd, service, Strategies, Voice, Lab, Exclude and Extra Resources retain accepted behavior. |
| AC-07 | Preserve product names, `zapret` namespace, `VERSION`/`PLUGIN_REVISION` and separate upstream engine manager. |
| AC-08 | Installed file modes, hooks, private ELF and normal service work; documented IPFW rule ranges and existing PF behavior unchanged. |
| AC-09 | CI checks actual package/ABI/Python regressions and the final package SHA. |
| AC-10 | **All active** TЗ, plan, README, architecture, requirements, state, roadmap/index and CI instructions agree; old experimental history does not block release. |
| **AC-11** | Native `pkg` install/update/reinstall/remove and service lifecycle tested with retained settings where appropriate; **no universal PRE_INSTALL veto or independent package-approval system**. |

**Accepted FIFTH-task `_148` ([PR #918](https://github.com/Tolian82/os-zapret2-restyle/pull/918), 21/21 exact-head, postmerge Stage 5/main CI PASS):** the existing official OPNsense Mk builder produces ONE `.pkg` on a disposable 26.7 guest; existing genuine native clean install verifies installed pkgdb, original hooks, all package files, dependencies, ABI and private ELF. A test-only receipt records the exact source HEAD, archive/manifest SHA-256 and installed file proof. The byte-identical archive and its read-only receipt must survive VM copyback and be uploaded as one short-lived GitHub Actions artifact. No rebuild between that installation and digest proof, no Release/Pages publication. This is an initial AC-09 identity gate, NOT yet acceptance of RUNNING upgrades, all functional suites, real WAN/IPv6/media or owner installation with that identical final artifact.

**Accepted `_148`:** [PR #918](https://github.com/Tolian82/os-zapret2-restyle/pull/918) merged at `d205d61615a1119a5430defbc4fbcf35690e7c72` with 21/21 exact-head checks PASS. Postmerge [Stage 5 #42091933021](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42091933021), main CI and Release trigger PASS: exact installed clean native `os-zapret2-restyle-0.6.2_148.pkg` SHA-256 `d8ddf8776d400488a72c67efed90ead552259bd549b66cd8ff76a728f3cdecce` (292 matching files, native hooks/pkgdb, real pkg add, copyback). It is an ephemeral Actions artifact, **not** a published package or the full final same-SHA feature suite.

**Accepted `_149`:** [PR #919](https://github.com/Tolian82/os-zapret2-restyle/pull/919) merged at `89586106c6959b3d797de7ccd36bda8310dfefc2` after 21/21 exact-head checks PASS, postmerge CI and Release trigger PASS. Real [RUNNING/Voice/HTTPS #42097681709](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42097681709) passed with one installed archive SHA-256 `63342a257270252fd1811c35504bdcc6061d9db70993a0939bfc1645e6a87a8b` (292 installed pkg-owned files, sealed original FD9, Telegram and HTTP Apply). Separately built [clean install #42097681719](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42097681719) passed with a DIFFERENT SHA-256 `ab1d93ec75a54aec315a4cce585ec83ff3210feb84adf94bac096b5a7a3006be`. Both are short-lived Actions artifacts, not release/owner-installed evidence.

**Accepted _150 same-physical-archive installed qualification:** [PR #920](https://github.com/Tolian82/os-zapret2-restyle/pull/920) merged at `f71311a9b6cf43472bb401608c53ba9591f6a6c7`. [Stage 5 exact-main two-guest #42105204095](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42105204095) passed: one Mk-built `0.6.2_150.pkg` installed clean on disposable OPNsense A, transferred without rebuilding, and installed over genuine old RUNNING `0.6.2_1` on separate disposable OPNsense B. One SHA-256 `ac88d4e678d8a6d2a563d590dc4b4ccd8935c1fed6c7ce74c235ee5d0923ea0a`, 292 exact pkg-owned files, original four hooks, seven dependencies, ABI, manifest and source identity bound to both receipts; original FD9 shared Strategies/Telegram Voice, real Stop/Start and authenticated HTTPS forward/reverse Apply passed. [Main CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42105203939) and [release classifier](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42105203907) passed with no new publication. _151 changes only source-revision and documentation to record the postmerge result. This qualifies this bounded same-archive scenario, NOT full AC-06/AC-09. Next: installed Exclude Domains/IPSet positive/negative offline policy tests on that same guest-B package route, then targeted installed Strategy Lab/Extra Resources checks; real browser, WAN, IPv6, media, common-owner reboot and owner device remain separate.

**Accepted `_152`:** [PR #922](https://github.com/Tolian82/os-zapret2-restyle/pull/922) merged at `deabd8f127a7a7388843951e2dbdb58f44bbb3dd` with 21/21 exact-head checks PASS. The exact merged-main [Stage 5 two-guest #42117710084](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42117710084) passed clean and old RUNNING shared FD9/Voice/HTTPS installation with one `0.6.2_152.pkg` SHA-256 `e7a1f17be8e89bdeb0ca4270affd8943be4a4f1573b33cbea9e12bff592b1a57`, 292 pkg-owned files and 19 offline Exclude Domains/IPSet tests on the actual installed backend. Postmerge CI and Release trigger PASS. This adds installed backend Exclude qualification, NOT real browser Exclude Apply, WAN/IPv6 packet or all-feature AC-09 acceptance.

**`_153` scope:** add installed native Strategy Lab private-state status/refusal and the existing Extra Resources offline archive/collision and Git inventory/cache tests directed at the actual package-owned modules after that same guest-B native RUNNING/FD9/Voice/Exclude route. Preserve exact Config, common journal/dvtws2/IPFW, every pkgdb-owned file and two-independent-guest identical archive SHA. A synthetic idle/invalid status is not a real Lab search; offline archive tests are not Extra Resources Install/Remove. No new auth/update mechanism, product service/GUI/hooks/firewall changes, WAN/IPv6/media claim or publication.
**Accepted `_153`:** [PR #923](https://github.com/Tolian82/os-zapret2-restyle/pull/923) merged at `349010e5dcbdaadea31be3f4d0c16e2d9366f986` after 21/21 exact-head CI PASS; exact merged-main [two-guest Stage 5 #42130557226](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42130557226) PASS used a single `0.6.2_153.pkg` SHA-256 `9942c5c3fc1910cbc64ea44de4b089ea97eb75a2d2b69deb63aa01577540f4f6` on clean and true old RUNNING/Voice/FD9 OPNsense, adding installed Strategy Lab status/refusal and Extra Resources preflight/inventory 18 offline tests. Main CI, release classifier, and all native Stage 5 postmerge routes PASS. No new testing/stable publication.

**Merged `_154` installed-functional increment:** [PR #924](https://github.com/Tolian82/os-zapret2-restyle/pull/924) merged to `0fd1ba5caab1d24f0266fff3f04564b1fa3bc0b9`, 21/21 exact-head CI PASS. Existing installed Strategy Lab launcher/worker passed eight privately mocked E2E job scenarios, installed Additional Resources Python transaction/operation modules 49 private transaction/rollback cases. Exact-main CI, Release trigger, standalone clean and RUNNING/HTTPS Stage 5 PASS; exact-main [two-guest Stage 5 #42159613937](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42159613937) also PASS: byte-identical `0.6.2_154.pkg` SHA-256 `0e84afe012ae9f35cdf5a99cc0d3e2bdb813026d629c9a02727fafd1ad1f6ed1`, 292 pkg-owned files and original hooks on two independent clean/RUNNING guests. No network probe, actual resource change, physical browser or owner-device action proved.

**Accepted `_155` test-only scope:** reuse authenticated cookie/CSRF OPNsense root session on disposable `https://127.0.0.1` guest B after genuine installed old RUNNING/FD9 Voice/HTTPS and Exclude/Lab/Extra. Confirm actual MVC-served General and Diagnostics pages, POST read-only Extra Resources `resourcesStatus`/`resourcesInventory` and Strategy Lab `status`, reject GETs, missing/invalid job and invalid start at production controller boundary. Validate inventory contents only if an existing cache is available, otherwise record availability as NOT TESTED. Save real Config, sealed FD9 journal/engine, scoped IPFW before/after; repeat all installed pkg-owned byte/manifest and same physical SHA cross-binding. No actual Lab job/network, Additional Resources Install/Remove, physical GUI button click, IPv6/WAN/media or owner installed PASS. Source-only, no product code change or release publication.

**Accepted _155:** [PR #925](https://github.com/Tolian82/os-zapret2-restyle/pull/925) merged to exact `main` `d1a8836f555da8465faccebd46c38b60ebac7264`. [Postmerge two-guest Stage 5 #42163689678](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42163689678), [main CI](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42163689584) and [release classifier](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42163689589) succeeded. One official `0.6.2_155.pkg`, 6,806,906 bytes, SHA-256 `ecc38e97a0387381643c48bec36b6bf28de8efbf959a0861b444ff8f4c72e8d6`, was clean-installed on guest A and transferred without rebuilding to genuine old RUNNING/FD9 Voice HTTPS guest B; 292 installed files and four original hooks were verified. The actual installed General/Diagnostics pages and cookie/CSRF-authenticated Lab/Extra read-only/invalid APIs passed with Config/FD9/engine/IPFW unchanged. The absent Extra inventory cache leaves inventory *contents* NOT TESTED; physical browser clicks, valid Lab network jobs and real Extra Install/Remove remain NOT TESTED.

**Former _156 source scope (now accepted):** On the already-existing disposable Stage 5 guest A, after official Mk clean install, run stock `pkg add -f` **using the same archive bytes** and the original four hooks, with explicit CI opt-in. Verify STOPPED before/after, unchanged native Config except ordinary firmware metadata, installed package manifest/hooks/dependencies, every pkg-owned file, executable modes and unmodified archive SHA-256; refuse missing proof in the machine-readable receipt. Transfer this *same* archive to separate guest B for the existing old RUNNING/FD9 Voice HTTPS/Exclude/Lab/Extra/Web checks. No new builder, pkg authorization, production service, browser assertion, owner action or publication. Successful guest CI would qualify only this bounded STOPPED reinstall, not a RUNNING same-version reinstall or full AC-06/AC-09.

**Accepted _156 — final exact-main Stage 5:** [PR #926](https://github.com/Tolian82/os-zapret2-restyle/pull/926) merged at `2787dc5561b1855b433cbbe7119698a8fb625e60`, 26 successful and 7 legitimately skipped exact-head checks. Postmerge [two-guest Stage 5 #42167771247](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42167771247) PASS with ONE Mk-built physical `0.6.2_156.pkg`, SHA-256 `923e69cbb68c1af986ee28b0dbe9fc73fd0d15124f16546c765edfd7d01f40c2`, clean installed and genuinely STOPPED force-reinstalled on guest A, then transferred unchanged to an independent genuine old RUNNING/FD9 Voice/HTTPS/Exclude/Lab/Extra/Web guest B; 292 files, original four hooks, Config/IPFW verified. Other successful postmerge CI #42167771203, Release classifier #42167771101, independent installed clean/force #42167771273 and RUNNING/Voice #42167771267 are separate builds with separate digests, not a common SHA claim. No new testing/stable publication, owner appliance untouched.

**Accepted `_157` — native positive Exclude HTTPS on identical final archive:** [PR #927](https://github.com/Tolian82/os-zapret2-restyle/pull/927) was merged at `ac7eaa0c6fe1c44a28d1b8859ac259ac0158ce9a` after 26 successful exact-head checks and seven legitimate skips. Exact merged-main [two-independent-guest #42174461997](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42174461997) **SUCCESS**: one physical `0.6.2_157.pkg` SHA-256 `00c1f77b17fb089c93c30b34fc2cb4b7b2d5f2f4f99e1ceb46491448989674a4` was clean-installed and STOPPED force-reinstalled in A, transferred unchanged to historical RUNNING/Voice/FD9 guest B, then passed real cookie/CSRF native Exclude Domains/IPSet forward and reverse Apply, 292 owned files and original hooks. [Main CI #42174462063](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42174462063), [release classifier #42174461985](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42174461985), [clean install #42174461948](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42174461948) and [RUNNING/Voice/Exclude #42174461983](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42174461983) all succeeded. No test/stable package publication or owner-system mutation.

**Historical `_158` test scope (merged in PR #928) — genuine installed Additional Resources Remove (AC-06/AC-09):** extend the existing two-disposable-guest, exact same-archive Stage 5 route *after* the real old RUNNING/Voice/Exclude HTTPS qualification. On guest B exclusively, authenticate using the installed cookie/CSRF General page, require an empty local Git-HEAD-only resource inventory, test real no-op and rejected confirmation, add exactly ONE harmless untracked `.lua` file under the already installed upstream runtime, compare the real native read-only plan to authenticated `/api/zapret/service/resourcesRemovePlan`, refuse wrong `REMOVE N` and stale witness without mutation, then use the stock `/api/zapret/service/resourcesRemove` once. Require correlated final `not_installed` receipt, only this one file removed, upstream Lua/BIN bytes unchanged, native unchanged saved Config and genuine newly committed shared Strategies/Voice FD9 owner, real dvtws2 PID transition and unchanged scoped lo0 IPFW; retain full installed package bytes, hooks and SHA identity across guests. No new product service, updater, firewall, resource catalogue or privileged approval mechanism. **NOT** a browser-button click, real external catalogue Install, Lab network jobs, IPv6/WAN/media, shared-owner kernel reboot, owner appliance acceptance or full release.

## 14. Reporting

Record source/upstream SHAs, supported target ABI, actual dependencies, native package SHA-256, test results and legitimate limitations. Never infer owner-installed PASS from source CI.

## 15. Excluded architecture

No external approval server, SQLite authorization journal, one-use crypto permissions, root `pkg` warnings/interception, managed privileged package gateway, universal pre-pkg refusal, new IPFW allocator/collision surveys, shaper flush monitoring or `pfilctl` migration.

## 16. Official references

- [OPNsense official plugins](https://github.com/opnsense/plugins/tree/stable/26.7), including `Mk/plugins.mk`.
- [OPNsense nginx](https://github.com/opnsense/plugins/tree/stable/26.7/www/nginx).
- [OPNsense IPFW template](https://github.com/opnsense/core/blob/stable/26.7/src/opnsense/service/templates/OPNsense/IPFW/ipfw.conf).

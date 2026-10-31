# Native OPNsense Packaging and Unified External Compatibility — Technical Specification v1.0

**Status:** OWNER-APPROVED intended contract, NOT YET IMPLEMENTED.  
**Approval:** 31 October 2026; standalone follow-up to the completed IPv4/IPv6 / Exclude IPSet scope and full v0.6.2 release.  
**Project:** `Tolian82/os-zapret2-restyle`.  
**Next deliverable:** exact-current-HEAD, detailed per-file implementation plan. No production implementation, package publication or owner-appliance experiment is authorized by recording this document.

## 1. Purpose and boundaries

Use the **official OPNsense plugin build system**, FreeBSD `pkg` dependency management, a single external-compatibility manifest and one unified, validated Python execution contract. Ordinary supported updates of external interpreters/packages must not require scattered feature-code rewrites. Audit the **entire active repository**; only change files that violate the contract or require a genuine integration adjustment.

This is a NEW approved technical specification. Former [issue #732](https://github.com/Tolian82/os-zapret2-restyle/issues/732) and closed/unmerged [PR #740](https://github.com/Tolian82/os-zapret2-restyle/pull/740) were cancelled **inside the previous dual-stack work**, not silently reactivated here. Do not change prior dual-stack acceptance or reopening rules.

**Not in scope:** rewriting Strategies, Strategy Lab, Voice, Targets, HOSTLIST/IPSET, Exclude, configd, service/IPFW logic, transaction/recovery semantics, the existing separately managed Zapret2 engine version process, or speculative pfSense adaptation.

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
| FreeBSD `pkg` | system package installation/update, dependency resolution, installed package names, actual versions and origins |
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

### 5.2. Package inputs and staging

Stage root `Makefile`, `VERSION`, `pkg-descr`, `src/opnsense/`, `src/etc/` and all four `pkg/+...` hooks from one identified project commit. Preserve actual file content, path, execute mode, permissions, symlink and sample/shadow semantics. Never stage developer host configuration, downloaded engine trees, secrets, scratch archives or unrelated material.

Keep current signed FreeBSD `latest` private `curl-impersonate` retrieval and existing capability/provenance checks. Stage its binary and private launcher scripts under their established packaged `libexec/zapret2-restyle` destination. Do not turn a bundled private build artifact into a mandatory installed system package merely for convenience.

The official build must retain the package identity `os-zapret2-restyle`, current project `VERSION` and `PLUGIN_REVISION`, project website (`PLUGIN_WWW=https://github.com/Tolian82/os-zapret2-restyle`), maintainer, license and valid OPNsense annotations; do not produce an unexpected `-devel` suffix or upstream-derived project version.

### 5.3. Exactly one packaging engine

Execute official BSD Make **`make package`** inside temporary `security/zapret2-restyle` using `.include "../../Mk/plugins.mk"`. Pass supported `WRKDIR`/`PKGDIR` options where needed; never modify upstream Makefiles to accommodate our project.

Retain `scripts/build-pkg.sh` only as a **thin orchestrator**: validate inputs/environment; prepare upstream tree, sources and private bundled files; invoke official build; verify output; deliver existing `dist/` artifact contract.

Remove hand-written `get_make_var()` parsing by `sed` for computed Make variables, `dep_origin()` mappings, synthetic dependency version `"0"`, custom `plist`/`+MANIFEST` generation, and parallel production package creation code that native `Mk/plugins.mk` already owns.

**All** development, testing-package and stable-release builds use the same mechanism. Publication, CI and release-authority policies remain distinct.

## 6. System dependencies: FreeBSD pkg is authoritative

Classify every actual external component as `runtime`, `build-only`, `test-only`, `bundled private` or `optional`. Audit at least Python, `git`, `jq`, `luajit`, `pkgconf`, `gmake`, PHP/OPNsense-provided tools, and all other executable dependencies actually reached by installed code.

Use official `PLUGIN_DEPENDS` for true mandatory runtime packages. Prefer no exact version pin unless proven necessary; trust native `pkg` for installed versions and origins. Distinguish base system tools from extra packages. Do not promote build/test-only dependencies to runtime merely because tests mention them.

Follow official HAProxy, ACME and ddclient Python-flavor examples using `py${PLUGIN_PYTHON}-...`, while independently verifying the **real package name and origin for the Python interpreter itself** in the target FreeBSD repository. Do not assume `python${PLUGIN_PYTHON}` and `/usr/local/bin/python3` are equivalent without checking the actual generic link and packages.

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

A simple shebang rewrite is insufficient if a PHP, configd or shell caller still contains a versioned path; verify **real** caller-to-callee contracts.

## 8. Installed package lifecycle and four manual hooks

Official `Mk/plugins.mk` provides `scripts-manual`. Keep `pkg/+PRE_INSTALL`, `+POST_INSTALL`, `+PRE_DEINSTALL` and `+POST_DEINSTALL` as full authoritative manual package scripts; verify generated scripts are not unexpectedly appended/replaced by auto hooks.

During a package replacement, incoming `+PRE_INSTALL` can run **before new files or the new installed manifest exist**, interacting with the previously installed service/old hooks. No new pre-install dependence on an unavailable launcher/JSON/runtime file. Test actual `pkg` ordering.

Keep configd watcher/action registration, template updates, lifecycle lock/FD9, foreign/incomplete IPFW refusal, service RUNNING/STOPPED state, safe interrupted-operation recovery, transaction atomicity, restoration and extra-resources operations. No speculative old-version transition branches under DEV-050; immediate current-operation rollback and cleanup remain mandatory.

## 9. OPNsense ABI, FreeBSD ABI and repository publication

Use official OPNsense product ABI discovery (e.g. `opnsense-version -a`) and actual FreeBSD `pkg`/build ABI; compare **each separately** to the matrix. Do not mistake OPNsense `PLUGIN_ABI=26.7` for `FreeBSD:15:amd64`. Do not silently trust missing-environment fallback values as proof of support.

Keep FreeBSD 15.0/15.1 VM versions only where needed as reproducible test selections, not as independent runtime locks. New Python/FreeBSD/OPNsense support requires qualification before changing the matrix.

Preserve `dist/`, signed/hashed artifact provenance, GitHub Release/Pages repo index generation and immutable existing published assets. Align `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf` and release workflows to one verified package ABI. If concrete repo URLs are required, **render/verify** them from the validated build output rather than manually maintaining a divergent constant.

The same native package build path is mandatory in `.github/workflows/ci.yml`, `testing-package-delivery-ci.yml`, `publish-prerelease.yml` and `release.yml`.

## 10. Entire-repository audit, exceptions and known work groups

Before implementation, scan the **exact then-current Git tree** and provide a path/line audit, dependency classifications, allowed exemptions and a tested plan for each affected caller. The prior audit is only an investigation baseline and is **not** a complete final-file inventory.

Required groups:

| Group | At least these files and integrations |
|---|---|
| Identity/policy | `Makefile`, `VERSION`, new `compatibility.json`, schema/validator tests |
| Build | `scripts/build-pkg.sh`, `scripts/build-curl-impersonate.sh`, private launch scripts and staging |
| Package lifecycle | four `pkg/+...` scripts and generated hooks |
| Runtime and Python | `src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh`, `setup.sh`, `setup_transaction.sh`, `strategy_lab_python_launcher.sh`, Python entrypoints and backend modules |
| GUI/configd | `src/opnsense/service/conf/actions.d/actions_zapret.conf`, `src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/IPSetPolicyBridge.php` and other actual callers |
| Publication | `scripts/build-pkg-repository.sh`, `repository/zapret2-restyle.conf`, `scripts/verify-release-package.sh` |
| CI/tests/docs | the four package workflows, targeted tests and fixture exceptions, `README.md` only if user-facing facts change, current docs and navigation |

Versions in historical records, golden fixtures, explicitly reproducible CI environments, GitHub Actions tags, immutable upstream resource SHA and demonstrated safety locks are permitted **only as classified, tested exceptions**. No broad exclusions that conceal live production version locks. Audit all files, **do not rewrite all files**.

## 11. Mandatory CI and regression gates

- **CI-01 Full-tree coverage:** scan active production/build/CI sources; classify every literal external version, executable and ABI; use narrow documented allowlists.
- **CI-02 Matrix:** validate schema and positive supported combination; negative invalid/missing matrix, unsupported OPNsense product ABI/FreeBSD ABI/Python, inconsistent capabilities and unsupported architecture.
- **CI-03 Python:** test actual shell, PHP, configd, package-hook, shebang and Python-child paths; preserve args, stdout/stderr, exit status and timeouts; reject absent/unsupported interpreter, wrong link and missing module.
- **CI-04 Native build:** verify genuine upstream `Mk/plugins.mk`, exact upstream revision, single standard `make package` path and correct product/source identity.
- **CI-05 Package metadata:** inspect the **real built `.pkg`** for version, name, ABI and real `pkg`-derived name/version/origin; reject fake `version: "0"`.
- **CI-06 Package contents:** compare old/new necessary files, execute permissions, rc/configd/templates, four manual hooks, private `curl-impersonate` resources and OPNsense annotations. Metadata changes need not be byte-identical.
- **CI-07 Regression:** preserve GUI/API, Start/Stop/Restart/Status, Strategies Apply, Strategy Lab, Voice/IPSet/Exclude, setup/removal, FD9, IPFW owner and restoration paths actually affected by changes.
- **CI-08 Negative injection:** deliberately insert a forbidden hard-coded Python version, wrong ABI, fake dependency version or divergent matrix in an isolated test; each corresponding guard must refuse it.
- **CI-09 Evidence honesty:** separately report source checks, isolated FreeBSD/native package checks and actual owner-installed OPNsense evidence. Unexecuted/waived IPv6/WAN/Voice scenarios are not `PASS` and do not automatically reopen prior accepted scope.

Use DEV-051 and GH-062: run fast relevant checks on real generated/consumed artifacts **before** long CI or a product PR. Preserve ordinary project documentation, link-integrity and governance checks.

## 12. Ordered implementation stages — separately authorized

| Stage | Work | Required exit evidence |
|---|---|---|
| 0. Exact baseline | current SHA; all-file/version/entrypoint audit; old package manifest/files/permissions; exception list | reproducible path/line map and baseline |
| 1. Policy | JSON schema/source, policy validator, positive/negative tests | single consistent authoritative matrix |
| 2. Python | shared interpreter contract across all real entrypoints, remove duplicated decisions | consumer-level tests and unchanged runtime behavior |
| 3. Native packaging | official temporary tree, `PLUGIN_PYTHON`, native pkg deps/hooks, stage private artifacts, ABI and repo alignment | real native-built `.pkg` and inspected manifest/files |
| 4. CI/acceptance | cross-tree guards, generated artifacts, focused regressions, platform-only checks where required | all acceptance gates evidenced without false PASS |

Implementation stages must be split into minimal, testable increments and follow current project PR/version governance. Documentation acceptance does not authorize the implementation.

## 13. Binding final acceptance criteria

| ID | Required result |
|---|---|
| AC-01 | All production Python entrypoints use one validated interpreter contract |
| AC-02 | No independent minor-version Python executable or path in feature code |
| AC-03 | FreeBSD `pkg` owns system dependencies and the resulting `+MANIFEST` contains actual name/version/origin |
| AC-04 | One matrix defines qualified OPNsense product ABI, FreeBSD package ABI, CPU architecture and Python policy |
| AC-05 | Official, provenance-attested `Mk/plugins.mk` / `make package` builds every package type |
| AC-06 | GUI, configd, service, Strategies, Strategy Lab, Voice, installation/removal and relevant recovery behavior are retained |
| AC-07 | Product/package names, `zapret` service key, `VERSION`, `PLUGIN_REVISION` and separate Zapret2 engine version policy are unchanged |
| AC-08 | All required installed files, permissions, four manual hooks and native state/rollback safety invariants are retained |
| AC-09 | CI rejects reintroduced fragmented version policy and inconsistent package/compatibility artifacts |
| AC-10 | Documentation and evidence accurately distinguish intended scope, source implementation, CI/package proof and owner-installed acceptance |

All criteria are required to close the future engineering implementation, not the current documentation PR.

## 14. Required final implementation report

Report exact source/upstream SHA, matrix schema/hash, package SHA-256, full-tree exceptions and touched files, `pkg query` dependency metadata and extracted `+MANIFEST`, FreeBSD/OPNsense ABI, old/new package content/mode comparisons, actual fast checks, CI links and any on-appliance evidence. List skipped/unverified cases explicitly. Publication and upgrade commands only apply if the owner separately requests a testing package or release.

## 15. Explicit prohibitions

Do not create a new package/dependency manager, custom Python version manager, altered OPNsense build-system fork, parallel package builder, speculative platform adapters, legacy product fallbacks, or an indiscriminate production code rewrite. No service rename; no change to engine version ownership.

The approved specification is the normative specialist contract for this **new** scope. Its publication is **documentation only**. The next action is a detailed per-file plan; implementation and new package/release publication require a separate owner instruction.

## 16. Official reference implementation

- [OPNsense defaults and native Python variables](https://github.com/opnsense/plugins/blob/stable/26.7/Mk/defaults.mk).
- [OPNsense native plugin builder](https://github.com/opnsense/plugins/blob/stable/26.7/Mk/plugins.mk).
- [Official HAProxy plugin](https://github.com/opnsense/plugins/blob/stable/26.7/net/haproxy/Makefile).
- [Official ACME plugin](https://github.com/opnsense/plugins/blob/stable/26.7/security/acme-client/Makefile).
- [Official ddclient plugin](https://github.com/opnsense/plugins/blob/stable/26.7/dns/ddclient/Makefile).

**Approved architecture:** project source → isolated complete official OPNsense tree → native `PLUGIN_PYTHON`, `Mk/plugins.mk` and FreeBSD `pkg` → exact package/metadata → unified compatibility matrix and Python execution contract → CI and evidence-based acceptance.

General canonical rules remain in [PROJECT_PRINCIPLES.md](../PROJECT_PRINCIPLES.md); current priority/handoff remain in [ROADMAP.md](../ROADMAP.md) and [START_HERE.md](../START_HERE.md).

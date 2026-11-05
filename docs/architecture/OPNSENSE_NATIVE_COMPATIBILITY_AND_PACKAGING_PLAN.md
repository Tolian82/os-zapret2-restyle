# Native OPNsense Packaging — Concrete Completion Plan v1.5

**Authority:** [Owner-approved TЗ v1.5](OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md).
**Decision:** 5 November 2026. Standard native OPNsense integration is primary; external pkg trust infrastructure and extra IPFW/PF work cancelled.
**Baseline:** `main` `a20c310aa181a8ed6b0b586c07b87d98d94cc2ec` / `v0.6.2_135`; documentation-only scope reset is `v0.6.2_136`. Published stable `0.6.2_1.pkg` and owner device unchanged.
**Document version:** v1.5 is editorial, independent of plugin/package versions. v1.4 and Stage 3.xx experiments are historical evidence, **not** current release gates.

**Stage 0 audit status: CLOSED** — historical source/target audit completed; not a new implementation task. **Stage 1 status: SOURCE/NATIVE-CI ACCEPTED** — the existing compatibility policy remains valid; this does not mean the final native installed package is accepted.

## Working rule — good and fast, not perfection at any cost

Inspect real current entrypoints and tests before writing. Fix confirmed failures against this TЗ by the smallest complete change. Reuse the native package builder and accepted functional tests. Remove checks for cancelled requirements instead of rebuilding their implementation. No new independent risk/research project without owner approval.

## Starting point — actual source, not another research stage

- `Makefile` uses `.include "../../Mk/plugins.mk"` and `PLUGIN_DEPENDS`.
- `scripts/build-pkg.sh` (19 lines) delegates to `scripts/native-opnsense-package.py`. This is **already written** and has native CI coverage; complete it rather than start a second package engine.
- `compatibility.json`, the `zapret` service, GUI, Strategies, Voice, Exclude, Lab and Extra Resources are present.
- Merged `_138` [PR #908](https://github.com/Tolian82/os-zapret2-restyle/pull/908) proved native dependency ownership/no stock repo writes with 15/15 exact-head CI PASS and postmerge main CI PASS. Merged `_139` [PR #909](https://github.com/Tolian82/os-zapret2-restyle/pull/909) passes 15/15 exact-head workflows, real Mk package build/clean install and postmerge main CI. `_140` [PR #910](https://github.com/Tolian82/os-zapret2-restyle/pull/910) merged with 15/15 exact-head native PASS and postmerge main CI. `_141` extends the disposable native installed guest to actual `pkg delete` + official firmware `register.php remove` with Config retention; active shared-owner Python-down Stop remains explicitly open.
- The cancelled experimental `backend/native_pkg_*`, standalone pre-pkg, Stage 3 external approval/FD9 tools/tests and workflows were removed in source revision `_137`. Historical evidence remains historical; source/native CI outcomes require separate verification.
- Unmerged branch `work/v0.6.2_136-offguest-host-checkpoint-ci` is abandoned. **Do not merge or develop it.**

## FIRST work package — obsolete authorization cleanup (_137 source candidate)

**Branch:** `work/v0.6.2_137-drop-cancelled-pkg-approval` from verified post-doc main `e883af146d375bcefb8243c1dd10b53355d0d4d8`; source changes must pass exact-head CI before the exit is accepted. Do not reuse the abandoned `_136` branch.

1. Check actual callers of the four `src/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_*.py` modules. Remove them if only used by the cancelled `pkg` inspection/admission experiment. Do not alter ordinary `dvtws2` runtime/GUI/Strategy Lab/Voice behavior.
2. Remove `scripts/native-prepkg-standalone.py` and cancelled `scripts/stage3-prepkg-*`, their `test-*` and related approval-only `stage3-native-configd-*`/witness tools. Check imports/callers before deletion, without conducting a new audit campaign.
3. Remove approval-only `.github/workflows/stage3-native-prepkg-archive-bootstrap.yml` and other obsolete admission workflows where they test **only** a cancelled mechanism. Clean references in `ci.yml` and remaining workflow path filters. **Keep stage0/stage2 tests** that prove real pkg hooks, service FD9, ABI, dependencies or actual installation, even if names include `pkg` or `fd9`.
4. Keep fixed **IPFW rule numbers** documented in TЗ, README and architecture: normal Zapret2 `19000–19010`, Lab `19100–19131`. These are not port ranges. No new rule collision scanner, foreign-rule inspection, dynamic numbering, shaper-flush monitor or automatic restoration.
5. **Mandatory post-deletion technical documentation review:** search active `docs/architecture/`, `README.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `START_HERE.md`, `PROJECT_STATE.md`, `ROADMAP.md`, `INDEX.md`, release/package guidance and CI docs. Remove or correct remaining mentions of deleted approval code, outdated pre-pkg veto gates and requirements conflicting with v1.5. Historical git evidence is not an active dependency. Check links.
6. Run fast syntax/import/doc reference checks before opening the PR, then exact-head relevant CI. Do not trigger expensive witness or package experiments that test code no longer in scope.

**Exit:** no active consumer of cancelled auth modules, no obsolete mandatory CI jobs, all active technical docs coherent, existing native builder/runtime untouched, relevant CI PASS. No package publication.

## SECOND task — finish the existing native OPNsense package

**Files:** `Makefile`, `scripts/build-pkg.sh`, `scripts/native-opnsense-package.py`, package verifier and native CI.

1. Qualify existing official `Mk/plugins.mk` staging and `make package`, target OPNsense catalog, ABI and `PLUGIN_PYTHON`.
2. Fix actual build/install gaps only: package metadata, package modes, four hooks, private `curl-impersonate` ELF/providers, missing artifacts and installed paths.
3. Install the resulting real `.pkg` on a disposable OPNsense 26.7 via `pkg` and test registration. Retire artificial source-only build restrictions only when the native path is actually ready.
4. No custom manifest or second packaging engine.

**Observed in `_137`:** official Mk native build and genuine disposable OPNsense 26.7 clean `pkg` install, files/manifest/dependencies/four hooks/Config checks passed (PR #907 exact-head CI and postmerge main CI). This validates the existing builder for its tested source, not the final release SHA or owner device.

**Exit:** one source SHA produces a real native installed package with correct manifest, dependencies, files and hooks. For the tested `_137` build this is qualified; repeat for the final candidate.

## THIRD task — system dependencies and one Python contract

**Completed `_138`:** setup dependency provisioning belongs to native OPNsense `pkg`, no FreeBSD repo mutating operation; source/native tests passed and merged. **Completed `_139`:** validated generic Python entrypoint and real callers accepted in native CI. **Completed `_140`:** bounded Python-down ordinary Strategies Stop/Status under FD9 with installed cold Status/Stop/Start refusal (15/15 exact-head CI PASS). **Current `_141`:** real disposable package deletion under native pkg hooks and OPNsense `register.php remove`, preserving configuration and shared system dependencies. **Remaining:** active shared owner Python-down teardown, full service/boot/Firmware GUI lifecycle, final package SHA; no Stage 3 revival.

**Files:** `setup.sh`, `setup_launcher.sh`/`setup_transaction.sh`, backend shell/Python, Strategy Lab, Voice, Extra Resources, PHP APIs, `actions_zapret.conf` and hooks.

1. `PLUGIN_DEPENDS`/target OPNsense `pkg` own mandatory system tools. Remove the stock FreeBSD repository toggle and redundant package installs in setup; retain the separate upstream Zapret2 engine selection/build process.
2. Consolidate real production interpreter entrypoints to qualified `/usr/local/bin/python3` with `sys.executable` for Python children and central `compatibility.json` policy. Remove only genuinely active hard-coded minor paths.
3. Exercise actual changed consumers and preserve args, JSON, timeout, FD9 service behavior and existing Start/Apply safety. Keep ambiguous leftover repo configuration read-only with diagnostic guidance, not a recovery subsystem.

**Exit:** native install provides necessary dependencies and all changed callers run with the supported Python without manual intervention.

## FOURTH task — normal native service and four lifecycle hooks

**Accepted `_140`:** verified ordinary Strategies Stop/Status without Python under FD9, installed cold Status/Stop/Start-refusal PASS. **Current `_141` slice (source-only pending CI):** after real native clean install and packaged configctl, exercise real `pkg delete -y` with original installed four-hook bodies, verify package file/pkgdb removal and no restart markers, then OPNsense official `register.php remove` and retained Config. Do **not** run global `pkg autoremove`; do not claim active running-owner/UI click/boot acceptance. Shared journal, seal and IPFW adapter remain Python dependent.

**Files:** `pkg/+PRE_INSTALL`, `pkg/+POST_INSTALL`, `pkg/+PRE_DEINSTALL`, `pkg/+POST_DEINSTALL`, `zapret_service.sh`, `actions_zapret.conf`, `zapret.inc` and rc.syshooks.

Test actual fresh installation, Start/Stop/Restart/Status/Apply, boot integration, updates from `0.6.2_1` in RUNNING and STOPPED, forced reinstall, removal, Config retention and bounded failure behavior. Use existing OPNsense services and local FD9 where necessary; no managed pre-pkg gateway.

**IPFW/PF:** no new numbered-rule management, scanner, foreign rules analysis, shaper-flush study or `pfilctl` conversion. Keep existing `pfctl -d; pfctl -e`. The implemented safe cold-IPFW initialization is checked with ordinary installed Start.

**Exit:** standard service and lifecycle works correctly on isolated target, no independent package authorization infrastructure.

## FIFTH task — CI consistency and final acceptance

Make `ci.yml`, testing/release and Pages delivery use one native package builder. Run relevant installed regressions for Strategies, Voice, Exclude, Lab, Extra Resources and service. Bind results to the exact **final native package SHA-256**. Record previous IPv6/WAN/Voice-media waivers as NOT TESTED where applicable; do not reopen closed campaigns or claim PASS without observations.

**Exit:** one qualified installable candidate, all applicable AC-01–AC-11 evidenced, and a short factual completion report. Owner separately authorizes any testing/stable publication or installation on their appliance.

## Non-goals that must not grow back

No external update approval server, SQLite/RSA witness, cryptographic one-use grant, root warning or pkg interceptor, universal PRE_INSTALL veto, independent managed updater, IPFW collision/ownership survey, automatic shaper-flush recovery, `sync_fw_hooks.py`/`pfilctl` conversion or speculative pfSense port. No new Stage 3.xx research microstages.

**Principle:** finish the actual native OPNsense product with the smallest justified engineering effort.

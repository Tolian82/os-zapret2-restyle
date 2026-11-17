# TZ6v2 native form/Apply source ownership — STEP 2 audit

Source: merged `_88` main `332459da115951ad7bd42a09fe38089cc67d8751`; source-only, not installed acceptance.

- `IndexController::indexAction` and native `forms/general.xml` own original Enabled checkbox, Advanced Auto Restart and manual YouTube/User textareas; KEEP original rows/controls.
- `Zapret.xml` owns Enabled Boolean and independent Auto Restart Off/hour/day/week/month OptionField, default Off; KEEP.
- `general.volt` owns bottom `reconfigureAct` Apply and current standalone Auto Hostlist Save/Reload; REWORK Save/Reload only after protected common Apply accepts all five sources.
- `SettingsController::applyAction` owns WAN-first Config lock, `SettingsApply::prepareStrategies`, Python domain/IPSet policy and root `zapret shared_apply` envelope; REUSE original FD9 and no second Config writer.
- `auto_detect_config_snapshot.php` and original protected source files own native Config+HOSTLIST read and separate discovered YouTube/User/fallback entries; REUSE with coherent five-list revisions.
- Original shared Apply and managed effective HOSTLIST/auto-detect owner handles one service and minute updates; VERIFY same-PID hot reload, Voice/WAN/IPFW/ACK.

**Confirmed user-facing defect:** old JS `mountAdvancedAutoRestart` removed the native advanced schedule row and reparented its dropdown into Enabled. The source fix leaves the original native form rendering and existing localized option labels; a focused test parses original Form XML+Model and rejects this JS reparent. Pre-fix fails, candidate source passes; native rendered/browser and schedule lifecycle NOT TESTED.

**Open by TZ6v2:** canonical positive found-only grammar, three automatic editors with revisions, locked three-way merge/atomic Apply, five-source F5 and RU/EN Help, actual scheduled RUNNING/STOPPED behavior, same-PID hot reload, native .pkg and owner install/update/uninstall/purge.

## First exact-head installed-browser evidence and corrected acceptance target

At candidate `963e613e` the native OPNsense clean package installation and native lower WAN Apply/F5 persistence succeeded in [browser run #44127986792](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44127986792). The next English Chromium check then **failed** because the old `p3-browser-i18n.py` acceptance still insisted on the superseded inline `#zapretAutoRestartInline` inside Enabled row. This does **not** prove that the new native row renders correctly; the test had not inspected that required row at all. Its owner-approved expected DOM must be the original independent `row_zapret.general.autorestart`, native advanced show/hide and independent Enabled, with unchanged five option values, Off default and preservation across hide/show. The same installed Chromium test is now corrected to assess that real native row, not a fabricated duplicate or source-only mock.

First-head [P5c #44127987088](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44127987088) reached an actual native plugin clean installation but its unrelated upstream zapret2 setup returned GitHub releases API `Forbidden` and `G03_SETUP_WORKER_REPORTED_FAILURE`, *before* P5c unsaved strategy preview. That run is NOT product preview acceptance and is NOT evidence of this GUI layout defect. The old head's source policy and Project validation failed because `docs/PROJECT_STATE.md` omitted exact `v0.6.5_89`/`VERSION`/`PLUGIN_REVISION`/package identity. This was a documentation guard error and is corrected in the next source-only fixup; no new product runtime or hook change. **All candidate native UI acceptance remains OPEN until exact relevant check passes.**

## Completed native GUI-only qualification and next P1 editor increment

PR [#1183](https://github.com/Tolian82/os-zapret2-restyle/pull/1183) was merged to main `_89` (`f45eddeda354110dd24709e8e72991e29744bbd6`). The exact source head [#44129229425](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44129229425) really installed the native package and Chromium verified native separate Enabled/Advanced-only Auto Restart, RU/EN, Off/five choices, Advanced hide/show draft retention, and WAN lower Apply/F5. Independent CI [#44129229343](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44129229343) PASS. No published binary and no owner appliance mutation. The previous source-audit text above was written *before* this actual browser result; the native-row UI gate is now PASS **only for this exact scoped candidate**. Original schedule RUNNING/STOPPED behavior remains OPEN. P5c [#44129229370](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/44129229370) failed upstream releases HTTP Forbidden before exercising preview; no P5c acceptance claim.

`_90` adds new **read-only pure editor inspection CLI** in the existing canonical P1 module. This does NOT wire UI/editor snapshot/three-way locked Apply, nor alter existing automatic minute producer. It is an integration building block, not a completed GUI or new published package.

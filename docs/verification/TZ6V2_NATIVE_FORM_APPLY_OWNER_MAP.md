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

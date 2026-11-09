# G07 — Lifecycle Start/Apply/status RU/EN acceptance

**Current status (9 November 2026):** `v0.6.3_24` LC-09 **source/GUI candidate**. Exact-head CI and installed OPNsense G07 S2 pending. Do not claim A10/A16/A17 or owner-live until their receipts exist.

## LC-09 concrete defect and correction

Before `_24`, `general.volt` labelled a genuinely uninstalled upstream `Error` and displayed hard-coded English `not installed` in both locales. Also `ServiceController::getRuntimeState` defaulted `installed=false,busy=false` for blank or incomplete `setup_status`, so `installAction` could launch a new setup even when lifecycle ownership had not been verified.

`_24` preserves the stock `setup_launcher.sh status` and original FD9. The controller accepts only a complete set of five unique, syntax-checked status keys (`installed,service,version,setup,busy`). Null/invalid/duplicate fields return `status=unavailable`, `installed=null`, `reason=status-unavailable`; the release installer refuses an ambiguous status before `configdpRun('zapret setup_install')`. Malformed status never aliases a clean missing runtime.

GUI classifier shows **exactly** `Не установлен / Not installed`, `Установка… / Installing…`, `Остановлена / Stopped`, `Запущена / Started`, `Ошибка / Error` as a single label, from verified backend evidence. Missing upstream `installed=0,service=error,setup=unknown,busy=0` is **Not installed**. Busy+installing displays **Installing**. A partial/malformed/conflicting receipt displays **Error**, with `status-unavailable` diagnostic, not an extra `Needs review` status or a fake Start. The release installer is blocked if status cannot be verified.

## Evidence and boundaries

Focused `scripts/test-g07-runtime-status.mjs` extracts and executes the actual GUI classifier, with all five states and malformed counterexamples. Existing `scripts/test-gui-runtime-management.sh` validates controller/source contracts and invokes the focused test; existing setup transaction test remains unmodified. On exact head, central CI is required. This proves **source contracts**, not a live button or native Start.

**Next gate:** one scoped installed OPNsense 26.7 first Start/Stop/Restart/lower Strategies Apply, real dvtws2 PID/FD9/IPFW and native diagnostics. WAN-first must preempt engine/profile failures; WAN-only Save, Stop and initial install remain available without WAN. Verify both GUI locales, HTTP failure visibility and reload on disposable guest; physical owner browser and real WAN/Voice media are separate. No new service manager or change to the existing WAN resolver.

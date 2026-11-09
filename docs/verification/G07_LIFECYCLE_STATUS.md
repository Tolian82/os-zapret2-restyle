# G07 — Lifecycle Start/Apply/status RU/EN acceptance

**Current status (9 November 2026):** `_24` five native runtime/GUI statuses and fail-closed Install [PR #998](https://github.com/Tolian82/os-zapret2-restyle/pull/998) merged 5/5 exact-head SUCCESS; G03 real first upstream [PASS #42675710441](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42675710441) and stopped real Chromium WAN lower Apply/F5 [PASS #42675710785](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42675710785). `_25` exactly one native authenticated HTTPS Start/Stop/Restart and Strategies Apply acceptance candidate PENDING; A10/A16/A17 owner-live and physical WAN/Voice/media remain OPEN.

## LC-09 concrete defect and correction

Before `_24`, `general.volt` labelled a genuinely uninstalled upstream `Error` and displayed hard-coded English `not installed` in both locales. Also `ServiceController::getRuntimeState` defaulted `installed=false,busy=false` for blank or incomplete `setup_status`, so `installAction` could launch a new setup even when lifecycle ownership had not been verified.

`_24` preserves the stock `setup_launcher.sh status` and original FD9. The controller accepts only a complete set of five unique, syntax-checked status keys (`installed,service,version,setup,busy`). Null/invalid/duplicate fields return `status=unavailable`, `installed=null`, `reason=status-unavailable`; the release installer refuses an ambiguous status before `configdpRun('zapret setup_install')`. Malformed status never aliases a clean missing runtime.

GUI classifier shows **exactly** `Не установлен / Not installed`, `Установка… / Installing…`, `Остановлена / Stopped`, `Запущена / Started`, `Ошибка / Error` as a single label, from verified backend evidence. Missing upstream `installed=0,service=error,setup=unknown,busy=0` is **Not installed**. Busy+installing displays **Installing**. A partial/malformed/conflicting receipt displays **Error**, with `status-unavailable` diagnostic, not an extra `Needs review` status or a fake Start. The release installer is blocked if status cannot be verified.

## G07 native Stage 2 (`_25`) — actual Start/Stop/Restart

`scripts/stage2-opnsense-g07-native-lifecycle.py` reuses genuine G04 same physical archive install and real dvtws2 v1.0.7 on ONE disposable OPNsense 26.7 guest. The browser-equivalent cookie/CSRF HTTPS Start must first refuse missing saved WAN with explicit `Select a WAN interface` and unchanged Config/PID/IPFW. Save `lo0` WAN while disabled (G04 has a prior committed journal, so the existing full FD9 Apply may correctly return `applied=true`), verify Stopped and zero owned IPFW/PID; first lower Apply enables one genuine no-action engine under original FD9. The same HTTP Stop, Start, Restart must show verified Stopped/Started and real PID transitions without new FD9 code. Lower Apply adds and removes scoped ordinary TCP 65431; invalid profile must refuse without Config/runtime/firewall mutation. Final native Stop and foreign Config/IPFW are checked.

This S2 is pending until its exact-head native PASS. The earlier real Chromium #42675710785 verifies STOPPED WAN save/F5 only, **not** actual browser Start/Restart, physical WAN, IPv6, real DPI or voice media.
## Evidence and boundaries

Focused `scripts/test-g07-runtime-status.mjs` extracts and executes the actual GUI classifier, with all five states and malformed counterexamples. Existing `scripts/test-gui-runtime-management.sh` validates controller/source contracts and invokes the focused test; existing setup transaction test remains unmodified. On exact head, central CI is required. This proves **source contracts**, not a live button or native Start.

**Next gate:** one scoped installed OPNsense 26.7 first Start/Stop/Restart/lower Strategies Apply, real dvtws2 PID/FD9/IPFW and native diagnostics. WAN-first must preempt engine/profile failures; WAN-only Save, Stop and initial install remain available without WAN. Verify both GUI locales, HTTP failure visibility and reload on disposable guest; physical owner browser and real WAN/Voice media are separate. No new service manager or change to the existing WAN resolver.

# G08 — Installed Standard/Extended Lab before first ordinary Start

**Current scope (9 November 2026):** `_26` real OPNsense 26.7 S2 PASS [#42681458370](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42681458370), [PR #1000](https://github.com/Tolian82/os-zapret2-restyle/pull/1000) merged. Both genuine HTTP Lab jobs completed Stage40 TARGET_ACCESSIBLE, Stage50 SKIPPED, Stage90 STOPPED PASS. Not real blocked-target search or owner-live bypass.

## Exact native qualification

Use **one** disposable OPNsense 26.7 guest, not an already started G04 guest. G05 performs first real cookie/CSRF WAN-only Save **before upstream exists**, proving WAN-first and then engine-second refusals without a Job or dvtws2. It leaves saved `wan`, `Enabled=0`, explicitly user-empty Traffic Strategy and YouTube Domains, no shared original-FD9 commit journal. G03 installs and reinstalls genuine `v1.0.7` via stock configd without starting the normal service. Retain the exact package SHA. None of these steps may invoke normal dvtws2 Start.

After authenticated native Status=Stopped, run the actual packaged `/api/zapret/strategy_lab/start/status/result` twice (Standard RU and Extended EN) against the established externally reachable TLS control `yandex.ru`. Require two distinct real `job.*` IDs, stages 00/10/20/30/40/90 PASS, Stage-90 `restoration.verified=true` with `initial_state=STOPPED` and `final_state=STOPPED`, final service actually Stopped, no dvtws2 PID, no owned 19000–19131 IPFW, unchanged byte-exact Config and foreign firewall, no shared ordinary owner. Cancel on failure without reporting a false PASS.

**Scope boundary:** a genuinely accessible public control stops at Stage 40 with `TARGET_ACCESSIBLE`; Stage 50 search is **SKIPPED**. This proves real Job + network/probe/STOPPED restore before first normal Start, *not* desync candidate discovery or DPI bypass. The blocked-target Stage50→60 investigation and real NO_CANDIDATE/failure handling remain G09; cancel/timeouts and owner-live must be separately qualified. No production Lab/FD9/IPFW/WAN implementation changes in `_26`.

**Evidence:** G05 early WAN-first + missing engine native #42646971454; G07 real installed Start/Stop/Restart [#42678641429](https://github.com/Tolian82/os-zapret2-restyle/actions/runs/42678641429). G08 native run evidence **PASS #42681458370**; G09 searches a separate unreachable negative control.

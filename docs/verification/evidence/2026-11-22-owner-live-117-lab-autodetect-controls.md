# Owner-installed `_117` — native Auto, Lab restore and GUI lifecycle incidents

**Date:** 2026-11-22. **Status:** documented *before* root-cause investigation or implementation. Exact user-provided status and screenshots. Related [#1223](https://github.com/Tolian82/os-zapret2-restyle/issues/1223), [#1224](https://github.com/Tolian82/os-zapret2-restyle/issues/1224), [#1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225); [approved TZ_6v4](../../architecture/TZ_6v4.md).

## Observed facts (chronology and evidence boundaries)

| Step | Observed owner evidence | Proof and limitation |
|---|---|---|
| Install | `_117.pkg` SHA-256 `6bdbfae46b2b2d56f16b92eebd573d7cf0fbb3bcc0ee527c45a2c92a1e2c9e7d`; `pkg-update=verified-installed-and-restored`; installed `os-zapret2-restyle-0.6.5_117`; status `zapret is running` | Physical protected update PASS, not Lab or Auto acceptance |
| Strategies no-edit Apply | Owner clicked `Применить`; subsequent service status `zapret is running` | Prior GUI refusal resolved for no-edit path, not all handlers |
| Strategies edited Apply | Edited `Домены YouTube`, clicked `Применить`; service `zapret is running` | Edited path visible PASS, not auto Found/P1 evidence |
| Auto test | `youtube.com` absent from manual YouTube list but active discovery strategy; not observed in any Found list after `Тестирование соединения с доменом`=`=== Result: TIMEOUT ===` | Desired auto journey OPEN; no native append/capture proved |
| Router curl | `curl -v https://www.youtube.com` twice stalled after IPv4 TLS ClientHello to `216.239.38.119` before operator `Ctrl+C`; second IPv6 `2001:4860:4802:32::77` `No route to host` | Interrupted HTTPS attempts do not prove full failure counter, native profile hit or native inbox write |
| Lab job | `job.iDvhRh` stage 90 `Восстановление Zapret2` `ОШИБКА RESTORE_FAILED — Исходное состояние Zapret2 восстановить не удалось.`; stage 99 `Итоговый отчёт` same | Restoration FAIL. Stage 99 can be downstream summary; no post-Lab status observed. |
| Attached toolbar screenshot | Three icon-only controls: green Play triangle, circular-arrow, white Stop square | Visual presence only. Tooltips, handlers and real semantics unverified. |

**Critical:** all owner `zapret is running` outputs precede the Lab run with `RESTORE_FAILED`. Do **not** label post-Lab service RUNNING. Do not rerun Lab, Start/Stop/Restart/Apply or alter original journals on owner device pending read-only evidence.

## Unproven candidate causes

- Shipped schema3 learning clone generator omits former explicit `--hostlist-auto-fail-threshold=1`, leaving upstream default 3 within failure time window; both old and new explicitly set `--hostlist-auto-retrans-reset=0`. This is a candidate source regression **not proved sole ISP cause**. `www.youtube.com` SNI is distinct from initial `youtube.com` name before normalization.
- Direct HTTPS `TIMEOUT` does not force Auto detection; manually aborted TLS requests may never reach required failure criteria. Need actual IPFW capture, native profile-N event in its dedicated `--hostlist-auto`, debug, original minute P1/ACK, protected persistent YouTube Found and active managed HOSTLIST.
- Lab stage 90 requires actual job provenance and predecessor owner/epoch inspection. Stage 99 may be reporting the earlier failure, not a second restoration attempt.

## User-requested same-intent control and lifecycle parity matrix

| Surface | Action | Required proof and current status |
|---|---|---|
| Strategies | Green Play triangle | Screenshot only. Identify tooltip, frontend→configd handler, protected original FD9 Start, valid already-RUNNING/STOPPED semantics and exact engine state. OPEN |
| Strategies | Circular-arrow icon | Screenshot only. Confirm Restart vs Reconfigure by tooltip/code, original protected old-epoch retirement/new engine or non-disruptive reconfigure, error receipt. OPEN |
| Strategies | White square Stop | Screenshot only. Verify original protected Stop, P1/ACK and old-N retirement, Config retained, owned IPFW cleanup. OPEN |
| Voice Transmission | Same three icons | Owner explicitly requests equivalence for same intent and lifecycle, Voice/IPFW safety, correct state/disabled/feedback; no handlers yet verified. OPEN |
| Zapret2 Service | Stop / Start (Restart where shown) | Verify actual backend vs toolbar routes, original FD9/Config/epoch/IPFW, exactly one dvtws2, negative guards and truthful completion. OPEN |
| Strategies | `Применить` unchanged | Actual owner-visible `status` RUNNING. PASS for the symptom; deeper list/epoch persistence unverified. |
| Strategies | `Применить` edited YouTube Domains | Actual owner-visible `status` RUNNING. PASS for the symptom; true managed list/Auto P1 unverified. |
| Voice Transmission | `Применить` unchanged/edited | Must use original FD9/Config and Voice IPFW transaction with rollback; currently untested. OPEN |
| Strategy Lab | Start / temporary stop / cancel / timeout / restore | Stage 90 + 99 `RESTORE_FAILED`. Must restore exact predecessor RUNNING→RUNNING or STOPPED→STOPPED and signed Config/IPFW/Voice/epoch on all outcomes, no false green status. FAIL/OPEN |
| `Установить версию` | Version installation | Verify if upstream engine installer, not assume it is `.pkg` upgrade; protect active dvtws2, Config/IPFW/FD9, version receipt/rollback and saved state. OPEN |

**Equivalent action** means same protected owner and outcome for the same user intent, not identical shell command for different operations (Apply vs Lab vs upstream version installation). No SIGSTOP/CONT for learning, second Config writer/daemon, PID journal deletion or unguarded `pkg add -f` on an installed running plugin.

## Ordered acceptance after documentary checkpoint

1. Read-only status and full original owner epoch/operation-journal/Config/IPFW/process census **AFTER** Lab; preserve events and current state, no repair action.
2. Trace real UI→configd→service→FD9 for every control, with exact before/after model and receipt; reproduce stage 90 failure on disposable RUNNING and STOPPED native test owners.
3. Native Lab success/error/timeout/cancel cleanup and recovery must restore exact state and avoid partial IPFW or extra engine; verify stage 99 truthful reporting.
4. Separately reproduce real native TCP feedback, profile-N inbox and original minute/P1/ACK/Found→managed without restart. Distinguish missing threshold from missing divert capture, unsafe source binding or no native event.
5. After root cause and narrow RED→GREEN tests, exact-head disposable OPNsense CI, protected pkg upgrade and one immutable testing `.pkg` before **owner** re-acceptance. No stable/pfSense promotion from this record.

**Outcome of this checkpoint:** tracked and fully documented; no production code, installed package or owner runtime changed.

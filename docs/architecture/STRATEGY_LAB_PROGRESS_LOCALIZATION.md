# Strategy Lab progress and localization

## Persisted progress

Each job stores a `progress` object with percentage, stage number, stage key, and current
message. Stage transitions use a fixed monotonic mapping: 00=0, 10=9, 20=18, 30=27,
40=36, 50=45, 60=55, 70=64, 80=73, 85=82, 90=91, and 99=100 percent.

The persisted value is authoritative for live polling and reloaded active results. The
browser contains the same mapping only as a compatibility fallback for historical or
incomplete snapshots.

The validated Python module `strategy_lab_py/state.py` owns revisioned atomic progress/status writes. The browser/status path uses that persisted owner:

- the long-lived automated worker closes launcher lock FD 9 so status polling can proceed
  while the job is active;
- Diagnostics renders progress from a validated persisted job snapshot only;
- a transient empty/invalid/AJAX status read does not reset progress or fabricate ERROR;
- the last valid progress remains visible while polling retries;
- an accepted start may show the known queued Stage-00 / 0% snapshot until the first
  persisted status response arrives;
- terminal 100% still comes from the persisted Stage-99 state.

## Localization

The job language continues to select backend worker messages. Diagnostics additionally
maps every visible stage key, job/circular state, outcome, mode, progress label, UDP
validation message, profile-copy message, circular lifecycle explanation, and
transient-status retry message to Russian or English according to the selected OPNsense
language.

The non-terminal backend job state `cancel_requested` is explicitly mapped in both RU and
EN dictionaries. It must never fall through to raw technical `CANCEL_REQUESTED` rendering.
Circular `stop_requested` remains a separate machine state and has its own localized
label/message contract.

Transient status text is deliberately localized:

- RU: `Статус Strategy Lab временно недоступен. Повторная попытка…`;
- EN: `Strategy Lab status is temporarily unavailable. Retrying…`.

All dynamic backend detail text remains escaped. Internal machine keys remain stable and
untranslated in JSON.

## Verification

Mandatory focused tests exercise persisted progress at initialization, family screening,
restoration and terminal report; exact revision semantics; concurrent state mutation; and
Python-owned atomic persistence.

`scripts/test-strategy-lab-gui-status-reconciliation.sh` additionally requires persisted
progress to remain the GUI source of truth across transient reads and checks the deliberate
RU/EN retry messages. Circular messages remain covered and the historical English
`canseled` typo remains rejected.

## Source history

The [full original page](/docs/history/stages/documentation-2026-11-13/snapshots/architecture/STRATEGY_LAB_PROGRESS_LOCALIZATION.md) preserves earlier source versions, investigation notes and acceptance claims at their actual dates. [PROJECT_STATE](../PROJECT_STATE.md) owns current evidence; this page owns its bounded technical contract.

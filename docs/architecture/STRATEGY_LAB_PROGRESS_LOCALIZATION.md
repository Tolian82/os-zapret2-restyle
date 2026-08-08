# Strategy Lab progress and localization

## Persisted progress

Each job stores a `progress` object with percentage, stage number, stage key, and current
message. Stage transitions use a fixed monotonic mapping: 00=0, 10=9, 20=18, 30=27,
40=36, 50=45, 60=55, 70=64, 80=73, 85=82, 90=91, and 99=100 percent.

The persisted value is authoritative for live polling and reloaded active results. The
browser contains the same mapping only as a compatibility fallback for historical or
incomplete snapshots.

Beginning with Migration Patch 2 (`v0.3.3_19` source), Python 3.13 module
`strategy_lab_py/state.py` is the authoritative writer of the persisted `progress` object
and its revisioned `status.json` mutation. Later migration patches moved the complete
automated backend path to Python without changing the progress schema.

Migration Patch 8 (`v0.3.3_25` source) reconciles the browser/status path with this
persisted progress owner:

- the long-lived automated worker closes launcher lock FD 9 so status polling can proceed
  while the job is active;
- Diagnostics renders progress from a validated persisted job snapshot only;
- a transient empty/invalid/AJAX status read does not reset progress or fabricate ERROR;
- the last valid progress remains visible while polling retries;
- an accepted start may show the known queued Stage-00 / 0% snapshot until the first
  persisted status response arrives;
- terminal 100% still comes from the persisted Stage-99 state.

These source changes directly address the mechanism consistent with the `_17` 0%-until-
terminal observation, but they do not close that owner-observed defect without new live
OPNsense evidence.

## Localization

The job language continues to select backend worker messages. Diagnostics additionally
maps every visible stage key, job/circular state, outcome, mode, progress label, UDP
validation message, profile-copy message, circular lifecycle explanation, and Patch-8
transient-status retry message to Russian or English according to the selected OPNsense
language.

The non-terminal backend job state `cancel_requested` is explicitly mapped in both RU and
EN dictionaries. It must never fall through to raw technical `CANCEL_REQUESTED` rendering.
Circular `stop_requested` remains a separate machine state and has its own localized
label/message contract.

Patch-8 transient status text is deliberately localized:

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

Owner-assisted live evidence is still required before the `_17` progress/presentation
backlog is marked closed.

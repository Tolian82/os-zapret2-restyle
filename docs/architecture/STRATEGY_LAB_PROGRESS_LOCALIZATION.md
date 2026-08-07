# Strategy Lab progress and localization

## Persisted progress

Each job stores a `progress` object with percentage, stage number, stage key, and current message. Stage transitions use a fixed monotonic mapping: 00=0, 10=9, 20=18, 30=27, 40=36, 50=45, 60=55, 70=64, 80=73, 85=82, 90=91, and 99=100 percent.

The persisted value is authoritative for live polling and reloaded results. The browser contains the same mapping only as a compatibility fallback for historical jobs.

Beginning with Migration Patch 2 (`v0.3.3_19` source), Python 3.13 module `strategy_lab_py/state.py` is the authoritative writer of the persisted `progress` object and its revisioned `status.json` mutation. The still-shell stage machine supplies stage/status/message decisions through the thin `strategy_lab/state.sh` adapter; it no longer performs jq/temp/mv state transforms itself.

This ownership change preserves the existing percentages and public JSON. It does not by itself close the owner-observed live GUI defect where progress remained at 0% during `_17`; that remains a later GUI/status reconciliation and live-verification gate.

## Localization

The job language continues to select backend worker messages. Diagnostics additionally maps every visible stage key, job/circular state, outcome, mode, progress label, UDP validation message, profile-copy message, and circular lifecycle explanation to Russian or English according to the selected OPNsense language.

The non-terminal backend job state `cancel_requested` is explicitly mapped in both RU and EN dictionaries. It must never fall through to raw technical `CANCEL_REQUESTED` rendering. Circular `stop_requested` remains a separate machine state and has its own localized label/message contract.

All dynamic backend detail text remains escaped. Internal machine keys remain stable and untranslated in JSON.

## Verification

The mandatory focused tests exercise persisted progress at initialization, family screening, restoration, and terminal report; exact revision semantics; concurrent state mutation; and Python-owned atomic persistence. They also create a real backend `cancel_requested` state, derive its machine presentation key, and require deliberate RU and EN mappings in Diagnostics. Circular messages remain covered and the historical English `canseled` typo remains rejected.

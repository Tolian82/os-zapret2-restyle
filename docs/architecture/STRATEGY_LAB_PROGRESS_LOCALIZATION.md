# Strategy Lab progress and localization

## Persisted progress

Each job stores a `progress` object with percentage, stage number, stage key, and current message. Stage transitions use a fixed monotonic mapping: 00=0, 10=9, 20=18, 30=27, 40=36, 50=45, 60=55, 70=64, 80=73, 85=82, 90=91, and 99=100 percent.

The persisted value is authoritative for live polling and reloaded results. The browser contains the same mapping only as a compatibility fallback for historical jobs.

## Localization

The job language continues to select backend worker messages. Diagnostics additionally maps every visible stage key, job/circular state, outcome, mode, progress label, UDP validation message, profile-copy message, and circular lifecycle explanation to Russian or English according to the selected OPNsense language.

The non-terminal backend job state `cancel_requested` is explicitly mapped in both RU and EN dictionaries. It must never fall through to raw technical `CANCEL_REQUESTED` rendering. Circular `stop_requested` remains a separate machine state and has its own localized label/message contract.

All dynamic backend detail text remains escaped. Internal machine keys remain stable and untranslated in JSON.

## Verification

The mandatory focused test exercises persisted progress at initialization, family screening, restoration, and terminal report. It also creates a real backend `cancel_requested` state, derives its machine presentation key, and requires deliberate RU and EN mappings in Diagnostics. Circular messages remain covered and the historical English `canseled` typo remains rejected.

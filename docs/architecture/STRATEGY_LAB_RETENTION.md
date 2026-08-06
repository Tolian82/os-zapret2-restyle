# Strategy Lab retention

## Defaults

The automated job store retains the 20 newest deletable terminal jobs. The circular
session store retains the 20 newest deletable terminal sessions. Integrators may set
`STRATEGY_LAB_RETENTION_MAX_JOBS` and `STRATEGY_LAB_RETENTION_MAX_CIRCULAR` to integers
from 1 through 1000.

## Protected evidence

Retention never deletes:

- the active automated job or circular session;
- the latest automated job or circular session;
- queued, running, cancel/stop-requested, or otherwise nonterminal state;
- automated `RESTORE_FAILED` results;
- circular `restore_failed` / `RESTORE_FAILED` sessions;
- any terminal artifact whose semantic restoration has not been verified;
- malformed or incomplete artifacts whose safety cannot be classified.

Protected artifacts do not count against the configured limit. Disk use may therefore
exceed the limit when lifecycle evidence requires operator attention.

## Deletable artifacts

An automated job is deletable only when it is terminal, is not `RESTORE_FAILED`, and has
`restoration.verified=true`. Its external worker log is removed with the job directory.

A circular session is deletable when it is terminal and either has verified restoration
or ended in a known pre-mutation failure (`lifecycle_lock`, `launch_failed`,
`owner_unavailable`, or `stale_before_mutation`).

## Execution

Automated retention runs under the automated launcher lock before start/status/cancel/result.
Circular retention runs under the circular launcher lock before start/status/stop. Cleanup
therefore cannot race pointer updates or a new lifecycle transaction.

Invalid limits fail closed and cause no deletion. Retention failure does not block the
requested diagnostic operation; evidence is preserved and the next launcher invocation
may retry cleanup.

## Ordering

Eligible directories are ordered by directory modification time, newest first. The newest
configured number are kept and older eligible artifacts are removed. Active/latest and
protected artifacts are skipped rather than counted.

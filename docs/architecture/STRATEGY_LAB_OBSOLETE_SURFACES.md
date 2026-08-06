# Strategy Lab obsolete-surface removal

Revision 43 removes two transitional implementation surfaces that were no longer part of
the supported product contract.

## Removed circular aliases

Circular validation state and stop control exist only inside the validated private session:

```text
circular/sessions/<session-id>/state.json
circular/sessions/<session-id>/stop.request
```

The former global `circular/state.json` and `circular/stop` symlinks are not created or
read. Active/latest pointer files select a session; they never duplicate session state.

## Removed duplicate state hook

The unused state-level `strategy_lab_skip_unfinished()` hook was removed. Skipping
unfinished stages remains explicit worker orchestration through
`worker_skip_unfinished()` in `worker_stage_machine.sh`, called only by the cancellation,
error, prerequisite-failure, and timeout paths in `worker_control.sh`.

This eliminates dependence on an accidental module load order while preserving mandatory
stage 90 restoration and stage 99 reporting.

## Verification

The obsolete-surface test rejects both global circular alias paths and the duplicate state
hook, while requiring private session helpers and the active worker cleanup calls. The
end-to-end fixture runs circular start/status/stop entirely through `active.session` and
private session artifacts and proves that no aliases appear.

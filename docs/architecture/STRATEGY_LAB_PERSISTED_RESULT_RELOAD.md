# Strategy Lab persisted result reload

## Contract

The backend maintains atomic `latest.job` alongside `active.job`. Every accepted start
writes the new job as latest before publishing it as active. `status -` returns the active
job when present, otherwise the latest persisted job.

For installations predating the pointer, the backend scans existing job directories once,
selects the newest valid status, repairs `latest.job`, and then uses the pointer normally.
Invalid or deleted pointers are repaired the same way.

Diagnostics page initialization always accepts a returned job ID. Nonterminal state resumes
polling. Terminal `completed` or `error` state is rendered immediately and fetched through
the result endpoint without starting a new job.

## Safety

- pointers contain only validated `job.*` IDs with readable status files;
- writes are atomic;
- active ownership remains authoritative over latest history;
- a page reload never mutates the saved result or lifecycle state;
- terminal results remain available until retention policy explicitly removes them.

## Verification

The focused test covers pointer creation, terminal completed/error lookup, corrupt-pointer
fallback and repair, plus the GUI terminal/nonterminal reload branches.

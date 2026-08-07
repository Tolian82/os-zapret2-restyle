# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary, blockers, active architectural direction, and next action.

Updated when:
Current source/package identity, live boundary, blocker, approved implementation direction, or next action changes.

Read after:
`AGENTS.md` and `docs/INDEX.md`.

Do not store here:
Full chronological history, detailed implementation design, or complete test logs.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Published stable release/package: `v0.3.2` / `os-zapret2-restyle-0.3.2_1.pkg`
Latest published testing prerelease: `v0.3.3_17` / `os-zapret2-restyle-0.3.3_17.pkg`
Latest owner-tested testing candidate: `v0.3.3_17` / `os-zapret2-restyle-0.3.3_17.pkg`
Current source line: `VERSION=0.3.3`
Current package revision: `PLUGIN_REVISION=19`
Current migration source candidate: `os-zapret2-restyle-0.3.3_19.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **Strategy Lab Migration Patch 2 — Python automated-job state/progress/structured persistence**
Stable release: **BLOCKED ON POST-MIGRATION LIVE MATRIX**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` together with repository-root `AGENTS.md` and `docs/GITHUB_PUBLICATION.md`.

==================================================
MIGRATION PATCH 1 FOUNDATION
==================================================

Migration Patch 1 established the supported OPNsense 26.7 platform contract:

- FreeBSD 15.1 / Python 3.13 (`PYTHON=313`);
- stable OPNsense interpreter link `/usr/local/bin/python3`;
- direct plugin dependency `python313` mapped to `lang/python313`;
- standard-library-only Python migration code;
- packaged Python launcher/entry point/foundation.

`zapret_service.sh` still launches `strategy_lab_worker.sh` directly. That remains true in
Patch 2; the production worker and numbered stage machine have not yet moved to Python.

==================================================
MIGRATION PATCH 2 STATE OWNERSHIP
==================================================

Migration Patch 2 moves authoritative automated-job persistence to Python 3.13.

`strategy_lab_py/state.py` now owns automated-job:

- initial schema-2 `status.json` creation;
- per-job revision ownership and serialized status mutations;
- persisted `current_stage` and `progress` snapshots;
- cancellation state and timestamp persistence;
- atomic `events.ndjson` persistence;
- structured target/network/baseline/family/expansion/stability/shortlist/extended/QUIC/UDP fields;
- lifecycle snapshot and restoration fields;
- stale-worker terminal reconciliation state;
- terminal circular-eligibility fields stored in the parent automated job.

The shell `strategy_lab/state.sh` retains the existing public helper names only as thin
adapters into the Python writer. The previous shell `strategy_lab_state_transform` and
private jq/temp/mv writers for authoritative automated-job state are removed from the
migrated paths.

Persistence invariants:

- public automated-job JSON schema remains version 2;
- stage numbers/keys and progress percentages remain unchanged;
- every serialized automated-job status mutation increments `revision` exactly once,
  including a terminal semantic no-op;
- writes use one Python state lock, same-directory temporary files, fsync, atomic replace,
  and mode `0644`;
- the GUI/API does not need to know which language owns automated-job persistence.

Private circular-session `state.json` remains on its pre-existing shell writer in Patch 2.
Shared lifecycle code preserves a circular fallback rather than creating two owners of
that private file. The Python automated-job writer explicitly rejects private circular
`state.json` paths; a separate migration scope is required before that ownership can
change.

Patch 2 does **not** move stage ordering, budgets, cancellation/finalization policy,
lifecycle decisions, probes, candidate execution, search algorithms, or circular-session
state transitions. Those remain shell responsibilities until their designated migration
patches.

==================================================
FINAL SHELL-ERA LIVE BOUNDARY
==================================================

Owner-assisted Standard Strategy Lab test on `v0.3.3_17`:

- target: `rutracker.org`;
- job shown by GUI: `job.w0nXxQ`;
- initial Zapret2 state: RUNNING.

Final stages:

- 00 PASS — target initialized as domain;
- 10 PASS — initial RUNNING state captured;
- 20 PASS — normal Zapret2 stopped;
- 30 PASS — IPv4 available; IPv6 unavailable; QUIC/IPv4 closed;
- 40 PASS — DNS OK; direct TLS 1.3 connection not established;
- 50 ERROR — `Temporary candidate runtime failed internally.`;
- 60–85 SKIPPED;
- 90 PASS — temporary state cleaned and original Zapret2 restored healthy RUNNING;
- 99 ERROR — internal Strategy Lab error with retained results.

Immediate active-GUI observation on the same run:

- the new job ID appeared together with `Статус: ОШИБКА` immediately after Run;
- `Strategy Lab returned no output.` was displayed while the job was still active;
- visible progress stayed at 0% during active work;
- terminal presentation jumped directly to 100%.

No `_17` candidate-runtime log bundle was collected in this run. Therefore the exact
remaining `_17` Stage-50 root cause is intentionally not claimed.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
CONFIRMED LIVE SUB-GATES
==================================================

The owner-assisted series has established these reusable facts:

- FreeBSD DNS foreground-timeout correction is live-proven: stage 40 can pass with `DNS: OK`;
- normal Zapret2 restoration is live-proven: stage 90 repeatedly returns initially RUNNING service to healthy RUNNING;
- temporary Strategy Lab runtime can reach real dvtws2 startup/bind/privilege-drop paths;
- `v0.3.3_17` still does not complete Stage 50 successfully;
- no complete Standard Strategy Lab scenario is yet live PASS.

Authoritative live matrix:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

All items remain open until replacement evidence closes them. Migration does not reset
or automatically resolve the backlog.

1. **Stage 50 remains ERROR on `_17`.** Exact `_17` root cause is not yet established.
2. **Immediate stale/new-job GUI error.** A fresh job ID can be shown with visible `ERROR` before terminal evidence exists.
3. **Active GUI no-output message.** `Strategy Lab returned no output.` can appear while backend work continues.
4. **GUI progress stuck at 0%.** Backend work advances while visible progress remains 0%, then jumps to terminal 100%.
5. **Baseline target-type corruption.** Shell-global `_strategy_lab_type` can turn domain state into `A`.
6. **DNS answer parser is semantically weak.** `IN A`/`IN AAAA` text can be matched without proving an answer-section record.
7. **DNS diagnostics flatten failure classes.** Timeout, command failure, and parser rejection can collapse into generic failure code 1.
8. **Terminal reload/state presentation defect.** Retained terminal state can be presented incorrectly on Diagnostics reopen.
9. **Candidate fatal-log classification defect.** Readiness evidence can report a clean log while fatal runtime text exists.

Patch 2 removes shell-global/private-writer mechanisms from the migrated automated-job
persistence layer, but it does not close any owner-observed defect by itself. Closure
still requires focused replacement regression and, where applicable, live/UI evidence.

==================================================
PYTHON MIGRATION PATCH SEQUENCE
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE IN `_18` SOURCE / MERGED**.

Patch 2 — Python automated-job state, progress, and structured persistence: **CURRENT `_19` SOURCE CHANGE**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **NEXT AFTER PATCH 2 QUALIFICATION**.

Patch 4 — Python request/probe execution and parsing.

Patch 5 — Python candidate runtime and family screening.

Patch 6 — Python expansion, stability, and extended protocol orchestration.

Patch 7 — Python result/shortlist completion and obsolete shell-orchestration retirement.

Patch 8 — GUI/status reconciliation and post-migration live gate.

The specialist plan may split a listed patch further when one item exceeds one logical
change. It must not compress the migration into a monolithic rewrite.

==================================================
DELIVERY AND PACKAGE BOUNDARY
==================================================

Migration Patch 2 is an installable package-source change:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION` advances to `19`;
- current source candidate is `os-zapret2-restyle-0.3.3_19.pkg`;
- latest published/owner-tested live evidence remains `_17`;
- `_19` does not resume the live matrix because the stage machine/search path has not yet reached the designated Python parity gate.

The `_19` source must pass focused Python state tests, the complete corrective matrix,
full repository CI, and FreeBSD 15 package/content verification before squash merge.
Testing-prerelease publication remains a separate operation requiring the repository's
normal publication authority.

Stable release and pkg-repository promotion remain blocked until the Python path reaches
functional parity and the owner-assisted live matrix passes.

==================================================
NEXT ACTION
==================================================

Complete Migration Patch 2 qualification on `_19`:

1. Python 3.13 foundation/import checks;
2. focused automated-job state/progress/event persistence parity and concurrency regression;
3. canonical Strategy Lab corrective matrix;
4. full repository CI;
5. FreeBSD 15 package build/content/manifest verification;
6. squash merge only from the successfully validated latest head.

After Patch 2 is merged, begin **Migration Patch 3 only**: move the numbered stage
machine, budgets, cancellation orchestration, and terminal finalization policy to Python
while preserving the persistence/API contract established here.

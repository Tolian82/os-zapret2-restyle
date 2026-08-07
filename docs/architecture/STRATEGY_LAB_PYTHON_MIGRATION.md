# Strategy Lab Python migration plan

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How will the current Strategy Lab shell orchestration be migrated to Python without changing its approved product contract or weakening OPNsense lifecycle safety?

Purpose:
Provide the implementation map, responsibility boundary, migration stages, compatibility constraints, test requirements, and handoff entry point for the next development topic.

Updated when:
Migration scope, module ownership, compatibility boundaries, or patch sequence changes.

Read after:
`docs/ARCHITECTURE.md`, `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`, and `docs/PROJECT_STATE.md`.

Do not store here:
Chronological implementation results or final live evidence.

==================================================
STATUS
==================================================

Migration Patch 0 is complete. Migration Patch 1 is complete and merged as source
candidate `v0.3.3_18`. Migration Patch 2 is implemented as source candidate
`v0.3.3_19` and is subject to the normal PR/CI/FreeBSD 15 qualification gate.

The production process entry remains the shell Strategy Lab worker:
`zapret_service.sh` still launches `strategy_lab_worker.sh` directly. Patch 2 changes one
internal responsibility boundary only: Python is now the authoritative writer for
automated-job state/progress/event persistence while the shell worker still owns numbered
stage orchestration and all later migration responsibilities.

==================================================
OBJECTIVE
==================================================

Move the Strategy Lab responsibilities that require structured state, reliable subprocess handling, explicit scoping, parsing, cancellation, and deterministic error classification from large sourced POSIX-shell composition into Python.

Do not rewrite unrelated plugin code.

The migration is successful when:

- public Strategy Lab API behavior remains compatible;
- lifecycle safety and exact restoration are preserved;
- Python owns the high-level job state machine and candidate orchestration;
- shell is reduced to small explicit system adapters where useful;
- obsolete shell orchestration is removed rather than retained as a fallback competitor;
- the current confirmed bug backlog is re-evaluated against focused tests and live evidence;
- the owner-assisted OPNsense matrix can resume from a documented Python candidate.

==================================================
TARGET COMPONENT BOUNDARY
==================================================

Target flow:

```text
Diagnostics GUI / JavaScript
        ↓
OPNsense PHP MVC/API
        ↓
configd action
        ↓
thin compatibility launcher
        ↓
Python Strategy Lab orchestration
        ↓
explicit system adapters / subprocesses
        ↓
zapret_service.sh, ipfw, drill/curl, dvtws2, sockstat/ps and related FreeBSD tools
```

PHP remains responsible for:

- HTTP request validation;
- API response shape;
- OPNsense MVC integration;
- configd invocation and bounded backend request handling.

Python is the target owner for:

- job model and state transitions;
- atomic status/event/result persistence;
- stage progression and progress percentages;
- stage and overall time budgets;
- cancellation state and signal-aware finalization;
- subprocess execution with explicit `returncode`, stdout, stderr, and timeout classification;
- DNS/TLS/HTTP output parsing;
- candidate runtime orchestration state;
- family screening, parameter expansion, stability confirmation, extended protocol orchestration;
- structured result generation and shortlist assembly;
- error typing and diagnostic evidence.

Shell may remain responsible for small, explicit boundaries where it is safer or clearer to reuse the existing audited OPNsense/FreeBSD lifecycle behavior, including:

- public Zapret2 service lifecycle entry points;
- shared lifecycle lock integration until intentionally migrated;
- short `ipfw` mutation helpers;
- process ownership/cleanup helpers that are already audited and easier to preserve than duplicate;
- compatibility launch wrappers during migration.

A shell helper must have a narrow input/output contract. It must not retain hidden ownership of the Python job state machine.

==================================================
PYTHON RUNTIME CONSTRAINT
==================================================

Migration Patch 1 established the supported runtime contract for OPNsense 26.7 / FreeBSD 15:

- OPNsense 26.7 build configuration selects FreeBSD 15.1 and `PYTHON=313`;
- the supported interpreter family is Python 3.13;
- OPNsense core owns the stable `/usr/local/bin/python3` compatibility link to its
  selected `python${CORE_PYTHON}` interpreter;
- `os-zapret2-restyle` declares `python313` directly in `PLUGIN_DEPENDS`;
- the custom package builder maps `python313` to package origin `lang/python313`;
- `.py` sources under `src/opnsense/` are staged automatically into the package;
- retained shell launchers remain executable through the existing package-mode handling.

The production compatibility launcher defaults to `/usr/local/bin/python3`. The stock
FreeBSD 15 CI VM uses `/usr/local/bin/python3.13` explicitly because it does not provide
the OPNsense core compatibility link.

No third-party `pip` dependency is approved. Python migration code remains standard
library only unless a later independent architectural decision proves another dependency
necessary.

==================================================
STATE AND DATA MODEL
==================================================

Python represents migrated automated-job state explicitly rather than through reused
shell-global mutation pipelines.

Minimum structured concepts remain:

- Job identity and mode;
- normalized target and immutable target type;
- required endpoints;
- lifecycle snapshot;
- current stage;
- progress snapshot;
- cancellation state;
- stage result;
- subprocess/probe result;
- candidate identity and runtime evidence;
- family result;
- shortlist/profile result;
- restoration evidence;
- terminal outcome.

Migration Patch 2 establishes these concrete ownership rules:

- `strategy_lab_py/state.py` is the sole authoritative writer for automated-job
  `status.json` and `events.ndjson`;
- the shell `strategy_lab/state.sh` exposes compatibility helper names only and delegates
  authoritative automated-job state/event mutations to Python;
- shell algorithms may continue to produce stage-specific intermediate/result files
  until their designated migration patch, but embedding those results into automated-job
  state is Python-owned;
- private circular-session `state.json` remains on its pre-existing shell writer in Patch
  2, preventing simultaneous Python/shell ownership of that separate contract;
- the Python state engine validates `state.json` paths for future migration/testing, but
  that support is not a production circular-state cutover;
- public JSON schema is the compatibility authority, not the internal Python layout.

==================================================
PERSISTENCE CONTRACT
==================================================

Existing evidence locations remain stable during migration:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate evidence files required by the current result contracts.

Patch 2 automated-job persistence invariants:

1. Schema remains `2` for automated `status.json`.
2. Existing stage numbers, stage keys, progress percentages, state/outcome fields,
   cancellation fields, and structured-result field names remain unchanged.
3. Every serialized automated-job status mutation increments `revision` exactly once,
   including a mutation whose semantic body becomes a terminal no-op.
4. Concurrent automated-job state/event writers use the Python state lock; the removed
   shell `strategy_lab_state_transform` is not a competing owner.
5. JSON/NDJSON replacement uses a same-directory temporary file, flush, fsync, atomic
   `os.replace`, and mode `0644`.
6. Event writes are serialized through the same automated-job state ownership boundary
   and remain valid line-delimited JSON.
7. The GUI/API never needs to know which language owns automated-job persistence.
8. Moving persisted progress to Python does not itself prove the owner-observed GUI
   progress defect is fixed; that remains live/UI gated.
9. Private circular-session `state.json` keeps its existing shell persistence contract
   until a separately scoped cutover.

==================================================
SUBPROCESS CONTRACT
==================================================

Every external command execution must preserve independently:

- command/arguments;
- start and completion/timeout state;
- return code when one exists;
- stdout;
- stderr;
- timeout classification;
- cancellation/termination classification;
- duration when needed for budget accounting.

Timeout must not be flattened into a generic code 1. Parser rejection must not be indistinguishable from command execution failure.

Python standard-library subprocess timeouts are preferred for ordinary finite probes. FreeBSD-specific daemon/lifecycle behavior must still be modeled explicitly where long-lived descendants are intentional.

==================================================
LIFECYCLE SAFETY
==================================================

The following requirements are migration invariants:

1. Snapshot exact initial Zapret2 state before mutation.
2. Use the existing shared lifecycle ownership boundary.
3. Stop normal runtime only through approved lifecycle paths.
4. Run one temporary candidate at a time.
5. Keep temporary firewall/divert ownership isolated.
6. Clean candidate runtime before moving to the next candidate.
7. Execute stage 90 on normal completion, timeout, cancel, signal, or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. A restoration failure is never hidden by a successful test result.
10. Saved Traffic Strategy remains immutable.

Patch 2 does not move lifecycle decisions. Existing audited lifecycle/recovery helpers
still make those decisions. For ordinary automated jobs, lifecycle snapshot/restoration
fields are persisted through Python. For private circular sessions, the shared lifecycle
helper retains the existing circular-state writer until that separate state contract is
explicitly migrated.

==================================================
CONFIRMED DEFECTS TO CARRY FORWARD
==================================================

The migration backlog is not reset. At the live handoff boundary:

1. `_17` Standard `rutracker.org` still fails stage 50 with `Temporary candidate runtime failed internally.`; exact `_17` stage-50 root cause is not yet established from runtime logs.
2. New job UI can show `Статус: ОШИБКА` immediately after Run before the new job has terminal evidence.
3. Active GUI can show `Strategy Lab returned no output.` while backend work continues.
4. Visible progress can remain 0% during active backend stages and jump directly to 100% at terminal result.
5. Shell-global `_strategy_lab_type` corruption can change domain target type to `A`.
6. DNS parser can accept `IN A`/`IN AAAA` text outside a proved answer record.
7. DNS diagnostics flatten timeout, command failure, and parser rejection.
8. Terminal reload/state presentation can resurrect retained terminal work incorrectly.
9. Candidate readiness log classification can miss fatal runtime log evidence.

Patch 2 removes shell-private authoritative automated-job state mutation from the migrated
layer. This is architectural progress, not automatic defect closure. Each backlog item
remains open until focused replacement tests and any required live/UI verification close
it.

==================================================
MIGRATION PATCH SERIES
==================================================

Patch 0 — documentation and handoff: **COMPLETE**

- freeze `v0.3.3_17` live boundary;
- record bug backlog;
- approve Python/PHP/shell responsibilities;
- prepare next-topic entry point.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**

- verify target Python interpreter path/version/dependency model on OPNsense FreeBSD 15;
- add the minimal packaged Python module/entry point;
- add CI syntax/import execution on the verified interpreter family;
- keep runtime behavior unchanged;
- establish a thin compatibility launcher and deterministic error reporting if Python cannot start.

Patch 2 — Python automated-job state, progress, and structured persistence: **IMPLEMENTED IN `_19` SOURCE**

- move authoritative automated-job status/event persistence helpers to Python;
- preserve exact public JSON, progress, cancellation, and revision contracts;
- route automated-job structured result/lifecycle/stale-recovery/eligibility fields through Python;
- remove the migrated shell jq/temp/mv status writers;
- keep private circular-session `state.json` on its existing writer until a separate cutover;
- add atomic-write, concurrency, revision, progress, event, stale-recovery, and state-path parity tests;
- keep numbered stage orchestration outside this patch.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **NEXT AFTER PATCH 2 QUALIFICATION**

- move numbered-stage orchestration and overall/stage budgets;
- model cancel and terminal outcomes explicitly;
- preserve mandatory stage 90 finalization;
- keep lifecycle mutations behind existing adapters.

Patch 4 — Python request/probe execution and parsing

- move DNS/TLS/HTTP finite subprocess execution;
- preserve returncode/stdout/stderr/timeout separately;
- implement answer-section-aware DNS parsing;
- eliminate target-type variable collision in the new state model;
- add focused regressions for the confirmed DNS/diagnostic backlog.

Patch 5 — Python candidate runtime and family screening

- move stage-50 candidate/family orchestration and readiness state;
- keep audited system/lifecycle helpers as explicit adapters where appropriate;
- make candidate startup, privilege-drop access, logs, PID ownership, divert readiness, probe result, and cleanup distinct evidence;
- remove the replaced shell stage-50 orchestration after parity tests pass.

Patch 6 — Python expansion, stability, and extended protocol orchestration

- move stages 60, 70, and 80 high-level orchestration;
- preserve ordered sequential strategy ownership and protocol gates;
- keep complete profile/replay contracts unchanged.

Patch 7 — Python result/shortlist completion and shell-orchestration retirement

- make Python the sole high-level Strategy Lab orchestration owner;
- remove obsolete sourced shell worker modules and load-order surfaces;
- retain only approved small adapters;
- run the full corrective matrix against the Python path.

Patch 8 — GUI/status reconciliation and post-migration live gate

- close remaining GUI polling/stale-error/no-output/progress/reload defects against the now-stable backend contract;
- publish the designated testing candidate;
- resume Scenario 1 and then the remaining owner-assisted OPNsense matrix;
- close backlog items only from evidence.

Patch numbering may be split further when one item becomes more than one logical change. It must not be compressed into a monolithic rewrite.

==================================================
TEST STRATEGY
==================================================

Every migration patch must include focused automated coverage for the responsibility it moves.

Migration Patch 1 requirements remain protected by the Python foundation test.

Migration Patch 2 additionally requires:

- Python 3.13 import and `py_compile` for `strategy_lab_py/state.py`;
- exact schema-2 initialization parity;
- exact stage-key and progress-percentage parity;
- revision increments under sequential and concurrent automated-job mutations;
- terminal-state guards with preserved revision semantics;
- cancellation timestamp preservation on repeated requests;
- valid concurrent readers during concurrent writes;
- atomic valid `events.ndjson` persistence;
- mode `0644` and no leftover temporary automated-job state/event files;
- deterministic state-path validation, including future-compatible private `state.json` syntax without changing current circular ownership;
- absence of shell `strategy_lab_state_transform` and private stale-recovery automated-job state writers;
- complete existing Strategy Lab corrective matrix, including unchanged circular isolation/ownership fixtures;
- FreeBSD 15 execution with `python313` and built-package presence of `state.py`.

Required principles:

- old public fixtures remain compatibility tests where they express product behavior rather than shell implementation details;
- new Python tests target migrated ownership directly without requiring real DPI traffic;
- integration tests continue to exercise configd/API-compatible entry points;
- FreeBSD-specific behavior remains represented by deterministic fixtures and FreeBSD 15 package CI;
- no test requires an obsolete internal shell transform after its responsibility migrates;
- a test proving old shell implementation detail may be retired only when an equivalent product/contract test protects the replacement.

==================================================
CUTOVER RULE
==================================================

For each responsibility:

1. Add Python implementation behind the stable compatibility boundary.
2. Run focused parity tests against required behavior.
3. Switch the authoritative call path once.
4. Verify there is only one owner of mutations/state.
5. Remove obsolete shell implementation in the same logical migration scope when safe, or in the immediately following dedicated retirement patch if removal would make the scope too large.

Patch 1 stopped before an ownership switch. Patch 2 performs the first responsibility
cutover: authoritative automated-job state/progress/event persistence switches to Python
and the competing shell transforms for that contract are removed. The shell numbered
stage machine remains a caller of that persistence API until Patch 3. Private circular
session state remains outside this cutover and retains its existing single shell owner.

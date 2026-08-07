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

Approved for implementation after the documentation/handoff patch is merged.

Current runtime implementation remains the shell Strategy Lab from `v0.3.3_17` until a migration patch explicitly replaces one responsibility. This document describes the target transition; it does not claim Python is already active.

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

No Python interpreter path/version is assumed by this document.

Migration Patch 1 must first establish on the supported OPNsense/FreeBSD 15 target:

- the Python interpreter path available to the plugin;
- the supported Python version;
- whether the interpreter is base-system, OPNsense-managed, or must be declared as a plugin dependency;
- package installation behavior for `.py` sources;
- CI/FreeBSD 15 syntax and execution coverage.

No third-party `pip` dependency is approved. Prefer the Python standard library so installation remains deterministic and offline-safe.

==================================================
STATE AND DATA MODEL
==================================================

Python should represent state explicitly rather than through reused shell-global variables.

Minimum structured concepts:

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

The implementation may use dataclasses or ordinary typed dictionaries/classes according to the verified Python version. The public JSON schema remains the compatibility authority, not the internal class layout.

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
PERSISTENCE CONTRACT
==================================================

Existing evidence locations remain stable during migration:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate evidence files required by the current result contracts.

JSON writes must remain atomic. A Python implementation should use write-to-temporary-file plus atomic rename/replace in the same filesystem.

The GUI must never need to know whether the active worker implementation is shell or Python.

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

Migration patches must prefer reusing already-audited lifecycle helpers over duplicating them in Python until a separate patch is justified.

==================================================
CONFIRMED DEFECTS TO CARRY FORWARD
==================================================

The migration backlog is not reset. At the handoff boundary:

1. `_17` Standard `rutracker.org` still fails stage 50 with `Temporary candidate runtime failed internally.`; exact `_17` stage-50 root cause is not yet established from runtime logs.
2. New job UI can show `Статус: ОШИБКА` immediately after Run before the new job has terminal evidence.
3. Active GUI can show `Strategy Lab returned no output.` while backend work continues.
4. Visible progress can remain 0% during active backend stages and jump directly to 100% at terminal result.
5. Shell-global `_strategy_lab_type` corruption can change domain target type to `A`.
6. DNS parser can accept `IN A`/`IN AAAA` text outside a proved answer record.
7. DNS diagnostics flatten timeout, command failure, and parser rejection.
8. Terminal reload/state presentation can resurrect retained terminal work incorrectly.
9. Candidate readiness log classification can miss fatal runtime log evidence.

Each item remains open until the Python implementation has a focused regression and any required live/UI verification.

==================================================
MIGRATION PATCH SERIES
==================================================

Patch 0 — documentation and handoff (this work)

- freeze `v0.3.3_17` live boundary;
- record bug backlog;
- approve Python/PHP/shell responsibilities;
- prepare next-topic entry point.

Patch 1 — Python platform and compatibility foundation

- verify target Python interpreter path/version/dependency model on OPNsense FreeBSD 15;
- add the minimal packaged Python module/entry point;
- add CI syntax/import execution on the verified interpreter family;
- keep runtime behavior unchanged;
- establish a thin compatibility launcher and deterministic error reporting if Python cannot start.

Patch 2 — Python job state, progress, and structured persistence

- move status/event/result persistence helpers to Python;
- preserve the exact public JSON contract;
- remove shared-variable classes of state corruption from the migrated layer;
- add atomic-write and revision/progress parity tests.

Patch 3 — Python stage machine, budgets, cancellation, and finalization

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

Required principles:

- old public fixtures remain useful as compatibility tests where they express product behavior rather than shell implementation details;
- new Python unit tests should target state transitions, timeout/error classification, parser behavior, and candidate orchestration without requiring real DPI traffic;
- integration tests should continue to exercise configd/API-compatible entry points;
- FreeBSD-specific behavior remains represented by deterministic fixtures and FreeBSD 15 package CI;
- no test should require exact internal shell function names after their responsibility migrates;
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

Do not keep a hidden shell fallback that can silently activate and recreate the same divergent behavior.

==================================================
NEXT-TOPIC ENTRY POINT
==================================================

When development resumes in a fresh chat/topic, the first action is:

1. Read repository-root `AGENTS.md`.
2. Read `docs/INDEX.md`.
3. Read `docs/PROJECT_STATE.md`.
4. Read this migration plan.
5. Read `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.
6. Inspect current `main`, package identity, and relevant Strategy Lab source.
7. Begin only Migration Patch 1: Python platform and compatibility foundation.

Do not resume speculative shell Stage-50 patching before this foundation unless a service-safety issue is discovered.

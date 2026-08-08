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

Migration Patch 0 is complete. Patch 1 is merged as `_18`, Patch 2 as `_19`, and Patch 3
as `_20`. Migration Patch 4 is the current source candidate `v0.3.3_21` and is subject to
the normal Ready-PR / corrective-CI / FreeBSD-15 qualification gate.

The stable outer production boundary remains compatible: `zapret_service.sh` launches
`strategy_lab_worker.sh`, which is a thin launcher into Python `orchestrate JOB_ID`.
Python owns numbered-stage order, wall-clock budgets, cancellation and terminal policy.
Patch 4 additionally makes Python the finite request/probe executor and parser. Candidate
runtime/family policy and later search algorithms remain behind explicit shell adapters
until their designated patches.

==================================================
OBJECTIVE
==================================================

Move Strategy Lab responsibilities that require structured state, reliable subprocess
handling, explicit scoping, parsing, cancellation, and deterministic error classification
from large sourced POSIX-shell composition into Python without rewriting unrelated plugin
code.

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
Python finite request/probe execution + explicit system adapters
        ↓
zapret_service.sh, ipfw, drill/curl, dvtws2, sockstat/ps and related FreeBSD tools
```

PHP remains responsible for HTTP request validation, API response shape, OPNsense MVC
integration, and configd invocation/bounded backend handling.

Python is the target owner for job state, persistence, stage progression/progress,
budgets, cancellation/finalization, structured subprocess execution/parsing, candidate
orchestration, family/search algorithms, result/shortlist assembly and diagnostic typing.

Shell may remain responsible for small explicit boundaries where preserving audited
OPNsense/FreeBSD behavior is safer or clearer: public service lifecycle entry points,
shared lifecycle locking until intentionally migrated, short `ipfw` mutation helpers,
audited process cleanup helpers, compatibility wrappers, and stage-specific algorithms
not yet migrated. Such helpers must not choose Python-owned stage order, budget,
cancellation policy or terminal outcome.

==================================================
PYTHON RUNTIME CONSTRAINT
==================================================

Migration Patch 1 established the supported OPNsense 26.7 / FreeBSD 15 contract:

- OPNsense selects FreeBSD 15.1 and `PYTHON=313`;
- supported interpreter family is Python 3.13;
- OPNsense core owns `/usr/local/bin/python3`;
- the plugin declares `python313` mapped to `lang/python313`;
- `.py` sources under `src/opnsense/` are packaged automatically;
- retained shell launchers remain executable.

The production launcher defaults to `/usr/local/bin/python3`; FreeBSD 15 CI uses
`/usr/local/bin/python3.13` explicitly. No third-party `pip` dependency is approved.

==================================================
STATE AND DATA MODEL
==================================================

Python represents migrated automated-job state explicitly rather than through reused
shell-global mutation pipelines. Public JSON schema is the compatibility authority.

Migration Patch 2 established:

- `strategy_lab_py/state.py` as sole authoritative writer for automated-job `status.json`
  and `events.ndjson`;
- shell state helpers as adapters only;
- Python ownership of persisted structured result/lifecycle fields;
- private circular-session `state.json` remains shell-owned;
- the Python automated-job writer rejects private circular-session paths.

Migration Patch 3 established:

- `strategy_lab_py/orchestrator.py` as production owner of stage order, Standard/Extended
  budgets, cancellation orchestration and terminal policy;
- thin `strategy_lab_worker.sh` launcher;
- one-action `strategy_lab_stage_adapter.sh` without next-stage/final-outcome policy;
- inherited lifecycle lock fd 9 preservation;
- Python orchestrator PID as legitimate active-job owner.

Migration Patch 4 establishes:

- `strategy_lab_py/request.py` as the finite subprocess owner for DNS, TLS 1.3, TLS 1.2,
  HTTP, TCP, QUIC-control and route checks;
- `strategy_lab_py/probe.py` as the Stage-30 network-capability and Stage-40 clean-baseline
  execution/parsing owner;
- shell `request.sh`, `extended_request.sh`, and `strategy_lab_probe_runner.sh` as thin
  compatibility adapters;
- candidate address selection reuses the Python DNS first-answer parser without moving
  candidate runtime/family orchestration from Patch 5.

==================================================
PERSISTENCE CONTRACT
==================================================

Existing evidence locations remain stable during migration:

- `/var/run/zapret2-restyle/strategy-lab/`;
- `/var/log/zapret2/strategy-lab/`;
- per-job `status.json`;
- `events.ndjson`;
- stage/candidate evidence files required by current result contracts.

Patch-2 persistence invariants remain mandatory: schema 2, unchanged public stage/progress/
outcome fields, one revision increment per serialized mutation, Python state lock,
same-directory fsync + atomic replacement, valid NDJSON, and no competing shell state
transform. Private circular-session state keeps its separate shell contract.

Patch 4 keeps public `network.json` and `baseline.json` unchanged and records richer
subprocess diagnostics in `network-evidence.json` and `baseline-evidence.json`.

==================================================
STAGE / BUDGET / CANCELLATION CONTRACT
==================================================

Patch 3 production stage order remains exactly:

`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Python owns the existing Standard 150-second budget, Extended +120-second budget,
per-operation ceilings, Stage-80 shared deadline, typed timeout handling, cancellation
process-group termination and mandatory Stage 90/99 convergence.

Terminal mapping remains unchanged: `ERROR`, `TIMEOUT`, `RESTORE_FAILED` => terminal
`error` / report FAIL; `SUCCESS`, `NO_CANDIDATE`, `TARGET_ACCESSIBLE`, `PARTIAL` =>
terminal `completed` / report PASS; restoration failure overrides prior outcome.

Patch 4 does not change those semantics. A race exposed by the faster request/probe path
is corrected only in publication ordering: Stage 99 report and circular eligibility are
persisted before terminal `completed/error` state becomes visible, preventing readers from
observing a terminal SUCCESS with stale `not_evaluated` eligibility.

==================================================
SUBPROCESS / PARSER CONTRACT
==================================================

Every migrated external command execution preserves independently:

- command and arguments;
- completion/timeout state;
- return code when one exists;
- stdout;
- stderr;
- timeout classification;
- termination/signal classification;
- duration.

Timeout is not flattened into generic code 1. Parser rejection is not indistinguishable
from command execution failure.

Patch 4 implements this contract for finite Strategy Lab requests. DNS A/AAAA parsing:

- accepts only records in the actual `ANSWER SECTION`;
- validates returned addresses with Python `ipaddress`;
- rejects QUESTION, AUTHORITY or unrelated `IN A`/`IN AAAA` text;
- distinguishes `timeout`, `command_error`, `parser_rejected`, and `pass` evidence.

Stage 30 and 40 preserve their existing public JSON while sidecar evidence keeps the full
structured subprocess facts. Target type is local Python data, eliminating the old
shell-global `_strategy_lab_type` collision from the production baseline path.

==================================================
LIFECYCLE SAFETY
==================================================

Migration invariants remain:

1. Snapshot exact initial Zapret2 state before mutation.
2. Use the shared lifecycle ownership boundary.
3. Stop normal runtime only through approved lifecycle paths.
4. Run one temporary candidate at a time.
5. Keep temporary firewall/divert ownership isolated.
6. Clean candidate runtime before moving to the next candidate.
7. Execute stage 90 on normal completion, timeout, cancel, signal or internal error.
8. Restore initial RUNNING to healthy RUNNING and initial STOPPED to STOPPED.
9. Never hide restoration failure behind a successful result.
10. Saved Traffic Strategy remains immutable.

Patch 4 does not duplicate lifecycle mutation logic in Python and does not move candidate
runtime/firewall ownership early.

==================================================
CONFIRMED DEFECTS TO CARRY FORWARD
==================================================

At the frozen `_17` live boundary:

1. Standard `rutracker.org` still fails Stage 50; exact `_17` root cause is not established.
2. New-job GUI can show visible ERROR before terminal evidence.
3. Active GUI can show `Strategy Lab returned no output.` while work continues.
4. Visible progress can remain 0% until terminal.
5. Shell-global target-type corruption existed in the shell baseline path.
6. DNS parser could accept non-answer `IN A`/`IN AAAA` text.
7. DNS diagnostics flattened timeout, command failure and parser rejection.
8. Terminal reload/state presentation can resurrect retained terminal work incorrectly.
9. Candidate readiness log classification can miss fatal runtime log evidence.

Patch 4 replaces the source mechanisms behind items 5–7 and adds focused regressions, but
live/UI closure is not claimed from source changes alone. All owner-observed items remain
open until the required evidence closes them.

==================================================
MIGRATION PATCH SERIES
==================================================

Patch 0 — documentation/handoff: **COMPLETE**.

Patch 1 — Python platform and compatibility foundation: **COMPLETE / MERGED AS `_18`**.

Patch 2 — Python automated-job state, progress, and structured persistence: **COMPLETE / MERGED AS `_19`**.

Patch 3 — Python stage machine, budgets, cancellation, and finalization: **COMPLETE / MERGED AS `_20`**.

Patch 4 — Python request/probe execution and parsing: **CURRENT `_21` SOURCE CHANGE**.

- finite DNS/TLS/HTTP/TCP/QUIC-control execution moves to Python;
- returncode/stdout/stderr/timeout/termination/duration remain distinct;
- DNS parsing is answer-section-aware;
- Stage 30/40 execution/parsing moves to Python with unchanged public JSON;
- candidate DNS binding uses the same parser without moving candidate orchestration;
- focused Linux and FreeBSD 15 regressions cover parser and diagnostic separation.

Patch 5 — Python candidate runtime and family screening: **NEXT AFTER PATCH 4 QUALIFICATION**.

- move Stage-50 candidate/family orchestration and readiness state;
- keep audited lifecycle/system helpers as explicit adapters where appropriate;
- preserve startup, privilege-drop access, logs, PID/divert ownership, probe and cleanup evidence;
- remove replaced Stage-50 shell orchestration after parity tests pass.

Patch 6 — Python expansion, stability, and extended protocol orchestration.

Patch 7 — Python result/shortlist completion and shell-orchestration retirement.

Patch 8 — GUI/status reconciliation and post-migration live gate.

Patch numbering may be split further when one item becomes more than one logical change;
it must not be compressed into a monolithic rewrite.

==================================================
TEST STRATEGY
==================================================

Every migration patch includes focused coverage for the responsibility it moves.

Patch 1 remains protected by the Python foundation test. Patch 2 remains protected by
state/revision/progress/event/atomicity/concurrency tests. Patch 3 remains protected by
stage-order, budget, cancellation, timeout, restoration and terminal tests.

Patch 4 additionally requires:

- Python 3.13 import and `py_compile` for `request.py`, `probe.py`, and compatibility dispatch;
- subprocess stdout/stderr/returncode separation;
- explicit timeout evidence distinct from command/parser failure;
- DNS ANSWER-section positive and QUESTION/AUTHORITY negative cases;
- exact public `network.json` and `baseline.json` parity fixtures;
- candidate first-answer parser delegation without candidate-policy migration;
- terminal eligibility-before-terminal-publication regression;
- complete existing Strategy Lab corrective matrix;
- FreeBSD 15 execution with `python313`;
- built-package presence of `request.py` and `probe.py`.

Old fixtures remain compatibility tests when they express product behavior rather than
retired shell implementation details. No test may require an obsolete shell subprocess or
parser owner after Patch 4 switches that responsibility.

==================================================
CUTOVER RULE
==================================================

For each responsibility:

1. Add Python implementation behind the stable compatibility boundary.
2. Run focused parity tests against required behavior.
3. Switch the authoritative call path once.
4. Verify there is only one owner of mutations/state/control policy.
5. Remove obsolete shell implementation in the same logical scope when safe, or the immediately following dedicated retirement patch if necessary.

Patch 2 switched persistence; Patch 3 switched stage/budget/cancel/finalization ownership;
Patch 4 switches finite request/probe execution and parsing. Private circular-session state
and candidate/family/search algorithms remain outside these cutovers until their designated
patches.

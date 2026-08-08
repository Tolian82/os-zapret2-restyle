# DEC-2026-08-07 — Strategy Lab Python orchestration migration

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Why is Strategy Lab orchestration being migrated from large POSIX-shell composition to Python, and what remains outside that migration?

Purpose:
Record the approved implementation-language boundary, compatibility requirements, migration sequencing, and verification rules before source migration begins.

Updated when:
The approved Python/shell/PHP responsibility boundary or migration acceptance criteria change.

Read after:
`docs/DECISIONS.md` and `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Do not store here:
Patch-by-patch implementation history or live test output.

==================================================
DECISION
==================================================

The project will stop extending the large composed Strategy Lab worker in POSIX shell as the primary orchestration implementation and will migrate the parts that benefit from structured state and process control to Python.

The migration is incremental. Existing public product behavior and integration contracts remain authoritative while implementation ownership moves behind those boundaries.

Approved responsibility boundary:

- PHP remains the OPNsense MVC/API layer: request validation, API actions, and configd invocation.
- Existing configd action names and the asynchronous job API remain stable unless a separately approved compatibility change is required.
- Python becomes the preferred implementation language for Strategy Lab job state, stage orchestration, cancellation/budgets, subprocess execution, output parsing, candidate/family control, and structured result generation.
- Small shell entry points and adapters may remain where they are the clearest FreeBSD/OPNsense boundary for service lifecycle, `ipfw`, process ownership, lock integration, and other short system mutations.
- Shell is not retained as a second competing orchestration engine after the corresponding Python replacement is qualified.

No third-party Python packages are introduced by default. The first implementation patch must verify the supported OPNsense Python interpreter path/version and package/runtime availability before Python becomes a required plugin runtime dependency.

==================================================
REASON
==================================================

Owner-assisted live testing through `v0.3.3_17` exposed repeated defect classes that are amplified by a large `set -eu` shell worker composed through many sourced modules:

- function variables share process-global shell scope and can corrupt unrelated state;
- later sourced functions can silently replace earlier declarations;
- unset variables can terminate a worker before structured diagnostics are produced;
- subprocess timeout, exit-code, stdout/stderr, signal, and daemon ownership semantics require repeated ad-hoc wrappers;
- JSON state and progress are assembled indirectly through files and `jq`;
- negative network results, command failures, parser failures, and internal errors are harder to keep structurally distinct;
- temporary runtime ownership, permissions, cleanup, and readiness evidence are difficult to model as typed state.

Python provides explicit local scope, exceptions, structured data, direct JSON handling, signal handling, and `subprocess` results with independent return code/stdout/stderr/timeout state. These capabilities directly address the defect classes observed during Strategy Lab hardening without changing the product contract.

==================================================
COMPATIBILITY CONTRACT
==================================================

The migration must preserve unless separately approved:

- Diagnostics start/status/cancel/result API behavior;
- current configd public action names;
- job IDs and active-job ownership semantics;
- `/var/run/zapret2-restyle/strategy-lab/` and `/var/log/zapret2/strategy-lab/` evidence boundaries;
- numbered stages 00, 10, 20, 30, 40, 50, 60, 70, 80, 85, 90, and 99;
- truthful PASS/FAIL/TIMEOUT/SKIPPED/ERROR semantics;
- overall standard/extended budgets and bounded stage operations;
- shared Zapret2 lifecycle ownership and exact restoration contract;
- reserved temporary firewall/divert ownership;
- immutable saved Traffic Strategy;
- structured shortlist/profile result contracts;
- RU/EN presentation contract.

Migration is not permission to weaken lifecycle safety or silently change product behavior.

Later search-policy amendment:

`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` keeps this Python/PHP/shell
ownership boundary active but explicitly changes the target search algorithm, QUIC search
scope, candidate/resource representation, finalist validation and timeout-review policy.
Where the 2026-08-08 decision deliberately changes one of the compatibility items above,
the later decision controls; lifecycle/restoration safety and public asynchronous job
ownership remain unchanged.

==================================================
BUG BACKLOG POLICY
==================================================

All defects already confirmed before migration remain open records until independently closed by evidence.

A rewrite may remove the implementation mechanism that caused a defect, but the defect is not marked fixed merely because the old shell path disappeared. The replacement must have a focused regression and, when the defect is live-only or presentation-dependent, owner-assisted verification.

At the `v0.3.3_17` handoff the preserved backlog includes:

- Stage 50 still terminates as `Temporary candidate runtime failed internally.`; the exact `_17` Stage-50 root cause is not yet established because no `_17` candidate-runtime log bundle was collected;
- immediate stale/new-job GUI `ERROR` presentation;
- `Strategy Lab returned no output.` during active work;
- visible progress remaining at 0% until terminal 100%;
- shell-global target-type corruption (`domain` becoming `A`);
- DNS answer parsing that can accept question-section text;
- flattened DNS command/timeout/parser diagnostics;
- terminal reload/state presentation defects;
- incomplete fatal-log classification in candidate readiness.

==================================================
MIGRATION DELIVERY RULES
==================================================

1. Documentation and handoff are completed before source migration begins.
2. Migration is split into small logical patches; no monolithic rewrite.
3. Every replaced shell responsibility gets an automated parity/contract test before the obsolete path is removed.
4. During transition there is one authoritative owner for each responsibility; Python and shell must not both mutate the same job state or runtime in competing paths.
5. Existing shell helpers may be called as explicit adapters while Python orchestration is introduced.
6. Obsolete shell orchestration is removed only after its Python replacement passes CI and package qualification.
7. Packaged migration changes receive the normal FreeBSD 15 package build. Testing-prerelease publication follows the project owner's standing installable-patch authority; live owner testing may be concentrated at meaningful parity gates rather than every internal layer.
8. Stable release and pkg-repository promotion require owner-assisted post-migration live
   evidence selected for the release. The later
   `DEC-2026-08-09-risk-based-live-release-gates.md` supersedes the original blanket
   interpretation that every matrix row must PASS for every release.

==================================================
CONSEQUENCES
==================================================

- `v0.3.3_17` becomes the documented shell-era live handoff boundary, not a successful Strategy Lab completion candidate.
- Further shell-only bug chasing is paused unless required to protect service/lifecycle safety during migration.
- The next source work begins with Python runtime/foundation verification, not another speculative Stage-50 shell patch.
- PHP MVC/API remains stable during the migration unless compatibility evidence requires a focused change.
- The live matrix remains failed and is resumed after the Python path reaches the relevant functional parity gate.

==================================================
AFFECTED DOCUMENTS
==================================================

- `docs/PROJECT_STATE.md`
- `docs/INDEX.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`
- `docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`
- `docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`
- `docs/devlog/2026-08-07-strategy-lab-python-migration-handoff.md`

Status:
Active

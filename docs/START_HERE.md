# os-zapret2-restyle — START HERE

Status: **AUTHORITATIVE OPERATIONAL HANDOFF**
Updated: 2026-08-14

==================================================
PURPOSE
==================================================

This file is the short operational memory of the project. It exists so a new ChatGPT session can
understand the current state, the accepted conclusions and the next actions quickly instead of
reconstructing the same history for hours.

For an ordinary continuation request, read:

1. repository-root `AGENTS.md`;
2. this file completely;
3. `docs/PROJECT_STATE.md` completely;
4. only the specialist source/docs named by the current documented task.

`docs/INDEX.md` is navigation. Historical patches, audits, devlogs and evidence remain part of the
project and must be read when the current plan, task risk or a new defect calls for them. They are
not automatically reprocessed merely because a new chat started.

Audits are **not forbidden**. The rule is: orient by current documentation first. If the documented
plan says an audit/review is the next action, perform it. If a new reproducible defect makes an
audit necessary, perform it. Do not invent a new audit only because the previous chat context was
lost when the current documentation already states what to do next.

==================================================
CURRENT PACKAGE / RUNTIME STATE
==================================================

Repository: `Tolian82/os-zapret2-restyle`
Primary branch: `main`
Semantic version: `0.4.1`
Current packaged source revision: `12`
Current testing package: `os-zapret2-restyle-0.4.1_12.pkg`
Testing tag: `v0.4.1_12`
Packaged runtime/source commit: `acf65d39eaa88a16debe1d35affa71f03f1d848d`
Package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`
Package URL:
`https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_12/os-zapret2-restyle-0.4.1_12.pkg`
Required ABI: `FreeBSD:15:amd64`

Always fetch the current `main` SHA once at session start. Documentation-only commits may follow the
packaged source commit, so do not hard-code an old docs-only `main` SHA into implementation logic.

Normal OPNsense user shell is root `csh`. Owner commands must be csh-safe; enter `/bin/sh` or `sh`
explicitly for POSIX-only blocks.

==================================================
WHAT THE MODEL-C SERIES ESTABLISHED
==================================================

The B -> C production transition is complete as an engineering direction. Current code still has
legacy automatic B/A fallbacks, and removing that transition tail is the next code task.

Key progression:

- `v0.4.0_23`: normal Stage 60 switched to `C-warm-bucket-source-port-dispatch`;
- `v0.4.0_25`: source-port leasing became `preferred-free-else-alternate`; owner-live Model C
  completed 16/16 without fallback and restored runtime cleanly;
- `v0.4.0_26`: `eligible-work-v1` finite adaptive budgets were accepted owner-live; Model C again
  completed 16/16 without fallback with clean Stage-90 restoration;
- `v0.4.1_2`: Lua initialization question closed; current/common init already equals the
  candidate-minimal union, so no production change was justified;
- `v0.4.1_3` + `_4`: BLOB startup/readiness/RSS and bounded common eager-set scaling showed no
  material penalty at width three, so no lazy-BLOB production change was justified;
- `v0.4.1_5` + `_6`: HEAD/GET-1 did not show a material advantage over production GET-4K, so
  discovery stays GET-4K;
- `v0.4.1_7`: lifecycle amortization measurement started;
- `_8`, `_9`, `_10`: fixed measurement-harness traversal/diagnostic/adapter defects;
- `v0.4.1_11`: fixed a real production Model-C profile-compatibility defect while preserving the
  planner-selected logical batch and executing compatible physical segments sequentially;
- `v0.4.1_12`: fixed a real readiness latency defect by retaining the same process/socket/log proof
  and two stable snapshots while polling every 25 ms instead of sleeping one second.

Accepted `_12` owner-live lifecycle replay:

- 5/5 repeats completed;
- `model_c_only=true` in every repeat;
- `fallback_detected=false`, `fallbacks=[]`;
- instrumentation/persisted logical-batch counts matched;
- lifecycle metrics and RSS complete;
- cleanup and semantic restoration PASS;
- median physical-segment `pool_startup_ms=82.5 ms`, mean `93.87 ms`, p90 `163 ms`;
- normal one-segment starts about `80-90 ms`; two sequential profile segments about `163-171 ms`;
- median aggregate RSS `4366 KiB`;
- median Stage-60 wall `22715 ms` in that five-run replay;
- cross-batch keep-warm/reuse closed as **NO FURTHER PRODUCTION CHANGE** under the measured
  cost/jitter boundary.

The strict historical lifecycle `measurement_rejected` label came from live candidate PASS/FAIL
variation between repeats, not Model-C infrastructure failure.

Durable evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

==================================================
HOW TO USE CLOSED EVIDENCE
==================================================

Accepted/closed work is still part of the project and may be audited when the current plan or new
evidence requires it. But a new session should not automatically re-derive it from scratch.

Current closed conclusions that remain authoritative until invalidated by new evidence or changed
architecture:

- Model C is the selected production direction;
- current Lua initialization needs no optimization;
- current width-three eager/common BLOB declarations have no measured material startup/RSS cost;
- production discovery remains GET-4K;
- cross-batch keep-warm/reuse is not justified by current measurements.

If a future audit is documented as required, use these accepted records as starting evidence rather
than treating the project as if no prior work exists.

==================================================
CURRENT CODE REALITY VERSUS CURRENT DECISION
==================================================

Current source still contains:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

The B/A automatic production fallback chain is now a **legacy transition tail**. Model B and Model A
may remain useful as benchmark/reference/test implementations, but they no longer need to be
automatic production fallbacks just because they were used during Model-C introduction.

Keeping the automatic fallback chain costs complexity and can mask real Model-C infrastructure
failures. It also created an aborted timeout-admission design that tried to improve `C -> B` fallback
instead of finishing the transition.

==================================================
NEXT CODE CHANGE — v0.4.1_13 MODEL-C-ONLY PRODUCTION FINALIZATION
==================================================

This is the current documented next implementation task. Before starting, verify that current
`main`, `VERSION`, revision and same-scope PR state still agree. If they do, start from the named
source surfaces rather than re-deriving the whole architecture.

Package metadata:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION` once: `12 -> 13`;
- candidate/title prefix: `v0.4.1_13:`.

### 1. What changes and why

Goal: make Model C the only normal production Stage-60 runtime.

Required implementation:

1. normal `strategy_lab_python.py stage60-parallel ...` execution uses Model C only;
2. Model-C infrastructure/selector/rendering/readiness/attribution failure is explicit and bounded;
   it does not silently replay the same batch through Model B or cold Model A;
3. production source-port leasing is owned for Model C and does not install a second production
   lease solely for Model-B fallback;
4. Model B / Model A modules may remain as benchmark/reference/test tooling where useful; do not
   broaden this patch into unrelated deletion;
5. retire production runtime-selection branches that choose `model-b` or `cold` unless a clearly
   non-production diagnostic/test interface still requires them;
6. preserve Model-C cleanup/restoration fail-closed behavior.

Start with:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- tests directly referencing production `C -> B -> A` fallback semantics, found by narrow search.

Preserve without redesign:

- adaptive planner/search graph and CandidateSpec identity;
- ResourceInventory;
- width at most three;
- exact source-port attribution;
- sequential endpoint probes inside one candidate;
- `_11` profile-compatible segmentation;
- `_12` 25 ms/two-stable-check readiness;
- discovery GET-4K;
- `eligible-work-v1` budgets;
- cancellation, cleanup, Stage-90 restoration;
- downstream Stage 70/80/85/result ownership.

### 2. Expected result after the patch

Automated acceptance:

- normal production entry reaches Model C;
- no production path silently invokes Model B or cold Model A after Model-C infrastructure failure;
- injected Model-C infrastructure failure is explicit and bounded;
- Model-C cleanup executes on success/failure/cancel boundaries;
- source-port leasing and exact attribution remain present;
- logical batch/profile segmentation remains unchanged;
- full Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

Owner-live acceptance after testing-package publication:

- one selected normal OPNsense regression proving Model-C-only execution, expected Stage-60 result
  handling, cleanup/restoration and no temporary rule/process residue;
- if the run exposes a concrete defect, diagnose/fix that defect under normal evidence-first rules;
- if it passes, close the B -> C transition and proceed to the next documented roadmap work.

### 3. Further plan — near and long term

Near-term ordered actions:

1. implement `_13` Model-C-only production finalization;
2. focused regression + complete corrective matrix + FreeBSD 15 package qualification;
3. squash merge exact verified head;
4. publish the deterministic `_13` testing package when owner package/live testing is requested;
5. execute the selected Model-C-only owner-live regression;
6. record result in `START_HERE`, `PROJECT_STATE`, patch/evidence docs and `ROADMAP`;
7. close the B -> C transition if accepted.

After B -> C closure:

8. return to the current project roadmap and canonical owner-assisted regression backlog rather than
   inventing another Model-C optimization by inertia;
9. select the next product/Strategy-Lab item according to owner priority and current roadmap;
10. retain deferred research ideas (for example width >3 or endpoint-level parallelism) as deferred,
    not automatic next steps; they become active only when the roadmap/owner explicitly selects them;
11. before every later GitHub publication, reconcile the complete near-term and long-term plan and
    update it if priorities changed.

Historical/current backlog still includes risk-selected live coverage for STOPPED initial state,
Extended TLS1.2/HTTP and capability-gated QUIC/Generic UDP, already-accessible target,
cancellation/internal failure, circular lifecycle/recovery, Settings Apply guards, Diagnostics
reload, RU/EN presentation, retention and reboot/residue. These are roadmap/backlog items, not all
unconditional blockers for `_13`.

==================================================
ABORTED TIMEOUT DESIGN
==================================================

A source review immediately before this handoff found that legacy Model C can execute multiple
physical profile segments and, after an infrastructure failure, replay through Model B without a
fresh child admission check. That observation is valid for the current fallback implementation.

The current plan is **not** to implement the proposed larger admission envelope for `C -> B` before
Model-C-only finalization. If the fallback is removed, that specific complexity disappears.

Future timeout/deadline audits remain valid project work when the roadmap selects them or a real
Model-C-only containment defect requires them. Start from current Model-C-only code/evidence rather
than from the retired fallback-chain problem.

==================================================
FAST START PROCEDURE FOR A NEW CHAT
==================================================

1. GitHub plugin: fetch current `main` ref.
2. Fetch `VERSION` and `Makefile`.
3. Check same-scope open PR state.
4. Read `AGENTS.md`, this file and `docs/PROJECT_STATE.md` through EOF.
5. Read specialist documents named by the current plan/task.
6. If an audit is the documented next step, perform it. If code is the documented next step and
   repository state matches, start coding.
7. Expand to recursive-tree or broad GitHub inventory only when the task itself requires broad
   discovery.

A pinned recursive tree remains a useful accelerator for genuine repository-wide/cross-cutting
investigation. It is not a mandatory startup ritual when the current task already names the files.

==================================================
MANDATORY DOCUMENTATION CONTRACT FOR EVERY GITHUB DELIVERY
==================================================

Documentation is part of the product change, not an afterthought.

Before every GitHub delivery of a logical project change, documentation must explicitly answer all
three questions:

1. **What are we changing and why?**
   Record the concrete scope, trigger/root reason and important non-goals.
2. **What result do we expect after the patch?**
   Record the intended user/runtime behavior and the automated/live acceptance boundary.
3. **What do we do next?**
   Record the complete ordered plan: immediate follow-up, next patches/tests, and known longer-term
   actions/deferred items.

Immediately before branch/PR publication or equivalent GitHub delivery, perform **plan
reconciliation**:

- reread the current plan in this handoff/`PROJECT_STATE`/`ROADMAP`;
- compare it with what was actually learned while implementing the patch;
- check whether near-term or long-term priorities changed;
- if anything changed, update the documentation **before** publishing the GitHub change;
- only then publish/merge/package according to the normal GitHub workflow.

At the end of every logical cycle, update `docs/START_HERE.md` and `docs/PROJECT_STATE.md`; update
`docs/ROADMAP.md` whenever priority, sequencing, future actions or deferred plans changed. Patch and
evidence records retain detailed history.

This three-part documentation contract applies to code, CI/governance and documentation changes
whenever they alter project state or future work.

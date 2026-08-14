# os-zapret2-restyle — START HERE

Status: **AUTHORITATIVE OPERATIONAL HANDOFF**
Updated: 2026-08-14

==================================================
PURPOSE
==================================================

This file exists so a new ChatGPT session can resume project work in minutes instead of
reconstructing the repository for hours.

For an ordinary continuation request, read:

1. repository-root `AGENTS.md`;
2. this file completely;
3. `docs/PROJECT_STATE.md` completely;
4. only the specialist source/docs named by the exact next task below.

`docs/INDEX.md` is a navigation map, not a mandatory historical reading list. Historical
patches, audits, devlogs and experiments are evidence archives. Do not reread them before an
ordinary continuation unless this handoff explicitly sends you there or current source
contradicts the handoff.

If the owner says `продолжаем`, `делай`, or equivalent and the current repository still
matches the state below, start implementing the exact NEXT CODE CHANGE. Do not begin with a
new architecture audit, a recursive-tree crawl, a review of all branches/workflows/releases,
or a fresh experiment plan.

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

The documentation-only `_12` owner-live closeout currently follows the packaged source tree.
Always fetch the current `main` SHA once at session start; do not hard-code a docs-only `main`
SHA into future implementation assumptions.

Normal OPNsense user shell is root `csh`. Commands supplied to the owner must be csh-safe;
enter `/bin/sh`/`sh` explicitly for POSIX-only blocks.

==================================================
WHAT THE LAST ~57 HOURS ACTUALLY ESTABLISHED
==================================================

The B -> C production transition is **complete as an engineering decision**. Do not treat
Model C as an experiment that still needs another general audit before coding.

Key progression:

- `v0.4.0_23`: normal Stage 60 was switched to
  `C-warm-bucket-source-port-dispatch`.
- `v0.4.0_25`: controlled source-port leasing was corrected to
  `preferred-free-else-alternate`; owner-live Model C completed 16/16 without fallback and
  restored runtime cleanly.
- `v0.4.0_26`: workload-derived finite budgets (`eligible-work-v1`) were accepted owner-live;
  Model C again completed 16/16 without fallback, with clean Stage-90 restoration.
- `v0.4.1_2`: Lua initialization question closed. Current/common initialization already equals
  the candidate-minimal union. **No production change justified.**
- `v0.4.1_3` + `_4`: BLOB startup/readiness/RSS and common eager-set scaling closed. No material
  penalty at current width three. **No lazy-BLOB production change justified.**
- `v0.4.1_5` + `_6`: discovery-probe HEAD/GET-1/GET-4K comparison closed. Cheaper probes did not
  show material timing benefit. **Production discovery remains GET-4K.**
- `v0.4.1_7`: lifecycle amortization measurement was opened.
- `_8`, `_9`, `_10`: corrected measurement-harness traversal/diagnostic/adapter defects. These
  were measurement plumbing, not evidence that Model C itself was unsuitable.
- `v0.4.1_11`: a real production Model-C issue was found and fixed: one planner-selected logical
  batch can contain different profile keys. Model C now preserves the logical batch but runs
  contiguous profile-compatible physical segments sequentially.
- `v0.4.1_12`: a real readiness latency defect was fixed. The shared warm readiness check keeps
  process/socket/log predicates and two stable snapshots but polls every 25 ms instead of sleeping
  one second between checks.

Accepted `_12` owner-live lifecycle replay:

- 5/5 requested repeats completed;
- `model_c_only=true` in every repeat;
- `fallback_detected=false`, `fallbacks=[]`;
- instrumentation/persisted logical-batch counts matched;
- lifecycle metrics and RSS were complete;
- cleanup and semantic restoration passed;
- median physical-segment `pool_startup_ms` fell to `82.5 ms` (mean `93.87 ms`, p90 `163 ms`);
- one-segment starts are normally about `80-90 ms`; two sequential profile segments about
  `163-171 ms`;
- median aggregate RSS `4366 KiB`;
- median Stage-60 wall `22715 ms` in that five-run replay;
- cross-batch keep-warm/reuse was closed as **NO FURTHER PRODUCTION CHANGE** because the remaining
  conservative amortizable upper bound was not cleanly separable from live jitter and did not
  justify additional stateful architecture.

The lifecycle report's historical strict `measurement_rejected` label was caused by live
candidate PASS/FAIL variation between repeats, not by Model-C infrastructure failure. Do not
reopen Model C because of that label.

Durable evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

==================================================
IMPORTANT CONCLUSION — STOP THE AUDIT LOOP
==================================================

The project spent too long continuing to prove an already accepted Model C. That process is now
explicitly closed.

Do **not** automatically start another general audit or measurement for:

- Model A versus Model B versus Model C performance;
- Lua initialization;
- BLOB eager/lazy loading at current width three;
- HEAD/GET-1 versus GET-4K discovery;
- cross-batch keep-warm/lifecycle amortization;
- generic timeout telemetry whose only purpose is to make the legacy `C -> B -> A` fallback chain
  more elaborate;
- a repository-wide recursive-tree investigation merely because a new chat started.

Reopen a closed question only when a new reproducible production defect, changed requirement, or
material architecture change invalidates its accepted evidence.

The owner explicitly wants forward implementation progress rather than repeated audits of the same
runtime.

==================================================
CURRENT CODE REALITY VERSUS CURRENT DECISION
==================================================

Current source still contains this production fallback chain:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

That chain is now considered a **legacy transition tail**, not the desired final production
architecture.

Model B and Model A remain useful as historical benchmark/reference/test implementations, but they
no longer need to remain automatic production fallbacks merely because they were used while Model C
was being introduced.

Keeping automatic B/A fallback now has negative cost:

- it increases production branching and cleanup/deadline complexity;
- it can hide a real Model-C infrastructure defect by silently replaying through old code;
- it forces maintenance of three runtime paths;
- it caused the aborted `_13` timeout-admission investigation to optimize a fallback path that the
  project should instead retire.

Therefore the next code change is not a new timeout experiment.

==================================================
NEXT CODE CHANGE — v0.4.1_13 MODEL-C-ONLY PRODUCTION FINALIZATION
==================================================

**This is the exact next implementation task. Do not precede it with another architecture audit.**

Package metadata for this packaged source change:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION` once: `12 -> 13`;
- candidate/title prefix: `v0.4.1_13:`.

Goal:

**Make Model C the only normal production Stage-60 runtime.**

Required implementation outcome:

1. normal `strategy_lab_python.py stage60-parallel ...` execution uses Model C only;
2. a Model-C infrastructure/selector/rendering/readiness/attribution failure is surfaced as an
   explicit bounded Stage-60 failure/corrective signal; it must not silently replay the same batch
   through Model B or cold Model A;
3. production source-port leasing is owned for Model C; it must not install a second production
   lease wrapper solely for Model-B fallback;
4. Model B / Model A implementation modules may remain in the repository as benchmark,
   compatibility, historical reference or focused-test tooling where useful; do **not** broaden
   this patch into a gratuitous deletion campaign;
5. remove/retire production runtime-selection branches that allow the normal entry point to choose
   `model-b` or `cold` unless a narrowly documented non-production test/diagnostic interface still
   requires them;
6. preserve current Model-C cleanup/restoration fail-closed behavior.

Start with these exact source surfaces; do not crawl the whole repository first:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- tests directly referencing production `C -> B -> A` fallback semantics, discovered by narrow
  symbol/string search only.

Preserve without redesign:

- native adaptive planner/search graph and CandidateSpec identity;
- ResourceInventory semantics;
- candidate width at most three;
- exact source-port-qualified attribution;
- sequential endpoint probes inside one candidate;
- Model-C profile-compatible physical segmentation from `_11`;
- 25 ms / two-stable-check readiness semantics from `_12`;
- discovery GET-4K;
- `eligible-work-v1` parent budgets;
- cancellation, cleanup and Stage-90 semantic restoration;
- downstream Stage 70/80/85/result ownership.

Focused automated acceptance for `_13`:

- normal production entry reaches Model C;
- no production call path silently invokes Model B or cold Model A after a Model-C infrastructure
  failure;
- injected Model-C infrastructure failure is explicit and bounded;
- Model-C cleanup still executes on success/failure/cancel boundaries;
- source-port leasing and exact attribution remain present;
- planner-selected logical batch/profile segmentation remains unchanged;
- full existing Strategy Lab corrective matrix passes;
- FreeBSD 15 package qualification passes.

Owner-live after publication:

- perform **one selected normal regression job** on OPNsense proving Model-C-only execution,
  expected Stage-60 result handling, cleanup/restoration and absence of temporary rules/processes;
- do not fabricate a large new experimental matrix and do not force appliance failures merely to
  justify more analysis;
- if that selected run passes, close the B -> C transition and move to the next product/roadmap
  task outside this runtime-transition series.

==================================================
DO NOT CONTINUE THE ABORTED `_13` TIMEOUT DESIGN
==================================================

Immediately before this handoff, source review found that the legacy Model-C logical batch can
contain several physical profile segments and that C infrastructure failure could replay through
Model B without a fresh child admission check. That observation is valid for the **current legacy
fallback implementation**.

Do not implement the previously proposed corrective that expands admission accounting for
`C -> B` fallback. It optimizes complexity that the next patch should remove.

After Model-C-only finalization, timeout/deadline work is reopened only for an observed Model-C-only
containment defect, not because the old B/A chain had an awkward envelope.

==================================================
FAST START PROCEDURE FOR EVERY NEW CHAT
==================================================

For ordinary continuation, use this sequence:

1. GitHub plugin: fetch current `main` ref once.
2. GitHub plugin: fetch `VERSION` and `Makefile` once.
3. GitHub plugin: check only open PRs relevant to the requested/current task.
4. Read `AGENTS.md`, this file, and concise `docs/PROJECT_STATE.md` through EOF.
5. Read only the specialist file(s) named by the exact current task.
6. If state still matches and no conflicting open PR exists, create the task branch and start the
   code change.

Do **not** inventory every historical branch, workflow, run, tag, release, artifact and PR for an
ordinary source/docs patch. Inspect those classes only when the requested operation depends on them
(CI debugging, package publication, release work, branch cleanup, etc.).

Do **not** fetch the recursive repository tree by default. Use a pinned recursive tree only for a
genuinely broad investigation where the call path/file set is unknown and narrow symbol/path search
cannot resolve it.

Do **not** reread old audits/patch histories to reconfirm a decision already summarized here.

==================================================
DOCUMENTATION MAINTENANCE RULE
==================================================

Documentation is the project's operational memory, not only an archive.

At the end of every logical work cycle that changes current state, update this handoff and
`docs/PROJECT_STATE.md` so the next session contains:

- current VERSION / revision and latest packaged source identity;
- latest owner-tested evidence that actually matters;
- current production architecture;
- closed questions that must not be reopened automatically;
- exact next action;
- likely source files for that action;
- explicit non-goals;
- verification/live boundary;
- any blocker that requires owner input.

Historical evidence remains in patches/devlogs/verification records and should be linked, not
copied into an ever-growing mandatory startup list.

If the handoff and current source disagree, resolve the concrete disagreement; do not use the
mismatch as an excuse for a repository-wide re-audit.

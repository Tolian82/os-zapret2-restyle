# os-zapret2-restyle — START HERE

Status: **AUTHORITATIVE OPERATIONAL HANDOFF**
Updated: 2026-08-14

This file answers: **What must the next session know to resume the current work immediately?**

Permanent rules are not repeated here. They are canonical in `docs/PROJECT_PRINCIPLES.md`.

## Mandatory continuation reading

1. repository-root `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md`;
3. this file;
4. `docs/PROJECT_STATE.md`;
5. specialist documents named by the current task below.

`docs/INDEX.md` is navigation when more evidence/history is required.

## Current identity

- repository: `Tolian82/os-zapret2-restyle`;
- branch authority: current `main` — fetch exact SHA at session start;
- `VERSION=0.4.1`;
- packaged source `PLUGIN_REVISION=12`;
- testing package: `os-zapret2-restyle-0.4.1_12.pkg`;
- testing tag: `v0.4.1_12`;
- packaged runtime/source commit: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`;
- package URL: `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_12/os-zapret2-restyle-0.4.1_12.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- owner console: root `csh`.

## What the Model-C series established

The B -> C transition is complete as an engineering direction. Current source still carries B/A as
automatic production fallbacks; removing that transition tail is the next code change.

Accepted progression:

- `v0.4.0_23`: normal Stage 60 switched to `C-warm-bucket-source-port-dispatch`;
- `v0.4.0_25`: source-port leasing corrected to `preferred-free-else-alternate`; owner-live Model C
  completed 16/16 without fallback and restored cleanly;
- `v0.4.0_26`: `eligible-work-v1` finite adaptive budgets accepted owner-live; Model C 16/16,
  no fallback, clean Stage-90 restoration;
- `v0.4.1_2`: Lua initialization already equals candidate-minimal union; no production change;
- `_3` + `_4`: no material BLOB startup/readiness/RSS penalty at current width three; no lazy-BLOB
  production change;
- `_5` + `_6`: HEAD/GET-1 gave no material advantage over production GET-4K; keep GET-4K;
- `_7` through `_10`: lifecycle measurement and measurement-harness corrections;
- `_11`: real Model-C profile-compatibility fix — preserve logical planner batch, execute contiguous
  profile-compatible physical segments sequentially;
- `_12`: real readiness latency fix — same process/socket/log + two-stable-snapshot proof, poll at
  25 ms instead of one-second sleeps.

Latest `_12` owner-live lifecycle evidence:

- 5/5 repeats completed;
- 5/5 `model_c_only=true`;
- `fallback_detected=false`, `fallbacks=[]`;
- logical batch instrumentation/persistence matched;
- lifecycle/RSS complete;
- cleanup/restoration PASS;
- physical-segment startup median `82.5 ms`, mean `93.87 ms`, p90 `163 ms`;
- normal one-segment startup about `80-90 ms`, two sequential segments about `163-171 ms`;
- median aggregate RSS `4366 KiB`;
- median Stage-60 wall `22715 ms` in that five-run replay;
- further cross-batch keep-warm/reuse not justified by current measured cost/jitter boundary.

Strict lifecycle `measurement_rejected` was caused by live candidate PASS/FAIL variation between
repeats, not Model-C infrastructure failure.

Durable evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Current production reality

Current code still has:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

Current decision:

- Model C is the production direction;
- B/A automatic fallbacks are legacy transition code;
- B/A modules may remain where useful as benchmark/reference/test tooling;
- do not spend the next patch improving timeout admission for `C -> B`; finish the transition first.

Accepted existing behavior to preserve:

- native adaptive planner/search graph and CandidateSpec identity;
- ResourceInventory semantics;
- candidate width at most three;
- exact source-port-qualified attribution;
- pinned endpoints sequential inside one candidate;
- `preferred-free-else-alternate` source-port leasing;
- `_11` profile-compatible segmentation;
- `_12` readiness semantics;
- production discovery GET-4K;
- `eligible-work-v1` budgets;
- cancellation, cleanup and Stage-90 semantic restoration;
- downstream Stage 70/80/85/result ownership.

# Exact next code change — `v0.4.1_13`

## 1. What changes and why

Make Model C the **only normal production Stage-60 runtime**.

Required implementation:

1. normal `strategy_lab_python.py stage60-parallel ...` path uses Model C only;
2. Model-C infrastructure/selector/rendering/readiness/attribution failures are explicit and bounded;
3. the same batch is not silently replayed through Model B or cold Model A;
4. production source-port leasing is Model-C-owned and no second production lease exists solely for
   Model-B fallback;
5. Model B/A implementation may remain as benchmark/reference/test tooling where useful;
6. remove normal production runtime-selection/fallback branches for B/A;
7. preserve current cleanup/restoration fail-closed behavior.

Start from these exact surfaces rather than a repository-wide discovery pass:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- narrow-search hits that directly encode production `C -> B -> A` semantics.

Package identity for the source patch:

- keep `VERSION=0.4.1`;
- `PLUGIN_REVISION 12 -> 13`;
- GitHub title/commit prefix `v0.4.1_13:`.

## 2. Expected result

Automated acceptance:

- normal production Stage 60 reaches Model C only;
- no silent Model-B/cold-Model-A replay after Model-C infrastructure failure;
- injected Model-C infrastructure failure is explicit and bounded;
- Model-C cleanup runs on success/failure/cancel paths;
- source-port leasing and exact attribution preserved;
- logical batch/profile segmentation unchanged;
- complete Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS.

Owner-live acceptance after testing-package publication:

- one selected normal OPNsense regression;
- Model-C-only Stage-60 evidence;
- expected result handling;
- cleanup/restoration PASS;
- no temporary IPFW/process/socket residue.

If it exposes a concrete defect, fix that defect under normal evidence-first rules. If it passes,
close B -> C transition work.

## 3. Complete further plan

Immediate ordered actions after this documentation handoff is on `main`:

1. implement `_13` Model-C-only production finalization;
2. run focused `_13` regression;
3. run complete Strategy Lab corrective matrix;
4. qualify the FreeBSD 15 package;
5. reconcile `START_HERE`, `PROJECT_STATE`, `ROADMAP` and `_13` patch docs against implementation/
   test discoveries before publication;
6. open Ready `_13` PR -> latest-head checks -> exact-head squash merge -> verify `main`;
7. when owner testing/package delivery is requested, publish deterministic `v0.4.1_13` testing `.pkg`;
8. execute the single selected owner-live Model-C-only regression;
9. record live evidence and close the B -> C transition if accepted.

After transition closure:

10. return to the documented product/Strategy-Lab roadmap rather than opening another Model-C
    optimization automatically;
11. select the next backlog item according to owner priority and current roadmap;
12. retain broader owner-assisted regression backlog for risk-selected execution:
    - initial Zapret2 STOPPED;
    - Extended TLS1.2/HTTP;
    - capability-gated QUIC and Generic UDP;
    - already-accessible target;
    - cancellation/internal failure;
    - circular start/stop/TTL/stale recovery;
    - Settings Apply guards;
    - Diagnostics reload behavior;
    - RU/EN presentation;
    - retention and reboot/residue checks;
13. keep research ideas such as candidate width >3 and endpoint-level parallelism deferred until
    owner/roadmap explicitly activates them;
14. before every later GitHub delivery, reconcile both the near-term and long-term plan and record any
    changed priority before publication.

## Aborted timeout design

A source review before this handoff found a legacy containment gap: Model C can execute multiple
physical profile segments and then replay through Model B without a fresh child admission check.
That observation is valid for the current legacy fallback chain.

Do not implement the previously considered larger `C -> B` admission envelope before `_13`.
If B/A automatic fallback is removed, that specific complexity disappears. Future timeout/deadline
audits remain valid when the roadmap/owner selects them or a real Model-C-only defect requires them.

## New-session execution rule

When the owner says `продолжаем` or equivalent:

1. follow the mandatory reading order above;
2. fetch current `main`, `VERSION`, `Makefile` and same-scope open PR state;
3. if current repository state still matches this handoff, perform the documented next task;
4. if the documented task is an audit, audit; if it is code, start coding;
5. expand to broad tree/history/GitHub inventory only when that task actually requires it.

Permanent principles and the mandatory three-part documentation/publication contract are canonical
in `docs/PROJECT_PRINCIPLES.md` and are not duplicated here.

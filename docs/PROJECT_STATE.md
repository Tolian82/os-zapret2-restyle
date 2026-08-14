# os-zapret2-restyle — Current state

Status: **CURRENT**
Updated: 2026-08-14

This file answers: **Where is the project now?**

Permanent principles are canonical in `docs/PROJECT_PRINCIPLES.md` and are not repeated here.
Operational continuation details are in `docs/START_HERE.md`.

## Current repository/package identity

- repository: `Tolian82/os-zapret2-restyle`;
- primary branch: `main`;
- semantic version: `0.4.1`;
- current packaged source revision: `12`;
- package candidate: `os-zapret2-restyle-0.4.1_12.pkg`;
- required ABI: `FreeBSD:15:amd64`;
- packaged runtime/source merge: `acf65d39eaa88a16debe1d35affa71f03f1d848d`;
- testing tag: `v0.4.1_12`;
- package SHA-256: `3b5a6c39c09abdfc8d8f1b59923312c40dda27e11c4f03e20773131996f6789d`;
- direct package URL: `https://github.com/Tolian82/os-zapret2-restyle/releases/download/v0.4.1_12/os-zapret2-restyle-0.4.1_12.pkg`.

Current documentation-only `main` may be later than the packaged source merge. Always resolve the
actual `main` SHA before mutation.

Stable semantic release remains `v0.4.1`; testing revisions remain forward candidate history and do
not rewrite the semantic tag.

## Current Strategy Lab production state

Current source normal path enters:

`C-warm-bucket-source-port-dispatch`

but still retains automatic legacy fallbacks:

`C-warm-bucket-source-port-dispatch -> B-warm-worker-parallel-batched -> A-cold-fallback`.

Current engineering decision:

- Model C is the selected/final production direction;
- automatic Model-B and cold-Model-A fallback is a legacy transition tail;
- B/A code may remain where useful as benchmark/reference/test tooling;
- the next packaged source change removes B/A from normal production fallback rather than optimizing
  that fallback further.

Preserved current Model-C behavior:

- native adaptive search/planner and CandidateSpec identity;
- ResourceInventory semantics;
- candidate width at most three;
- exact source-port-qualified attribution;
- sequential pinned endpoints inside a candidate;
- source-port leasing `preferred-free-else-alternate`;
- `_11` logical-batch preservation with profile-compatible physical segmentation;
- `_12` readiness: process identity + socket ready + clean log + two consecutive qualified
  snapshots, 25 ms polling, 4 s bound;
- production discovery GET-4K;
- `eligible-work-v1` finite adaptive budgets;
- bounded cancellation/cleanup and Stage-90 restoration;
- downstream Stage 70/80/85/result ownership.

## Latest accepted live evidence

### Production baseline — `v0.4.0_26`

Extended `telegram.org`, `job.xhdgCU`:

- effective adaptive budgets `150/120/270/120`;
- Model C 16/16, graph exhausted, zero winners;
- `.parallel.fallbacks=[]`;
- Stage 60 `34209 ms`, total `114644 ms`;
- Stage-90 restoration PASS;
- normal Zapret2 remained RUNNING;
- no `19128-19130` residue.

### Latest Model-C lifecycle/readiness evidence — `v0.4.1_12`

Retained `job.lWLjqL`, five repeats:

- 5/5 completed;
- 5/5 `model_c_only=true`;
- no fallback;
- instrumentation/persisted logical-batch counts matched;
- lifecycle/RSS complete;
- cleanup/restoration PASS;
- physical-segment startup median `82.5 ms`, mean `93.87 ms`, p90 `163 ms`;
- one segment about `80-90 ms`, two sequential segments about `163-171 ms`;
- median aggregate RSS `4366 KiB`;
- median Stage-60 wall `22715 ms`.

Strict lifecycle `measurement_rejected` was caused by live candidate result variation between repeats,
not Model-C infrastructure failure.

Evidence:
`docs/verification/evidence/2026-08-14-v0.4.1_12-warm-readiness-live-pass.md`.

## Accepted/closed optimization evidence

These conclusions remain current until invalidated by new evidence, owner requirement or a material
architecture change. They may be audited when the current plan calls for it.

- Lua initialization (`_2`): current/common init already equals candidate-minimal union; no production
  change justified.
- BLOB startup/RSS (`_3`): 27/27 starts accepted; stable readiness medians
  `63.061/62.652/62.566 ms` for BLOB-free/builtin/external; median RSS `4360 KiB`; no material cost.
- BLOB common set (`_4`): 48/48 starts accepted; common-3 vs external-single median readiness
  `+0.234 ms/+0.375%`, median RSS `+2 KiB/+0.046%`; below run spread; no lazy-BLOB change justified.
- Discovery (`_5/_6`): HEAD/GET-1/GET-4K agreement established on comparable samples; cheaper probes
  did not show a material timing benefit; production GET-4K retained.
- Cross-batch lifecycle (`_7` through `_12`): `_11` and `_12` fixed real production defects; further
  keep-warm/reuse architecture not justified by accepted measured cost/jitter boundary.

## Current next packaged source change — `v0.4.1_13`

### What changes and why

Make Model C the only normal production Stage-60 runtime:

- remove automatic production replay through Model B/cold Model A;
- surface Model-C infrastructure/selector/rendering/readiness/attribution failures explicitly and
  within existing bounded behavior;
- keep B/A modules where useful as benchmark/reference/test tooling;
- preserve Model-C leasing, attribution, segmentation, readiness, cleanup and restoration semantics.

Primary source/test surfaces:

- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_model_c.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_python.py`;
- `src/opnsense/scripts/OPNsense/Zapret/strategy_lab_py/stage60_source_port_lease.py`;
- `scripts/test-strategy-lab-stage60-model-c-production.sh`;
- narrow-search hits that encode production `C -> B -> A` fallback.

Metadata:

- keep `VERSION=0.4.1`;
- increment `PLUGIN_REVISION 12 -> 13`;
- candidate/title prefix `v0.4.1_13:`.

### Expected result

- normal production Stage 60 uses Model C only;
- no silent B/A fallback after Model-C infrastructure failure;
- injected Model-C infrastructure failure is explicit and bounded;
- cleanup succeeds on success/failure/cancel boundaries;
- leasing/attribution and `_11` segmentation remain intact;
- complete Strategy Lab corrective matrix PASS;
- FreeBSD 15 package qualification PASS;
- one selected owner-live Model-C-only regression proves result handling, restoration and no
  temporary residue.

### Further plan

1. merge the current docs/governance handoff patch without package metadata change;
2. implement `_13`;
3. run focused and full corrective validation;
4. qualify FreeBSD 15 package;
5. reconcile docs/near/long-term plan before publication;
6. Ready PR -> checks -> exact-head squash merge -> verify `main`;
7. publish deterministic `_13` testing package when owner testing/package delivery is requested;
8. perform one selected owner-live Model-C-only regression;
9. record evidence and close B -> C transition on PASS;
10. return to `docs/ROADMAP.md` for the next owner-selected product/Strategy-Lab work.

Do not implement the previously considered larger timeout-admission envelope for legacy `C -> B`
before `_13`; that specific problem disappears if the automatic fallback is retired. Future timeout
audits remain valid when selected by roadmap/owner or triggered by a real Model-C-only defect.

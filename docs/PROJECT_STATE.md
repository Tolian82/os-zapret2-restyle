# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary,
blockers, active architectural direction, and next action.

Updated when:
Current source/package identity, live boundary, blocker, approved implementation direction,
or next action changes.

Read after:
`AGENTS.md` and `docs/INDEX.md`.

Do not store here:
Full chronological history, detailed implementation design, or complete test logs.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current published project release/package: `v0.4.0` / `os-zapret2-restyle-0.4.0_1.pkg`
Latest published testing prerelease: `v0.4.0_2` / `os-zapret2-restyle-0.4.0_2.pkg`
Latest owner-tested testing candidate: `v0.4.0_2` / `os-zapret2-restyle-0.4.0_2.pkg`
Current source line: `VERSION=0.4.0`
Current package revision: `PLUGIN_REVISION=5`
Current source candidate: `os-zapret2-restyle-0.4.0_5.pkg` (source-qualified; not published or owner-tested)
Current released package: `os-zapret2-restyle-0.4.0_1.pkg`
Target ABI: **FreeBSD:15:amd64 only**
Current phase: **adaptive-search `_31` source-qualified; `_32` telemetry-driven timeout containment is next**
v0.4.0 release gate: **COMPLETE — published and installed by the owner**

Current primary Strategy Lab authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current migration decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Approved next search architecture:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

Active adaptive-search decision and experiment gate:
`docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md` and
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Current GitHub delivery authority:
`docs/GITHUB_PUBLICATION.md`,
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`, and the other active dated
GitHub decisions referenced by the publication authority.

Current live-gate authority:
`docs/verification/STRATEGY_LAB_LIVE_OPNSENSE_MATRIX.md`.

Current live evidence:
`docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.

Current live-release-gate decision:
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

==================================================
MIGRATION OWNERSHIP
==================================================

The automated Strategy Lab migration is complete through Patch 8:

- Patch 1 (`_18`) — FreeBSD 15 / Python 3.13 packaging and compatibility;
- Patch 2 (`_19`) — Python automated-job state/progress/event persistence;
- Patch 3 (`_20`) — Python numbered-stage orchestration, budgets, cancellation and finalization;
- Patch 4 (`_21`) — Python finite request/probe execution and Stage-30/40 parsing;
- Patch 5 (`_22`) — Python candidate runtime/readiness/interception and Stage-50 screening;
- Patch 6 (`_23`) — Python Stage-60 expansion, Stage-70 stability/replay and Stage-80 extended protocols;
- Patch 7 (`_24`) — Python final profile construction, exact replay, shortlist and automated circular eligibility;
- Patch 8 (`_25`) — GUI/status reconciliation and post-migration live-gate handoff.

The shared lifecycle lock, audited FreeBSD system mutations and private circular-session
state remain deliberate shell boundaries. Corrective work must not reopen automated Python
ownership without a new architectural decision.

==================================================
APPROVED POST-MIGRATION SEARCH REDESIGN
==================================================

The owner approved the next Strategy Lab search architecture on 2026-08-08. `_28`
removed Stage-50 family hard gating and `_29` established the normalized immutable Python
candidate/resource boundary. `_30` replaced the active Stage-50/60 TSV policy with a
validated native Zapret2 DAG: seven reconnaissance seeds and sixteen expansion nodes,
including exact built-in and owner-external golden candidates. Resource eligibility is
semantic, Stage-50 evidence changes priority without removing graph reachability, and
candidate-defined `-d8`, `-d10` or absent ranges survive runtime and final-profile
rendering. `_31` now selects each next graph node from live PASS/FAIL evidence, pins all
candidate/replay comparisons to one recorded Stage-40 endpoint epoch, targets two to
three winners and persists phase timing. Cold execution and current timeout/validation
behavior remain unchanged until their dedicated decisions/cycles.

Approved direction:

- native Zapret2 search semantics only; classic zapret strategy syntax is not a search
  source;
- Stage 50 becomes evidence rather than an allowlist for Stage 60;
- Python gains explicit `CandidateSpec` and job-scoped installed-resource
  `ResourceInventory`;
- BLOB-free, built-in, inline and installed external BLOB cases are representable;
- `--out-range` is candidate data rather than a fixed `-d10` invariant;
- native/owner working strategies form a golden expressiveness/reachability corpus;
- adaptive graph search prioritizes useful neighboring candidates without making a
  family unreachable because its simple representative failed;
- IPv4/TCP/TLS receives the primary budget; IPv6 stays capability-gated/lower priority;
- QUIC retains only the fixed IPv4 UDP/443 capability/precheck and no longer has a
  planned Strategy Lab candidate-search branch;
- discovery and finalist deep validation are separated; 3/3 is fail-fast and finalists
  receive real bounded long-GET evidence;
- two to three strong stable candidates are the normal early-stop target;
- all timeout constants receive telemetry-driven review.

Warm candidate execution remains unresolved by design. Cold-per-candidate A, multiple
warm-worker B and warm-bucket/dispatcher C are compared under the explicit experiment
matrix before any one becomes production architecture. Coexisting warm workers and truly
parallel candidate probes are separate questions.

Detailed target architecture:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

Experiment/measurement authority:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Implementation sequence: `_28` hard-gate removal is source/CI/FreeBSD and owner-live
qualified; `_29` CandidateSpec/ResourceInventory and active-adapter cleanup, `_30` native
search graph/resources/golden corpus/range preservation and `_31` live planner/fixed
endpoint epoch/winner defaults/timing telemetry are source-qualified. Next are `_32`
timeout containment and `_33` discovery/stability/deep validation.

==================================================
LATEST OWNER LIVE RESULT — `_28`
==================================================

Owner-assisted Standard Strategy Lab test:

- candidate: `v0.4.0_2` / `os-zapret2-restyle-0.4.0_2.pkg`;
- target: `discord.com`;
- diagnostic job: `job.2HVQqr`;
- Stage 50 PASS with `accepted=[]`, seven of seven family representatives rejected;
- Stage 60 PASS with `total_available=14` and `completed=14`, proving every current
  catalog row remained reachable despite the empty Stage-50 acceptance set;
- Stage-60 stop reason: `catalog_exhausted`, not `no_accepted_family`;
- Stage 90 PASS and `configctl zapret status` confirmed the initially RUNNING service was
  running after the job;
- no temporary IPFW rule from `19100–19131` remained; only normal rule `19000` was shown;
- Stage 99 truthfully reported `NO_CANDIDATE` rather than an internal search error.

This is the focused qualification required for `_28`. It proves search reachability and
restoration, not that the pre-`_29` fixed catalog must find a strategy for every blocked
target. Exact owner evidence is preserved in
`docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.

==================================================
LATEST OWNER LIVE RESULT — `_26`
==================================================

Owner-assisted Standard Strategy Lab test:

- candidate: `v0.3.3_26` / `os-zapret2-restyle-0.3.3_26.pkg`;
- target: `rutracker.org`;
- diagnostic job: `job.Cs5ryG`;
- Stage 40 ERROR — required A lookup timed out;
- `baseline-evidence.json` classifies the lookup as `timeout` with `duration_ms=2024`,
  `returncode:null`, empty stdout/stderr and command `/usr/bin/drill rutracker.org A`;
- Stage 50–85 did not run because Stage 40 is a prerequisite gate;
- Stage 99 completed as `PARTIAL` because completed diagnostic results were preserved;
- the owner repeated the test five more times and every run stopped at Stage 40;
- a manual `/usr/bin/drill rutracker.org A` can answer in about 33 ms but intermittently
  takes roughly 8–10 seconds against local resolver `127.0.0.1`.

The `_26` source did not change `request.py` or `probe.py`; it only corrected Stage-50
candidate aggregation. The new failure is therefore a newly demonstrated deadline defect,
not a regression of the Patch-4 ANSWER-section parser correction.

==================================================
STAGE-50 LIVE DIAGNOSIS
==================================================

The `_25` failure is **not** evidence that the temporary dvtws2 runtime could not start.
Preserved `candidate-smoke.json` and candidate runtime evidence prove:

- Stage 50 completed 4 of 7 catalog families before aborting;
- `multisplit` failed normally;
- `multidisorder` failed normally;
- `seqovl` **passed** and opened the blocked target;
- `fake` failed normally;
- `accepted=["seqovl"]` and `all_pass=true` were already persisted;
- the `seqovl` candidate runtime had `process_identity:true`, `socket_ready:true`,
  `log_clean:true`, `stable:true`, `ready:true`;
- its reserved IPFW rule counter increased (`intercepted:true`);
- curl returned success against the selected endpoint with HTTP 301;
- candidate shutdown was clean;
- Stage 90 restoration passed.

Source diagnosis:

`strategy_lab_py/candidate.py` deliberately writes a structured JSON result for a
candidate-local error. `strategy_lab_candidate_runner.sh` returns status 1 when that result
contains `"error":true`. Before `_26`, `strategy_lab_py/family.py` treated every nonzero
runner status as a fatal Stage-50 exception before reading the structured candidate result.
Therefore one candidate-local error after the first four catalog entries aborted the whole
screening run, even though `seqovl` had already succeeded.

==================================================
CORRECTIVE `_26`
==================================================

Corrective `_26` has one logical purpose: **candidate-local failure isolation inside
Stage 50**.

Required behavior:

- candidate timeout remains a rejected candidate and screening continues;
- nonzero candidate-runner status accompanied by a fresh, valid structured result with
  `error:true` remains a rejected candidate and screening continues;
- accepted candidates already found are preserved;
- screening proceeds through the remaining catalog entries;
- missing/invalid candidate evidence, runner launch failure, cancellation or another true
  screening/system failure may still abort Stage 50;
- stale candidate JSON must never be reused as evidence for a new attempt.

Implementation:

- `strategy_lab_py/family.py` removes any old per-candidate result before launch;
- it reads fresh structured candidate evidence even when the compatibility runner returns
  nonzero;
- structured `error:true` is aggregated as rejected and records `runner_status`;
- nonzero status without structured candidate error evidence remains fatal.

Focused regression:
`scripts/test-strategy-lab-stage50-candidate-isolation.sh`.

Existing Python candidate/family regression remains authoritative:
`scripts/test-strategy-lab-python-candidate-family.sh`.

`_26` passed source/CI/package qualification, was published as a testing prerelease and
installed by the owner. Its Stage-50 correction remains live-unverified because the `_26`
Scenario-1 runs now stop earlier at Stage 40.

==================================================
CORRECTIVE `_27`
==================================================

Corrective `_27` has one logical purpose: **accept slow but valid local DNS resolution at
the mandatory Stage-40 baseline while preserving bounded execution**.

Implementation contract:

- keep `/usr/bin/drill` and the local OPNsense resolver path;
- increase the Python-owned DNS subprocess deadline from 2 to 15 seconds;
- increase the enclosing Stage-40 operation limit from 5 to 20 seconds so the outer stage
  watchdog cannot kill a still-valid DNS request before its own deadline;
- keep DNS timeout, command failure and parser rejection as distinct structured evidence;
- keep ANSWER-section-only A/AAAA parsing unchanged;
- keep the 150-second Standard overall budget unchanged;
- prove that a DNS answer arriving after the old 2-second deadline succeeds and that a
  genuinely over-deadline request still terminates as timeout.

Changing the `PARTIAL` GUI/result wording is explicitly outside `_27`; that is a separate
logical presentation task.

==================================================
CONFIRMED DEFECT BACKLOG
==================================================

Owner evidence on `_27` closes the release-blocking `_26`/`_27` corrective items. Other
presentation/regression observations remain backlog rather than implicit release blockers.

1. **Stage-40 DNS deadline — CLOSED for release.** `_27` owner Scenario 1 passes Stage 40.
2. **Stage-50 candidate isolation — CLOSED for release.** The same `_27` run passes Stage
   50 and advances through Stages 60/70.
3. **Immediate stale/new-job GUI error.** The owner reported that the start error was not
   reproduced on `_26`; retain as open until a complete Scenario-1 run confirms it.
4. **Active GUI no-output message.** Patch 8 separates transient reads from persisted state;
   `_25` evidence did not explicitly reproduce or close this item.
5. **GUI progress stuck at 0%.** `_25` showed live persisted progress at 36%; retain as
   partially improved evidence until a complete Scenario-1 run confirms behavior through
   later stages.
6. **PARTIAL summary wording/presentation.** `_26` Stage 99 says available results were
   preserved even though search stages never ran and no strategies exist. The GUI exposes
   the partial summary but no strategy list. Clarifying this is a separate logical task.
7. **Terminal reload/state presentation.** Live recheck still required.
8. **Baseline target-type / DNS parser / DNS failure-class corrections from Patch 4.** Source
   regressions pass; `_27` preserves those semantics while changing only deadlines.
9. **Candidate fatal-log classification from Patch 5.** Source regressions pass; final live
   closure remains tied to the matrix.

==================================================
DELIVERY AND LIVE-GATE BOUNDARY
==================================================

Corrective `_27` source is squash-merged on `main` at
`0420dbf0632dc823a2d9086974db365030596a61`. Its source/CI qualification is complete;
owner-assisted replacement live evidence now passes Scenario 1 on the published `_27`
prerelease.

Its delivery contract was:

- `VERSION` remains `0.3.3`;
- `PLUGIN_REVISION=27`;
- candidate identity is `os-zapret2-restyle-0.3.3_27.pkg`;
- focused Python request/probe and orchestration deadline regressions must pass;
- all Python migration continuity tests must pass;
- complete Strategy Lab corrective matrix must pass;
- repository CI/governance/hygiene must pass;
- FreeBSD 15 package build/inspection must pass.

Testing-prerelease/package publication state remains distinct from source qualification
and must be read from current GitHub Release state under `docs/GITHUB_PUBLICATION.md`
before an installation instruction is issued.

The owner installed `_27` and completed Scenario 1 on `rutracker.org`: Stage 40 PASS,
Stage 50 PASS, Stages 60/70 PASS, Stage 90 PASS and truthful `NO_CANDIDATE`. Under the
risk-based live-release policy, this is the mandatory v0.4.0 post-migration live row.
Rows 2–18 remain useful regression backlog without blocking v0.4.0 solely because they
are pending.

The `v0.4.0 / 0.4.0_1` release cycle is complete. Immutable tag `v0.4.0` resolves to
release commit `5e2f98c503a94413be76d7fd6b7f5721fc436f56`; Release workflow run 17 passed and
published the package/checksum plus the Pages/pkg repository. The owner subsequently
installed `0.4.0_1` on OPNsense.

Adaptive-search `_28` advanced the candidate to `0.4.0_2`, passed source/CI/FreeBSD
qualification, was published as a testing prerelease and passed the focused owner-live
gate on `discord.com`: Stage 50 accepted no family, Stage 60 still attempted all 14
catalog candidates, and Stage 90 restored the initial RUNNING service without temporary
IPFW residue. The full regression matrix remains open under risk-based selection. `_29`
added the canonical CandidateSpec/ResourceInventory boundary and removed active
shell-adapter policy. `_30` added the native search graph, golden corpus, semantic
resource branches and exact variable-range output. `_31` advances the unpublished source
candidate to `0.4.0_5` with live-evidence ordering, a fixed endpoint epoch,
three-winner defaults and timing telemetry. `_32` is now the next source cycle.

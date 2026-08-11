# os-zapret2-restyle — Current state

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where is the project now?

Purpose:
Provide the fastest authoritative recovery of current version, verified live boundary,
blockers, active architectural direction, and next action.

Read after:
`AGENTS.md` and `docs/INDEX.md`.

Do not store here:
Full chronological history, detailed implementation design, or complete test logs.
Those belong in `docs/devlog/`, `docs/patches/`, and `docs/verification/evidence/`.

==================================================
QUICK CONTEXT
==================================================

Project: `os-zapret2-restyle`
Primary branch: `main`
Current source line: `VERSION=0.4.0`, `PLUGIN_REVISION=23`
Current source candidate: `os-zapret2-restyle-0.4.0_23.pkg`
Latest published testing prerelease: `v0.4.0_23`
Latest owner-tested testing candidate: `v0.4.0_22`
Required package ABI: `FreeBSD:15:amd64`
Current `_23` merge commit: `77b1beec471d161fb80584bf884e98970d4c75b3`
Published `_23` asset digest: `sha256:f735f88e62fc82e5e856123f0d7c3dc26bd550b3ec0d5ab0e72bb2277dabe364`

Active Strategy Lab ownership authority:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Active GitHub delivery authority:
`docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`.

Current `_23` change authority:
`docs/decisions/DEC-2026-08-11-strategy-lab-model-c-production-switch.md`,
`docs/architecture/STRATEGY_LAB_MODEL_C.md`, and `docs/patches/v0.4.0_23.md`.

Publication evidence:
`docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md`.

Current Strategy Lab Stage-60 production candidate:
`C-warm-bucket-source-port-dispatch`.

The accepted `_22` `B-warm-worker-parallel-batched` implementation remains the immediate
runtime fallback/reference. Cold Model A remains the final fail-closed fallback. Candidate
parallel width stays at most 3, pinned endpoints inside one candidate remain sequential,
and there is no CPU-count gate.

==================================================
AUTHORITATIVE OWNER-LIVE BASELINE
==================================================

Latest completed owner-live evidence remains:
`docs/verification/evidence/2026-08-11-v0.4.0_22-production-model-b-live.md`.

The `_22` baseline remains authoritative until `_23` appliance results are supplied:

- Standard `telegram.org` `job.KpLHgb`: production Model B, 16/16 graph exhaustion,
  zero winners, width-three overlap, no fallback, `NO_CANDIDATE`, Stage 60 `34227 ms`,
  total `89039 ms`, clean restoration;
- Standard `rutracker.org` `job.GK0X66`: production Model B, 16/16, Stage-60 winners
  `seqovl-host` and `seqovl-midsld`, Stage 70/85 successful, Stage 60 `28151 ms`, total
  `81272 ms`, clean restoration;
- Extended `rutracker.org` `job.d5XV82`: one `42003` controlled-source-port conflict
  activated the designed cold fallback; the job completed `SUCCESS` and restoration/
  cleanup passed.

The historical Stage-60 partial/parent-timeout defect was closed by `_7`/`_8`. A current
16/16 Stage-60 run is therefore not evidence that the old defect returned.

==================================================
CURRENT `_23` ARCHITECTURE
==================================================

Strategy Lab orchestration remains Python-owned. The stage order remains:
`00 -> 10 -> 20 -> 30 -> 40 -> 50 -> 60 -> 70 -> 80 -> 85 -> 90 -> 99`.

Stage 60 still uses the same native Zapret2 deterministic graph, fixed Stage-40 endpoint
epoch, adaptive frontier priority, winner band, budgets, cancellation and deterministic
planner-order persistence.

For each currently admitted Stage-60 frontier batch, Model C renders up to three immutable
`CandidateSpec` objects into one warm `dvtws2` bucket:

- one physical worker uses the existing first dedicated divert port;
- up to three exact IPFW routes (`19128-19130`) can concurrently divert candidate flows
  to that one worker;
- every route is qualified by the accepted controlled TCP source port, pinned destination
  IPv4 and TCP/443;
- `zapret-auto.lua` `condition` orchestrates each candidate action chain;
- packaged `strategy_lab_model_c.lua` selects the chain by the client source port and
  fails closed when selector/packet metadata is invalid;
- candidate-specific payload, `in-range`/`out-range`, ordered Lua actions and BLOB
  resources are reset/rendered per chain, preserving the existing `-d8` and `-d10`
  semantics;
- endpoints inside one candidate remain sequential while independent candidate tasks may
  overlap up to the existing width-three limit.

Successful probes retain strict connected-socket endpoint/local-port identity. Failed or
blocked probes retain `_21` exact command source-port + exact pinned `--resolve` + exact
matching IPFW counter growth + successful route cleanup attribution.

If Model C cannot prove compatible rendering, selector availability, worker readiness,
route attribution, required overlap or cleanup, it is disabled and the same planned work
falls back to accepted Model B. If Model B warm infrastructure also fails, the existing
cold Model A fallback applies. Ordinary network FAIL/timeout remains candidate evidence
rather than an infrastructure fallback trigger.

Stage 70/80/85 ownership is unchanged. Stage-90 semantic restoration remains mandatory on
every terminal path.

==================================================
CURRENT VERIFICATION BOUNDARY
==================================================

`v0.4.0_23` is **published and ready for owner-live testing**. PR #177 passed the complete
project validation, Strategy Lab corrective matrix and FreeBSD 15 package build/inspection.
Publication workflow run `31520848437` built, verified and published the exact prerelease,
then deleted `publish/v0.4.0_23`.

GitHub Release `v0.4.0_23` is `draft=false`, `prerelease=true`, targets exact main commit
`77b1beec471d161fb80584bf884e98970d4c75b3`, and contains one package asset:
`os-zapret2-restyle-0.4.0_23.pkg`, 177429 bytes, digest
`sha256:f735f88e62fc82e5e856123f0d7c3dc26bd550b3ec0d5ab0e72bb2277dabe364`.

This proves source/CI/FreeBSD/package publication only. **Model C has not yet been
owner-live accepted.** Do not rewrite the `_22` accepted live evidence as `_23` evidence.

Initial `_23` owner-live checks should establish:

1. normal Stage 60 reports `C-warm-bucket-source-port-dispatch` rather than silently using
   Model B;
2. a multi-candidate batch has `physical_worker_count=1`, distinct route rules and exact
   selector source-port sets;
3. a no-candidate target remains truthful through graph exhaustion;
4. a working-candidate target still hands correct candidates to Stage 70/85;
5. Model-C/Model-B fallback evidence is truthful if a runtime conflict occurs;
6. Stage 90 restores the original service state and rules `19128-19130` leave no residue.

==================================================
ACCEPTED HISTORICAL BASELINES
==================================================

- `_32` timeout-containment: owner-live PASS through `v0.4.0_8`.
- `_33` adaptive validation: change-specific owner-live PASS on `v0.4.0_9`.
- Model A cold reference: accepted on `v0.4.0_11` / `job.TtZeaH`.
- Model B coexistence: accepted on `_16`, repeated 5/5 on `_17`.
- Model B sequential exhaustive: `_19` owner-live ACCEPT 5/5, mean `74808.2 ms`, about
  `15.96%` candidate-runtime improvement versus cold Model A.
- Model B controlled parallel: `_21` reproducible ACCEPT, repeat mean `33025.6 ms`, about
  `62.90%` candidate-runtime reduction versus cold Model A and about `55.85%` versus
  sequential warm Model B, aggregate RSS roughly 13 MiB.
- Model B production integration: `_22` owner-live no-candidate, working-candidate,
  fallback and restoration evidence accepted.

Historical evidence remains valid comparison material but never overrides a later current
patch/PR/live record when diagnosing the installed package.

==================================================
CURRENT WATCH ITEMS
==================================================

1. `_23` Model C has not yet been owner-live tested. Publication/CI qualification must not
   be described as appliance acceptance.
2. `_22` `job.d5XV82` observed one source-port collision on `42003`. `_23` retains the
   existing source-port ownership rules and fail-closed chain; if the collision recurs,
   capture exact socket/process/batch evidence rather than weakening attribution.
3. The explicit three-winner early-stop branch remains automated-regression covered; the
   supplied `_22` owner-live set did not reach three Stage-60 winners.
4. Broader live-matrix rows not selected for this change remain regression backlog rather
   than blanket release blockers.

==================================================
DOCUMENT / EVIDENCE PRECEDENCE
==================================================

For current diagnosis read, in order:

1. this `PROJECT_STATE.md`;
2. `docs/patches/v0.4.0_23.md`;
3. PR #177 implementation/publication comments and later owner-live comments;
4. `docs/verification/evidence/2026-08-11-v0.4.0_23-publication.md` and the later dated
   `_23` owner-live evidence when created;
5. `_22` and older records only as retained baselines/comparisons.

==================================================
NEXT ACTION
==================================================

Install the published `v0.4.0_23` package and run the focused owner-live Model-C checks
above. Do not spend another cycle re-proving the accepted `_22` parallel Model B
architecture unless `_23` evidence specifically implicates the fallback boundary.

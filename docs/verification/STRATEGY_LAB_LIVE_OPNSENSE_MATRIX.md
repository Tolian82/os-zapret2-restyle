# Strategy Lab live OPNsense verification matrix

Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; FULL REGRESSION MATRIX OPEN**

This matrix is the canonical live-appliance regression inventory for Strategy Lab.
Source tests, GitHub CI, and FreeBSD package builds cannot substitute for a live PASS when
a row is selected as mandatory for a release. Not every pending row is automatically a
release blocker; selection follows
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest test date/time: `2026-08-10`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.4.0_7.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_7.pkg`
- Current adaptive-search source candidate: `os-zapret2-restyle-0.4.0_8.pkg`
- Latest owner-tested Standard job: `job.RFVs75`
- Latest owner-tested diagnostic job: `job.QbUuYO`
- WAN interface: `vtnet1`
- Latest blocked-domain target: `telegram.org`
- Generic UDP target/port: `PENDING OWNER`

Architecture / ABI baseline evidence:
`docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`.

Latest live evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`.

Previous timeout evidence:
`docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md`.

v0.4.0 release-selected evidence:
`docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md`.

Previous migration-handoff evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
SCENARIO 1 HISTORY
==================================================

The early failed attempts and their exact evidence remain preserved under
`docs/verification/evidence/`. The third-audit source record is
`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

Key live progression:

- `_12` exposed Stage-50 failure plus Stage-90 FreeBSD timeout reaping of restored daemon descendants.
- `_13` corrected restoration timeout semantics; owner testing proved Stage 90 PASS.
- `_14` corrected FreeBSD DNS foreground timeout; owner testing proved Stage 40 PASS with `DNS: OK`.
- `_15` corrected unset family-runner timeout ownership but Stage 50 still failed.
- `_16` corrected resident FreeBSD daemon startup blocking and reached real candidate dvtws2 startup/bind/privilege-drop; it then failed post-drop hostlist traversal through a private job directory.
- `_17` corrected that hostlist traversal permission boundary and became the frozen shell-era handoff to the Python migration.
- `_18` through `_24` completed the automated Python migration.
- `_25` reconciled GUI/status transport behavior, was published as a testing prerelease and was installed for post-migration owner testing.
- `_26` corrected Stage-50 candidate-local failure isolation, passed CI/package
  qualification, was published as a testing prerelease and was installed for live retest.
- `_26` live retesting exposed an earlier Stage-40 blocker: the Python DNS subprocess
  deadline is shorter than intermittent valid local-Unbound response time.
- `_27` widened the DNS/stage deadline envelope; owner retesting passed Stage 40, passed
  Stage 50, continued through Stages 60/70 and ended truthfully as `NO_CANDIDATE` with
  Stage-90 cleanup/restoration PASS.
- `_28` removed Stage-50 acceptance as a Stage-60 hard gate; owner testing on
  `v0.4.0_2` produced `accepted=[]`, still attempted all 14 Stage-60 catalog candidates,
  and passed exact Stage-90 cleanup/restoration.
- `v0.4.0_6` owner retesting against `telegram.org` proved the Stage-50 containment
  correction: all seven reconnaissance families completed in about 39 seconds. Both
  Standard and Extended runs then exposed the next `_32` boundary when the fixed 70-second
  Stage-60 parent limit terminated expansion after 12 of 16 candidates. Stage 90 restored
  the initially RUNNING service and no temporary IPFW rule remained.
- `v0.4.0_7` owner retesting closed that Stage-60 boundary: both Standard and Extended
  runs completed all 16 expansion candidates, continued through Stage 70/80/85 as
  applicable, ended truthfully as `NO_CANDIDATE`, and restored the initially RUNNING
  service without temporary IPFW residue.
- `v0.4.0_8` is the current `_32` source correction for the remaining late-stage
  containment gaps: Stage-70/80 candidate admission plus explicit Stage-85 and Stage-90
  parent bounds. Owner-live verification remains pending.

Historical `_17`, job `job.w0nXxQ`, ended with Stage 50 ERROR and Stage 90 PASS. Its
candidate-runtime bundle was not collected, so the exact `_17` Stage-50 root cause remains
unclaimed historical context.

==================================================
POST-MIGRATION OWNER TEST — `_25`
==================================================

Owner-assisted `_25`, job `job.c0oydv`:

- 00 PASS;
- 10 PASS — initial Zapret2 RUNNING;
- 20 PASS — normal service stopped;
- 30 PASS — IPv4 available; IPv6 unavailable; QUIC/IPv4 closed;
- 40 PASS — `DNS: OK`; direct TLS 1.3 connection not established;
- 50 ERROR — visible message `Temporary candidate runtime failed internally.`;
- 60–85 SKIPPED;
- 90 PASS — temporary state removed and initial RUNNING Zapret2 restored healthy;
- 99 ERROR.

GUI behavior on `_25`:

- the owner still observed a brief immediate `Статус: ОШИБКА` after pressing Run;
- a later active screenshot correctly showed `Статус: ВЫПОЛНЯЕТСЯ`;
- persisted progress was visible at 36% / Stage 40 instead of remaining at 0% until terminal;
- no unsupported closure is claimed for active no-output or reload behavior that was not
  explicitly exercised during this run.

The preserved Stage-50 evidence proves the temporary candidate runtime itself was capable
of running correctly and that a working family was already found before Stage 50 aborted:

- `candidate-smoke.json`: `total=7`, `completed=4`, `accepted=["seqovl"]`, `all_pass=true`;
- `multisplit`: normal candidate FAIL, curl exit 28;
- `multidisorder`: normal candidate FAIL, curl exit 28;
- `seqovl`: **candidate PASS**;
- `fake`: normal candidate FAIL, curl exit 35;
- the `seqovl` candidate used selected IP `172.67.182.196`;
- curl returned exit 0, HTTP/1.1 301 and matching remote IP;
- IPFW rule 19100 counters increased and `intercepted=true`;
- runtime evidence recorded `process_identity=true`, `socket_ready=true`, `log_clean=true`,
  `stable=true`, `ready=true` after two stable checks;
- dvtws2 bound the divert socket, dropped to UID/GID 65534 and shut down cleanly.

Therefore `_25` Stage 50 did **not** fail because every temporary runtime was broken. The
aggregate stage failed after four catalog entries despite already having a working family.

==================================================
CORRECTIVE `_26` SOURCE DIAGNOSIS
==================================================

`strategy_lab_py/candidate.py` writes a structured JSON result for candidate-local errors.
The compatibility `strategy_lab_candidate_runner.sh` intentionally returns status 1 when
that JSON contains `"error":true`.

Before corrective `_26`, `strategy_lab_py/family.py` treated every nonzero candidate-runner
status as a fatal Stage-50 exception before reading the candidate JSON. A candidate-local
error could therefore abort the entire catalog, discard continuation after an already
accepted family and produce the misleading generic Stage-50 internal-error message.

Correct `_26` contract:

- timeout remains a rejected candidate and screening continues;
- nonzero runner status plus a fresh valid structured candidate result with `error:true`
  remains a rejected candidate and screening continues;
- already accepted candidates remain preserved;
- missing/invalid structured evidence or nonzero runner status without a structured
  candidate error remains a true screening failure;
- stale candidate JSON is removed before each launch and cannot be reused.

Focused regression:
`scripts/test-strategy-lab-stage50-candidate-isolation.sh`.

==================================================
POST-MIGRATION OWNER TEST — `_26`
==================================================

Owner-assisted `_26`, diagnostic job `job.Cs5ryG`, against `rutracker.org`:

- Stage 40 ERROR — required A resolution failed;
- `baseline-evidence.json` records `/usr/bin/drill rutracker.org A` as `timeout`;
- subprocess duration was `2024 ms`, with `returncode:null`, `timed_out:true` and no
  stdout/stderr before termination;
- Stage 50–85 did not run because Stage 40 is a prerequisite gate;
- Stage 99 completed as `PARTIAL`, preserving completed diagnostic results;
- five additional Strategy Lab attempts stopped at the same Stage-40 prerequisite.

Manual owner testing of `/usr/bin/drill rutracker.org A` against resolver `127.0.0.1`
shows the same query can return immediately (captured at 33 ms) or intermittently take
about 8–10 seconds before returning valid A answers.

The `_26` change did not touch `request.py`/`probe.py`, so this is not loss of the `_21`
ANSWER-section parsing correction. It is a newly proven deadline mismatch.

The `_26` Stage-50 correction remains live-unverified because these runs do not reach
Stage 50.

==================================================
CORRECTIVE `_27` SOURCE DIAGNOSIS
==================================================

`strategy_lab_py/request.py` gives DNS subprocesses 2 seconds. The Python orchestrator
also gives the entire Stage-40 adapter only 5 seconds. A valid 8–10-second local-resolver
response therefore cannot complete reliably under either current limit.

Correct `_27` contract:

- keep `/usr/bin/drill` and local OPNsense resolver semantics;
- DNS subprocess deadline: 15 seconds;
- enclosing Stage-40 operation limit: 20 seconds;
- Standard overall job budget remains 150 seconds;
- `timeout`, `command_error` and `parser_rejected` evidence remain distinct;
- ANSWER-section-only A/AAAA parsing remains unchanged;
- a delayed valid answer beyond the old two-second cutoff must pass;
- an over-deadline subprocess must still terminate as timeout.

The `PARTIAL` summary wording observed after the early `_26` stop is a separate logical
presentation issue and is not part of `_27`.

==================================================
POST-MIGRATION OWNER TEST — `_27`
==================================================

Owner-assisted `_27` Standard run against `rutracker.org`:

- Stages 00, 10, 20, 30 and 40 PASS;
- Stage 40 reports `DNS: OK` and no direct TLS 1.3 connection;
- Stage 50 PASS and finds at least one working TLS 1.3 family;
- Stage 60 PASS: two working candidates from two tested;
- Stage 70 PASS: three stable candidates from three tested;
- Stage 80 SKIPPED as expected in Standard mode;
- Stage 85 PASS and forms the final result;
- Stage 90 PASS: temporary processes/rules removed and initial RUNNING Zapret2 restored
  healthy;
- Stage 99: `NO_CANDIDATE`, which is a valid terminal outcome rather than internal error.

This closes the `_26` Stage-50 and `_27` Stage-40 corrective live boundary. Exact supplied
evidence is preserved in
`docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md`.

==================================================
ADAPTIVE-SEARCH OWNER TEST — `_28`
==================================================

Owner-assisted `v0.4.0_2` Standard job `job.2HVQqr` against `discord.com`:

- package version/ABI: `0.4.0_2`, `FreeBSD:15:amd64`;
- Stages 00–40 PASS and direct TLS 1.3 baseline remains inaccessible;
- Stage 50 PASS with `total=7`, `completed=7`, `accepted=[]` and all families rejected;
- Stage 60 PASS with `total_available=14`, `completed=14`, all catalog candidates failed,
  and `stopped_reason=catalog_exhausted`;
- the obsolete `no_accepted_family` hard gate did not terminate or skip Stage 60;
- Stage 70 PASS with zero stability candidates, as expected after no Stage-60 winner;
- Stage 80 SKIPPED in Standard mode;
- Stage 90 PASS and the initially RUNNING service was restored healthy;
- post-job service status was RUNNING and the IPFW excerpt contained only normal rule
  `19000`, with no temporary rule in `19100–19131`;
- Stage 99 truthfully reported `NO_CANDIDATE` rather than an internal error.

This is the change-specific focused PASS that was required before `_29`. It does not mark unrelated
pending matrix rows as PASS. Exact evidence is preserved in
`docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.

==================================================
TIMEOUT-HIERARCHY OWNER TEST — `v0.4.0_6`
==================================================

Owner-assisted Standard job `job.3Vh6rW` and Extended job `job.Y8bR9M` against
`telegram.org`:

- package version/ABI: `0.4.0_6`, `FreeBSD:15:amd64`;
- both runs passed Stages 00–50;
- Stage 50 completed all seven reconnaissance families in about 39 seconds and no working
  TLS 1.3 family was found;
- both Stage-60 runs reached the fixed 70-second local parent limit after 12 of 16
  expansion candidates;
- the thirteenth candidate was prepared but did not produce a result JSON before the
  parent terminated Stage 60;
- the Standard run still had about 33 seconds of its 150-second search budget available;
- the Extended run still had about 154 seconds of its 270-second overall budget available;
- both runs restored the initially RUNNING Zapret2 service successfully;
- post-run IPFW evidence contained normal rule `19000` and no temporary rule in
  `19100–19131`.

This proves the immediate `v0.4.0_6` Stage-50 containment boundary and selects Stage-60
parent/child deadline admission as the next `_32` correction. Exact evidence is preserved
in `docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md`.

==================================================
TIMEOUT-HIERARCHY OWNER TEST — `v0.4.0_7`
==================================================

Owner-assisted Standard job `job.RFVs75` and Extended job `job.QbUuYO` against
`telegram.org`:

- package version/ABI: `0.4.0_7`, `FreeBSD:15:amd64`;
- both runs passed Stage 50 and Stage 60;
- Standard Stage 60 completed all 16 candidates in about 90.243 seconds;
- Extended Stage 60 completed all 16 candidates in about 89.249 seconds;
- Stage 70 completed normally with no stability candidates because Stage 60 found no
  working candidate; its measured parent allowance was only 13–14 seconds;
- Standard Stage 80 was skipped by mode; Extended Stage 80 completed, with QUIC and
  configured UDP explicitly skipped by capability/input state;
- Stage 85 completed in about 0.2 seconds in both runs but had no Python parent operation
  timeout in telemetry;
- Stage 90 restoration completed in about 6.9 seconds in both runs and likewise had no
  Python parent operation timeout;
- both jobs ended truthfully as `NO_CANDIDATE`;
- the post-run snapshot showed Zapret2 running and only normal IPFW rule `19000`, with no
  temporary Strategy Lab rule in `19100–19131`.

This closes the observed Stage-60 timeout defect and selects the remaining `_32`
late-stage containment work for `v0.4.0_8`. Exact evidence is preserved in
`docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`.

==================================================
PYTHON MIGRATION OWNERSHIP
==================================================

Authoritative migration plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Migration Patch 1 (`_18`) established the packaged Python 3.13 platform and compatibility
boundary. Patch 2 (`_19`) moved automated-job state/progress/event persistence to Python.
Patch 3 (`_20`) moved numbered stage order, budgets, cancellation, timeout and terminal
restoration/finalization policy to Python. Patch 4 (`_21`) moved finite network requests and
Stage-30/40 parsing. Patch 5 (`_22`) moved candidate runtime/readiness/interception and
Stage-50 family screening. Patch 6 (`_23`) moved Stage-60 expansion, Stage-70 stability and
Stage-80 extended protocols. Patch 7 (`_24`) completed final profile/exact replay/shortlist
ownership. Patch 8 (`_25`) reconciled GUI/status polling with persisted Python state.

Audited FreeBSD system mutations remain behind narrow shell adapters; private circular
sessions remain shell-owned by design. Corrective `_26` does not change those ownership
boundaries.

==================================================
REQUIRED EVIDENCE BUNDLE
==================================================

For each mandatory release-selected scenario preserve at minimum:

- exact installed candidate/version and supported ABI;
- the terminal stage/result report for the exercised behavior;
- restoration/cleanup outcome when the scenario owns the Zapret2 lifecycle.

When available, preserve the deeper diagnostic bundle below. It is required when needed
to diagnose a failure, resolve ambiguous behavior, or prove a safety property that the
terminal report does not itself establish; absence of an unrelated diagnostic artifact
does not invalidate an otherwise unambiguous successful release-selected row:

- screenshot of Diagnostics result and progress display;
- final automated `status.json` or circular `state.json`;
- initial and final `configctl zapret status` output;
- initial and final `pgrep -af 'dvtws2|zapret.*supervisor'` output;
- initial and final `ipfw show` excerpt for rules `19000` and `19100–19131`;
- generated temporary runtime log when a failure is investigated;
- exact scenario result and tester notes in this matrix.

Recommended appliance identity evidence:

```text
opnsense-version
uname -a
pkg info os-zapret2-restyle
configctl zapret status
```

Recommended residue evidence after every terminal scenario:

```text
pgrep -af 'strategy_lab|dvtws2|zapret.*supervisor'
ipfw show | grep -E '^(1910[0-9]|191[12][0-9]|1913[01]) '
configctl zapret status
```

==================================================
SCENARIO MATRIX
==================================================

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; Stage 90 restores RUNNING; no temporary residue | `2026-08-08-v0.3.3_27-scenario-01-pass.md` | **PASS ON `_27` — v0.4.0 mandatory row** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Test completes while final service remains STOPPED; restoration evidence verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 3 | Extended TLS 1.2 and HTTP | Available protocol successes appear as complete replay-verified profiles; unavailable protocols explicitly skipped | `PENDING OWNER` | **PENDING REGRESSION** |
| 4 | Extended QUIC | QUIC result endpoint-bound and replay-verified when capability exists; otherwise explicit skip reason | `PENDING OWNER` | **PENDING REGRESSION** |
| 5 | Generic UDP port and payload | Port/payload pair accepted only in Extended mode; result identifies selected IP and complete profile; payload removed after terminal cleanup | `PENDING OWNER` | **PENDING REGRESSION** |
| 6 | Target already accessible | Outcome `TARGET_ACCESSIBLE`; strategy search skipped; service state remains exact | `PENDING OWNER` | **PENDING REGRESSION** |
| 7 | No working candidate | Outcome `NO_CANDIDATE`; shortlist empty; not reported as internal error | `_27` Scenario 1 also terminates `NO_CANDIDATE`, but this dedicated row remains unexecuted | **PENDING REGRESSION** |
| 8 | User cancellation after service stop | Cancel requested; unfinished stages skipped; stages 90 and 99 run; original service restored | `PENDING OWNER` | **PENDING REGRESSION** |
| 9 | Hard whole-worker timeout | Outcome `TIMEOUT`; available results persist; Stage 90 restoration verified; no residue | `PENDING OWNER` | **PENDING REGRESSION** |
| 10 | Controlled internal failure | Outcome `ERROR`; failure stage truthful; original service restored and verified | `PENDING OWNER` | **PENDING REGRESSION** |
| 11 | Circular start, browser validation, and stop | Parent job files unchanged; private session active; stop ends completed; no global circular aliases | `PENDING OWNER` | **PENDING REGRESSION** |
| 12 | Circular stale-worker recovery | Owner mismatch detected; temporary runtime/rules cleaned; semantic restoration verified before retry | `PENDING OWNER` | **PENDING REGRESSION** |
| 13 | Settings Apply during automated Strategy Lab | Apply rejected before model mutation with lifecycle-owner information; saved configuration unchanged | `PENDING OWNER` | **PENDING REGRESSION** |
| 14 | Settings Apply during circular or `restore_failed` state | Apply rejected; unsafe retry blocked until restoration proven | `PENDING OWNER` | **PENDING REGRESSION** |
| 15 | Diagnostics page reload | Active reload resumes job; terminal reload opens idle view without deleting retained evidence or starting a new job | `PENDING OWNER` | **PENDING REGRESSION** |
| 16 | Russian and English presentation | Progress deterministic; stage/state/outcome/circular/UDP/copy/messages correct in both languages | `PENDING OWNER` | **PENDING REGRESSION** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence protected | `PENDING OWNER` | **PENDING REGRESSION** |
| 18 | Reboot after clean terminal completion | No temporary process or reserved IPFW residue returns; normal Zapret2 service/rule identity valid | `PENDING OWNER` | **PENDING REGRESSION** |

==================================================
CONFIRMED DEFECTS / LIVE RECHECKS
==================================================

- **Stage 40 DNS timeout on `_26`.** Closed by `_27` owner live Scenario 1 PASS.
- **Stage 50 aggregate abort on `_25`.** Closed by `_27` owner live Scenario 1 reaching
  Stage 50 PASS and continuing through Stages 60/70.
- **Stage 50 parent-timeout boundary on `v0.4.0_5`.** Closed for the observed live target
  by `v0.4.0_6`: Stage 50 completed all seven families and published PASS.
- **Stage 60 fixed 70-second parent timeout on `v0.4.0_6`.** Closed by `v0.4.0_7` in both
  Standard and Extended owner runs; all 16 Stage-60 candidates completed.
- **Late-stage containment after Stage 60.** `v0.4.0_7` proved the normal no-winner
  Stage-70/80/85/90 path and exposed missing Stage-70/80 admission plus unbounded Python
  parent calls for Stage 85/90; corrective `v0.4.0_8` is source-qualified/live-pending.
- **Immediate stale/new-job GUI error.** Not reproduced on `_26`, but retain as open until
  a complete Scenario-1 run confirms behavior.
- **Active `Strategy Lab returned no output.` message.** Patch-8 source correction exists;
  `_25` live run did not explicitly reproduce or close it.
- **Visible 0%-until-terminal progress.** `_25` showed live persisted progress at 36%; treat
  as improved evidence but do not close the whole presentation row until Scenario 1 runs
  through later stages.
- **Terminal reload/state presentation.** Live recheck pending.
- **PARTIAL summary wording.** `_26` preserves diagnostics but reports that available
  results were saved even though search never ran and no strategies exist; separate
  presentation correction pending outside `_27`.
- **Patch-4 target/DNS corrections.** Parser/classification source regressions pass; `_27`
  changes deadlines only and matrix closure remains pending.
- **Patch-5 candidate fatal-log classification.** Source regressions pass; matrix closure pending.

==================================================
FAILURE HANDLING
==================================================

Any of the following blocks a release when it occurs on a mandatory release-selected row
or is a known critical condition in the candidate:

- candidate ABI/architecture is not exactly FreeBSD 15 amd64;
- `RESTORE_FAILED` or unverified restoration;
- unexpected change to saved Traffic Strategy;
- lingering Strategy Lab worker, temporary dvtws2 process, divert socket, PID file, or rules `19100–19131`;
- parent-result mutation by circular validation;
- Settings Apply succeeding while lifecycle ownership is active;
- active work not resumed after reload;
- completed/error result automatically resurrected as the state of a newly opened Diagnostics page;
- reload deleting retained terminal evidence;
- missing evidence required for the release-selected behavior or for an observed failure.

A failed live row requires source correction when a source defect is identified, complete
CI/FreeBSD 15 package verification, and repetition of the affected live row plus required
independent rows. CI alone never marks a live row PASS.

==================================================
RELEASE GATE
==================================================

Stable release preparation uses the risk-based selection policy in
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`. Every row selected as
mandatory for the release must have owner evidence and PASS. Pending rows that are not
selected remain regression backlog and are not blockers merely because they are pending.

For `v0.4.0`, Scenario 1 is the selected mandatory post-migration row and is PASS on
`v0.3.3_27`. No known critical restoration/runtime defect remains from the `_26`/`_27`
corrective cycle. Adaptive-search `_28` additionally has its focused change-specific
owner PASS on `v0.4.0_2`. Rows 2–18 remain open regression coverage without a claimed
PASS. The newer `v0.4.0_7` live evidence closes the observed Stage-60 timeout and selects
`v0.4.0_8` for the remaining `_32` late-stage containment work; it does not retroactively
invalidate the release-selected `_27` or focused `_28` evidence.

# Strategy Lab live OPNsense verification matrix

Overall status: **FAILED ON `_26` — CORRECTIVE `_27` REQUIRED**

This matrix is the final live-appliance gate for Strategy Lab. Source tests, GitHub CI,
and FreeBSD package builds cannot substitute for evidence collected on the owner's
OPNsense appliance.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest test date/time: `2026-08-08`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.3.3_26.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_26.pkg`
- Current corrective source candidate: `os-zapret2-restyle-0.3.3_27.pkg`
- Current migration source candidate: `os-zapret2-restyle-0.3.3_27.pkg`
- Latest owner-tested diagnostic job: `job.Cs5ryG`
- WAN interface: `vtnet1`
- Blocked-domain target: `rutracker.org`
- Generic UDP target/port: `PENDING OWNER`

Architecture / ABI baseline evidence:
`docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`.

Latest live evidence:
`docs/verification/evidence/2026-08-08-v0.3.3_26-scenario-01-stage40-dns-deadline.md`.

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

For each applicable scenario preserve:

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
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; Stage 90 restores RUNNING; no temporary residue | Latest: `2026-08-08-v0.3.3_26-scenario-01-stage40-dns-deadline.md`; historical failed attempts remain under `docs/verification/evidence/` | **FAILED ON `_26` — `_27` STAGE-40 RETEST REQUIRED** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Test completes while final service remains STOPPED; restoration evidence verified | `PENDING OWNER` | **BLOCKED BY #1** |
| 3 | Extended TLS 1.2 and HTTP | Available protocol successes appear as complete replay-verified profiles; unavailable protocols explicitly skipped | `PENDING OWNER` | **BLOCKED BY #1** |
| 4 | Extended QUIC | QUIC result endpoint-bound and replay-verified when capability exists; otherwise explicit skip reason | `PENDING OWNER` | **BLOCKED BY #1** |
| 5 | Generic UDP port and payload | Port/payload pair accepted only in Extended mode; result identifies selected IP and complete profile; payload removed after terminal cleanup | `PENDING OWNER` | **BLOCKED BY #1** |
| 6 | Target already accessible | Outcome `TARGET_ACCESSIBLE`; strategy search skipped; service state remains exact | `PENDING OWNER` | **BLOCKED BY #1** |
| 7 | No working candidate | Outcome `NO_CANDIDATE`; shortlist empty; not reported as internal error | `PENDING OWNER` | **BLOCKED BY #1** |
| 8 | User cancellation after service stop | Cancel requested; unfinished stages skipped; stages 90 and 99 run; original service restored | `PENDING OWNER` | **BLOCKED BY #1** |
| 9 | Hard whole-worker timeout | Outcome `TIMEOUT`; available results persist; Stage 90 restoration verified; no residue | `PENDING OWNER` | **BLOCKED BY #1** |
| 10 | Controlled internal failure | Outcome `ERROR`; failure stage truthful; original service restored and verified | `PENDING OWNER` | **BLOCKED BY #1** |
| 11 | Circular start, browser validation, and stop | Parent job files unchanged; private session active; stop ends completed; no global circular aliases | `PENDING OWNER` | **BLOCKED BY #1** |
| 12 | Circular stale-worker recovery | Owner mismatch detected; temporary runtime/rules cleaned; semantic restoration verified before retry | `PENDING OWNER` | **BLOCKED BY #1** |
| 13 | Settings Apply during automated Strategy Lab | Apply rejected before model mutation with lifecycle-owner information; saved configuration unchanged | `PENDING OWNER` | **BLOCKED BY #1** |
| 14 | Settings Apply during circular or `restore_failed` state | Apply rejected; unsafe retry blocked until restoration proven | `PENDING OWNER` | **BLOCKED BY #1** |
| 15 | Diagnostics page reload | Active reload resumes job; terminal reload opens idle view without deleting retained evidence or starting a new job | `PENDING OWNER` | **BLOCKED BY #1** |
| 16 | Russian and English presentation | Progress deterministic; stage/state/outcome/circular/UDP/copy/messages correct in both languages | `PENDING OWNER` | **BLOCKED BY #1** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence protected | `PENDING OWNER` | **BLOCKED BY #1** |
| 18 | Reboot after clean terminal completion | No temporary process or reserved IPFW residue returns; normal Zapret2 service/rule identity valid | `PENDING OWNER` | **BLOCKED BY #1** |

==================================================
CONFIRMED DEFECTS / LIVE RECHECKS
==================================================

- **Stage 40 DNS timeout on `_26`.** Root cause identified: the 2-second DNS subprocess
  and 5-second stage envelope are shorter than an observed valid 8–10-second local
  resolver response; corrective `_27` required.
- **Stage 50 aggregate abort on `_25`.** Corrective `_26` source/CI/package qualification
  is complete, but live closure remains pending because `_26` stops earlier at Stage 40.
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

Any of the following keeps the live gate failed or pending:

- candidate ABI/architecture is not exactly FreeBSD 15 amd64;
- `RESTORE_FAILED` or unverified restoration;
- unexpected change to saved Traffic Strategy;
- lingering Strategy Lab worker, temporary dvtws2 process, divert socket, PID file, or rules `19100–19131`;
- parent-result mutation by circular validation;
- Settings Apply succeeding while lifecycle ownership is active;
- active work not resumed after reload;
- completed/error result automatically resurrected as the state of a newly opened Diagnostics page;
- reload deleting retained terminal evidence;
- missing required evidence.

A failed live row requires source correction when a source defect is identified, complete
CI/FreeBSD 15 package verification, and repetition of the affected live row plus required
independent rows. CI alone never marks a live row PASS.

==================================================
RELEASE GATE
==================================================

Stable release preparation and pkg-repository promotion remain blocked until every
required live row is marked PASS by the owner and linked evidence is recorded.

Corrective `_27` is not published merely because source exists. It must first pass the
normal latest-head CI and FreeBSD 15 package gate. Testing-prerelease publication requires
separate explicit owner authorization under `docs/GITHUB_PUBLICATION.md`.

There is no successful complete Strategy Lab live scenario PASS claim yet. The current
live record preserves the prior `_25` evidence for a functioning/intercepting candidate
runtime, a working `seqovl` family during partial Stage 50, and Stage 90 restoration. The
latest `_26` record supersedes Stage 40 as the active blocker and requires `_27` retest.

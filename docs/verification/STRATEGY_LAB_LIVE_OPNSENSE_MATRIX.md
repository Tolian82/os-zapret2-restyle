# Strategy Lab live OPNsense verification matrix

Overall status: **FAILED ON `_17` — LIVE MATRIX PAUSED FOR PYTHON MIGRATION**

This matrix is the final live-appliance gate for Strategy Lab. Source tests, GitHub CI,
and FreeBSD package builds cannot substitute for evidence collected on the owner's
OPNsense appliance.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Test date/time: `2026-08-07`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.3.3_17.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_17.pkg`
- Current migration source candidate: `os-zapret2-restyle-0.3.3_18.pkg`
- Latest owner-tested job: `job.w0nXxQ`
- WAN interface: `vtnet1`
- Blocked-domain target: `rutracker.org`
- Generic UDP target/port: `PENDING OWNER`

Architecture / ABI baseline evidence:
`docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`.

Current handoff evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`.

==================================================
SCENARIO 1 HISTORY AND CURRENT BOUNDARY
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
- `_17` corrected that hostlist traversal permission boundary and was published/installed for owner testing.

Owner-assisted `_17`, job `job.w0nXxQ`, is the final shell-era boundary before the
approved Python migration:

- 00 PASS;
- 10 PASS;
- 20 PASS;
- 30 PASS;
- 40 PASS — `DNS: OK`; direct TLS 1.3 connection not established;
- 50 ERROR — `Temporary candidate runtime failed internally.`;
- 60–85 SKIPPED;
- 90 PASS — temporary state removed and initial RUNNING Zapret2 restored healthy;
- 99 ERROR.

Immediate GUI behavior on the same active job:

- new job ID appeared with `Статус: ОШИБКА` immediately after Run;
- `Strategy Lab returned no output.` appeared while the job was still active;
- visible progress remained 0%;
- terminal result jumped directly to 100%.

No `_17` candidate-runtime log bundle was collected. Therefore this matrix does not claim
the exact remaining `_17` Stage-50 root cause. The identical high-level message does not
prove that the `_16` permission defect survived `_17`; it proves only that Stage 50 still
contains at least one unresolved failure.

==================================================
PYTHON MIGRATION HOLD
==================================================

The owner approved pausing further growth of the large sourced shell Strategy Lab worker
and migrating appropriate orchestration to Python.

Authoritative migration plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

Migration Patch 1 source candidate `_18` only establishes the packaged Python 3.13
platform and compatibility boundary. Its production service path still invokes the shell
worker directly, so `_18` neither supersedes the owner-tested `_17` live evidence nor
resumes Scenario 1.

The live matrix remains failed during migration. Do not mark a row PASS because a defect
mechanism was rewritten. Resume live Scenario 1 only when the Python implementation has
reached the designated functional parity gate and a testing candidate has passed CI and
the FreeBSD 15 package gate.

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
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; Stage 90 restores RUNNING; no temporary residue | Failed shell-era attempts include `_1`, `_2`, `_4`, `_5`, `_12`, `_13`, `_14`, `_15`, `_16`, and `_17`; current handoff is `2026-08-07-v0.3.3_17-scenario-01-python-handoff.md` | **FAILED ON `_17` — RETEST AFTER PYTHON PARITY** |
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
| 16 | Russian and English presentation | Progress deterministic; stage/state/outcome/circular/UDP/copy messages correct in both languages | `PENDING OWNER` | **BLOCKED BY #1** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence protected | `PENDING OWNER` | **BLOCKED BY #1** |
| 18 | Reboot after clean terminal completion | No temporary process or reserved IPFW residue returns; normal Zapret2 service/rule identity valid | `PENDING OWNER` | **BLOCKED BY #1** |

==================================================
CONFIRMED DEFECTS TO RECHECK AFTER MIGRATION
==================================================

- Stage 50 internal failure on `_17`.
- Immediate stale/new-job GUI error.
- Active `Strategy Lab returned no output.` message.
- Visible 0%-until-terminal progress behavior.
- shell-global target-type corruption.
- DNS answer-section/parser weakness.
- DNS failure-class flattening.
- terminal reload/state presentation.
- candidate fatal-log classification.

These defects remain open records. The Python migration may eliminate their old mechanism,
but closure requires focused replacement tests and any required owner live/UI evidence.

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

There is no successful complete Strategy Lab live scenario PASS claim yet. The shell-era
series does provide reusable live PASS evidence for Stage-40 DNS and Stage-90 restoration.

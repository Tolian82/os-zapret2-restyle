# Strategy Lab live OPNsense verification matrix

Overall status: **RELEASE-SELECTED LIVE GATE PASS ON `_27`; ADAPTIVE `_28` FOCUSED PASS; `_32` TIMEOUT-CONTAINMENT LIVE PASS; `_33` ADAPTIVE-VALIDATION CHANGE-SPECIFIC LIVE PASS; MODEL A COLD REFERENCE COLLECTED ON `_11`; MODEL B `_12` SOURCE EXPERIMENT PENDING LIVE; FULL REGRESSION MATRIX OPEN**

This matrix is the canonical live-appliance regression inventory for Strategy Lab. Source
tests, GitHub CI, and FreeBSD package builds cannot substitute for a live PASS when a row
is selected as mandatory for a release. Not every pending row is automatically a release
blocker; selection follows
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`.

Detailed historical logs remain under `docs/verification/evidence/`; this matrix keeps the
current inventory and the verified progression needed to select the next live work.

Only FreeBSD 15 amd64 packages are valid.

==================================================
TEST RECORD
==================================================

- Tester: repository owner
- Latest test date/time: `2026-08-10`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Required package ABI: `FreeBSD:15:amd64`
- Latest published testing candidate: `os-zapret2-restyle-0.4.0_11.pkg`
- Latest owner-tested candidate: `os-zapret2-restyle-0.4.0_11.pkg`
- Current source candidate: `os-zapret2-restyle-0.4.0_12.pkg`
- Current source purpose: experiment-only Model B warm-worker coexistence harness; owner-live experiment pending
- Latest owner-tested Model A job: `job.TtZeaH` (`rutracker.org`)
- Latest owner-tested Standard winner job: `job.TtZeaH` (`rutracker.org`)
- Latest owner-tested Standard no-winner job: `job.tU3wiL` (`telegram.org`)
- Latest owner-tested Extended no-winner job: `job.hsP8Ro` (`telegram.org`)
- WAN interface: `vtnet1`
- Generic UDP target/port: `PENDING OWNER`

Architecture / ABI baseline evidence:
`docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`.

Latest accepted live experiment evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Current source experiment contract:
`docs/patches/v0.4.0_12.md`.

Adaptive `_33` evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_9-adaptive-validation-pass.md`.

Previous timeout-containment evidence:

- `docs/verification/evidence/2026-08-10-v0.4.0_8-timeout-containment-pass.md`;
- `docs/verification/evidence/2026-08-10-v0.4.0_7-late-stage-pass.md`;
- `docs/verification/evidence/2026-08-09-v0.4.0_6-stage60-timeout.md`.

v0.4.0 release-selected evidence:
`docs/verification/evidence/2026-08-08-v0.3.3_27-scenario-01-pass.md`.

Adaptive `_28` focused evidence:
`docs/verification/evidence/2026-08-09-v0.4.0_2-stage60-family-reachability-pass.md`.

Third-audit source record:
`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

==================================================
VERIFIED PROGRESSION
==================================================

- `_27` widened the DNS/stage deadline envelope and owner retesting passed Stage 40,
  Stage 50, Stages 60/70, Stage 90 restoration and a truthful terminal result. This
  remains the selected mandatory v0.4.0 post-migration row.
- `_28` removed Stage-50 acceptance as a Stage-60 hard gate. Owner testing on
  `v0.4.0_2` produced `accepted=[]`, still attempted all 14 then-current Stage-60 catalog
  candidates and restored the initially running service without temporary IPFW residue.
- `v0.4.0_6` proved the Stage-50 parent containment correction but exposed the old fixed
  Stage-60 70-second parent limit after 12 of 16 candidates.
- `v0.4.0_7` closed that Stage-60 boundary: Standard and Extended both completed all
  16 expansion candidates and restored Zapret2 cleanly.
- `v0.4.0_8` closed the observed late-stage `_32` containment boundary: Stage 70/80/85/90
  reached their normal terminal states on Standard/Extended no-winner paths without a late
  timeout.
- `v0.4.0_9` closed the change-specific `_33` owner-live boundary. Standard and Extended
  `telegram.org` runs retained truthful `NO_CANDIDATE`; Standard `rutracker.org`
  `job.UPRDlc` stopped Stage 60 after 6 tested candidates when 3 working candidates were
  available, proved all three strict fresh-connection 3/3 in Stage 70, and executed one
  cold exact-profile finalist replay for each in Stage 85.
- The three `_9` finalist responses were successful HTTP 301 responses of 162 bytes. The
  16-KiB depth criterion was therefore correctly `inconclusive` rather than a false PASS or
  network failure. Separate 3/3 connectivity/stability evidence remained valid.
- `_9` post-run restoration evidence records initial RUNNING -> final RUNNING,
  `strategy_unchanged=true`, `temporary_runtime_clean=true`; the appliance snapshot showed
  only normal IPFW rule `19000` in the inspected Strategy Lab range.
- The `_9` live winner set was stable 3/3, so the fail-fast rejection branch remains
  automated-regression evidence rather than owner-live evidence. No broader claim is made.
- `v0.4.0_10` completed the first Model A appliance measurement on Standard
  `rutracker.org` job `job.Oeq7Rc`: 25 cold samples covered PASS/FAIL, repeated candidates,
  all required resource classes, `-d8`, 16 overlapping TLS/443 specs and verified clean
  restoration. The report remained `inconclusive` only because RSS was missing.
- `_10` timing evidence measured total candidate median 1556 ms / p90 3403 ms, readiness
  median 1046 ms / p90 1054 ms, probe median 208 ms / p90 2056 ms and stop+cleanup median
  78 ms / p90 85 ms. This is retained as the first cold timing baseline.
- `v0.4.0_11` corrected the snapshot-to-readiness `rss_kb` propagation gap. Standard
  `rutracker.org` job `job.TtZeaH` produced 25 cold samples with every Model A coverage
  check true and `conclusion=reference_collected`.
- `_11` measured total candidate median 1580 ms / p90 3411 ms, readiness median 1046 ms /
  p90 1052 ms, probe median 220 ms / p90 2045 ms and stop+cleanup median 81 ms / p90
  102 ms. Candidate RSS was numeric on all 25 samples with median 4332 KiB, p90 4348 KiB
  and max 4356 KiB.
- `_11` restoration records initial RUNNING -> final RUNNING,
  `strategy_unchanged=true`, `temporary_runtime_clean=true`. Model A is therefore accepted
  as the cold correctness/performance reference; no Model B/C production claim is made.
- `v0.4.0_12` is the current source-only Model B experiment harness. It starts three exact
  reference candidates on distinct warm ports `9990–9992`, routes probes sequentially via
  only one selected dedicated rule `19128–19130` at a time, measures RSS/latency and tests
  independent stop plus controlled worker death. It is not owner-live accepted yet.

==================================================
MODEL A COLD REFERENCE — PASS ON `v0.4.0_11`
==================================================

The first `v0.4.0_10` Model A measurement returned `conclusion=inconclusive` only because
`coverage.checks.rss_observed=false`. The FreeBSD candidate adapter was already measuring
RSS; `v0.4.0_11` preserved that measured field through Python readiness/candidate evidence.

Owner Standard `rutracker.org` job `job.TtZeaH` on `_11` now satisfies the complete
machine-checkable Model A contract:

- 25 cold Stage 50/60/70/85 candidate samples;
- known PASS and known FAIL candidates;
- repeated candidate execution;
- `blob-free`, `builtin`, and `external` resource classes;
- `-d8` and `-d10` output-range coverage;
- 16 unique overlapping TLS/443 candidate specs;
- numeric RSS on all 25 samples;
- verified restoration and temporary-runtime cleanup;
- `coverage.complete=true`, `coverage.missing=[]`;
- `conclusion=reference_collected`.

Accepted cold distributions:

- prepare median/p90/max: 140 / 160 / 165 ms;
- launch median/p90/max: 17 / 20 / 21 ms;
- readiness median/p90/max: 1046 / 1052 / 1138 ms;
- probe median/p90/max: 220 / 2045 / 2055 ms;
- stop+cleanup median/p90/max: 81 / 102 / 109 ms;
- total candidate median/p90/max: 1580 / 3411 / 3463 ms;
- RSS minimum/median/p90/max: 4316 / 4332 / 4348 / 4356 KiB.

`resource_init_ms` remains explicitly unavailable while inseparable from launch/readiness,
and teardown remains combined as `stop_cleanup_ms`. Those limitations remain recorded and
do not block the cold reference.

Exact accepted evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_11-model-a-reference-collected.md`.

Previous `_10` gap evidence:
`docs/verification/evidence/2026-08-10-v0.4.0_10-model-a-rss-gap.md`.

==================================================
MODEL B `_12` SOURCE EXPERIMENT — LIVE PENDING
==================================================

The `_12` harness is deliberately separate from normal Strategy Lab execution. It consumes
`job.TtZeaH` as the cold reference, requires an identical current `ResourceInventory`, and
selects a repeated blob-free PASS, a builtin FAIL and an external `-d8` FAIL from the exact
retained `CandidateSpec` evidence.

Machine-checkable source/live acceptance requires:

- three unique warm worker PIDs and divert ports;
- numeric per-worker and aggregate RSS;
- strict sequential probe execution (`parallel_probes=false`);
- only the selected worker's dedicated rule present for each probe;
- selected-rule packet-counter growth and pinned-endpoint evidence;
- PASS/FAIL equivalence with Model A for A/B/C/A;
- repeated A unchanged while the other two workers coexist;
- remaining workers healthy after one worker is stopped;
- remaining PASS worker unchanged after controlled death/cleanup of another worker;
- exact removal of rules `19128–19130` and ports/processes `9990–9992`;
- semantic restoration of initial service state, config hash, runtime-argument hash and
  normal-firewall hash.

Even `conclusion=accept` is an **experiment result only**. `_12` explicitly retains
`experiment_only=true`, `parallel_probes=false` and `production_approved=false`. Model B
cannot become production architecture until owner live evidence is reviewed and the
adaptive-search decision is updated separately.

==================================================
PYTHON MIGRATION OWNERSHIP
==================================================

Authoritative migration plan:
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Decision:
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`.

The automated Strategy Lab Python migration is complete. Python owns automated state,
stage orchestration, finite requests/probes, candidate runtime evidence, search/stability,
extended orchestration, final profile/replay/shortlist processing and active Diagnostics
status/reload presentation. Audited FreeBSD mutations and private circular state remain
narrow shell boundaries.

==================================================
REQUIRED EVIDENCE BUNDLE
==================================================

For each mandatory release-selected scenario preserve at minimum:

- exact installed candidate/version and supported ABI;
- terminal stage/result report for the exercised behavior;
- restoration/cleanup outcome when the scenario owns the Zapret2 lifecycle.

When needed to diagnose failure or prove safety, additionally retain status/state JSON,
process/runtime logs, lifecycle state, and IPFW/process residue snapshots.

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
| 7 | No working candidate | Outcome `NO_CANDIDATE`; shortlist empty; not reported as internal error | `_9` owner evidence includes Standard and Extended no-winner paths, but this dedicated row remains unselected/unexecuted as a formal matrix row | **PENDING REGRESSION** |
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
- **Stage 50 aggregate abort on `_25`.** Closed by `_27` reaching Stage 50 PASS and
  continuing through Stages 60/70.
- **Stage 50 parent-timeout boundary on `v0.4.0_5`.** Closed for the observed live target
  by `v0.4.0_6`.
- **Stage 60 fixed 70-second parent timeout on `v0.4.0_6`.** Closed by `v0.4.0_7` in
  Standard and Extended owner runs.
- **Late-stage containment after Stage 60.** Closed for observed normal no-winner Standard
  and Extended paths by `v0.4.0_8`.
- **Adaptive validation depth / winner path.** Change-specific live PASS on `v0.4.0_9`;
  fail-fast rejection remains source-regression-only because all live finalists passed 3/3.
- **Model A measurement.** The `_10` RSS-only gap is closed on `v0.4.0_11`; owner
  `job.TtZeaH` returned `reference_collected` with all 25 samples carrying numeric RSS and
  every coverage check true.
- **Model B coexistence.** `_12` source harness exists, but no owner-live result is recorded
  yet. Model B/C remain experimental and unapproved.
- **Immediate stale/new-job GUI error.** Retain as open until dedicated presentation
  regression coverage.
- **Active `Strategy Lab returned no output.` message.** Dedicated live recheck pending.
- **Terminal reload/state presentation.** Live recheck pending; issue #155 separately
  tracks idle-state presentation/localization without changing the internal `state: idle`
  contract.
- **PARTIAL summary wording.** Separate presentation correction remains pending.

==================================================
FAILURE HANDLING
==================================================

Any of the following blocks a release when it occurs on a mandatory release-selected row
or is a known critical condition in the candidate:

- candidate ABI/architecture is not exactly FreeBSD 15 amd64;
- `RESTORE_FAILED` or unverified restoration;
- unexpected change to saved Traffic Strategy;
- lingering Strategy Lab worker, temporary dvtws2 process, divert socket, PID file, or
  rules `19100–19131`;
- parent-result mutation by circular validation;
- Settings Apply succeeding while lifecycle ownership is active;
- active work not resumed after reload;
- completed/error result automatically resurrected as a newly opened Diagnostics state;
- reload deleting retained terminal evidence;
- missing evidence required for the release-selected behavior or an observed failure.

A failed live row requires source correction when a source defect is identified, complete
CI/FreeBSD 15 package verification, and repetition of the affected selected row. CI alone
never marks a live row PASS.

==================================================
RELEASE GATE
==================================================

Stable release preparation uses the risk-based selection policy in
`docs/decisions/DEC-2026-08-09-risk-based-live-release-gates.md`. It is not an
all-or-nothing release checklist. Every row selected as mandatory for a release must have
owner evidence and PASS; pending unselected rows remain regression backlog.

For `v0.4.0`, Scenario 1 remains the selected mandatory post-migration row and is PASS on
`v0.3.3_27`. Adaptive `_28` has its focused owner PASS on `v0.4.0_2`; `_32` timeout
containment is owner-live passed through `v0.4.0_8`; `_33` adaptive validation has its
change-specific owner-live PASS on `v0.4.0_9`. Rows 2–18 remain open regression coverage
without a formal row PASS. `v0.4.0_11` supplies the accepted Model A cold reference.
`v0.4.0_12` is only the current source candidate for the next Model B coexistence
experiment; it does not alter the stable v0.4.0 release-gate result and does not approve a
warm runtime model.

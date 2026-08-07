# Strategy Lab live OPNsense verification matrix

Overall status: **PENDING OWNER — SCENARIO 1 RETEST ON _12**

This matrix is the final live-appliance gate for the Strategy Lab hardening series. Source tests, GitHub CI, and FreeBSD package builds cannot substitute for evidence collected on the owner's OPNsense appliance.

Only FreeBSD 15 amd64 packages are valid. The revision 46 GitHub Actions artifact has ABI `FreeBSD:14:amd64` and must not be installed or used for this matrix.

## Test record

- Tester: repository owner
- Test date/time: `2026-08-07` (latest completed scenario 1 attempt; `_12` retest pending)
- OPNsense version: `26.7.1_1`; later diagnostic kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Architecture / ABI evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`
- Required package ABI: `FreeBSD:15:amd64`
- Current corrective candidate: `os-zapret2-restyle-0.3.3_12.pkg`
- Patch 7 source/CI qualification: exact PR head `dd2a484a4aa3711834b722aae0cc025d3fd4758e`; title check `31157848071` PASS; CI run `31157848056` PASS; FreeBSD 15 artifact `8985927074`; squash-merged main `256ffa09452dabfb001665b729c1f4c3d3462688`.
- Final `_12` roll-up: package revision only; no runtime behavior change. The `_12` artifact must be produced by the successful final-roll-up GitHub Actions build and is the installation candidate for Scenario 1.
- Historical `_6` CI package: `os-zapret2-restyle-0.3.3_6.pkg` (not owner-tested; superseded by `_12`)
- Latest tested package: `os-zapret2-restyle-0.3.3_5.pkg`
- WAN interface: `vtnet1`
- LAN test client: `PENDING OWNER`
- Blocked-domain target: `rutracker.org` for the latest scenario 1 attempt
- Generic UDP target/port: `PENDING OWNER`

Installation and service baseline for `0.3.3_1`: **PASS**. The package installed successfully with architecture `FreeBSD:15:amd64`, annotation `FreeBSD_version: 1500068`, and the `zapret` service running after installation. This baseline does not mark any scenario row as passed.

The first scenario 1 attempt on `0.3.3_1` failed before runtime mutation because FreeBSD daemon processes were omitted from PID identity queries. Evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md`.

The diagnostic repeat on `0.3.3_2` proved that the installed process wrapper and shared matcher detected both daemon processes, but `zapret_service.sh strategy-lab-evidence` still reported both as absent because the complete service entry point overwrote the wrapper binding with direct `/bin/ps`. Evidence: `docs/verification/evidence/2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md`.

The live check on `0.3.3_4` proved that the wrapper binding correction alone was insufficient. Semantic evidence still returned both processes as absent because its direct `read ... || return 1` rejected valid FreeBSD `daemon(8)` PID files that ended at EOF without a trailing newline. Evidence: `docs/verification/evidence/2026-08-06-v0.3.3_4-scenario-01-pidfile-eof.md`.

The `0.3.3_5` live attempt confirmed that the PID-file correction works: before Strategy Lab execution, semantic evidence correctly reported `RUNNING` with both child and supervisor present. The run then failed later at stage 50 with `Temporary candidate runtime failed internally.` Stage 90 failed with `RESTORE_FAILED`, and the final normal service state was `INCOMPLETE` with both child and supervisor absent. Evidence: `docs/verification/evidence/2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md`.

The `_6` source corrective sequence for those later failures completed and remains historical evidence:

- baseline repository reconciliation: `471ad322b805c14423c4cee553e6cb111a569b29`;
- stage-50 candidate-runtime ownership correction: `808d77bcdb4f9e5fb63f94985d01144e7f2216a4`;
- stage-90 bounded restoration-path correction: `4fca1fccbdd92237c76d84e11f864090fc4d1a9d`.

The exact final restoration-path PR head passed full CI run `31144038425` and produced FreeBSD 15 artifact `8980876980`, package `os-zapret2-restyle-0.3.3_6.pkg`, with manifest `0.3.3_6 / FreeBSD:15:amd64 / freebsd:15:x86:64 / FreeBSD_version 1500068`. Post-merge `main` CI run `31144323095` also passed.

These source/CI results do not convert the failed `_5` live attempt into PASS. `_6` was never owner-tested. A third source audit on 2026-08-07 then identified `SL3-001` through `SL3-007` and superseded `_6` before live retest.

The approved third-audit corrective sequence is source/CI complete. Patches 2–6 implemented every finding, Patch 7 bound all corrected paths into the mandatory integration/corrective matrix, and Patch 8 closed the source/CI handoff. Revision `_12` is a final package roll-up from the complete post-Patch-8 repository state; it adds no new runtime behavior and therefore inherits the Patch 7 integrated runtime qualification while requiring its own successful FreeBSD 15 package build/manifest inspection before installation. This evidence authorizes resuming the owner-assisted matrix at Scenario 1; it does **not** authorize any live PASS claim.

Authoritative third-audit record:

`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`

## Required evidence bundle

For each applicable scenario preserve:

- screenshot of the Diagnostics result and progress display;
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

Before installation of the designated candidate, preserve its `+MANIFEST` and confirm:

```text
abi: FreeBSD:15:amd64
arch: freebsd:15:x86:64
version: 0.3.3_12
```

Recommended residue evidence after every terminal scenario:

```text
pgrep -af 'strategy_lab|dvtws2|zapret.*supervisor'
ipfw show | grep -E '^(1910[0-9]|191[12][0-9]|1913[01]) '
configctl zapret status
```

## Scenario matrix

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; stage 90 restores RUNNING; no temporary residue | Failed attempts: `2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md`, `2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md`, `2026-08-06-v0.3.3_4-scenario-01-pidfile-eof.md`, `2026-08-07-v0.3.3_5-scenario-01-candidate-runtime-restore-failure.md`; next evidence must be collected on `_12` | **PENDING OWNER — RETEST REQUIRED** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Test completes while final service remains STOPPED; restoration evidence is verified | `PENDING OWNER` | **BLOCKED BY #1** |
| 3 | Extended TLS 1.2 and HTTP | Available protocol successes appear as complete replay-verified profiles; unavailable protocols are explicitly skipped | `PENDING OWNER` | **BLOCKED BY #1** |
| 4 | Extended QUIC | QUIC result is endpoint-bound and replay-verified when network capability exists; otherwise explicit skip reason | `PENDING OWNER` | **BLOCKED BY #1** |
| 5 | Generic UDP port and payload | Port/payload pair is accepted only in Extended mode; result identifies selected IP and complete profile; payload file is removed after terminal cleanup | `PENDING OWNER` | **BLOCKED BY #1** |
| 6 | Target already accessible | Outcome is `TARGET_ACCESSIBLE`; strategy search is skipped; service state remains exact | `PENDING OWNER` | **BLOCKED BY #1** |
| 7 | No working candidate | Outcome is `NO_CANDIDATE`; shortlist is empty; this is not reported as an internal error | `PENDING OWNER` | **BLOCKED BY #1** |
| 8 | User cancellation after service stop | State becomes cancel-requested, unfinished stages are skipped, stages 90 and 99 run, original service state is restored | `PENDING OWNER` | **BLOCKED BY #1** |
| 9 | Hard whole-worker timeout | Outcome is `TIMEOUT`; available results persist; stage 90 restoration is verified; no worker/runtime residue | `PENDING OWNER` | **BLOCKED BY #1** |
| 10 | Controlled internal failure | Outcome is `ERROR`; failure stage is truthful; original service state is restored and verified | `PENDING OWNER` | **BLOCKED BY #1** |
| 11 | Circular start, browser validation, and stop | Parent job files remain unchanged; private session becomes active; client traffic can be tested; stop ends in `completed`; no global circular aliases exist | `PENDING OWNER` | **BLOCKED BY #1** |
| 12 | Circular stale-worker recovery | After controlled worker termination, owner mismatch is detected; temporary runtime/rules are cleaned; semantic service restoration is verified before retry | `PENDING OWNER` | **BLOCKED BY #1** |
| 13 | Settings Apply during automated Strategy Lab | Apply is rejected before model mutation with lifecycle-owner information; saved configuration remains unchanged | `PENDING OWNER` | **BLOCKED BY #1** |
| 14 | Settings Apply during circular or `restore_failed` state | Apply is rejected; unsafe retry remains blocked until restoration is proven | `PENDING OWNER` | **BLOCKED BY #1** |
| 15 | Diagnostics page reload | Reload during active work resumes that job; reload after completed/error work opens the initial idle view without deleting retained evidence or starting a new job | `PENDING OWNER` | **BLOCKED BY #1** |
| 16 | Russian and English presentation | Progress reaches deterministic percentages; stage/state/outcome/circular/UDP/copy messages are correct in both languages | `PENDING OWNER` | **BLOCKED BY #1** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts are removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence remains | `PENDING OWNER` | **BLOCKED BY #1** |
| 18 | Reboot after clean terminal completion | No Strategy Lab temporary process or reserved IPFW residue returns; normal Zapret2 service state and rule identity remain valid | `PENDING OWNER` | **BLOCKED BY #1** |

## Failure handling

Any of the following keeps the live gate failed or pending:

- candidate package ABI or architecture is not exactly FreeBSD 15 amd64;
- `RESTORE_FAILED` or unverified restoration;
- unexpected change to the saved Traffic Strategy;
- lingering Strategy Lab worker, temporary dvtws2 process, divert socket, PID file, or rules `19100–19131`;
- parent-result mutation by circular validation;
- Settings Apply succeeding while lifecycle ownership is active;
- active work is not resumed after reload;
- a completed/error result is automatically resurrected as the state of a newly opened Diagnostics page;
- a reload deletes retained terminal evidence;
- missing required evidence.

A failed live row requires same-scope source correction when a source defect is identified, complete CI/FreeBSD 15 package verification, and repetition of the affected live row plus dependent rows. Once source correction is complete, the row remains pending owner until new appliance evidence is collected; CI alone never marks it PASS.

## Release gate

Third-audit source/CI closure is complete. Stable release preparation and pkg-repository promotion remain blocked until every required live row is marked `PASS` by the owner and linked evidence is recorded. The matrix contains no successful Strategy Lab live scenario PASS claim yet.
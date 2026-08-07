# Strategy Lab live OPNsense verification matrix

Overall status: **FAILED ON _16 — STAGE-50 CORRECTION `_17` IN PROGRESS**

This matrix is the final live-appliance gate for the Strategy Lab hardening series. Source
tests, GitHub CI, and FreeBSD package builds cannot substitute for evidence collected on
the owner's OPNsense appliance.

Only FreeBSD 15 amd64 packages are valid. The historical revision 46 GitHub Actions
artifact has ABI `FreeBSD:14:amd64` and must not be installed or used for this matrix.

## Test record

- Tester: repository owner
- Test date/time: `2026-08-07`
- OPNsense version: `26.7.1_1`; kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Architecture / ABI evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`
- Required package ABI: `FreeBSD:15:amd64`
- Latest owner-tested candidate: `os-zapret2-restyle-0.3.3_16.pkg`
- Current corrective source candidate: `os-zapret2-restyle-0.3.3_17.pkg`
- Patch 7 source/CI qualification: exact PR head `dd2a484a4aa3711834b722aae0cc025d3fd4758e`; title check `31157848071` PASS; CI run `31157848056` PASS; FreeBSD 15 artifact `8985927074`; squash-merged main `256ffa09452dabfb001665b729c1f4c3d3462688`.
- Historical `_6` final restoration-path CI produced artifact `8980876980`; Post-merge `main` CI run `31144323095` also passed.
- Corrective `_13`: PR #125, main `9a9879c6f88d77ab64c06647dd8d1e2437fc5f25`; owner-tested stage 90 PASS.
- Corrective `_14`: PR #126, main `36e34414c869ff6e1062e37b91772aa8cdc05455`; owner-tested stage 40 and stage 90 PASS.
- Corrective `_15`: PR #127, main `6807bd7068f960832bf0ee42005c58cdf9d355ff`; timeout-variable ownership corrected.
- Corrective `_16`: PR #128, main `88d33360be7b9fda8ddd8a8e903296cd775aae41`; published testing prerelease `v0.3.3_16`; resident FreeBSD candidate supervisor detached so readiness can execute.
- WAN interface: `vtnet1`
- LAN test client: `PENDING OWNER`
- Blocked-domain target: `rutracker.org`
- Generic UDP target/port: `PENDING OWNER`

Installation and service baseline for `0.3.3_1` is historical **PASS** evidence only. It
does not mark any scenario row as passed.

## Scenario 1 failure history and live sub-gates

The early failed attempts and their exact evidence remain preserved under
`docs/verification/evidence/`. The third-audit source record is
`docs/audit/AUDIT-2026-08-07-STRATEGY-LAB-THIRD-AUDIT.md`.

`_12` reopened the live gate: stage 50 failed and FreeBSD non-foreground `timeout` reaped
healthy restored daemon descendants at stage 90. `_13` corrected the stage-90 timeout and
owner testing proved restoration PASS.

`_13` then exposed the stage-40 DNS wrapper defect: direct `drill` succeeded while
non-foreground `/usr/bin/timeout 2 /usr/bin/drill rutracker.org A` returned 124. `_14`
used FreeBSD foreground timeout and owner testing proved stage 40 PASS with `DNS: OK`.

`_14` then exposed the stage-50 unset `STRATEGY_LAB_TIMEOUT_BIN` defect before any family
completed. `_15` corrected ownership of that timeout default.

Owner-assisted `_15`, job `job.6eZM24`, still failed stage 50. Source review proved that
FreeBSD `daemon(8)` remains resident with the candidate child and synchronous startup
prevented readiness from running. `_16` detached that monitor.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_15-scenario-01-stage50-freebsd-daemon-supervisor.md`.

Owner-assisted `_16`, job `job.VmWk32`, provides the current authoritative boundary.
Stages 00–40 passed; stage 50 failed; stage 90 again restored the normal RUNNING Zapret2
service completely. Unlike previous stage-50 attempts, `_16` created the full temporary
runtime and dvtws2 reached real execution:

```text
Loading hostlist /var/run/zapret2-restyle/strategy-lab/jobs/job.VmWk32/candidate-runtime/hostlist.txt
Loaded 1 hosts from /var/run/zapret2-restyle/strategy-lab/jobs/job.VmWk32/candidate-runtime/hostlist.txt
creating divert4 socket
binding divert4 socket
Running as UID=65534 GID=65534
file_open_test: Permission denied
cannot access hostlist file '/var/run/zapret2-restyle/strategy-lab/jobs/job.VmWk32/candidate-runtime/hostlist.txt'
```

Candidate DNS was successful and selected `104.21.32.39`; the runtime prepared rule 19100,
divert port 9989, and the intended smoke strategy. The hostlist itself is mode 0644. The
blocking boundary is parent-directory traversal after `--user=nobody`: the random job
directory is created privately by `mktemp -d`, so dvtws2 cannot reopen the nested hostlist
after dropping privileges.

The `_17` corrective scope keeps the job directory private at rest, grants only
search-only traversal while a hostlist-backed candidate is alive, keeps the candidate
runtime traversable, and restores mode 0700 during candidate cleanup. Its regression
starts from a private job directory, models post-drop non-owner/non-group access, and
requires privacy restoration after teardown.

The same `_16` evidence reconfirmed the separately tracked baseline `target_type:"A"`,
stale immediate GUI `ERROR`, stuck visible 0% progress, terminal reload, DNS parsing, and
DNS failure-diagnostic defects. It also exposed a new deferred diagnostic defect:
`readiness.json` recorded `log_clean:true` even though the dvtws2 log contained
`file_open_test: Permission denied` and `cannot access hostlist file`.

Evidence:
`docs/verification/evidence/2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md`.

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
version: 0.3.3_17
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
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; stage 90 restores RUNNING; no temporary residue | Failed attempts include `_1`, `_2`, `_4`, `_5`, `_12`, `_13`, `_14`, `_15`, and `2026-08-07-v0.3.3_16-scenario-01-stage50-hostlist-access.md`; `_16` proves real dvtws2 startup/bind/drop but fails post-drop hostlist access; `_17` must survive that access and enter family execution | **FAILED ON `_16` — `_17` STAGE-50 RETEST REQUIRED** |
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

A failed live row requires same-scope source correction when a source defect is identified,
complete CI/FreeBSD 15 package verification, and repetition of the affected live row plus
dependent rows. CI alone never marks a live row PASS.

## Release gate

Third-audit source/CI closure remains historical source evidence only. Stable release
preparation and pkg-repository promotion remain blocked until every required live row is
marked `PASS` by the owner and linked evidence is recorded. The matrix contains no
successful complete Strategy Lab live scenario PASS claim yet; `_16` does provide live
PASS evidence for stage-40 DNS and stage-90 restoration, and proves temporary dvtws2 now
reaches startup, divert bind, and privilege drop before the hostlist traversal failure.

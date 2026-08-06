# Strategy Lab live OPNsense verification matrix

Overall status: **PENDING OWNER**

This matrix is the final live-appliance gate for the Strategy Lab hardening series. Source tests, GitHub CI, and FreeBSD package builds cannot substitute for evidence collected on the owner's OPNsense appliance.

Only FreeBSD 15 amd64 packages are valid. The revision 46 GitHub Actions artifact has ABI `FreeBSD:14:amd64` and must not be installed or used for this matrix.

## Test record

- Tester: repository owner
- Test date/time: `2026-08-06 15:14:15 MSK` (installation baseline)
- OPNsense version: `26.7.1_1`; later diagnostic kernel evidence: `15.1-RELEASE-p1 stable/26.7`
- Architecture / ABI evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-installation.md`
- Required package ABI: `FreeBSD:15:amd64`
- Candidate package: `os-zapret2-restyle-0.3.3_4.pkg`
- WAN interface: `vtnet1`
- LAN test client: `PENDING OWNER`
- Blocked-domain target: `PENDING OWNER`
- Generic UDP target/port: `PENDING OWNER`

Installation and service baseline for `0.3.3_1`: **PASS**. The package installed successfully with architecture `FreeBSD:15:amd64`, annotation `FreeBSD_version: 1500068`, and the `zapret` service running after installation. This baseline does not mark any scenario row as passed.

The first scenario 1 attempt on `0.3.3_1` failed before runtime mutation because FreeBSD daemon processes were omitted from PID identity queries. Evidence: `docs/verification/evidence/2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md`.

The diagnostic repeat on `0.3.3_2` proved that the installed process wrapper and shared matcher detected both daemon processes, but `zapret_service.sh strategy-lab-evidence` still reported both as absent because the complete service entry point overwrote the wrapper binding with direct `/bin/ps`. Evidence: `docs/verification/evidence/2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md`. Scenario 1 remains pending and must be repeated on `0.3.3_4`.

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

Before installation, preserve the candidate package identity from its `+MANIFEST` and confirm:

```text
abi: FreeBSD:15:amd64
arch: freebsd:15:x86:64
version: 0.3.3_4
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
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; stage 90 restores RUNNING; no temporary residue | Failed attempts: `2026-08-06-v0.3.3_1-scenario-01-stage10-failure.md`, `2026-08-06-v0.3.3_2-scenario-01-semantic-inspector-binding.md`; corrected `_4` retest required | **PENDING OWNER** |
| 2 | Standard blocked domain, initial Zapret2 STOPPED | Test completes while final service remains STOPPED; restoration evidence is verified | `PENDING OWNER` | **PENDING OWNER** |
| 3 | Extended TLS 1.2 and HTTP | Available protocol successes appear as complete replay-verified profiles; unavailable protocols are explicitly skipped | `PENDING OWNER` | **PENDING OWNER** |
| 4 | Extended QUIC | QUIC result is endpoint-bound and replay-verified when network capability exists; otherwise explicit skip reason | `PENDING OWNER` | **PENDING OWNER** |
| 5 | Generic UDP port and payload | Port/payload pair is accepted only in Extended mode; result identifies selected IP and complete profile; payload file is removed after terminal cleanup | `PENDING OWNER` | **PENDING OWNER** |
| 6 | Target already accessible | Outcome is `TARGET_ACCESSIBLE`; strategy search is skipped; service state remains exact | `PENDING OWNER` | **PENDING OWNER** |
| 7 | No working candidate | Outcome is `NO_CANDIDATE`; shortlist is empty; this is not reported as an internal error | `PENDING OWNER` | **PENDING OWNER** |
| 8 | User cancellation after service stop | State becomes cancel-requested, unfinished stages are skipped, stages 90 and 99 run, original service state is restored | `PENDING OWNER` | **PENDING OWNER** |
| 9 | Hard whole-worker timeout | Outcome is `TIMEOUT`; available results persist; stage 90 restoration is verified; no worker/runtime residue | `PENDING OWNER` | **PENDING OWNER** |
| 10 | Controlled internal failure | Outcome is `ERROR`; failure stage is truthful; original service state is restored and verified | `PENDING OWNER` | **PENDING OWNER** |
| 11 | Circular start, browser validation, and stop | Parent job files remain unchanged; private session becomes active; client traffic can be tested; stop ends in `completed`; no global circular aliases exist | `PENDING OWNER` | **PENDING OWNER** |
| 12 | Circular stale-worker recovery | After controlled worker termination, owner mismatch is detected; temporary runtime/rules are cleaned; semantic service restoration is verified before retry | `PENDING OWNER` | **PENDING OWNER** |
| 13 | Settings Apply during automated Strategy Lab | Apply is rejected before model mutation with lifecycle-owner information; saved configuration remains unchanged | `PENDING OWNER` | **PENDING OWNER** |
| 14 | Settings Apply during circular or `restore_failed` state | Apply is rejected; unsafe retry remains blocked until restoration is proven | `PENDING OWNER` | **PENDING OWNER** |
| 15 | Diagnostics page reload | Reload during active work resumes that job; reload after completed/error work opens the initial idle view without deleting retained evidence or starting a new job | `PENDING OWNER` | **PENDING OWNER** |
| 16 | Russian and English presentation | Progress reaches deterministic percentages; stage/state/outcome/circular/UDP/copy messages are correct in both languages | `PENDING OWNER` | **PENDING OWNER** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts are removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence remains | `PENDING OWNER` | **PENDING OWNER** |
| 18 | Reboot after clean terminal completion | No Strategy Lab temporary process or reserved IPFW residue returns; normal Zapret2 service state and rule identity remain valid | `PENDING OWNER` | **PENDING OWNER** |

## Failure handling

Any of the following keeps the live gate failed:

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

A failed row requires one same-scope corrective patch, complete CI/FreeBSD 15 package verification, and repetition of the affected live row plus any dependent rows.

## Release gate

Stable release preparation and pkg-repository promotion remain blocked until every required row is marked `PASS` by the owner and linked evidence is recorded. The current candidate is a testing surface only. The current matrix contains no live scenario PASS claims.

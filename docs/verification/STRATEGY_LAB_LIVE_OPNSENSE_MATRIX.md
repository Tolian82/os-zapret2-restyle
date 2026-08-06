# Strategy Lab live OPNsense verification matrix

Overall status: **PENDING OWNER**

This matrix is the final live-appliance gate for the Strategy Lab hardening series. Source tests, GitHub CI, and FreeBSD package builds cannot substitute for evidence collected on the owner's OPNsense appliance.

## Test record

- Tester: `PENDING OWNER`
- Test date/time: `PENDING OWNER`
- OPNsense version: `PENDING OWNER`
- Architecture / ABI: `PENDING OWNER`
- Candidate package: `os-zapret2-restyle-0.3.2_46.pkg`
- WAN interface: `PENDING OWNER`
- LAN test client: `PENDING OWNER`
- Blocked-domain target: `PENDING OWNER`
- Generic UDP target/port: `PENDING OWNER`

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

Recommended residue evidence after every terminal scenario:

```text
pgrep -af 'strategy_lab|dvtws2|zapret.*supervisor'
ipfw show | grep -E '^(1910[0-9]|191[12][0-9]|1913[01]) '
configctl zapret status
```

## Scenario matrix

| # | Scenario | Required expected result | Evidence location | Result |
|---|---|---|---|---|
| 1 | Standard blocked domain, initial Zapret2 RUNNING | Terminal result is truthful; at least one verified profile or `NO_CANDIDATE`; stage 90 restores RUNNING; no temporary residue | `PENDING OWNER` | **PENDING OWNER** |
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
| 15 | Diagnostics page reload after terminal result | Latest completed/error result is restored without starting a new job; structured result and copy controls remain available | `PENDING OWNER` | **PENDING OWNER** |
| 16 | Russian and English presentation | Progress reaches deterministic percentages; stage/state/outcome/circular/UDP/copy messages are correct in both languages | `PENDING OWNER` | **PENDING OWNER** |
| 17 | Retention with reduced test limits | Only excess verified terminal artifacts are removed; active/latest/nonterminal/unverified/`RESTORE_FAILED` evidence remains | `PENDING OWNER` | **PENDING OWNER** |
| 18 | Reboot after clean terminal completion | No Strategy Lab temporary process or reserved IPFW residue returns; normal Zapret2 service state and rule identity remain valid | `PENDING OWNER` | **PENDING OWNER** |

## Failure handling

Any of the following keeps the live gate failed:

- `RESTORE_FAILED` or unverified restoration;
- unexpected change to the saved Traffic Strategy;
- lingering Strategy Lab worker, temporary dvtws2 process, divert socket, PID file, or rules `19100–19131`;
- parent-result mutation by circular validation;
- Settings Apply succeeding while lifecycle ownership is active;
- a terminal result disappearing after page reload;
- missing required evidence.

A failed row requires one same-scope corrective patch, complete CI/package verification, and repetition of the affected live row plus any dependent rows.

## Release gate

Release preparation is blocked until every required row is marked `PASS` by the owner and linked evidence is recorded. The current matrix contains no live PASS claims. Tagging, GitHub Release publication, release assets, and pkg-repository publication are outside revision 46 and require separate explicit owner authorization after this gate passes.

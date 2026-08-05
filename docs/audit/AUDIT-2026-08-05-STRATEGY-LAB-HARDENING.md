# Strategy Lab hardening audit — 2026-08-05

Audited source: `main` at `a95fcc33b2bdd97830fe5cd44090ae189a141dfa` (`0.3.2_24`).

## Confirmed strengths

- asynchronous start/status/cancel/result contract;
- explicit stages 00–99;
- persistent cancellation and terminal result storage;
- semantic lifecycle restoration evidence;
- domain normalization and API/configd integration harness;
- successful current CI and package build.

## Accepted remaining findings

1. Cooperative budgets do not impose a hard whole-worker deadline.
2. Candidate cleanup can report success after deleting its PID file without proving process termination or divert-port release.
3. Residue from a previous abnormal run can contaminate the baseline.
4. Concurrent status writers can lose updates and terminal state.
5. Dead workers leave nonterminal jobs and ambiguous active state.
6. Shortlist items expose a catalog strategy fragment rather than the complete tested Traffic Strategy profile.
7. Probe success does not prove that the temporary IPFW rule and candidate runtime handled the successful connection.
8. DNS resolution, firewall installation, and curl may use different addresses; redirects are not bounded by an explicit endpoint contract.
9. Candidate readiness checks only process existence.
10. Automated rules currently use `from any`, so normal LAN client traffic can be intercepted during automatic tests.
11. Circular validation mutates evidence belonging to the completed parent job and has no independent launch serialization.
12. Settings can be saved while Strategy Lab owns lifecycle state.
13. Page reload does not render a persisted terminal result.
14. Extended TLS 1.2/HTTP/QUIC/UDP successes are not unified in the final shortlist; UDP input is not exposed through the supported GUI/API contract.
15. Progress, localization, retention, and CI coverage are incomplete.

## Hardening progress

- Findings 2, 3, 6, 7, 8, 9, 10 and the runtime-safety portions of findings 1, 4, and 5 are implemented and verified by Patches `_26`–`_34`.
- Patch `_35` completes the shortlist half of finding 14.
- Patch `_36` completes the UDP-input half of finding 14; finding 14 is source-complete.
- Patch `_37` closes the evidence-mutation half of finding 11: circular validation snapshots the completed parent and stores all mutable state, runtime, and restoration evidence in an independent private session.
- The launch-serialization and stale-owner half of finding 11 remains assigned to Patch `_38`.
- Findings 12–13 and the remaining portions of finding 15 remain open.

## Explicit exclusion

No corrective work is required for occupancy detection, ownership validation, snapshotting,
or restoration of IPFW rules `19100–19131`. The range is reserved exclusively for Strategy
Lab and remains destructively cleaned.

## Release gate

The hardening series must complete focused source tests and an owner-assisted live OPNsense
matrix before release preparation.

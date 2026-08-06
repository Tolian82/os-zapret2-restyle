# Strategy Lab hardening audit — 2026-08-05

Audited source: `main` at `a95fcc33b2bdd97830fe5cd44090ae189a141dfa` (`0.3.2_24`).

## Accepted findings

1. Cooperative budgets lacked a hard whole-worker deadline.
2. Candidate cleanup lacked proof of process/socket termination.
3. Previous residue could contaminate baseline.
4. Concurrent status writers could lose terminal state.
5. Dead workers left ambiguous active state.
6. Shortlist exposed incomplete strategy fragments.
7. Probe success lacked interception evidence.
8. DNS/firewall/request endpoints could diverge.
9. Candidate readiness checked process existence only.
10. Automated rules could intercept LAN traffic.
11. Circular validation mutated parent evidence and lacked independent ownership.
12. Settings could save while Strategy Lab owned lifecycle state.
13. Page reload did not restore a persisted terminal result or structured output.
14. Extended protocols were not unified and UDP input was not supported.
15. Progress, localization, retention, and CI coverage were incomplete.

## Hardening progress

- Patches `_26`–`_34` address findings 2, 3, 6–10 and runtime-safety portions of 1, 4, and 5.
- Patches `_35`–`_36` complete finding 14.
- Patches `_37`–`_38` complete finding 11.
- Patch `_39` completes finding 12.
- Patches `_40`–`_41` complete finding 13.
- Patch `_42` completes the progress and localization portions of finding 15.
- Patch `_43` removes obsolete circular aliases and the duplicate state-level skip hook.
- Patch `_44` completes the retention portion of finding 15 with lock-protected bounded cleanup that preserves active/latest, nonterminal, malformed, unverified-restoration, and `RESTORE_FAILED` evidence.
- The final corrective CI matrix remains assigned to `_45`.
- Final source closure and owner-assisted live verification are recorded in `_46`.

## Explicit exclusion

IPFW rules `19100–19131` remain an exclusive Strategy Lab reservation and are destructively cleaned without external occupancy restoration.

## Release gate

The hardening series requires complete source tests and an owner-assisted live OPNsense matrix before release preparation.

# DEC-2026-08-05 — Strategy Lab corrective series

## Status

Approved by the project owner on 2026-08-05.

## Context

Source audit of the activated Strategy Lab in package candidate `0.3.2_15` found that
the repository is structurally complete and buildable, but several runtime contracts
are not implemented consistently:

- cancellation is not persisted atomically and may be ignored during active long
  probes;
- the normal worker path always ends as `PARTIAL`;
- final messages depend on module load order and can be factually wrong;
- stage 80 can consume three independent 120-second budgets;
- stage 85 can run before stage 80;
- restoration failure can be stored as normal completion;
- lifecycle restoration evidence is weaker than the documented exact-restoration
  promise;
- circular controls can appear before restoration completes;
- tests do not exercise the complete state machine.

No parallel branch contains a safe ready-to-merge correction. Existing branches are
historical implementation or transport branches whose useful lifecycle and testing
patterns are already present in `main`.

## Decision

Implement the corrective work as eleven strictly serial logical patches from current
`main`:

1. corrective contract and documentation;
2. atomic cancel-state persistence;
3. cancellation-aware active runners;
4. explicit monotonic stage machine;
5. terminal state/outcome/message correction;
6. shared overall time budget;
7. stronger semantic restoration verification;
8. GUI and backend circular eligibility;
9. explicit domain/IP target contract;
10. end-to-end regression harness;
11. repository hygiene.

The authoritative detailed behavior is recorded in
`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`.

## Delivery rule

Each patch is one logical change and must complete this gate before the next begins:

- one task branch from current `main`;
- documentation synchronized in the same logical patch;
- focused automated tests;
- pull-request CI and FreeBSD package build;
- one squash merge;
- successful post-merge `main` workflow;
- verified deletion of the exact task branch.

GitHub App operations may create multiple technical commits while editing repository
files remotely. The pull request must still be squash merged into exactly one logical
`main` commit.

## Verification policy

Owner-assisted live OPNsense verification remains deferred until all corrective code
patches are published and processed. The final live matrix will cover standard,
extended, cancellation during active stages, timeout, restoration from RUNNING and
STOPPED, circular start/stop, cleanup, and saved-strategy immutability.

## Consequences

- Package candidate `0.3.2_15` is not promoted to a release while the corrective series
  is active.
- Existing source is treated as implemented but not contract-complete.
- Direct merge or cherry-pick from old parallel branches is prohibited for this work.
- The corrected state machine and persisted result become the source of truth for GUI
  behavior and integration tests.

# Strategy Lab corrective CI matrix

## Authority

`scripts/test-strategy-lab-corrective-matrix.sh` is the single CI entry point for Strategy Lab source verification. The GitHub workflow invokes it exactly once.

The matrix first runs the focused domain-connectivity contract, then discovers every `scripts/test-strategy-lab-*.sh` file in stable lexical order and runs each exactly once, excluding only the matrix itself. New focused Strategy Lab tests therefore become mandatory automatically when added to the repository.

## Nonrecursive contract

`test-domain-diagnostics-contract.sh` validates only domain normalization, timeout/reset/failure classification, and the Diagnostics API empty-output behavior. It must not invoke Strategy Lab tests.

`test-strategy-lab-corrective-matrix-contract.sh` proves that:

- CI invokes the matrix exactly once;
- CI does not invoke the old domain wrapper as an orchestration path;
- the domain test contains no Strategy Lab recursion;
- the matrix excludes itself and discovers all other focused Strategy Lab tests;
- both matrix files remain required repository artifacts.

## Clean fixture requirement

Focused tests must provide every dependency they exercise. Warning-only missing mock functions are treated as fixture defects even when the shell exit status remains zero. Terminal-result and stale-worker fixtures therefore define explicit no-op UDP cleanup mocks instead of emitting `strategy_lab_udp_input_cleanup: not found` warnings.

## Scope

The matrix covers lifecycle state, cancellation, deadlines, stale recovery, serialized state, traffic isolation, runtime readiness, interception evidence, exact profile replay, multi-protocol shortlist, UDP input, circular isolation/ownership, Settings guard, persisted reload, structured results, progress/localization, obsolete-surface removal, retention, Diagnostics activation, and full end-to-end behavior.

Project-wide profile, package lifecycle, release, GitHub governance, repository hygiene, PHP/XML/shell lint, and FreeBSD package build remain separate CI steps because they are not Strategy Lab focused contracts.

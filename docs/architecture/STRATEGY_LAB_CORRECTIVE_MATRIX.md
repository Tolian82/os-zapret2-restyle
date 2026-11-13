# Strategy Lab corrective CI matrix

## Authority

`scripts/test-strategy-lab-corrective-matrix.sh` is the retained full Strategy Lab source matrix entrypoint. When that matrix is selected, invoke it once. Current automatic routing and affected-path selection are governed by GH-069–GH-072; a documentation or unrelated GUI change does not automatically select the full matrix.

The matrix first runs the focused domain-connectivity contract, then discovers every `scripts/test-strategy-lab-*.sh` file in stable lexical order. Every discovered file is syntax-checked. Focused contracts run directly once except four cleanup-sensitive contracts deliberately delegated to the end-to-end test: active cancellation, candidate runtime, semantic restoration, and time budget. E2E invokes each delegated contract exactly once.

The full matrix discovers new focused Strategy Lab tests unless they are deliberately delegated with matching matrix-contract evidence. This describes matrix composition, not an obligation to run the full historical matrix on every PR.

## Nonrecursive contract

`test-domain-diagnostics-contract.sh` validates only domain normalization, timeout/reset/failure classification, and the Diagnostics API empty-output behavior. It must not invoke Strategy Lab tests.

`test-strategy-lab-corrective-matrix-contract.sh` proves that:

- CI invokes the matrix exactly once;
- CI does not invoke the old domain wrapper as an orchestration path;
- the domain test contains no Strategy Lab recursion;
- the matrix excludes itself and discovers all focused Strategy Lab tests;
- every delegated contract is invoked exactly once by E2E;
- both matrix files remain required repository artifacts.

## Clean fixture requirement

Focused tests must provide every dependency they exercise. Warning-only missing mock functions are treated as fixture defects even when the shell exit status remains zero. Terminal-result and stale-worker fixtures therefore define explicit no-op UDP cleanup mocks instead of emitting `strategy_lab_udp_input_cleanup: not found` warnings.

## Scope

The matrix covers lifecycle state, cancellation, deadlines, stale recovery, serialized state, traffic isolation, runtime readiness, interception evidence, exact profile replay, multi-protocol shortlist, UDP input, circular isolation/ownership, Settings guard, persisted reload, structured results, progress/localization, obsolete-surface removal, retention, Diagnostics activation, and full end-to-end behavior.

Project-wide profile, package lifecycle, release, GitHub governance, repository hygiene, PHP/XML/shell lint, and FreeBSD package build remain separate CI steps because they are not Strategy Lab focused contracts.

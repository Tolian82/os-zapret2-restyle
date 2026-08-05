# 2026-08-05 — Complete Strategy Lab profile output

Patch candidate: `v0.3.2_34`.

Strategy Lab now separates internal catalog fragments from user-ready Traffic Strategy output. The generated profile contains the tested TLS selectors, one static target selector, the tested range, and the exact catalog desynchronization fragment. Runtime-global process arguments and dynamic temporary list paths are rejected.

Stage 85 no longer publishes a stable fragment directly. It constructs the exact displayed profile and executes that profile three times through a dedicated replay runner. The runner resolves only the static selector to the temporary isolated runtime representation; all remaining displayed lines are replayed unchanged. A shortlist item is retained only after all three attempts pass the endpoint-binding, candidate-readiness, and IPFW interception contracts.

Focused verification is provided by `scripts/test-strategy-lab-profile-output.sh` and is part of the mandatory domain-diagnostics suite. Patch `_35` remains blocked until all GitHub checks and the FreeBSD package build for `_34` complete successfully.

# Strategy Lab adaptive workload budget architecture

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How does Strategy Lab derive finite job/stage parent budgets from measured eligible work?

Read after:

- `docs/architecture/STRATEGY_LAB.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Current implementation patch: `docs/patches/v0.4.0_26.md`.

==================================================
BOUNDARY
==================================================

The budget owner is scheduling/containment policy, not search policy.

It may change only parent time envelopes according to work that the current job is actually
eligible to execute. It must not change candidate identity, native graph reachability,
Model-C/Model-B/cold-Model-A ordering, source-port ownership, PASS/FAIL classification,
result ranking, cancellation, or restoration semantics.

The invariant remains:

`bounded child operation <= stage parent <= finite job parent`.

An adaptive extension is never permission for an unbounded child and never restarts the job
clock.

==================================================
WHEN THE PLAN IS CREATED
==================================================

The initial configured budget is recorded at job start because Stage 00/10/20/30 themselves
must already have a finite parent.

A workload-derived plan can be authoritative only after Stage 30 has completed successfully,
because that is the first point where Strategy Lab has both:

- validated endpoint count from Stage 00;
- measured IPv4/IPv6/QUIC capability state from Stage 30;
- validated job mode and Generic UDP request from job state.

Therefore production `_26` applies the adaptive plan immediately after Stage-30 PASS and
before Stage 40. Every resulting absolute deadline remains calculated from the original
`started_epoch`.

==================================================
INPUT MATRIX
==================================================

The canonical input is:

`number of endpoints × IPv4/IPv6 × TLS/QUIC × Generic UDP × Standard/Extended mode`.

The matrix records actual current semantics rather than hypothetical future support:

- IPv4 must be `available` for the plan to exist;
- the native search epoch remains IPv4;
- IPv6 currently adds Stage-40 AAAA/TLSv6 baseline work when available;
- Extended TCP remains part of the existing Extended floor;
- QUIC work exists only in Extended mode and only when `quic_ipv4=available`;
- Generic UDP work exists only in Extended mode with a validated configured UDP request.

==================================================
CALIBRATED FLOOR
==================================================

The existing environment-controlled values remain the minimum:

- `STRATEGY_LAB_STANDARD_BUDGET`, default `150 s`;
- `STRATEGY_LAB_EXTENDED_BUDGET`, default `120 s`;
- `STRATEGY_LAB_STAGE80_TIMEOUT`, default `120 s`.

The current reference topology contains at most two endpoints. The clean `_25` owner-live
Extended Telegram run completed in `114759 ms` total with Stage 60 `34198 ms`, two endpoints,
IPv4 available, IPv6 unavailable, QUIC closed and Generic UDP inactive. `_26` intentionally
keeps that topology at exactly the existing `270 s` total floor; it does not reduce a proven
safe parent merely because one observed run finished faster.

==================================================
FINITE ADDITIONS — `eligible-work-v1`
==================================================

`policy=eligible-work-v1` uses these explicit bounded weights:

- endpoint count above two: `+30 s` per extra endpoint to Standard;
- endpoint count above two in Extended mode: another `+15 s` per extra endpoint to Extended
  and Stage 80;
- IPv6 available: `+5 s` per endpoint to Standard for the additional AAAA/TLSv6 baseline;
- Extended QUIC available: `+20 s`, matching the current four-entry catalog times the
  existing `5 s` optional-candidate envelope;
- Extended Generic UDP configured: `+15 s`, matching the current three-entry catalog times
  the existing `5 s` optional-candidate envelope.

The calculation is additive and monotonic. It never subtracts from environment-configured
base values. Recalculation on the same Budget object uses the cached original base so an
adaptive addition cannot compound itself.

For two endpoints with every currently optional branch eligible:

- Standard: `150 + 10 = 160 s`;
- Extended: `120 + 20 + 15 = 155 s`;
- overall Extended search budget: `315 s`;
- Stage 80: `155 s`.

==================================================
DEADLINES
==================================================

Let `t0` be the original job start epoch.

After adaptation:

- `standard_deadline = t0 + effective_standard`;
- Standard `overall_deadline = standard_deadline`;
- Extended `overall_deadline = t0 + effective_standard + effective_extended`;
- Stage-80 deadline remains `min(stage80_start + effective_stage80, overall_deadline)`.

Thus optional work receives finite headroom but Stage 80 can never outlive the whole-job
parent. Candidate admission and operation-specific limits remain active below these parents.

==================================================
EVIDENCE
==================================================

Every successful adaptation persists `adaptive-budget.json` in the job directory with:

- policy and schema;
- exact measured work matrix;
- weights used;
- additions by source;
- configured base seconds;
- effective Standard/Extended/search/Stage-80 seconds.

The established atomic state owner rewrites the public effective numeric budget/deadline
fields in `status.json`. `timing-telemetry.json` receives a `budget_adaptation` event at
Stage 30 containing the same plan.

This evidence is required for owner-live validation because a terminal PASS alone cannot
prove that the adaptive owner was actually active.

==================================================
FAIL-CLOSED RULES
==================================================

Adaptive planning fails closed if Stage-30 state is malformed, no endpoint exists, or IPv4
is not actually available. It does not infer capabilities from DNS names, old jobs, historical
telemetry or user expectation.

An unavailable optional capability contributes zero additional seconds; Strategy Lab does not
charge time for a branch it will skip. Standard mode similarly ignores Extended-only QUIC and
Generic UDP even if corresponding state fields are present.

==================================================
VERIFICATION
==================================================

Source contract: `scripts/test-strategy-lab-adaptive-budget.sh`.

Owner-live `_26` gate: one normal Extended run must show `policy=eligible-work-v1`, a work
matrix matching the appliance state, exact calculated effective seconds, no new timeout or
unexpected Stage-60 fallback, and clean semantic restoration. Optional IPv6/QUIC/UDP need not
be fabricated on the owner appliance; their deterministic additions are source-tested.

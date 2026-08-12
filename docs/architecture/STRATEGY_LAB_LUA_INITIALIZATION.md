# Strategy Lab Lua initialization measurement

Status: **MEASUREMENT COMPLETE / PRODUCTION MODEL C UNCHANGED**

## Question

Can Stage 60 reduce warm-bucket startup/readiness/RSS cost by replacing the current Model-C
Lua initialization policy with candidate-minimal initialization?

## Current production behavior

`stage60_model_c.py` builds one physical warm bucket for at most three ready candidates. For
that batch it initializes the ordered union of every selected `CandidateSpec.lua_dependencies`,
then adds the two shared runtime requirements:

- `zapret-auto.lua`;
- `strategy_lab_model_c.lua`.

The shared selector is required because one physical `dvtws2` dispatches the candidate chain
from the controlled source port. Removing it is not a candidate-minimal optimization; it
would change the accepted Model-C architecture.

## Native graph result for v0.4.1_2

All 16 current native TLS 1.3 Stage-60 expansion candidates declare the same dependencies:

- `zapret-lib.lua`;
- `zapret-antidpi.lua`.

Consequently every current width-three Model-C batch has the same effective initialization
set:

1. `zapret-lib.lua`;
2. `zapret-antidpi.lua`;
3. `zapret-auto.lua`;
4. `strategy_lab_model_c.lua`.

That is already the candidate-minimal union compatible with one shared Model-C bucket.
There is no smaller distinct A/B variant to benchmark without changing candidate semantics
or replacing the one-worker dispatcher architecture.

## Measurement contract

The packaged `lua-init-measure` command reports `policy=lua-init-set-equivalence-v1` and:

- enumerates the exact native Stage-60 expansion corpus;
- records every candidate's declared Lua dependencies;
- compares current Model-C batch init sets with the candidate-minimal union;
- records installed file presence/size evidence without executing `dvtws2`;
- sets `runtime_comparison_required=false` when every batch is equivalent;
- emits `timing_claim=not_applicable_equivalent_init_set` and
  `rss_claim=not_applicable_equivalent_init_set` instead of fabricating a speedup;
- never starts/stops Zapret2, adds IPFW rules, allocates source ports, or changes production
  Stage-60 routing.

The `_2` measurement implementation defaulted to `/usr/local/share/zapret2/lua`; the
canonical ResourceInventory root is `/usr/local/etc/zapret2/lua`. That mismatch affected
only installed-file evidence. The corrected owner invocation selected the canonical root;
the next packaged measurement patch must eliminate the duplicate default-path definition.

## Accepted owner-live result

The owner-installed `_2` package reported, using the canonical installed Lua root:

- `candidate_count=16`;
- all six batches `equivalent_init_set=true`;
- `checks.all_required_files_present=true`;
- `checks.production_model_unchanged=true`;
- `runtime_comparison_required=false`;
- `conclusion=equivalent_init_set`.

Evidence: `docs/verification/evidence/2026-08-12-v0.4.1_2-lua-init-live-pass.md`.

## Decision / next work

Lua initialization optimization is closed. Do not modify production Model C for Lua loading.

The next independent optimization is BLOB loading/startup/RSS measurement. That work must
separately establish whether eager/common BLOB declarations have measurable startup or RSS
cost while preserving exact CandidateSpec resource identity and existing attribution,
deadline, cleanup and restoration guarantees.

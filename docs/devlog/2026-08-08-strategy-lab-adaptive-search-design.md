# 2026-08-08 — Strategy Lab adaptive native-Zapret2 search design

## Trigger

Review of the post-migration Strategy Lab search path found that the Python rewrite
preserved several intentionally narrow first-generation assumptions: Stage-60 expansion
is gated by Stage-50 family acceptance, the candidate adapter initializes all discovered
Lua files and injects `--out-range=-d10`, final profile validation requires the same range,
and every candidate pays a fresh dvtws2 startup/readiness/cleanup cycle.

The owner requested that search quality take priority over those simplifying assumptions
and that every proposed runtime optimization be measured before becoming a new postulate.

## Design recorded

Created the active decision and specialist design:

- `docs/decisions/DEC-2026-08-08-strategy-lab-adaptive-search.md`;
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`;
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

The approved target direction is:

- native Zapret2 only; classic zapret strategy syntax is not a search source;
- Python remains the planner/search owner and shell remains a narrow system adapter;
- Stage 50 becomes evidence rather than a hard family allowlist;
- `CandidateSpec` and job-scoped `ResourceInventory` make candidate/resource identity
  explicit;
- BLOB-free, built-in, inline and installed external BLOB strategies are all representable;
- `--out-range` belongs to the candidate rather than a fixed global `-d10` rule;
- known native-Zapret2 strategies form a golden expressiveness/reachability corpus;
- IPv4/TCP/TLS receives the main search budget, IPv6 is capability-gated/lower priority,
  and QUIC remains only the fixed IPv4 UDP/443 capability/precheck signal;
- discovery is separated from strict finalist replay/long-GET evidence;
- stable early stop targets two to three strong candidates rather than filling five slots;
- all timeout constants are subject to telemetry-driven review.

## Runtime hypotheses preserved for testing

No decision was made yet between:

- A — cold candidate -> fresh dvtws2;
- B — multiple warm dvtws2 workers with isolated divert ownership;
- C — one warm dvtws2 with compatible preloaded candidate buckets and deterministic
  dispatcher.

The design records upstream facts that make warm execution worth measuring while also
recording the first-match limitation of ordinary `--new` profiles. Controlled source-port
selection, a laboratory Lua dispatcher, common Lua preload, lazy buckets and true parallel
candidate probes all remain hypotheses.

The experiment plan requires cold-result equivalence, deterministic candidate attribution,
no state leakage, exact cleanup/restoration, RSS/timing measurement and separate testing of
warm coexistence versus simultaneous probing.

## Source boundary

This work is documentation only. `VERSION=0.3.3` and `PLUGIN_REVISION=27` remain unchanged,
and no Strategy Lab runtime/source behavior is changed by this design record.

Future source sequence is `_28` hard-gate removal, `_29` CandidateSpec/ResourceInventory,
`_30` native search graph/golden corpus/resources/range, `_31` adaptive planning/endpoint
pinning/telemetry, `_32` timeout model, and `_33` discovery/stability/deep validation.

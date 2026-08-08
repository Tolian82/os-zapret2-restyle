# DEC-2026-08-08 — Strategy Lab adaptive native-Zapret2 search

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Which Strategy Lab search rules replace the original family-first search contract, and
which runtime-acceleration ideas remain hypotheses until measured on OPNsense?

Purpose:
Record the approved post-migration search architecture before source changes begin.

Read after:
`docs/DECISIONS.md`, `docs/architecture/STRATEGY_LAB.md`, and
`docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`.

Detailed architecture:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`.

Experimental verification plan:
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`.

Status:
Active design decision with incremental source implementation. `_28` implements the
Stage-50/60 hard-gate removal in the `0.4.0_2` source candidate; `_29`–`_33` remain
planned. Documentation must continue to distinguish each implemented slice from the
remaining approved target architecture.

==================================================
CONTEXT
==================================================

The Python migration made Python authoritative for automated Strategy Lab search policy,
candidate execution and final results, but preserved the original search semantics:

- Stage 50 tests one representative of each named family;
- Stage 60 considers only families accepted by Stage 50;
- the candidate adapter starts a fresh dvtws2 for each candidate, initializes every Lua
  file found in the runtime directory and injects `--out-range=-d10`;
- final profile construction also requires exactly `--out-range=-d10`;
- the implementation contains a separate capability-gated QUIC search branch.

Those constraints were useful for the first bounded implementation but are too narrow for
the product objective: discover native Zapret2 strategies that actually work on the
owner's current provider/runtime without excluding stronger combinations merely because a
simple representative failed.

The design review also established that startup cost and candidate isolation are separate
questions. Zapret2 permits startup-time Lua/BLOB initialization and multiple profiles, but
`--new` is not a candidate selector: profiles are scanned in order and the first matching
profile wins. Warm workers may therefore be useful, but only after deterministic dispatch,
traffic isolation and state-leakage behavior are proven on the real FreeBSD/IPFW path.

==================================================
DECISION
==================================================

1. Strategy Lab search is native-Zapret2-only.

   Search candidates, examples, syntax and regression cases come from `bol-van/zapret2`
   concepts and the installed Zapret2 runtime. Classic zapret/nfqws1/dvtws/winws strategy
   syntax is not translated into the search space and is not used as a technical strategy
   reference. Upstream Zapret2 `blockcheck2` may inform search methodology, but Strategy
   Lab does not import its POSIX-shell implementation.

2. Python remains the search-policy owner.

   Candidate generation, adaptive ordering, budgets, resource selection, evidence,
   stability decisions and final selection remain Python responsibilities. Shell remains
   a narrow OPNsense/FreeBSD adapter for lifecycle, dvtws2, IPFW and other audited system
   mutations. No new shell search policy is approved.

3. Stage 50 is evidence, not a hard family gate.

   A simple representative PASS or FAIL may change priority, but neither result permits or
   forbids an entire family. `family` becomes descriptive metadata. Stage 60 explores a
   native-Zapret2 candidate graph according to evidence, cost and remaining budget.

4. Search becomes adaptive rather than family-first.

   Start with cheaper/simple candidates. A success raises the priority of nearby simpler
   or closely related variants. A failure may open stronger branches such as different
   positions, `seqovl`, alternate patterns/BLOBs, fake-plus-split, `fakedsplit`, `syndata`
   or other native-Zapret2 combinations. Exhausting one branch advances to the next useful
   branch instead of terminating search because a representative family failed.

   Historical success data may change ordering only. It must never make a valid branch
   unreachable.

5. Candidate identity becomes explicit Python data.

   A `CandidateSpec` must carry the complete information needed to reproduce and publish
   the candidate: protocol/transport filters, ordered Lua instances, payload/range data,
   positions and technique parameters, BLOB requirements, target-binding requirements,
   resource dependencies and stable candidate identity. `--out-range` is candidate data;
   `-d10` is not a global invariant and the field may be absent when the candidate does
   not require an output range.

6. Runtime resources are discovered, not permanently hardcoded.

   At job start Python creates a job-scoped `ResourceInventory` from the installed
   `/usr/local/etc/zapret2/lua/` and `/usr/local/etc/zapret2/files/fake/` trees. The
   inventory is recorded as evidence so a result can be reproduced against the runtime
   that was actually tested.

   Candidate resources are selected semantically. The planner must not form a blind
   Cartesian product of every Lua file and every BLOB.

7. External BLOB files are optional.

   The search space explicitly supports four resource forms:

   - BLOB-free candidate;
   - Zapret2 built-in BLOB;
   - inline `0x...` BLOB/pattern;
   - installed external `.bin` resource.

   Zapret2's standard built-ins (`fake_default_tls`, `fake_default_http`,
   `fake_default_quic`) and default inline behavior such as `multisplit`
   `seqovl_pattern=0x00` are valid native mechanisms. An external file must not be added
   merely to make every candidate look structurally identical.

8. A bypass candidate contains a Zapret2 Lua action.

   Zapret2 profile actions are implemented by Lua instances invoked through
   `--lua-desync`. A profile with only filters/resource initialization and no Lua action
   is pass-through evidence and belongs to baseline/control behavior, not to the set of
   discovered bypass strategies.

9. Known native-Zapret2 working strategies form a golden regression corpus.

   The corpus is used to prove expressiveness, resource binding and graph reachability;
   it is not a provider-wide allowlist. The planner must be able to represent known
   working strategies, including candidates whose output range is not `-d10`, candidates
   without external BLOBs and candidates using installed external BLOBs.

10. Endpoint conditions are held stable across candidate comparison.

    Resolve the job target once for the search epoch, retain the hostname/SNI contract and
    pin the selected endpoint set for candidate comparison. A deliberate re-resolution is
    a recorded search-epoch change, not an invisible per-candidate variable.

11. Discovery and final validation are separate evidence levels.

    Mass discovery uses the least expensive bounded probe that preserves useful ranking
    signal. Finalists receive strict fresh-connection replay and a real bounded GET with a
    sufficiently long response target. The exact lightweight discovery probe remains an
    implementation/measurement choice; it must not weaken the finalist contract.

    Stability is 3/3 and fail-fast: once an attempt proves that 3/3 is impossible, the
    remaining repetitions are not spent on that candidate. A long-response validation
    that cannot reach 16 KiB because the selected resource is itself shorter is recorded
    as `inconclusive`, never as a fabricated 16-KiB PASS.

12. Search stops on quality, not an arbitrary count of five.

    The normal early-stop target is two to three strong, stable candidates when available.
    A smaller truthful result is preferable to spending the remaining budget only to fill
    a five-item quota.

13. Protocol priority is intentionally narrow.

    IPv4/TCP/TLS receives the primary search budget. IPv6 is capability-gated and lower
    priority. QUIC keeps only the existing fixed IPv4 UDP/443 capability/precheck signal;
    Strategy Lab does not expand a QUIC strategy search space under this decision.
    TLS 1.2, HTTP and explicitly configured generic UDP remain separate extended work.

14. Circular is not a discovery algorithm.

    Upstream `circular` remains eligible only for later validation/operation on already
    discovered compatible winners. Its stateful switching model does not decide which
    Strategy Lab candidates are initially searched.

15. Warm/multi-process execution remains an experiment, not a postulate.

    The previous statement "only one temporary candidate dvtws2 may exist" and the
    opposite statement "multiple dvtws2 are faster" are both withdrawn as search-policy
    assumptions. Models A/B/C in the experimental plan are measured against the cold
    reference before one is selected.

    Coexisting warm workers and concurrently probing different strategies are distinct
    questions. The first may be useful even if probes remain sequential. No parallel
    candidate-probe requirement is approved by this decision.

16. Finalists remain independently verifiable.

    Any warm-worker optimization selected for discovery must be checked against a cold,
    isolated execution reference. Final shortlist evidence must not depend on hidden
    state retained by an earlier candidate.

17. Timeout constants are reopened for measurement.

    The current values remain executable defaults until replaced by a source patch, but
    they are no longer presumed optimal. The redesign must collect timing for DNS,
    preparation, dvtws2 launch/readiness, probe, stop/cleanup and long GET, then derive a
    consistent hierarchy:

    `operation deadline <= candidate deadline <= stage deadline <= job deadline`.

    An enclosing deadline may not expire before a valid child operation has consumed its
    allowed deadline and required cleanup envelope.

==================================================
OPEN EXPERIMENTS
==================================================

The following are deliberately not approved as production mechanisms yet:

- several warm dvtws2 workers on different divert ports;
- one warm dvtws2 containing a bucket of compatible candidates;
- a small Lua laboratory dispatcher that selects one preloaded candidate;
- controlled client source-port encoding as a candidate selector;
- a common preloaded Lua bundle versus candidate-minimal Lua initialization;
- lazy bucket startup and bucket compatibility rules;
- simultaneous candidate probes.

Each must meet the measurement and cold-equivalence criteria in
`docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md` before it can become a
production postulate.

==================================================
SUPERSESSION
==================================================

This decision supersedes only the conflicting search-policy portions of
`docs/decisions/DEC-2026-08-04-strategy-lab.md`:

- product rule 6 is retained for one active Strategy Lab **job**, but its "one candidate
  strategy/process may exist" interpretation is reopened for A/B/C measurement;
- product rule 14 family-first/accepted-family-only search is superseded;
- product rule 15 is superseded only for its QUIC strategy-search branch; the fixed
  UDP/443 capability/precheck remains;
- fixed timeout values are treated as current implementation values pending the approved
  telemetry-driven review.

The lifecycle, cancellation, exact restoration, saved-configuration immutability,
job-state and RU/EN contracts remain active. The Python/shell responsibility decision in
`docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md` remains active and
is reinforced by this decision.

==================================================
IMPLEMENTATION SEQUENCE
==================================================

After this documentation-only design record, source work is split into separate logical
package revisions:

- `_28` — implemented in `0.4.0_2` source: remove Stage-50 accepted-family hard gating
  while preserving accepted-first evidence priority;
- `_29` — introduce Python `CandidateSpec` and job-scoped `ResourceInventory`, and move
  candidate resource/search decisions out of the shell adapter;
- `_30` — introduce the native-Zapret2 search graph, golden corpus, BLOB-free/builtin/
  inline/file-resource branches and candidate-defined output ranges;
- `_31` — adaptive ordering, endpoint pinning, early-stop policy and timing telemetry;
- `_32` — telemetry-driven operation/candidate/stage/job timeout model;
- `_33` — lightweight discovery, fail-fast 3/3 stability and finalist long-GET/16-KiB
  validation.

The A/B/C runtime experiment may inform `_31` or a later dedicated source patch. It is
not silently folded into `_28`–`_30` before its equivalence and safety gates pass.

==================================================
AFFECTED DOCUMENTS
==================================================

- `docs/INDEX.md`
- `docs/PROJECT_STATE.md`
- `docs/DECISIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/architecture/STRATEGY_LAB.md`
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`
- `docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
- `docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`
- `docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`
- `docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md`
- `docs/verification/STRATEGY_LAB_ADAPTIVE_SEARCH_EXPERIMENTS.md`
- `docs/devlog/2026-08-08-strategy-lab-adaptive-search-design.md`

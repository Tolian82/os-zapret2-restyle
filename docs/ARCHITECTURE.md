# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
How is the current system built?

Purpose:
Describe active technical architecture, runtime ownership, interfaces and component
responsibilities. This file is current-state architecture only; historical implementation
sequences belong in decisions/devlog/patch/evidence records.

Read after:
`docs/PROJECT_STATE.md` and `docs/DEVELOPMENT_GUIDE.md`.

==================================================
IDENTITY AND SOURCE OF TRUTH
==================================================

Repository: `https://github.com/Tolian82/os-zapret2-restyle`
Primary branch: `main`
Project/package: `os-zapret2-restyle`
Internal service/configd namespace: `zapret`
Version source: `VERSION`
Required packaged runtime: Python 3.13 on supported OPNsense / FreeBSD 15 amd64.

Committed source describes actual implemented behavior. Current project direction and
approved transition state are recorded in current documentation. A stale historical
architecture statement cannot override newer owner canon.

==================================================
CONFIGURATION AND NORMAL RUNTIME
==================================================

```text
OPNsense model
  -> generated zapret.conf
  -> parser and count-carrying profile pipeline
  -> Target Mode and profile normalization
  -> HOSTLIST/IPSET resolver and exclusions
  -> BLOB and port resolution
  -> dvtws2 argument generation
  -> candidate validation
  -> atomic activation or rollback
  -> launcher
  -> target firewall rules
  -> supervisor
```

The active generated runtime is `/usr/local/etc/zapret2/runtime-v2`. One supervised
normal dvtws2 process owns the active saved strategy. Invalid candidate configuration
must not replace the active runtime or leave partial firewall/process state.

Only `HOSTLIST:name` and `IPSET:name` target selectors are supported. Multiple unique
supported selectors in one user profile are normalized into separate runtime profiles
while preserving non-selector lines, order and user-authored `--new` boundaries.

==================================================
SETTINGS APPLY
==================================================

```text
/ui/zapret
  -> Settings API validation/normalization
  -> persistent save
  -> configctl zapret reconfigure
  -> zapret_service.sh
  -> Backend-v2 candidate build/validation
  -> atomic runtime switch or rollback
```

Only an exact successful configd response completes Apply. On failure, persistent model,
generated template and runtime are restored to the prior valid state.

==================================================
DIAGNOSTICS INTERFACES
==================================================

Short connectivity probe:

```text
/ui/zapret/diagnostics
  -> /api/zapret/diagnostics/testdomain
  -> configctl zapret testdomain
  -> test_domain.sh
```

Strategy finding uses only asynchronous Strategy Lab:

```text
/ui/zapret/diagnostics
  -> POST /api/zapret/strategy_lab/start
  -> immediate job_id
  -> read-only status/events polling
  -> structured stage/partial results
  -> terminal result
  -> optional cancel
```

The synchronous Blockcheck path is retired and is not an active fallback interface.

==================================================
STRATEGY LAB CURRENT ARCHITECTURE
==================================================

An automated Strategy Lab job owns the shared Zapret2 lifecycle boundary from initial
snapshot through mandatory restoration. The normal service is stopped only after its
exact initial state is recorded and verified.

The current implementation boundary is:

```text
Diagnostics GUI / JavaScript
        ↓
OPNsense PHP MVC/API
        ↓
configd
        ↓
thin compatibility launcher
        ↓
Python 3.13 Strategy Lab orchestration
        ↓
small explicit FreeBSD/OPNsense adapters
        ↓
IPFW/divert + temporary dvtws2 + bounded probes
```

Python owns automated job state, stages, budgets/cancellation, subprocess execution,
probe parsing, CandidateSpec/ResourceInventory, adaptive search decisions, runtime
rendering inputs and structured results. Small shell/service adapters own narrow
FreeBSD/OPNsense lifecycle and firewall/process mutations only.

Stages remain:

```text
00 target initialization
10 lifecycle snapshot
20 normal service stop
30 network capability precheck
40 clean baseline
50 TLS 1.3 reconnaissance / evidence
60 bounded adaptive native-Zapret2 expansion
70 stability confirmation
80 extended protocol branches
85 shortlist
90 cleanup and exact restoration
99 final report
```

The public asynchronous API, stage numbers, saved-configuration immutability,
cancellation semantics and Stage-90 restoration contract remain stable.

Specialist base contract:
`docs/architecture/STRATEGY_LAB.md`.

==================================================
MODEL C — SELECTED PRODUCTION DIRECTION
==================================================

**Model C is selected. A/B/C model selection is closed.**

Model roles:

- Model A: retained cold correctness/reference implementation;
- Model B: retained warm/reference implementation and temporary legacy fallback in
  packaged source through `v0.4.1_12`;
- Model C: selected normal production Stage-60 runtime.

Current packaged `_12` source still contains transition debt:

`Model C -> Model B -> Model A cold`.

That describes current implementation only. It is **not** an architecture choice, gate,
fallback requirement or invitation to re-select Model B. `v0.4.1_13` removes B/A from
the normal production Stage-60 fallback chain.

Model C uses source-port-qualified dispatch so one compatible physical warm worker can
serve a planner-selected logical batch while preserving exact candidate attribution.
Current accepted constraints include:

- immutable CandidateSpec and job-scoped ResourceInventory;
- logical candidate width at most three;
- pinned endpoints sequential inside one candidate;
- exact source-port-qualified IPFW/Lua attribution;
- `preferred-free-else-alternate` source-port leasing;
- profile-compatible physical segmentation while preserving the logical planner batch;
- readiness from process identity + socket + clean startup log + two consecutive good
  snapshots with 25 ms polling and a 4 s bound;
- cleanup on success/failure/cancel and Stage-90 semantic restoration.

Specialist authority:
`docs/architecture/STRATEGY_LAB_MODEL_C.md`.

==================================================
ADAPTIVE SEARCH CONTRACT
==================================================

Strategy Lab searches native `bol-van/zapret2` semantics only.

Stage 50 provides evidence/priority and never acts as a hard family allowlist. Stage 60
uses a bounded native DAG where current-job evidence changes priority/reachability of
compatible neighbors without silently inventing strategies.

Stable search identities:

- immutable CandidateSpec;
- one job-scoped installed ResourceInventory;
- exact candidate ranges/resources/action order;
- pinned endpoint/search epoch;
- bounded GET-4K discovery;
- downstream stability/result ownership;
- finite `eligible-work-v1` parent budgets;
- infrastructure failures remain distinct from candidate network PASS/FAIL.

Runtime acceleration must not change search semantics.

Specialist authority:
`docs/architecture/STRATEGY_LAB_ADAPTIVE_SEARCH.md` and
`docs/architecture/STRATEGY_LAB_ADAPTIVE_BUDGET.md`.

==================================================
CURRENT MEASUREMENT DECISIONS
==================================================

The following measurement questions are closed for the current architecture unless the
owner, roadmap, a material architecture change or fresh reproducible evidence reopens
them:

- Lua initialization: no production reduction justified;
- current-width BLOB preload/common set: no material startup/RSS penalty and no lazy-BLOB
  production change justified;
- discovery: bounded GET-4K retained;
- cross-batch keep-warm/reuse: not justified after the `_11/_12` lifecycle/readiness
  corrections.

Do not restore an old experiment sequence merely because older documentation mentions it.

==================================================
DNS / NETWORK FACT BOUNDARY
==================================================

The previously reported local/container DNS slowness/failure is historical and closed:
**the owner fixed DNS**. Current work treats DNS as working.

A future DNS issue requires fresh direct reproducible evidence. An old timeout, old log,
old document or new-session memory gap is not sufficient to classify DNS as broken again.

==================================================
SHORTLIST AND CIRCULAR VALIDATION
==================================================

Strategy Lab may publish up to three replay/stability-qualified finalists and never
writes a candidate automatically into saved Traffic Strategy.

Temporary circular validation is a separate bounded lifecycle transaction. Circular
validation and an automated Strategy Lab job cannot run concurrently because they share
the lifecycle lock. Saved configuration remains immutable and original service state is
restored exactly.

==================================================
SERVICE LIFECYCLE
==================================================

All public mutating operations converge on `zapret_service.sh` and share
`/var/run/zapret2-lifecycle.lock`:

- start;
- stop;
- restart/reconfigure;
- automated Strategy Lab job;
- temporary circular validation.

Status operations are read-only. Long-lived processes must not inherit the lifecycle
lock descriptor. Runtime-failure callbacks use bounded/non-competing lifecycle ownership.
The supervisor detects runtime failure but does not become a second independent lifecycle
manager.

==================================================
PACKAGE / UPSTREAM BOUNDARY
==================================================

The FreeBSD package owns plugin files and immediate OPNsense integration.

`setup.sh` is the single approved backend for upstream bol-van/zapret2 acquisition,
release selection, build and verification. Service Start/Apply/Reconfigure never compile
or install upstream dependencies.

Package lifecycle preserves the initially running/stopped service state and fails closed
on incomplete/unknown state or unsuccessful stop/setup verification.

==================================================
TECHNICAL CONSTRAINTS
==================================================

- FreeBSD `/bin/sh` compatibility remains required for retained shell adapters;
- owner console examples target root `csh` unless explicitly entering `sh`;
- Python runtime uses the supported OPNsense Python 3.13 dependency model;
- OPNsense configuration/configd are the integration boundary;
- candidate validation precedes activation;
- generated runtime is never committed;
- lifecycle mutation is serialized and fail-closed;
- temporary diagnostics use owned target-scoped firewall rules;
- no automatic permanent strategy modification;
- ordinary package patches do not imply stable release/pkg-repository publication.

Current state is in `docs/PROJECT_STATE.md`; exact next work in `docs/START_HERE.md`;
future sequence in `docs/ROADMAP.md`; historical rationale/evidence in decisions,
patches, devlogs and verification records.

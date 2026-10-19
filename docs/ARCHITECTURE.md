# os-zapret2-restyle

## Approved transition — shared Voice/Strategies backend, 2026-10-13

The owner approved one shared model, full-runtime generator and Apply/lifecycle owner for Strategies and Voice. Voice adds STUN profiles and scoped UDP/IPSET capture; frontend and full requirements are unchanged. This is an approved target, not an implemented-source claim. [Section 12 of the Voice specification](architecture/VOICE_TRANSMISSION_GUI.md#12-общий-backend-со-стратегиями-утверждено-13102026) owns the contract; [v0.5.2 implementation plan](architecture/VOICE_TRANSMISSION_COMPLETION_PLAN.md) owns the proposed code changes and controls. Stage `v0.5.2_1` was opened without release; the owner has now instructed execution of the detailed plan. Existing frontend/backend behavior is unchanged by that version transition. Legacy private Voice transactions are reuse/transition material, not a second authoritative production architecture.

## Document role

Question answered:
How is the current system built?

Purpose:
Describe active technical architecture, runtime ownership, interfaces and component
responsibilities. This file is current-state architecture only; historical implementation
sequences belong in decisions/devlog/patch/evidence records.

Read after:
`docs/PROJECT_STATE.md` and the task-selected specialist architecture documents.

## Identity and source of truth

Repository: `https://github.com/Tolian82/os-zapret2-restyle`
Primary branch: `main`
Project/package: `os-zapret2-restyle`
Internal service/configd namespace: `zapret`
Version source: `VERSION`
Required packaged runtime: Python 3.13 on supported OPNsense / FreeBSD 15 amd64.

Committed source describes actual implemented behavior. Current project direction and
approved transition state are recorded in current documentation. A stale historical
architecture statement cannot override newer owner canon.

## Configuration and normal runtime

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

## Settings apply

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

## Menu localization

`src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml` declares the static English URLs and labels. `Menu/Menu.php` implements the supported OPNsense `MenuContainer::collect()` hook; for an active `ru_RU` system/user locale it sets `FixedName` on the three existing nodes (`General`, `Voice`, `Diagnostics`) when OPNsense builds the menu on any page. Per-user language overrides the system language, as in OPNsense's `ControllerRoot::setLang()`. Other locales continue to use the native gettext-translated Menu.xml labels. Individual Zapret Volt views must not rewrite the global menu DOM after page load.

## Voice form observation layout

The five Voice service checkboxes are rendered by OPNsense 26.7 native `base_form`/`form_input_tr` in the second table column. The UI-only `voice-profile-observation` is inserted immediately after each checkbox into the same cell, not into the third-column native `.help-block`. It stays inline while help is hidden; the native per-field help `div[data-for="help_for_…"]` gains class `show` when individual or full help opens, moving the observation above the original help text via local CSS. This is read-only presentation; native input IDs, help behavior, validation, Apply and persistence are unchanged.

## Diagnostics interfaces

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

## Strategy lab current architecture

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

## Model c — only normal production stage-60 runtime

**Model C is selected. A/B/C model selection is closed.**

Model roles from source revision `v0.4.1_13`:

- Model A: retained explicit cold correctness/reference implementation;
- Model B: retained explicit warm/reference/benchmark implementation;
- Model C: the only normal packaged production Stage-60 runtime.

The transitional `_12` chain

`Model C -> Model B -> Model A cold`

is no longer reachable from the normal packaged production entry point. The compatibility
command routes through `strategy_lab_py/stage60_model_c_production.py`, which reuses the
proven Model-C bucket engine and existing authoritative Stage-60 planner.

A Model-C infrastructure/selector/rendering/readiness/attribution/cleanup failure is
converted into a bounded structural Stage-60 error that is deliberately not
`WarmInfrastructureError`. Therefore the legacy Model-B/cold-Model-A replay handler does
not consume it. Candidate network FAIL/timeout remains candidate evidence and is not an
infrastructure fallback signal.

Explicit `model-b|parallel|cold` runtime overrides remain available only for reference,
benchmark and focused test tooling. Legacy fallback behavior inside those explicit
reference modules is not normal production architecture.

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
- cleanup on success/failure/cancel and Stage-90 semantic restoration;
- persisted normal-production policy evidence `model_c_only=true` and
  `cold_fallback_available=false`.

Specialist authority:
`docs/architecture/STRATEGY_LAB_MODEL_C.md`.

## Adaptive search contract

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

## Current measurement decisions

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

## Dns / network fact boundary

The previously reported local/container DNS slowness/failure is historical and closed:
**the owner fixed DNS**. Current work treats DNS as working.

A future DNS issue requires fresh direct reproducible evidence. An old timeout, old log,
old document or new-session memory gap is not sufficient to classify DNS as broken again.

## Shortlist and circular validation

Strategy Lab may publish up to three replay/stability-qualified finalists and never
writes a candidate automatically into saved Traffic Strategy.

Temporary circular validation is a separate bounded lifecycle transaction. Circular
validation and an automated Strategy Lab job cannot run concurrently because they share
the lifecycle lock. Saved configuration remains immutable and original service state is
restored exactly.

## Service lifecycle

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

## Package / upstream boundary

The FreeBSD package owns plugin files and immediate OPNsense integration.

`setup.sh` is the single approved backend for upstream bol-van/zapret2 acquisition,
release selection, build and verification. Service Start/Apply/Reconfigure never compile
or install upstream dependencies.

Package lifecycle preserves the initially running/stopped service state and fails closed
on incomplete/unknown state or unsuccessful stop/setup verification.

## Technical constraints

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

Current state is in `docs/PROJECT_STATE.md`; exact handoff in `docs/START_HERE.md`;
future sequence in `docs/ROADMAP.md`; historical rationale/evidence in decisions,
patches, devlogs and verification records.

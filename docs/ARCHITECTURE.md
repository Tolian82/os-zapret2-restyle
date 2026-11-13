# os-zapret2-restyle — system architecture

## Document role

Question answered:
How is the current system built?

Purpose:
Describe active technical architecture, runtime ownership, interfaces and component
responsibilities. This file is current-state architecture only; historical implementation
sequences belong in decisions/devlog/patch/evidence records.

Read after:
`docs/PROJECT_STATE.md` and the task-selected specialist architecture documents.

## Current native integration

The official OPNsense `Mk/plugins.mk` package owns plugin files and declared system dependencies. Native `pkg`, configd, rc/syshooks and the existing package hooks remain the integration boundaries. `setup.sh` manages the separately selected upstream Zapret2 runtime; it verifies system dependencies rather than provisioning a competing package environment. The [native packaging contract](architecture/OPNSENSE_NATIVE_COMPATIBILITY_AND_PACKAGING_SPEC.md) owns the details.

The shared Strategies/Voice model, builder and lifecycle are implemented and accepted within the [current-state evidence](PROJECT_STATE.md). Historical transition plans do not describe a pending second architecture.

Domain lists use `backend/domain_policy.py`, IP lists `backend/ipset_policy.py`, and profile parsing/normalization `backend/profile_policy.py`; the PHP bridges and retained shell entrypoints adapt those policies. IPFW rule ranges and the WAN-first contract belong to the [lifecycle specification](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md).

## Identity and source of truth

Repository: `https://github.com/Tolian82/os-zapret2-restyle`
Primary branch: `main`
Project/package: `os-zapret2-restyle`
Internal service/configd namespace: `zapret`
Version source: `VERSION`
Supported runtime, ABI, dependency providers and pinned private inputs are declared in the root `compatibility.json` and native `Makefile` package metadata; they are not independently versioned here.

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

The actual Strategies entrypoint is `SettingsController::applyAction()`. Native model validation and the Python list bridges produce the bounded `SharedApplyEnvelope`. The existing configd shared-Apply route takes original FD9, rereads the current Config, reconstructs and revalidates eligible list deltas, renders the detached candidate and uses the original full builder/validator. Runtime activation and the native root Config commit belong to that one transaction; there is no earlier GUI-side `Config::save()`.

`SharedConfigCommit::persist()` owns the native save. A verified stopped WAN-only save uses the existing shared WAN route without requiring runtime installation or a nonempty strategy. A running/common owner uses full runtime Apply/rollback. Definitive preflight refusal, uncertain commit and verified success remain distinct.

The separate Validate and Preview action reuses candidate preparation/generation/native validation without saving or activating. Product details live in the [Strategies contract](architecture/ZAPRET2_STRATEGIES_HOSTLIST_I18N_PREVIEW_SPEC.md) and [lifecycle contract](architecture/OPNSENSE_CLEAN_INSTALL_LIFECYCLE_RECOVERY_SPEC.md).

## Menu localization

`src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.xml` declares the static English URLs and labels. `Menu/Menu.php` implements the supported OPNsense `MenuContainer::collect()` hook; for an active `ru_RU` system/user locale it sets `FixedName` on the three existing nodes (`General`, `Voice`, `Diagnostics`) when OPNsense builds the menu on any page. Per-user language overrides the system language, as in OPNsense's `ControllerRoot::setLang()`. Other locales continue to use the native gettext-translated Menu.xml labels. Individual Zapret Volt views must not rewrite the global menu DOM after page load.

## Voice form observation layout

The five Voice service checkboxes are rendered by OPNsense 26.7 native `base_form`/`form_input_tr` in the second table column. The UI-only `voice-profile-observation` is inserted immediately after each checkbox into the same cell, not into the third-column native `.help-block`. The observation always uses the same block position immediately below the checkbox, regardless of help state. OPNsense's native per-field help `div[data-for="help_for_…"]` gains `show` when individual or full help opens, but only the help is toggled: it follows the stationary observation; no `:has(.show)` layout selector or custom event handler is needed. This is read-only presentation; native input IDs, help behavior, validation, Apply and persistence are unchanged.

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
Validated Python Strategy Lab orchestration
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
- Python invocation and dependency capabilities use the single compatibility policy and `python_runtime.sh`;
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

## Current and historical references

[Current architecture map](architecture/README.md) · [product contracts](REQUIREMENTS.md) · [current facts](PROJECT_STATE.md). The [source snapshot](history/stages/documentation-2026-11-13/snapshots/ARCHITECTURE.md) preserves prior transition notes, measurement conclusions and superseded implementation descriptions in full.

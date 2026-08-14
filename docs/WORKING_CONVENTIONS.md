# os-zapret2-restyle — Working conventions

This file answers: **How are the permanent principles applied in day-to-day engineering?**

Canonical permanent principles are defined only in `docs/PROJECT_PRINCIPLES.md`. This file must not
create competing formulations of them.

## Stable identities

- project/repository/package: `os-zapret2-restyle`;
- Makefile `PLUGIN_NAME`: `zapret2-restyle`;
- MVC namespace: `OPNsense\Zapret`;
- internal service/configd namespace: `zapret`;
- semantic version source: `VERSION`.

## Audit conventions

Every inherited reference must be classified before removal.

Allowed classifications:

- `OK`;
- `broken`;
- `unused`;
- `duplicate`;
- `inherited`;
- `requires live test`.

The word `zapret` alone is not evidence of obsolete inheritance.

`docs/AUDIT.md` is the authoritative register for audit scope, findings, evidence, live-test needs,
remediation and closure.

Every non-OK finding requires:

- globally unique ID;
- exact affected locations/chain;
- evidence and impact;
- verification plan;
- remediation plan;
- acceptance criteria;
- required documentation updates;
- remediation status.

A broken chain is recorded before it is fixed. Resolved findings remain as history.

Audits are complete only when affected current-state/roadmap/decision/specialist documentation is
synchronized. Audits are performed when the owner/current plan/new evidence requires them; existing
evidence is the starting point.

## Change conventions

- use the exact current GitHub base commit;
- keep one logical scope per task branch/PR;
- same-scope work and repair commits may coexist in that branch;
- include affected documentation and file-mode changes in the same logical scope;
- validate before publication;
- review the complete diff;
- repair same-scope failures in the same PR;
- do not publish a failed or partially validated latest head.

Package metadata:

- packaged source/behavior change with unchanged `VERSION`: increment `PLUGIN_REVISION` once;
- docs/governance/CI-only change: change neither value;
- explicitly authorized semantic release: change `VERSION`, reset revision to `1`.

## Testing conventions

Run syntax/static/focused tests appropriate to the changed behavior.

When working from a local checkout, inspect at least:

- `git status --short`;
- `git diff --check`;
- `git diff --stat`;
- complete relevant diff/staged diff.

Perform focused live OPNsense tests when the changed behavior needs appliance evidence.
Never claim a test passed unless it actually ran.

Static verification, package archive verification and live OPNsense verification are distinct states.
A package built from uncommitted source is not a reproducible project baseline until source and
synchronized documentation are committed.

## Engineering Memory workflow

The documentation principle from `PROJECT_PRINCIPLES.md` is implemented as follows.

Before work:

- record objective;
- record implementation plan;
- record expected verification/acceptance.

During work:

- record approved concepts immediately;
- record permanent rules/architecture changes immediately;
- record discoveries that change later work.

Before GitHub publication:

- confirm documentation states what changes and why;
- confirm expected result/acceptance boundary;
- confirm the complete near-term and long-term plan;
- reconcile that plan with what implementation/testing learned;
- update changed priorities before publication.

After work:

- record what completed and what was verified;
- record failures/unresolved issues;
- update `START_HERE` and `PROJECT_STATE`;
- update patch/evidence record;
- update `ROADMAP` when priority/sequencing/future/deferred work changed;
- record the exact next stage.

Engineering Memory is maintained during development, not reconstructed only at the end.

## Findings versus Architecture Debt

A Finding is a confirmed implementation defect/inconsistency/obsolete or concrete operational risk.

Architecture Debt is an unresolved design question. It is not fixed in code before intended behavior
is approved.

Architecture Debt lifecycle:

`Open -> Discussion -> Decision -> Implementation -> Verification -> Documentation -> Closed`

A Finding must not be remediated while open Architecture Debt determines its intended behavior.

## Project-context preflight

Mandatory reading order is controlled by root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task specialists`.

Read the selected documents completely through EOF. Use broader historical reading for a broad audit
or when the current plan/evidence calls for it; do not use it as automatic startup ceremony.

Before GitHub mutation, also read `docs/GITHUB_PUBLICATION.md` and apply scope-first inventory from
the active operational-handoff decision.

## GitHub development convention

Ordinary flow:

1. connected GitHub plugin first;
2. current `main` SHA, metadata, current plan and same-scope PR state;
3. create one logical task branch;
4. implement + synchronized documentation;
5. focused validation + complete diff review;
6. plan reconciliation;
7. one Ready PR;
8. latest-head required CI;
9. same-scope repair in the same PR if needed;
10. exact-head squash merge using exact versioned subject;
11. verify `main` and clean the temporary branch;
12. package/live verification when applicable.

Additional branch/workflow/tag/release/tree inventory is performed when that operation actually needs
it. A pinned recursive tree is recommended for a genuine broad/cross-cutting investigation with
unknown path/call chain, not for every known-file patch.

The connected GitHub plugin is the mandatory first repository interface. A narrow fallback is allowed
only when the plugin is responding and one exact function/permission is confirmed missing. Plugin
unavailability stops GitHub work.

Direct publication to `main` requires explicit owner authority and must never rewrite history.

## Standing delivery authorization

A request to fix/add/change/implement/complete an ordinary task authorizes the normal task branch,
Ready PR, checks, same-scope repair, squash merge, main verification and temporary branch cleanup.

Explicit stopping points override the default.

Stop for owner direction only on material product/architecture ambiguity, relevant unpublished
owner-local state, unresolvable required checks, unavailable GitHub plugin/authority, destructive
changes to user/pre-existing remote data, history rewriting/direct-main publication, or required
live appliance evidence available only from the owner.

Never ask the owner to confirm facts available from repository/GitHub/CI/current docs/read-only
diagnostics.

## Local-only state exception

GitHub is authoritative for committed/pushed state only.

If relevant owner-local changes are uncommitted/unpushed:

1. stop before editing overlapping source;
2. ask the owner to commit/push or explicitly transfer archive/patch;
3. establish exact transferred baseline;
4. never reconstruct/overwrite unpublished state from memory.

## OPNsense command presentation

Default owner console is root `csh`.

- keep read-only checks separate from state-changing installation/actions;
- do not silently assume bash/POSIX shell;
- if POSIX constructs such as `$(...)`, `name=value`, `export`, `if ...; then`, `$((...))`, functions
  are needed, enter explicit `sh`/`/bin/sh` and return with explicit `exit`;
- commands after `exit` must again be csh-valid.

Do not mutate tracked repository files directly from the OPNsense console with editor/rewrite one-
liners unless the owner explicitly selects a local patch-transfer workflow. Temporary runtime/log/
build files outside tracked source are unaffected by this rule.

## Focus and sufficiency

The project is a focused OPNsense addon. Prefer sufficient, maintainable implementation over
speculative completeness.

Priorities:

1. make approved functionality work correctly;
2. verify it on supported OPNsense;
3. keep documentation synchronized enough for reliable development/recovery;
4. retain future ideas without displacing current implementation work.

Keep UI stable unless implemented capability requires a change or the current interface demonstrably
blocks it.

## Runtime lifecycle ownership

Package lifecycle/runtime bootstrap changes are one architectural unit: hooks, setup backend, service
boundaries, configd integration, verification and documentation move together.

Runtime setup uses the single approved `setup.sh install` backend.

Package upgrade preserves service state:

- replacement `+PRE_INSTALL` stops an installed running service before file replacement;
- `+PRE_DEINSTALL` keeps fail-closed removal/upgrade behavior;
- new `+POST_INSTALL` starts replacement code only when the prior state requires it;
- a stopped service stays stopped;
- stop/setup failure aborts rather than being suppressed;
- incomplete/unknown initial state fails closed;
- successful setup captures and verifies service state before reporting ready.

## BLOB shorthand

- supported shorthand: `--blob=<name>`;
- resolves to `files/fake/<name>.bin`;
- `.bin` suffix omitted in strategy;
- no implicit alias table;
- native upstream `--blob=name:value` declarations containing `:` remain untouched;
- missing files are hard errors, never silently substituted.

## GUI maintenance backend

`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is the single approved backend for GUI
management of bol-van/zapret2 releases. Do not introduce a second installer.

Required user-visible capability: release discovery, installed version, update notice, release
selection, install/update/reinstall. Internal download/Git mechanics remain backend details.

The separately discussed additional BLOB repository is a deferred GUI item. Do not invent its URL,
manifest, directory layout, version scheme, integrity or update behavior before the owner supplies/
approves that technical contract.

## Repository artifact hygiene

Forbidden tracked artifacts include editor backups/rejects/ad-hoc patches/transport fragments such as:

`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, `*~`.

Historical engineering evidence may remain when it is an intentional record and clearly marked as
historical/superseded where needed.

`scripts/test-repository-hygiene.sh` is the repository-hygiene CI gate.

Normal steady-state branch authority is `main`; `recovery/base` is retained as a recovery reference.
Ordinary task/publication branches are temporary and removed after completion.

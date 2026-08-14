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

## Owner canon lock

The owner's newest unambiguous instruction, explicit project fact or explicitly confirmed decision is
current canon.

Once accepted:

- do not repeatedly reconfirm it merely because an old document/test disagrees;
- do not write later reports as if the decision is still open;
- reopen a factual claim only when the owner changes it or fresh direct reproducible evidence
  contradicts it;
- old documentation, historical CI assertions, previous chats and missing model memory are not
  counter-evidence.

Current locked examples: DNS is fixed; Model C is selected for normal production Stage 60.

When the owner says `зафиксируй`, `запиши это`, `record this` or equivalent:

1. write the new canon into canonical/current authority;
2. obtain a broad active-document map when multiple authorities may mention it;
3. inspect all active/current authority documents capable of contradicting it;
4. correct every active contradiction in the same logical docs change;
5. keep old statements only in clearly historical/superseded records.

A stale test/CI contract that asserts superseded canon is updated; current architecture is not bent
back toward the obsolete assertion.

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

A failed test proves only that its assertion failed. If it exposes a real same-scope defect, repair
that defect. If it exposes a stale assertion that contradicts newer owner canon, update the stale
contract instead of reverting current documentation/architecture.

Static verification, package archive verification and live OPNsense verification are distinct states.
A package built from uncommitted source is not a reproducible project baseline until source and
synchronized documentation are committed.

## Engineering Memory workflow

The documentation principle from `PROJECT_PRINCIPLES.md` is implemented as follows.

Before work:

- record objective;
- record implementation plan;
- record expected verification/acceptance;
- reconcile task with newest owner canon.

During work:

- record approved concepts immediately;
- record permanent rules/architecture changes immediately;
- record discoveries that change later work;
- when the owner changes/records canon, synchronize all affected active authority before stale text
  can drive later work.

Before GitHub publication:

- confirm documentation states what changes and why;
- confirm expected result/acceptance boundary;
- confirm the complete near-term and long-term plan;
- reconcile that plan with what implementation/testing learned;
- update changed priorities before publication;
- if the owner said `зафиксируй`, confirm the full active-authority reconciliation was performed;
- confirm every new durable principle is in `PROJECT_PRINCIPLES`.

After work:

- record what completed and what was verified;
- record failures/unresolved issues;
- update `START_HERE` and `PROJECT_STATE`;
- update patch/evidence/devlog record;
- update `ROADMAP` when priority/sequencing/future/deferred work changed;
- record the exact next stage;
- verify repository/temporary-branch cleanup.

Engineering Memory is maintained during development, not reconstructed only at the end.

## Findings versus Architecture Debt

A Finding is a confirmed implementation defect/inconsistency/obsolete or concrete operational risk.

Architecture Debt is an unresolved design question. It is not fixed in code before intended behavior
is approved.

Architecture Debt lifecycle:

`Open -> Discussion -> Decision -> Implementation -> Verification -> Documentation -> Closed`

A Finding must not be remediated while open Architecture Debt determines its intended behavior.

Once the owner explicitly closes an architecture question (for example, selecting Model C), old
Architecture Debt/experiment records cannot reopen it; remaining implementation differences are
transition debt/findings against the settled direction.

## Project-context preflight

Mandatory reading order is controlled by root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task specialists`.

Read the selected documents completely through EOF. Use broader historical reading for a broad audit
or when the current plan/evidence calls for it; do not use it as automatic startup ceremony.

Before GitHub mutation, also read `docs/GITHUB_PUBLICATION.md` and apply scope-first inventory from
the active operational-handoff decision.

A requested `зафиксируй`/canon reconciliation is a broad active-document consistency task by
definition when several active authority files can mention the subject.

## GitHub development convention

Ordinary flow:

1. connected GitHub plugin first;
2. current `main` SHA, metadata, newest canon/current plan and same-scope PR state;
3. create one logical task branch;
4. implement + synchronized documentation;
5. focused validation + complete diff review;
6. plan/canon reconciliation;
7. one Ready PR;
8. latest-head required CI;
9. same-scope repair in the same PR if needed;
10. exact-head squash merge using exact versioned subject;
11. verify `main`;
12. verify whether the temporary branch has useful unique work, preserve it if so, otherwise remove
    the branch and verify clean branch state;
13. package/live verification when applicable.

Additional branch/workflow/tag/release/tree inventory is performed when that operation actually needs
it. A pinned recursive tree is recommended for a genuine broad/cross-cutting investigation with
unknown path/call chain and for explicit broad active-document canon reconciliation, not for every
known-file patch.

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
diagnostics. Never ask the owner to reconfirm an already-settled owner fact/decision solely because
old documentation/test history disagrees.

## Local-only state exception

GitHub is authoritative for committed/pushed state only.

If relevant owner-local changes are uncommitted/unpushed:

1. stop before editing overlapping source;
2. ask the owner to commit/push or explicitly transfer archive/patch;
3. establish exact transferred baseline;
4. never reconstruct/overwrite unpublished state from memory.

## Owner-facing communication

Project status/results to the owner are written in clear Russian by default.

Internal GitHub/CI English is secondary evidence. Terms such as `latest head`, `Ready PR`,
`exact-head`, `squash`, `governance`, `hygiene`, or raw check names must not be left unexplained when
they are necessary. State the practical meaning in Russian: what passed/failed, whether the change is
already in `main`, and what happens next.

Routine successful CI/branch housekeeping should not distract the owner. Report it only when it
changes the project outcome or when a real blocking boundary remains.

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
Ordinary task/publication branches are temporary. After completion, preserve any useful unique work
first and otherwise remove them automatically. Routine cleanup is not delegated to the owner.

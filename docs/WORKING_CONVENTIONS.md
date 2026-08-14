# os-zapret2-restyle — Working conventions

This file answers: **how are permanent principles applied day to day?**

Canonical project principles: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md).
Canonical numbered documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).
This file must not create competing formulations of either.

## Stable identities

- project/repository/package: `os-zapret2-restyle`;
- Makefile `PLUGIN_NAME`: `zapret2-restyle`;
- MVC namespace: `OPNsense\Zapret`;
- internal service/configd namespace: `zapret`;
- project version source: `VERSION`;
- package revision suffix: `PLUGIN_REVISION`.

## Owner canon lock

The owner's newest unambiguous instruction/fact/confirmed decision is current canon. Apply the
“Суслик” rule from `DOCUMENTATION_RULES.md`: active contradictions are corrected, not negotiated back
into the owner's wording. `Зафиксируй` requires the complete active-document/CI sweep at the first
GitHub documentation opportunity.

## Change conventions

- use the exact current GitHub base commit;
- keep one logical scope per task branch/PR;
- same-scope work and repairs may coexist in that branch;
- include affected documentation/file-mode changes in the same scope;
- validate before publication and review complete diff;
- repair same-scope failures in the same PR;
- do not publish a failed/partially validated latest head.

## Version conventions

For `v0.4.2_14`, `4` is the second-component state line, `2` is the development stage and `_14` is the
patch/iteration.

- same-stage packaged source/behavior change -> keep `VERSION`, increment `_N` once;
- docs/governance/CI-only change -> change neither;
- genuine new development stage -> change third component and reset `_N` to `_1`;
- third-component transition alone -> no full release;
- second-component transition -> explicit owner authority, `_1`, state/archive rollover and full release;
- full release inside same second-component line -> exact current candidate; no release-only revision reset.

Before every `_N` increment reconcile `START_HERE`, master plan and `PROJECT_STATE` when current facts
changed.

## Testing conventions

Run syntax/static/focused tests appropriate to changed behavior. Never claim a test passed unless it
ran. Static verification, package archive verification and live verification are distinct states.
A failed test proves only its assertion failed; diagnose whether implementation or assertion is stale.

## Documentation workflow

Mandatory startup:

`AGENTS -> PROJECT_PRINCIPLES -> DOCUMENTATION_RULES -> START_HERE -> PROJECT_STATE -> task specialists`.

During work:

- keep `START_HERE` as the live `_N` handoff;
- flow completed durable facts into the current second-line `PROJECT_STATE`;
- keep the complete concise completed/current/future checklist in `ROADMAP`;
- keep richer line chronology in the current ledger;
- use deep records only for distinct execution/proof/rationale value;
- keep `INDEX` and archive links intact;
- avoid narrative duplication.

At a second-component rollover preserve final old `PROJECT_STATE` in the old line archive, initialize
new current state/ledger/handoff, update index/master plan, review README and complete the full release.
Older `v0.4.0` and earlier history is not retroactively rewritten.

## Findings versus architecture debt

A Finding is a confirmed implementation defect/inconsistency/obsolete behavior or concrete operational
risk. Architecture Debt is an unresolved design question and is not fixed before intended behavior is
approved.

Lifecycle:

`Open -> Discussion -> Decision -> Implementation -> Verification -> Documentation -> Closed`

Settled architecture cannot be reopened by old historical material alone.

## GitHub development convention

1. connected GitHub plugin first;
2. exact `main`, metadata, current handoff/state/plan and same-scope PR state;
3. one logical task branch;
4. implementation + synchronized documentation;
5. focused validation + complete diff review;
6. plan/canon reconciliation;
7. one Ready PR;
8. required latest-head CI;
9. same-scope repair in same PR;
10. exact-head squash merge with versioned subject;
11. verify `main`;
12. preserve unique work or remove temporary branch;
13. package/live verification when applicable.

Direct publication to `main`, history rewriting or published-tag movement requires explicit authority
and is never inferred from ordinary task authorization.

## Standing delivery authorization

An ordinary owner request to fix/add/change/implement/complete covers normal branch, Ready PR, checks,
same-scope repair, squash merge, main verification and cleanup. Explicit stopping points override it.

Stop for owner direction on material product ambiguity, unpublished overlapping owner-local state,
unresolvable required checks, unavailable GitHub authority/plugin, destructive changes to pre-existing
remote data, history rewrite/direct-main publication, owner-only live evidence, or any unapproved
second-component version transition.

## Local-only state exception

GitHub is authoritative for committed/pushed state only. Never reconstruct or overwrite relevant
unpublished owner-local changes from memory.

## Owner-facing communication

Project status/results are clear Russian by default. Explain useful internal English GitHub/CI labels
in Russian. Routine successful cleanup is handled silently.

## OPNsense command presentation

Default owner console is root `csh`. Keep read-only checks separate from state changes. Enter explicit
`sh`/`/bin/sh` for POSIX-only constructs and return with `exit`.

## Focus and sufficiency

Priorities:

1. make approved functionality work correctly;
2. verify it on supported OPNsense;
3. keep documentation synchronized for zero-memory recovery;
4. retain every known future intention in the concise master plan without displacing current work.

Prefer sufficient maintainable implementation over speculative completeness.

## Runtime lifecycle ownership

Package lifecycle/runtime bootstrap changes are one architectural unit: hooks, setup backend, service
boundaries, configd integration, verification and documentation move together.

Runtime setup uses the approved `setup.sh install` backend. Package upgrade preserves service state:
running returns running; stopped stays stopped; incomplete/unknown state fails closed; successful setup
verifies service state before reporting ready.

## BLOB shorthand

- supported shorthand: `--blob=<name>`;
- resolves to `files/fake/<name>.bin`;
- `.bin` suffix omitted in strategy;
- no implicit alias table;
- native upstream `--blob=name:value` declarations containing `:` remain untouched;
- missing files are hard errors, never silently substituted.

## GUI maintenance backend

`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is the approved backend for GUI management of
bol-van/zapret2 releases. Required capability includes release discovery, installed version, update
notice, release selection and install/update/reinstall.

The separately discussed additional BLOB repository remains deferred until its technical contract is
supplied/approved; do not invent URL/manifest/layout/version/integrity/update behavior.

## Repository artifact hygiene

Forbidden tracked artifacts include editor backups/rejects/ad-hoc patches/transport fragments such as
`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, `*~`.

Historical engineering proof may remain when intentional and clearly historical/superseded.
Normal steady-state branches are `main` plus retained recovery references; ordinary task/publication
branches are temporary after useful work is preserved.

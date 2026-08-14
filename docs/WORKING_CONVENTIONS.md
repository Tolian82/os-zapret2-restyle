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

Allowed classifications: `OK`, `broken`, `unused`, `duplicate`, `inherited`, `requires live test`.
The word `zapret` alone is not evidence of obsolete inheritance.

`docs/AUDIT.md` is the authoritative register for audit scope, findings, evidence, live-test needs,
remediation and closure. Every non-OK finding requires a unique ID, exact affected chain, evidence/
impact, verification/remediation plan, acceptance criteria, required docs updates and status.

A broken chain is recorded before it is fixed. Resolved findings remain as history. Audits are
complete only when affected current-state/roadmap/decision/specialist documentation is synchronized.
Use existing evidence as the starting point rather than repeating an audit because memory was lost.

## Change conventions

- use the exact current GitHub base commit;
- keep one logical scope per task branch/PR;
- same-scope work and repairs may coexist in that branch;
- include affected documentation/file-mode changes in the same logical scope;
- validate before publication and review the complete diff;
- repair same-scope failures in the same PR;
- do not publish a failed/partially validated latest head.

Package metadata:

- packaged source/behavior change with unchanged `VERSION`: increment `PLUGIN_REVISION` once;
- docs/governance/CI-only change: change neither;
- explicitly authorized semantic release: change `VERSION`, reset revision to `1`.

## Testing conventions

Run syntax/static/focused tests appropriate to changed behavior. For a local checkout inspect at least
`git status --short`, `git diff --check`, `git diff --stat` and complete relevant diff.

Perform focused live OPNsense tests when changed behavior needs appliance evidence. Never claim a test
passed unless it ran. Static verification, package archive verification and live verification are
distinct states.

A failed test proves only that its assertion failed. Repair a real same-scope defect; update a stale
assertion that contradicts newer owner canon rather than reverting current architecture/docs.

## Engineering Memory workflow

Documentation follows the three-level model from `PROJECT_PRINCIPLES.md`.

### Before work

- Level 1 only by default: `AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task docs`;
- read the current minor-line ledger only if richer current-line context is needed;
- read archives/deep records only for a concrete historical dependency, investigation or proof;
- record/reconcile objective, implementation plan and expected acceptance in the appropriate primary
  current home.

### During work

- record approved concepts/permanent rules where they belong;
- record discoveries that materially change later work;
- keep richer chronology in the current semantic-minor ledger;
- create/update patch/devlog/evidence/decision records only when they add distinct contract,
  execution, proof or rationale value;
- when owner canon changes, synchronize all affected active authority before stale text can drive work.

### Before GitHub publication

- confirm current facts, current task and current/future plan are synchronized;
- confirm Level 1 remains compact and does not copy detailed history;
- confirm `INDEX` routes to the current ledger, completed version archives and deep evidence;
- if the owner said `зафиксируй`, confirm full active-authority reconciliation;
- confirm every new durable principle is in `PROJECT_PRINCIPLES`.

### After work

- record current factual changes in `PROJECT_STATE` only when current state changed;
- update exact handoff/task in `START_HERE` only when the recovery boundary changed;
- append useful richer chronology to the current minor-line ledger;
- update `ROADMAP` only when current/future priority or sequencing changed;
- add detailed patch/devlog/evidence records only when they contribute non-duplicate information;
- record exact next stage and verify repository/temporary-branch cleanup.

Engineering Memory is maintained during development, but **duplication is not preservation**. Preserve
history by durable links and primary homes rather than copying the same narrative into every active
document.

### Version-line rollover

On the first release in a new semantic minor line, automatically finalize the old current ledger into
`docs/history/archive/vX.Y.x.md`, initialize the new current ledger, update `INDEX` and Level 1, and
preserve all original deep records. Current architecture/contracts and permanent principles do not
become historical merely because the version line changed.

## Findings versus Architecture Debt

A Finding is a confirmed implementation defect/inconsistency/obsolete or concrete operational risk.
Architecture Debt is an unresolved design question and is not fixed before intended behavior is
approved.

Architecture Debt lifecycle:

`Open -> Discussion -> Decision -> Implementation -> Verification -> Documentation -> Closed`

Once the owner explicitly closes an architecture question, old debt/experiment records cannot reopen
it; remaining implementation differences are transition debt/findings against the settled direction.

## Project-context preflight

Mandatory order is controlled by root `AGENTS.md`:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task specialists`.

Read broader history only when the current task needs it. Before GitHub mutation also read
`docs/GITHUB_PUBLICATION.md` and apply scope-first inventory. A requested owner-canon reconciliation is
a broad active-document consistency task when several active authorities can mention the subject.

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
12. preserve useful unique branch work or remove temporary branch and verify clean state;
13. package/live verification when applicable.

Additional branch/workflow/tag/release/tree inventory is performed only when needed. The GitHub plugin
is the mandatory first repository interface. A narrow fallback is allowed only for an exact confirmed
missing function while the plugin responds. Plugin unavailability stops GitHub work.

Direct publication to `main` requires explicit owner authority and must never rewrite history.

## Standing delivery authorization

A request to fix/add/change/implement/complete an ordinary task authorizes normal task branch, Ready
PR, checks, same-scope repair, squash merge, main verification and cleanup. Explicit stopping points
override the default.

Stop for owner direction only on material product/architecture ambiguity, relevant unpublished owner-
local state, unresolvable required checks, unavailable GitHub plugin/authority, destructive changes to
pre-existing user remote data, history rewriting/direct-main publication, or owner-only live evidence.

## Local-only state exception

GitHub is authoritative for committed/pushed state only. If relevant owner-local changes are
uncommitted/unpushed, stop overlapping edits, establish exact transferred baseline, and never
reconstruct/overwrite unpublished state from memory.

## Owner-facing communication

Project status/results to the owner are clear Russian by default. Explain any materially useful
internal GitHub/CI English in Russian. Routine successful CI/branch housekeeping should not distract
the owner.

## OPNsense command presentation

Default owner console is root `csh`. Keep read-only checks separate from state changes. Enter explicit
`sh`/`/bin/sh` for POSIX-only constructs and return with `exit`; subsequent commands must be csh-valid.
Do not mutate tracked repository files from OPNsense with editor/rewrite one-liners unless owner
explicitly selects a local patch-transfer workflow.

## Focus and sufficiency

Priorities:

1. make approved functionality work correctly;
2. verify it on supported OPNsense;
3. keep documentation synchronized for reliable recovery;
4. retain future ideas without displacing current implementation work.

Prefer sufficient maintainable implementation over speculative completeness. Keep UI stable unless
implemented capability requires a change or current interface demonstrably blocks it.

## Runtime lifecycle ownership

Package lifecycle/runtime bootstrap changes are one architectural unit: hooks, setup backend, service
boundaries, configd integration, verification and documentation move together.

Runtime setup uses the single approved `setup.sh install` backend. Package upgrade preserves service
state: running replacement is stopped before file replacement and restored as required; stopped stays
stopped; stop/setup failure and incomplete/unknown initial state fail closed; successful setup verifies
service state before reporting ready.

## BLOB shorthand

- supported shorthand: `--blob=<name>`;
- resolves to `files/fake/<name>.bin`;
- `.bin` suffix omitted in strategy;
- no implicit alias table;
- native upstream `--blob=name:value` declarations containing `:` remain untouched;
- missing files are hard errors, never silently substituted.

## GUI maintenance backend

`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` is the single approved backend for GUI
management of bol-van/zapret2 releases. Required user-visible capability includes release discovery,
installed version, update notice, release selection and install/update/reinstall.

The separately discussed additional BLOB repository is deferred until its technical contract is
supplied/approved; do not invent its URL/manifest/layout/version/integrity/update behavior.

## Repository artifact hygiene

Forbidden tracked artifacts include editor backups/rejects/ad-hoc patches/transport fragments such as
`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, `*~`.

Historical engineering evidence may remain when intentional and clearly marked historical/superseded
where needed. `scripts/test-repository-hygiene.sh` is the CI gate.

Normal steady-state branch authority is `main`; `recovery/base` is retained as recovery reference.
Ordinary task/publication branches are temporary and are removed after useful unique work is preserved.

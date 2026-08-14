# os-zapret2-restyle — Working conventions

This file answers: **How are permanent principles applied day to day?**

Canonical principles live only in `docs/PROJECT_PRINCIPLES.md`.

## Stable identities

- project/repository/package: `os-zapret2-restyle`;
- Makefile `PLUGIN_NAME`: `zapret2-restyle`;
- MVC namespace: `OPNsense\Zapret`;
- internal service/configd namespace: `zapret`;
- semantic version source: `VERSION`.

## Owner canon workflow

Treat the owner's newest unambiguous instruction/fact/confirmed decision as current canon.

Once accepted:

- do not repeatedly reconfirm it;
- do not write later reports as if it is still undecided;
- do not use old docs/tests/roadmap/history as counter-authority;
- reopen a factual claim only on owner change or fresh direct reproducible evidence.

If the owner says `зафиксируй` / `запиши это` / equivalent:

1. write the canon into the appropriate canonical/current docs;
2. obtain a broad active-document map when multiple authorities may mention it;
3. inspect all active/current authority files that could contradict it;
4. correct every active contradiction in the same docs change;
5. preserve old statements only in clearly historical/superseded records.

A new chat or missing model memory is never grounds to reopen a settled item.

## Active vs historical documentation

Current authority files describe current state/architecture/plan/procedure. Historical audits,
decisions, patch records, devlogs and evidence may truthfully describe superseded states.

Historical statements are allowed to differ from current canon only when their role/status makes it
clear that they are history. An active architecture/current-state file must never keep an obsolete
choice merely for chronology.

## Change conventions

- use exact current GitHub base commit;
- one logical scope per task branch/PR;
- same-scope repair stays in that PR;
- include affected documentation in same logical scope;
- validate before publication;
- review complete diff;
- do not publish a failed latest head.

Package metadata:

- packaged source/behavior change with unchanged `VERSION`: increment `PLUGIN_REVISION` once;
- docs/governance/CI-only change: change neither;
- explicitly authorized semantic release: change `VERSION`, reset revision to `1`.

## Testing / stale-contract convention

Never claim a test passed unless it ran.

A failed test is evidence about the assertion it checks, not automatic authority over product intent.
If the failure shows a real same-scope defect, repair it. If it shows that the test asserts superseded
owner canon, update the stale test/contract instead of reverting current docs/architecture.

Static verification, package verification and live OPNsense verification are distinct.

## Engineering Memory workflow

Before work:

- objective;
- implementation plan;
- expected verification/acceptance;
- newest owner canon relevant to scope.

During work:

- record new durable decisions immediately;
- record discoveries that change later work;
- if owner canon changes, synchronize affected active docs before old text can drive subsequent work.

Before publication:

- most recent completed logical work;
- what changes and why;
- intended effect/acceptance;
- exact next step;
- complete near-/long-term/deferred plan;
- full active-doc reconciliation when the owner said `зафиксируй`;
- new durable principles in `PROJECT_PRINCIPLES`.

After work:

- record what completed/verified/failed;
- update current handoff/state/roadmap as applicable;
- record patch/devlog/evidence;
- clean temporary repository state.

## Project-context preflight

Mandatory reading order:

`AGENTS -> PROJECT_PRINCIPLES -> START_HERE -> PROJECT_STATE -> task specialists`.

Before GitHub mutation also read `docs/GITHUB_PUBLICATION.md`.

A broad recursive tree/document sweep is required for genuine broad/cross-cutting audits and explicit
canon/documentation reconciliation, not for every known-file code patch.

## GitHub development convention

Normal flow:

1. GitHub plugin first;
2. verify main SHA, metadata, canon/plan, relevant PRs;
3. task branch;
4. implementation + synchronized documentation;
5. validation + full diff review;
6. Ready PR;
7. latest-head required checks;
8. same-scope repair if needed;
9. exact-head squash merge;
10. verify `main`;
11. verify/preserve any useful unique branch content, then remove obsolete temporary branch;
12. package/live verification when applicable.

## Repository hygiene

Routine cleanup is part of the task and normally silent.

Forbidden tracked transport/editor artifacts include:

`*.orig`, `*.rej`, `*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, `*~`.

Historical engineering evidence may remain when intentional and clearly identified.

Normal steady-state branch authority is `main`; intentionally documented recovery references may
remain. Ordinary task/publication branches are temporary and removed after completion after checking
for useful unique work.

Do not push routine cleanup back to the owner. Escalate only a real permission/tool boundary that
prevents safe completion.

## Owner-facing communication

Owner-facing project updates/results are clear Russian by default.

Internal words such as `latest head`, `Ready PR`, `exact-head`, `squash`, `governance`, `hygiene` or
raw CI check names are not a substitute for a Russian explanation. If shown for evidence, explain the
practical meaning immediately.

Prefer concise outcomes:

- what was changed;
- what was found;
- whether checks passed;
- whether change is already in `main`;
- what the next meaningful project action is.

Do not burden the owner with routine branch/CI housekeeping details that were successfully handled.

## OPNsense command presentation

Owner console target is root `csh`.

- separate read-only checks from state-changing actions;
- do not silently assume bash/POSIX syntax;
- if POSIX syntax is needed, explicitly enter `sh`/`/bin/sh` and return with `exit`;
- commands after `exit` must again be csh-valid.

Do not mutate tracked repository source directly from the OPNsense console unless the owner explicitly
selects a local patch-transfer workflow.

## Audit conventions

Audit inherited references before removal when audit scope applies. Findings remain historical after
resolution. Existing audit evidence is the starting point; missing conversational memory does not
justify repeating already-closed audit work.

## Runtime lifecycle ownership

All Zapret2 lifecycle mutations remain serialized/fail-closed. Runtime setup uses the single approved
`setup.sh install` backend. Package upgrade preserves initial running/stopped service state and aborts
on incomplete/unknown or unsuccessful lifecycle/setup verification.

## BLOB shorthand

- supported shorthand: `--blob=<name>`;
- resolves to `files/fake/<name>.bin`;
- `.bin` suffix omitted in strategy;
- no implicit alias table;
- native upstream `--blob=name:value` containing `:` remains untouched;
- missing files are hard errors.

## GUI maintenance backend

`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh` remains the single approved backend for GUI
management of bol-van/zapret2 releases. Do not introduce a second installer.

The separately discussed additional BLOB repository remains deferred until the owner supplies/approves
its technical contract.

# os-zapret2-restyle — Development guide

This file answers: **how do we develop this project?**

Permanent principles: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md).
Numbered documentation rules: [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md).
Current revision: [`START_HERE.md`](START_HERE.md).
Current second-component state: [`PROJECT_STATE.md`](PROJECT_STATE.md).
Master plan: [`ROADMAP.md`](ROADMAP.md).
GitHub delivery: [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md).

Do not store competing current state or documentation policy here.

## 1. Restore context with the smallest sufficient read set

Mandatory Level 1:

`AGENTS -> PROJECT_PRINCIPLES -> DOCUMENTATION_RULES -> START_HERE -> PROJECT_STATE -> current-task specialists`.

Then use the current `history/current/vX.Y.x.md` ledger only for richer current-line chronology and
Level-3 archives/deep records only for a concrete historical dependency, investigation, rationale or
proof.

## 2. Establish exact baseline

Use the connected GitHub plugin first. Verify exact `main`, `VERSION`, `PLUGIN_REVISION`, current
handoff/state/master plan, same-scope PR state and relevant unpublished owner-local state if reported.

## 3. Define one logical work package

Before implementation documentation must make clear:

1. what changes and why;
2. intended effect/acceptance;
3. exact immediate next action after the patch;
4. master-plan progress/future direction affected by it;
5. any new owner canon or numbered documentation rule.

Use primary homes from `DOCUMENTATION_RULES.md`; do not duplicate one long narrative across Level 1,
roadmap, ledger, patch and devlog.

## 4. Apply version roles

For `v0.4.2_14`:

- `4` = current second-component state line;
- `2` = current development stage;
- `_14` = exact patch/iteration.

Use these transitions:

- ordinary same-stage packaged source patch -> keep `VERSION`, increment `_N` once;
- docs/governance/CI-only patch -> change neither value;
- genuine new development stage -> change third component, reset `_N` to `_1`, no automatic release;
- owner-authorized second-component transition -> reset `_N` to `_1`, archive old line/state and full release;
- owner-requested full release inside same line -> release exact current candidate; do not reset `_N`
  merely because it is a release.

Before every `_N` increment reconcile `START_HERE`, master plan and `PROJECT_STATE` when facts changed.

## 5. Audit only when scope requires it

Audit when owner requests it, the master plan schedules it, inherited behavior must be classified
before removal/refactor, new reproducible evidence has unknown/cross-cutting scope, or source/current
architecture cannot be reconciled narrowly. Do not repeat an audit merely because a new chat lacks
memory.

## 6. Implement one logical scope

- smallest maintainable change satisfying approved intent;
- preserve working behavior outside scope;
- affected documentation belongs to the same logical change;
- generated runtime/build output stays out of source control;
- same-scope repairs stay in the same branch/PR.

## 7. Validate

Run focused syntax/static/unit/contract tests and broader matrix required by changed risk. Review the
complete diff. Never claim a test passed unless it ran. Diagnose CI failure from exact evidence before
changing source/workflow. Update stale assertions instead of reversing current canon.

## 8. Reconcile documentation before publication

Before Ready PR and again before merge verify:

- `START_HERE` describes the exact current revision, recent work/effect, immediate continuation;
- completed durable facts have flowed into the current second-line `PROJECT_STATE`;
- `PROJECT_STATE` ends with links to all completed line archives;
- `ROADMAP` contains every known future intention and the compact completed trajectory;
- `INDEX` still reaches all current/archive/deep stores;
- owner `зафиксируй` received the complete “Суслик” sweep;
- new documentation rules are numbered in `DOCUMENTATION_RULES.md`;
- Level 1 remains readable and compact.

Acceptance question: **could a future session with no chat/model memory resume correctly without first
rediscovering the repository?**

## 9. Second-component rollover

When the owner explicitly authorizes a second-component change, for example `v0.4.x -> v0.5.x`:

1. reconcile final old `PROJECT_STATE`;
2. finish the old current-line ledger;
3. create/freeze `history/archive/v0.4.x.md` containing the compact map plus final state snapshot;
4. preserve all original detailed records;
5. initialize `history/current/v0.5.x.md`;
6. initialize `PROJECT_STATE` for `v0.5.x` and retain links to every completed archive;
7. initialize `START_HERE` for the new exact revision;
8. update `ROADMAP`, `INDEX` and lifetime path;
9. perform complete README review;
10. complete the full project release.

Do not retroactively rewrite `v0.4.0` or older archive history into the new state-snapshot scheme.

## 10. Deliver through GitHub

Follow `GITHUB_PUBLICATION.md`:

`task branch -> implementation + docs -> validation -> Ready PR -> required checks -> exact-head squash merge -> verify main -> clean temporary branch`.

Standing owner authorization covers normal branch/PR/check/repair/merge/verification/cleanup unless the
current request explicitly stops earlier.

## 11. Package / live verification

Build/live gates follow changed risk. Owner requests for installable testing bytes mean persistent
GitHub `.pkg`; Actions artifacts/local files are build evidence only. Full release additionally
publishes the current exact candidate through the Pages/pkg repository and OPNsense Web channel.

## 12. OPNsense / owner communication

Owner console target is root `csh`; enter explicit `sh`/`/bin/sh` for POSIX-only syntax and return with
`exit`. Owner-facing status is clear Russian; technical English is translated/explained when shown.

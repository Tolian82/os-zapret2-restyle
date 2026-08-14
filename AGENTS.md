MANDATORY: Use the connected GitHub plugin first for every repository operation. If the plugin is unavailable or cannot provide required authoritative state, stop GitHub work and report the boundary.

# AGENTS.md

This is the mandatory repository entrypoint. Do not reconstruct project state from chat/model memory.

## Mandatory startup order — Level 1

Read completely through EOF:

1. `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md` — permanent project/development canon;
3. `docs/DOCUMENTATION_RULES.md` — numbered canonical documentation rules;
4. `docs/START_HERE.md` — exact current package-revision handoff and immediate continuation;
5. `docs/PROJECT_STATE.md` — current facts for the active second-numeric-component line;
6. only the specialist documents named by the current task in `START_HERE.md`.

`docs/ROADMAP.md` is the concise master development plan and is linked at the top of `START_HERE.md`.
`docs/INDEX.md` is the navigation/integrity map. Do not routinely load historical devlogs, patch
records, proof or archives. The active `history/current/vX.Y.x.md` ledger is Level 2 and is read only
when richer current-line chronology is needed.

If a selected mandatory document is truncated/paginated, continue to EOF before acting. If required
authority cannot be read completely, stop before mutation rather than guess.

## Canon and documentation

The owner's newest unambiguous instruction/fact/confirmed decision supersedes conflicting older active
documentation, tests and plans. Apply `PROJECT_PRINCIPLES.md` and the numbered rules in
`DOCUMENTATION_RULES.md` directly.

The permanent owner-canon “Суслик” rule applies: an active contradiction is a documentation defect.
When the owner says `зафиксируй` / equivalent, the first GitHub documentation change must record the
canon and reconcile every active/current authority and CI contract capable of contradicting it.
Historical material may keep the old state only when clearly historical/superseded.

Every substantive GitHub delivery must leave a zero-memory recovery checkpoint. Detailed chronology
belongs in the current-line ledger and deep records rather than being copied into Level 1.

## Version/documentation hierarchy

For candidate `v0.4.2_14`:

- second numeric component `4` => current project-state line `v0.4.x` and `PROJECT_STATE.md` scope;
- third numeric component `2` => current development stage/task inside that line;
- package revision suffix `_14` => exact patch/iteration and `START_HERE.md` handoff boundary.

A second-component change is never assistant-initiated and always requires owner authority plus a full
release. A third-component-only stage transition does not itself mean a release and resets package
revision to `_1`. A full release may occur without changing the second component and may use the
current `_N` candidate.

## Scope-first preflight

Before mutation verify through the GitHub plugin:

- exact current `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- current documented task reconciled with the newest owner instruction;
- current `START_HERE` / `PROJECT_STATE` / master-plan consistency;
- same-scope/relevant open PR state;
- plugin availability for the required operation.

Expand inventory only when scope needs it: CI logs for CI failure, tags/assets for publication,
branches for cleanup/recovery, protection/permissions when relevant, recursive tree for a genuine
broad investigation, and active-document sweep for owner-canon reconciliation.

## GitHub delivery

Before GitHub mutation read `docs/GITHUB_PUBLICATION.md` completely. Ordinary implementation flow:

`one logical scope -> task branch -> implementation + synchronized docs -> validation -> Ready PR -> required checks -> exact-head squash merge -> verify main -> clean temporary branch`.

- same-scope repairs stay in the same PR;
- Draft only for intentional WIP;
- PR/branch commit/final squash subjects begin `v<VERSION>_<PLUGIN_REVISION>:`;
- docs/governance/CI-only changes do not change package metadata;
- every revision increment reconciles `START_HERE`, the master plan and `PROJECT_STATE` when facts changed;
- never force-update `main`, move published tags or rewrite published history;
- diagnose failed checks from exact evidence before changing source;
- external infrastructure failure causes no speculative source change;
- stale tests are corrected instead of reversing current canon;
- preserve useful unique branch work before routine cleanup.

Standing owner authorization for `fix/add/change/implement/complete` covers branch, PR, checks,
same-scope repair, squash merge, main verification and cleanup. Explicit stopping points override it.

## Package / release boundary

- ordinary packaged source change in the same stage: keep `VERSION`, increment `PLUGIN_REVISION` once;
- new third-component development stage: change third component and reset `PLUGIN_REVISION=1`;
- docs/governance/CI-only change: change neither;
- testing package: persistent GitHub `.pkg`, no full release/Pages/pkg-repo promotion;
- full release: explicit owner release authority, exact current candidate, full README review, semantic
  tag, GitHub release assets/checksum and verified Pages/pkg-repository publication ready for OPNsense
  Web installation;
- second-component change: explicit owner authority, archive rollover and mandatory full release.

## Owner-facing communication / OPNsense

Project status/results are clear Russian by default. Translate or explain internal English GitHub/CI
terms instead of making the owner decode them. Routine cleanup is handled silently.

Owner console commands target root `csh`. POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and
return with `exit`.

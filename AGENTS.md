MANDATORY: Use the connected GitHub plugin first for every repository operation. If the plugin is unavailable or cannot provide required authoritative state, stop GitHub work and report the boundary.

# AGENTS.md

This is the mandatory repository entrypoint. Do not reconstruct project state from chat/model memory.

## Mandatory startup order — Level 1

Read completely through EOF:

1. `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md` — permanent project canon;
3. `docs/START_HERE.md` — compact operational handoff, short lifetime path and exact next task;
4. `docs/PROJECT_STATE.md` — current facts only;
5. only the specialist documents named by the current task in `START_HERE.md`.

Do **not** routinely load historical devlogs, patch records, evidence or archives. Use
`docs/INDEX.md` to navigate them only when the current task needs history, proof or older rationale.
The active version-line ledger is Level 2 and is read only when more current-line chronology is needed.

If a required selected document is truncated/paginated, continue to EOF before acting. If required
authority cannot be read completely, stop before mutation rather than guess.

## Canon and documentation

`docs/PROJECT_PRINCIPLES.md` is the single cumulative authority for permanent principles. Apply its
owner-canon, stale-contract, zero-memory, three-level-memory, release and archive-rotation rules
directly.

The newest unambiguous owner instruction/fact/confirmed decision supersedes conflicting older active
docs/tests/plans. Once accepted, do not reconfirm it merely because older material disagrees. Reopen
only if the owner changes it or fresh direct reproducible evidence contradicts a factual claim.

When the owner says `зафиксируй` / equivalent, the first GitHub documentation change must record the
canon and reconcile every active/current authority capable of contradicting it. Historical material
may keep the old state only when clearly historical/superseded.

Every substantive GitHub delivery must leave a zero-memory recovery checkpoint, but detailed
chronology belongs in the current-line ledger/deep records rather than being copied into mandatory
Level-1 files.

## Scope-first preflight

Before mutation verify through the GitHub plugin:

- exact current `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- current documented task reconciled with the newest owner instruction;
- same-scope/relevant open PR state;
- plugin availability for the required operation.

Expand inventory only when scope needs it: CI logs for CI failure, tags/assets for publication,
branches for cleanup/recovery, protection/permissions when relevant, recursive tree for a genuine
broad investigation, and active-document sweep for owner canon reconciliation.

## GitHub delivery

Before GitHub mutation read `docs/GITHUB_PUBLICATION.md` completely. Ordinary implementation flow:

`one logical scope -> task branch -> implementation + synchronized docs -> focused validation -> Ready PR -> required checks -> exact-head squash merge -> verify main -> clean temporary branch`.

- same-scope repairs stay in the same PR;
- Draft only for intentional WIP;
- PR/branch commit/final squash subjects begin `v<VERSION>_<PLUGIN_REVISION>:`;
- docs/governance/CI-only changes do not change package metadata;
- never force-update `main`, move published tags or rewrite published history;
- diagnose failed checks from exact evidence before changing source;
- external infrastructure failure causes no speculative source change;
- stale tests are corrected instead of reversing current canon;
- preserve useful unique branch work before routine cleanup.

Standing owner authorization for `fix/add/change/implement/complete` covers branch, PR, checks,
same-scope repair, squash merge, main verification and cleanup.

A change to the **second numeric component** of `VERSION` — the `4` in `0.4.x`, for example
`v0.4.x -> v0.5.x` — is never assistant-initiated. It requires an explicit owner version/transition
instruction or separate owner approval of a proposal. Once authorized it always includes the complete
full-release + documentation-rollover procedure. A full release may also be explicitly requested
without changing that second component.

Stop for owner input only on material product ambiguity, relevant unpublished owner-local state,
owner-only live evidence, credentials/protected authority, destructive changes to pre-existing user
remote data, history rewrite/direct-main publication, unresolvable required-check failure or plugin
unavailability.

## Package boundary

- packaged source change with unchanged `VERSION`: increment `PLUGIN_REVISION` once;
- docs/governance/CI-only change: change neither;
- testing package: persistent GitHub `.pkg`, no full release/Pages/pkg-repo promotion;
- full release: explicit owner release + VERSION authority, revision reset to `1`, full README review,
  GitHub release assets and verified Pages/pkg-repository publication ready for OPNsense Web install.

## Owner-facing communication / OPNsense

Project status/results are clear Russian by default. Translate/explain internal GitHub/CI labels when
shown. Routine cleanup is handled silently.

Owner console commands target root `csh`. POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and
return with `exit`.

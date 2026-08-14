MANDATORY: Use the connected GitHub plugin first for every repository operation. If the plugin is unavailable or cannot provide the authoritative state required to proceed safely, stop GitHub work and report the boundary.

# AGENTS.md

This file is the mandatory entrypoint. Do not reconstruct project state from chat history or model memory.

## Mandatory startup order

For every new or resumed project context, read completely through EOF in this order:

1. `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md` — canonical permanent principles that must always be in context;
3. `docs/START_HERE.md` — current operational handoff;
4. `docs/PROJECT_STATE.md` — current repository/product state;
5. specialist documents named by the current documented task.

Use `docs/INDEX.md` only as navigation when additional specialist/history material is required.

Historical audits, decisions, patches, devlogs and evidence remain authoritative project records. Read them when the current plan, owner request, new defect or specialist scope requires them. Do not automatically reread the complete history merely because a new chat started.

If a selected required document is truncated, paginated, clamped or range-limited, continue until EOF before acting. If a required authority cannot be read completely, stop before mutation/source change/package delivery rather than guessing.

## Documentation authority

`docs/PROJECT_PRINCIPLES.md` is the single canonical set of permanent project principles. Do not create competing formulations of those principles in current-state or specialist documents.

Before any GitHub delivery, verify that the documentation contract in `PROJECT_PRINCIPLES.md` is satisfied: the repository must state what changes and why, the expected result/acceptance boundary, and the complete near-term and long-term plan. Reconcile the plan immediately before publication and update it first if implementation/testing changed it.

## Scope-first repository preflight

Before mutation always verify through the GitHub plugin:

- exact current `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- same-scope/relevant open PR state;
- current documented task/plan;
- plugin availability for the required operation.

Expand the inventory only when the operation needs it:

- workflows/runs/job logs for CI debugging or current-PR checks;
- artifacts/tags/releases/assets for package publication or release work;
- complete branch inventory for cleanup/collision/recovery/hygiene work;
- rulesets/protection/permissions when relevant;
- recursive repository tree for a genuine broad audit/cross-cutting investigation whose file/call path is unknown.

A known-file task already named by `START_HERE.md` does not require a full repository/GitHub inventory before implementation.

Authority: `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`.

## GitHub delivery mechanics

For any GitHub mutation, read `docs/GITHUB_PUBLICATION.md` completely immediately before mutation. Package/release work also uses the current package-delivery and release decisions listed there.

Ordinary implementation flow:

one logical scope → one task branch + Ready PR → focused validation → latest-head required checks → exact-head squash merge → verify `main` → clean temporary branch.

Rules:

- same-scope repairs stay in the same PR;
- Draft is only for intentional WIP;
- every PR title, branch commit subject and final squash subject begins with the exact current package-candidate prefix `v<VERSION>_<PLUGIN_REVISION>:`;
- docs/governance/CI-only changes do not change package metadata;
- never force-update `main`, move a published tag or rewrite published history;
- read exact failed-job evidence before changing source/workflow/runner;
- external infrastructure failure causes no speculative source change.

## Request scope / standing authority

- `analyse`, `diagnose`, `review`, `audit`, `explain`: inspect/report only unless the owner also asks for changes;
- `fix`, `add`, `change`, `implement`, `complete`: perform the ordinary branch → Ready PR → checks → squash merge → verification cycle;
- package/test-package/installable-patch request: complete packaged source work as needed and persist the deterministic `.pkg` on GitHub;
- explicit candidate publication: publish only that testing package, no Pages/pkg-repository promotion;
- explicit new semantic release: perform the authorized full release pipeline.

Do not ask for routine branch names, commit wording, PR text, CI inspection, same-scope repair, squash merge, cleanup or a second testing-package publication confirmation when the scope already authorizes them.

Stop for owner input only on material product ambiguity, relevant unpublished owner-local state, unavailable owner-only live evidence, credentials/protected authority, destructive changes to user/pre-existing remote data, history rewrite/direct-main publication, unresolvable required-check failure, or GitHub-plugin unavailability.

## Package boundary

- ordinary packaged source change: keep `VERSION`, increment `PLUGIN_REVISION` once;
- documentation/governance/CI-only change: change neither;
- testing-package publication: no semantic VERSION change, no Pages/pkg repo;
- full project release: explicit VERSION authority, revision reset to `1`, full release pipeline;
- owner-facing package delivery is a persistent GitHub `.pkg`; Actions artifacts/local files are build evidence only.

## OPNsense command rule

Owner console commands target root `csh`. POSIX-only syntax must be explicitly placed inside `sh`/`/bin/sh` and returned with `exit`.

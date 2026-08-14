MANDATORY: Use the connected GitHub plugin first for every repository operation. If the plugin is unavailable or cannot provide the authoritative state required to proceed safely, stop GitHub work and report the boundary.

# AGENTS.md

This file is the mandatory entrypoint. Do not reconstruct project state from chat history or model memory.

## Mandatory startup order

For every new or resumed project context, read completely through EOF in this order:

1. `AGENTS.md`;
2. `docs/PROJECT_PRINCIPLES.md` — canonical permanent principles that must always be in context;
3. `docs/START_HERE.md` — current operational handoff, including the most recent completed logical work;
4. `docs/PROJECT_STATE.md` — current repository/product/environment state;
5. specialist documents named by the current documented task.

Use `docs/INDEX.md` only as navigation when additional specialist/history material is required.

Historical audits, decisions, patches, devlogs and evidence remain authoritative project records only for the state/time they describe. Read them when the current plan, owner request, new defect or specialist scope requires them. `START_HERE.md` must point to the latest relevant patch/devlog/evidence record so recent work is never lost merely because the full historical log is not reread on every session.

If a selected required document is truncated, paginated, clamped or range-limited, continue until EOF before acting. If a required authority cannot be read completely, stop before mutation/source change/package delivery rather than guessing.

## Owner canon lock

The owner's newest unambiguous instruction, explicit project fact or explicitly confirmed decision is current project canon and immediately supersedes conflicting older documentation, tests and plans.

Once the owner has stated/confirmed a fact or direction unambiguously, do **not** ask again merely because an old document/test disagrees. Reopen it only if:

- the owner explicitly changes it; or
- fresh direct reproducible evidence contradicts the factual claim.

Old documentation, old CI assertions, previous chats, missing memory or an earlier architecture plan are not counter-evidence.

Current locked examples:

- DNS is fixed; historical DNS slowness/failures are closed unless fresh direct evidence shows a new DNS problem;
- Model C is the selected production Stage-60 direction; A/B are not competing production choices.

When the owner says `зафиксируй`, `запиши это`, `record this` or equivalent, the first GitHub documentation change must include a **full reconciliation of all active/current authority documents that could contradict the new canon**. Correct every active contradiction in the same logical docs change. Historical records may keep old state only as clearly historical/superseded material.

If a test/CI contract encodes stale canon, update the stale contract; never bend current documentation back toward an obsolete decision to make the test green.

## Documentation authority

`docs/PROJECT_PRINCIPLES.md` is the single canonical set of permanent project principles. Every new durable development principle must be added there in the first synchronized documentation change after approval; it must not remain only in chat, a patch note or a decision file.

Every substantive GitHub delivery is also a zero-memory recovery checkpoint. Before publication, verify that a future session with no chat/model memory can determine from the repository alone: the most recent completed logical work, what the latest/current delivery changed and why, its intended effect/acceptance boundary, the exact immediate next step, the complete ordered plan with completed/superseded/deferred status, and the active rules through `PROJECT_PRINCIPLES.md`.

Before any GitHub delivery, verify that the documentation contract in `PROJECT_PRINCIPLES.md` is satisfied and reconcile it against the owner's newest canon.

## Owner-facing communication

Project status/results to the owner are written in clear Russian by default.

Do not require the owner to decode raw GitHub/CI jargon. If an English/internal term is materially useful (`pull request`, `CI`, `latest head`, check name, etc.), immediately explain it in Russian and state the practical result: what succeeded/failed and what happens next.

Routine internal cleanup is not an owner problem. Fix ordinary branch/repository hygiene silently inside the authorized task unless a real permission/tool boundary prevents safe completion.

## Scope-first repository preflight

Before mutation always verify through the GitHub plugin:

- exact current `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- same-scope/relevant open PR state;
- current documented task/plan, reconciled against any newer owner instruction;
- plugin availability for the required operation.

Expand the inventory only when the operation needs it:

- workflows/runs/job logs for CI debugging or current-PR checks;
- artifacts/tags/releases/assets for package publication or release work;
- complete branch inventory for cleanup/collision/recovery/hygiene work;
- rulesets/protection/permissions when relevant;
- recursive repository tree for a genuine broad audit/cross-cutting investigation whose file/call path is unknown;
- active/current authority document sweep when the owner requests canon/documentation reconciliation.

A known-file task already named by `START_HERE.md` does not require a full repository/GitHub inventory before implementation unless the owner explicitly requested a broad consistency review.

Authority: `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`, `docs/decisions/DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`, and `docs/decisions/DEC-2026-08-14-owner-canon-lock-and-repository-hygiene.md`.

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
- external infrastructure failure causes no speculative source change;
- if a failed test proves only that the test encodes superseded canon, update the stale test/contract instead of reverting current canon;
- after completion, verify temporary branches contain no useful unique work and remove them; preserve useful unique work before cleanup.

## Request scope / standing authority

- `analyse`, `diagnose`, `review`, `audit`, `explain`: inspect/report only unless the owner also asks for changes;
- `fix`, `add`, `change`, `implement`, `complete`: perform the ordinary branch → Ready PR → checks → squash merge → verification → cleanup cycle;
- `зафиксируй` / equivalent: synchronize the stated canon plus all conflicting active documentation at the first GitHub docs opportunity;
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

MANDATORY: Use the connected GitHub plugin first for every repository operation; use another
transport only when the plugin is responding and lacks the exact required function or confirmed
permission. If the plugin is unavailable or cannot provide the authoritative state required to
proceed safely, stop GitHub work and report the boundary.

# AGENTS.md

This repository treats documentation as **operational project memory**. A new session must be able
to read the current handoff and resume the documented task without reconstructing the same project
history for hours.

==================================================
MANDATORY STARTUP READING
==================================================

For ordinary project continuation, read completely through EOF:

1. this file;
2. `docs/START_HERE.md`;
3. `docs/PROJECT_STATE.md`;
4. specialist documents named by the current documented task.

Use `docs/INDEX.md` as navigation when additional specialist/history material is needed.

Historical audits, patches, devlogs and evidence are part of the project. Read them when the current
plan, owner request, new defect or specialist scope requires them. Do not automatically reread the
entire historical repository merely because a new chat started.

Audits are not prohibited. If the documented plan says audit, perform the audit. If new evidence
requires one, perform it. The rule is to orient by current documentation first rather than inventing
a fresh context-recovery audit by default.

MANDATORY DOCUMENT-COMPLETION RULE:

- every document selected as required for the current scope must be read from first line through EOF;
- a successful file-open/fetch is not proof of a complete read;
- if a response is truncated/paginated/clamped/range-limited, fetch the remaining ranges;
- if a required authority cannot be read completely, stop before mutation/source change/package
  delivery rather than guessing from partial text.

==================================================
CURRENT OPERATIONAL AUTHORITY
==================================================

Current owner instruction has highest scope priority.

For ordinary continuation and project-state recovery:

1. owner instruction;
2. this file;
3. `docs/decisions/DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`;
4. `docs/START_HERE.md`;
5. `docs/PROJECT_STATE.md`;
6. current specialist architecture/patch/evidence documents;
7. historical records.

For GitHub delivery mechanics also use:

- `docs/GITHUB_PUBLICATION.md`;
- `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`;
- `docs/decisions/DEC-2026-08-06-evidence-first-github-operations.md`;
- `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md`;
- `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md`;
- `docs/GITHUB_WORKFLOW.md`.

The 2026-08-14 operational-handoff decision amends broad older pre-mutation inventory wording:
inventory breadth is proportional to the actual operation/risk. Evidence-first remains mandatory.

==================================================
DOCUMENTATION IS PART OF EVERY DELIVERY
==================================================

Before every logical GitHub delivery, project documentation must explicitly answer:

1. **What are we changing and why?**
   Concrete scope, trigger/root reason and important non-goals.
2. **What result do we expect after the patch?**
   Intended runtime/user result and automated/live acceptance boundary.
3. **What do we do next?**
   The complete ordered plan: immediate follow-up, next work, longer-term actions and deferred items.

Immediately before publishing a branch/PR or equivalent project delivery, perform **plan
reconciliation**:

- reread the current plan in `START_HERE` / `PROJECT_STATE` / `ROADMAP`;
- compare it with what implementation/testing actually taught us;
- check whether immediate or long-term plans changed;
- if they changed, update the documentation **before** publication;
- never silently lose a long-term plan: mark it completed, superseded, deferred or rejected with a
  reason.

At the end of every logical cycle that changes current state:

- update `docs/START_HERE.md`;
- update `docs/PROJECT_STATE.md`;
- update the current patch/evidence record;
- update `docs/ROADMAP.md` whenever priority, sequencing, future work or deferred plans changed.

Do not let startup/current-state documentation lag several package revisions behind `main`.

==================================================
GITHUB PLUGIN FIRST / SCOPE-FIRST PREFLIGHT
==================================================

Before every mutation always verify through the connected GitHub plugin:

- exact current `main` SHA;
- current `VERSION` and `PLUGIN_REVISION`;
- same-scope/relevant open PR state;
- plugin availability for the required operation;
- the current documented plan.

Inspect additional GitHub object classes only when the operation depends on them:

- workflows/runs/job logs for CI debugging or current-PR check handling;
- artifacts/tags/releases/assets for package publication/release work;
- complete branch inventory for branch cleanup/collision/recovery/hygiene work;
- protection/ruleset/permission settings when relevant to the operation;
- historical closed PRs when a concrete evidence question requires them.

An ordinary known-scope source/docs patch does not require enumeration of every historical branch,
workflow, successful run, artifact, tag and release before starting.

Pinned recursive-tree indexing remains recommended for genuine repository-wide audits/cross-cutting
investigations where the file/call path is unknown. It is not mandatory startup ceremony for a
known-file task already named by `docs/START_HERE.md`.

==================================================
ORDINARY DELIVERY FLOW
==================================================

Default ordinary delivery:

one logical change
        ↓
one task branch and one Ready pull request
        ↓
focused validation
        ↓
required checks for the latest PR state
        ↓
one squash merge into `main` using the expected head SHA
        ↓
verify `main` and clean the temporary branch

Rules:

- keep one logical scope per PR;
- same-scope repairs stay in the same branch/PR;
- Draft is optional and only for intentional WIP;
- every PR title, branch commit subject and final squash subject starts with the exact current
  package-candidate prefix `v<VERSION>_<REVISION>:`;
- docs/governance/CI-only work does not change package metadata;
- required CI gates the latest mergeable head, not every historical run;
- independent analysis may continue while CI runs;
- never force-update `main`, move a published tag or rewrite published history.

==================================================
CI / FAILURE HANDLING
==================================================

Read the exact failed job log before changing source, workflow, runner or branch.

- same-scope source/documentation/test defect: repair in the same PR;
- external GitHub/runner/network/action outage: zero source change; at most one unchanged rerun after
  recovery;
- second unchanged infrastructure failure: stop for diagnosis;
- do not create speculative retry/final sibling branches, runner switches, replacement workflows or
  unbounded trackers;
- plugin unavailability is a stop condition, not permission to switch transports silently.

==================================================
OWNER PACKAGE DELIVERY
==================================================

Any owner request for a package/patch deliverable for testing, installation or delivery means a
persistent GitHub-hosted `.pkg`, unless the owner explicitly asks for build/CI evidence only.

- Actions artifacts are build evidence, not final delivery;
- sandbox/local files are never final project package delivery;
- `не релиз, а пакет` means no stable/full semantic release, no Pages and no pkg-repository
  promotion, but still requires persistent GitHub testing-package publication;
- the package request itself authorizes deterministic testing-package publication; do not ask for a
  second publication confirmation;
- final owner-facing output is a direct GitHub `.pkg` URL or csh-safe install command.

Authority: `docs/decisions/DEC-2026-08-13-github-only-package-delivery.md`.

==================================================
REQUEST SCOPE / AUTHORIZATION
==================================================

- analyse, diagnose, explain, review, audit: inspect/report, no mutation unless the owner also asks
  for changes;
- fix, add, change, implement, complete: perform ordinary branch -> Ready PR -> checks -> squash
  merge -> verification;
- package/test package/installable patch: complete packaged source cycle as needed and persist the
  deterministic `.pkg` on GitHub;
- publish candidate `vX.Y.Z_N`: publish only that testing package, no Pages/pkg-repo promotion;
- release version `X.Y.Z`: perform the explicitly authorized full stable release pipeline.

Do not ask for routine branch names, commit wording, PR text, CI inspection, same-scope repair,
squash merge, cleanup or a second testing-package publication confirmation when the scope already
authorizes them.

Stop for owner input only on material product ambiguity, unavailable owner-only live evidence,
credentials/protected authority, destructive changes to user/pre-existing remote data, history
rewrite/direct-main publication, unresolvable required-check failure, or GitHub-plugin unavailability.

==================================================
PATCH / RELEASE BOUNDARY
==================================================

- ordinary packaged source change: keep `VERSION`, increment `PLUGIN_REVISION` once;
- documentation/governance/CI-only change: change neither;
- testing-package publication: no semantic VERSION change, no Pages/pkg repo;
- full project release: change VERSION, reset revision to `1`, use the versioned release-preparation
  subject and full release pipeline;
- published tags/releases/assets/versions are immutable and forward-only.

==================================================
OPNSENSE COMMAND RULE
==================================================

OPNsense console commands target the default root `csh` shell. POSIX-only syntax must be placed
between an explicit standalone `sh` (or `/bin/sh`) and matching `exit`.

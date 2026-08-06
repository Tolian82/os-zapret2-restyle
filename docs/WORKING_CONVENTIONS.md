# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Which engineering rules are already settled?

Purpose:
Store permanent project identities, engineering principles, and working rules.

Updated when:
A permanent rule or approved convention changes.

Read after:
PROJECT_STATE.md and the applicable active decision under `docs/decisions/`.

Do not store here:
Current task status, history, roadmap, or implementation detail.

==================================================
STABLE IDENTITIES
==================================================

Project and repository:
os-zapret2-restyle

Installed package:
os-zapret2-restyle

Makefile PLUGIN_NAME:
zapret2-restyle

MVC namespace:
OPNsense\Zapret

Internal service and configd namespace:
zapret

Version source:
VERSION

==================================================
ENGINEERING PRINCIPLES
==================================================

- Correctness over speed.
- Preserve working behavior before optimization.
- Keep one logical scope per delivery.
- A task branch may contain same-scope repair commits; `main` receives one logical
  squash commit.
- Repository source is authoritative.
- Generated runtime is never committed.
- Validate before activation.
- Transactional Apply is mandatory.
- Do not remove inherited references mechanically.
- Audit before refactoring.
- Documentation is part of the project architecture.
- Changes to the documentation system are architectural changes.
- Every approved rule must be recorded in the applicable current authority.

==================================================
DOCUMENTATION AND DECISION AUTHORITY
==================================================

`docs/INDEX.md` defines the reading order and authority map.

A focused dated decision under `docs/decisions/` may be the primary authority for its
scope. `docs/DECISIONS.md` remains the consolidated historical ledger. When an older
entry conflicts with a later active dated decision that explicitly records supersession,
the later decision controls.

Code and all directly affected documentation belong in the same logical delivery.
Historical records remain when they are genuine evidence, but wording that may be
mistaken for current behavior must be marked historical or superseded and point to the
current authority.

==================================================
AUDIT RULES
==================================================

Every inherited reference must be classified before removal.

Allowed classifications:

OK
broken
unused
duplicate
inherited
requires live test

The word `zapret` alone is not evidence of obsolete inheritance.

`AUDIT.md` is the authoritative register for audit scope, evidence, chains,
classifications, live-test requirements, remediation plans, acceptance criteria, and
status. A broken chain is recorded before remediation and retained after closure.

Findings and Architecture Debt are separate records. A Finding is a confirmed defect or
risk. Architecture Debt is an unresolved design question and cannot be implemented or
closed before a recorded decision, implementation, verification, and documentation.

==================================================
CHANGE AND TESTING RULES
==================================================

- Fix the exact GitHub base SHA before editing.
- Make minimal reviewable changes.
- Include affected documentation and Git modes.
- Run appropriate syntax and focused tests.
- Review the complete diff.
- Stop when validation fails; do not publish a knowingly failed or partial change.
- Never claim a test passed unless it was executed.
- Static verification, package-archive verification, and live OPNsense verification are
  distinct states.
- A live finding is closed only by exact recorded live evidence.

Normal local checks when a checkout exists:

`git status --short`

`git diff --check`

`git diff --stat`

==================================================
RISK-BASED RESPONSE PREFLIGHT
==================================================

For every new or resumed project context:

1. read repository-root `AGENTS.md`, `docs/INDEX.md`, and `docs/PROJECT_STATE.md`;
2. read the specialist documents and active decisions relevant to the requested scope;
3. read `docs/GITHUB_PUBLICATION.md` before a GitHub mutation;
4. re-read any authority whose command or workflow detail is uncertain;
5. perform the OPNsense root-csh check before sending console commands.

A full reading of every audit, decision, architecture, devlog, roadmap, and requirement
file is required only for repository-wide audit or genuine full-context recovery. It is
not required before every focused diagnosis or small change.

==================================================
GITHUB ORDINARY DELIVERY RULE
==================================================

Required sequence:

read and record exact current `main`
↓
perform the pre-mutation GitHub inventory
↓
prepare and validate one logical change
↓
publish one task branch and one Ready PR
↓
keep same-scope repairs in the same PR
↓
pass required checks for the latest mergeable head
↓
squash merge with expected head SHA and exact versioned subject
↓
verify `main` and clean the task branch

Draft is optional and reserved for intentional work in progress.

Every PR title, PR-branch commit subject, and final squash subject begins with the exact
candidate prefix derived from `VERSION` and `PLUGIN_REVISION`.

Do not create sibling branches merely named `-clean`, `-final`, `-fixed`, `-retry`, or
`-publish`. Never force-update `main`, move a published tag, or rewrite published
history.

==================================================
GITHUB PRE-MUTATION INVENTORY
==================================================

Before any branch, PR, workflow, tag, release, or asset mutation, inspect:

- exact `main` and candidate metadata;
- relevant PRs and branches;
- existing workflows capable of the operation;
- active, queued, failed, and successful runs;
- reusable artifacts and their run ID, artifact ID/name, expiry, and digest;
- existing tags, releases, and assets;
- actual connector/API/Git/`gh` permissions.

Do not create a new mechanism until the inventory proves the current mechanisms are
insufficient.

==================================================
GITHUB FAILURE RULE
==================================================

Read the exact failed job log before changing source, workflow, runner, or branch.

- A confirmed same-scope defect is repaired in the same PR.
- An external GitHub, runner, network, action-distribution, or dependency failure causes
  zero source changes and permits at most one unchanged rerun after recovery.
- Do not switch runner operating systems, create replacement branches, or add workflows
  without evidence that the current implementation is defective.
- A second unchanged infrastructure failure stops the operation for diagnosis.
- Duplicate trackers and unbounded scheduled retries are forbidden.

==================================================
TESTING PRERELEASE RULE
==================================================

Publishing an already verified candidate is a release operation, not a code PR.

- Exact owner authorization is required for `v<VERSION>_<REVISION>` and its asset.
- Prefer direct Release API/UI/`gh` upload when verified package bytes already exist.
- Reused Actions artifacts are bound by exact run ID, artifact ID/name, and digest.
- Recheck package `+MANIFEST` before publication.
- Use the single generic `.github/workflows/publish-prerelease.yml` only when automated
  build-and-publish is needed.
- Permit only one active publication run per candidate.
- A temporary `publish/v<VERSION>_<REVISION>` branch does not receive a PR.
- Testing prereleases publish neither GitHub Pages nor the pkg repository.
- Verify target SHA, tag, flags, asset, and direct URL, then delete the temporary branch.

==================================================
PATCH, PRERELEASE, AND RELEASE BOUNDARY
==================================================

Ordinary packaged change:

- keep `VERSION`;
- increment `PLUGIN_REVISION` once;
- publish no tag, release, asset, Pages, or pkg repository without separate authority.

Governance/documentation/CI-only change:

- change neither version value;
- use the unchanged candidate prefix;
- run applicable path-gated CI.

Testing prerelease:

- explicit authority for exact `v<VERSION>_<REVISION>`;
- publish one verified package asset only;
- no Pages/pkg repository.

Full project release:

- explicit authority for exact new `VERSION=X.Y.Z`;
- reset revision to `1`;
- release-preparation title is `vX.Y.Z_1: Prepare release vX.Y.Z`;
- existing product and live gates apply;
- published tags, releases, assets, and versions are immutable.

==================================================
STANDING DELIVERY AUTHORIZATION
==================================================

An instruction to fix, add, change, implement, or complete an ordinary task authorizes
the normal branch → Ready PR → CI → squash merge → verification cycle unless the owner
sets a narrower boundary.

Analysis/review/audit requests are read-only. Patch-only, branch-only, and PR-only
requests stop at the named boundary. Testing prerelease or full release publication
requires explicit authority for the exact candidate/version.

Do not ask for routine branch names, commit text, PR text, CI inspection, same-scope
repair, Ready state, squash merge, or task-branch cleanup when those choices are
deterministic.

Stop for owner direction only on material product ambiguity, relevant unpublished owner
state, unavailable credentials/protected authority, destructive changes to user data or
pre-existing remote objects, history rewriting/direct-main publication, an unresolvable
required-check failure, or mandatory live evidence available only from the owner.

==================================================
COMMAND BLOCK AND CSH RULE
==================================================

Operational instructions separate read-only validation from state-changing actions.

OPNsense console instructions target root `csh`. POSIX-only constructs such as `$(...)`,
`name=value`, `export`, `if ...; then`, arithmetic expansion, or shell functions require
an explicit standalone `sh` before the block and standalone `exit` afterward.

Commands remain in actual execution order. A validation block must not silently perform
installation, publication, restart, or another mutation.

==================================================
FOCUS AND SUFFICIENCY
==================================================

The project is a small applied addon. Prefer the least complexity needed for reliable
approved functionality. Current priorities are working behavior, real OPNsense evidence,
and sufficient synchronized documentation. UX and broad redesign are supporting work,
not independent goals.

==================================================
RUNTIME LIFECYCLE OWNERSHIP
==================================================

Package lifecycle and runtime bootstrap changes are one architectural unit. Code hooks,
setup backend, service boundaries, configd integration, verification, and affected
material documentation are delivered together.

The single approved runtime installation and maintenance backend is
`/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh`. GUI maintenance must reuse it and
must not implement an independent installer.

Package and setup operations preserve complete running/stopped service state and fail
closed on incomplete state or stop failure. Runtime staging/rollback remains a separate
architectural concern.

==================================================
BLOB SHORTHAND RULE
==================================================

- Supported shorthand is `--blob=<name>`.
- It resolves directly to `files/fake/<name>.bin`.
- The `.bin` suffix is omitted in strategy text.
- There is no implicit alias table.
- Native `--blob=name:value` declarations remain untouched.
- Missing files are hard errors.

==================================================
LOCAL-ONLY STATE EXCEPTION
==================================================

GitHub is authoritative only for committed and pushed state. If relevant owner changes
exist only in a local OPNsense checkout, stop before editing and request that exact state
be committed/pushed or explicitly transferred. Never reconstruct or overwrite
unpublished state from memory.

A clean checkout matching the recorded GitHub SHA requires no archive. Unified patches
are optional and used only when explicitly requested or transferring local-only state.

==================================================
REPOSITORY ARTIFACT HYGIENE
==================================================

Tracked editor backups, merge rejects, ad-hoc patches, transport fragments, encoded
payloads, and local backup files are forbidden. This includes `*.orig`, `*.rej`,
`*.patch`, `*.diff`, `*.b64`, `*.base64`, `*.bak`, `*.part-*`, and editor `*~` files.

`scripts/test-repository-hygiene.sh` is a mandatory CI gate.

Normal steady-state branch authority is `main`. `recovery/base` is preserved as a
recovery reference. Ordinary task and publication branches are temporary and are removed
after successful merge/publication or proven abandonment.

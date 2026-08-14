# DEC-2026-08-14 — Three-level versioned documentation memory

Status: **ACTIVE / SUPERSEDING FOR DOCUMENT-READ AND HISTORY-RETENTION RULES**

## Decision

Project engineering memory uses three levels:

1. **Level 1 — mandatory bounded recovery memory:** root `AGENTS.md`, `PROJECT_PRINCIPLES.md`,
   `START_HERE.md`, `PROJECT_STATE.md`, then only current-task specialist documents named by the
   handoff.
2. **Level 2 — current version-line memory:** one rolling `docs/history/current/vX.Y.x.md` ledger plus
   specialist documents selected by the active task.
3. **Level 3 — historical memory:** one compact archive map per completed version line plus the
   original detailed devlog/patch/verification/release/decision/audit records.

`docs/INDEX.md` is navigation only and must directly link the current ledger, every completed version-
line archive and the deep record stores.

The mandatory Level-1 handoff always contains a very short lifetime project path and exact next task,
not a patch-by-patch history.

## Second-numeric-component rollover

The version-line boundary is the **second numeric component**: the `4` in `0.4.x`, for example
`v0.4.x -> v0.5.x`. This wording is intentionally explicit; the standalone word `minor` is not used as
the authority for the transition.

The assistant never initiates a second-component change. It requires either an explicit owner
version/transition instruction or separate owner approval of a proposal. Once that transition is
authorized, no second confirmation is required for its implied documentation rollover and full
release.

The transition procedure automatically:

1. finalizes the old current-line ledger;
2. creates/freezes the compact `history/archive/v0.4.x.md` map;
3. preserves every original detailed record;
4. initializes `history/current/v0.5.x.md`;
5. updates `INDEX`, Level 1 and the short lifetime path;
6. performs the mandatory full human-facing `README.md` revision;
7. proceeds with the full project release, including the package published into the OPNsense
   Pages/pkg repository for Web GUI installation.

A full project release can also be explicitly requested while keeping the same second numeric
component. Thus the implication is one-way: second-component change requires a full release; a full
release does not itself authorize a second-component change.

## Integrity rule

Archiving is **not** deletion, history rewriting or consolidation that destroys traceability. Archive
maps point to original detailed records. Old devlogs, patch records, verification evidence, decisions,
audits, release records and Git history remain intact and are loaded only when a current task needs
them.

Current architecture/contracts and permanent project principles are not archived merely because a
version line changes.

## Single-primary-home rule

- `PROJECT_STATE` — current facts only;
- `START_HERE` — compact recovery handoff + short project path + exact current task;
- `ROADMAP` — current/future ordering;
- current version-line ledger — richer current chronology;
- devlog/patch/verification/decision — distinct deep execution/contract/proof/rationale only;
- `INDEX` — navigation only.

A separate patch/devlog file is not mandatory when it would merely duplicate a docs/governance change
already completely represented by the current-line ledger and canonical documents.

## Reason

The repository must preserve full engineering history for auditability and zero-memory recovery, but
loading that history during every new ChatGPT context wastes working context and can elevate stale
history over current facts. Read-set control provides the memory reduction without sacrificing
traceability.

The explicit second-component wording prevents an assistant from treating an inferred semantic
versioning convention as permission to move the project from one version line to another.

## Supersession

This decision and the newer canonical principles supersede older `docs/DECISIONS.md` statements to
the extent they conflict, specifically old rules that:

- made `INDEX.md` the mandatory context entrypoint rather than navigation only;
- required the historical long-form context restoration order beginning with `INDEX` and including
  `DECISIONS`, `DEVLOG`, `ROADMAP`, etc. on every restore;
- required every approved concept/rule to be duplicated into monolithic `DECISIONS.md`;
- required a standalone patch/devlog/evidence update after every logical change even when it would be
  duplicate content;
- required old document-role formatting where it conflicts with the newer Level/status/read-when
  responsibility model.

The underlying historical decision text remains intact as history and rationale. It must not be read
as current authority where this newer decision explicitly supersedes it.

## Initial migration

- `v0.1.x`, `v0.2.x`, `v0.3.x` receive compact archive maps now;
- `v0.4.x` remains the active current-line ledger;
- a future owner-authorized `v0.4.x -> v0.5.x` transition will create/freeze the `v0.4.x` archive as
  part of the required full release;
- `INDEX.md` provides direct routes to every archive/current ledger and to deep detailed records.

## Affected documents

- `AGENTS.md`
- `README.md`
- `docs/PROJECT_PRINCIPLES.md`
- `docs/START_HERE.md`
- `docs/PROJECT_STATE.md`
- `docs/INDEX.md`
- `docs/ROADMAP.md`
- `docs/WORKING_CONVENTIONS.md`
- `docs/DEVELOPMENT_GUIDE.md`
- `docs/GITHUB_PUBLICATION.md`
- `docs/history/current/v0.4.x.md`
- `docs/history/archive/v0.1.x.md`
- `docs/history/archive/v0.2.x.md`
- `docs/history/archive/v0.3.x.md`

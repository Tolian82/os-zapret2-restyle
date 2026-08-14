# DEC-2026-08-14 — Three-level versioned documentation memory

Status: **ACTIVE / SUPERSEDING FOR DOCUMENT-READ AND HISTORY-RETENTION RULES**

## Decision

Project engineering memory uses three levels. The complete current documentation-governance contract is now enumerated in `docs/DOCUMENTATION_RULES.md`; this decision records the architecture/rationale.

1. **Level 1 — mandatory bounded recovery:** read completely in context-first order: root `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.md`, `DOCUMENTATION_RULES.md`, `PROJECT_PRINCIPLES.md`, `CHAT_RULES.md`, `GITHUB_PUBLICATION.md`, `ROADMAP.md`, `INDEX.md`, then only current-task specialist documents named by the handoff.
2. **Level 2 — current second-component-line memory:** one rolling `docs/history/current/vX.Y.x.md` ledger plus specialist documents selected by the active task.
3. **Level 3 — historical memory:** compact archive map per completed second-component line plus the original detailed devlog/patch/verification/release/decision/audit records.

`docs/INDEX.md` is navigation/integrity only and directly links the current ledger, every completed version-line archive and the deep record stores.

After Level 1 has been completely read for an exact repository state, unchanged mandatory files may be reused during the same continuous work. If `main` advances, compare the new repository state and reread every affected mandatory/current document before further mutation. This reduces repeated context load without allowing stale canon.

## Version/document roles

For `v0.4.2_14`:

- second numeric component `4` defines the `v0.4.x` line and `PROJECT_STATE.md` scope;
- third numeric component `2` defines the current development stage/task;
- `_14` defines the exact package revision and `START_HERE.md` handoff boundary.

A third-component stage transition resets revision to `_1` but is not a full release by itself. A second-component transition is owner-controlled and always includes a full release. A full release may occur inside the same second-component line and may use the current exact `_N` candidate; release publication itself does not reset revision.

## State / handoff flow

`START_HERE` is a live revision handoff. When its task becomes a durable current fact, that fact flows into `PROJECT_STATE`; execution detail stays in the current ledger/deep records.

`PROJECT_STATE` remains the current facts file throughout one second-component line. When the second component changes, its final old-line contents are preserved in that line's archive before the file is initialized for the new line. From the eventual `v0.4.x` archive onward, archive files therefore contain both the compact archive map and final state snapshot.

Older `v0.4.0` and earlier history is not retroactively rewritten into this new state-snapshot model.

## Master plan

`ROADMAP.md` is the always-available concise whole-project plan. It retains short completed milestones, marks the current item, and contains every known future intention at least once. Detailed execution and proof remain outside the roadmap.

## Integrity rule

Archiving is **not** deletion, history rewriting or consolidation that destroys traceability. Archive maps point to original detailed records. Old devlogs, patch records, verification evidence, decisions, audits, release records and Git history remain intact and are loaded only when a current task needs them.

Current architecture/contracts and permanent project principles are not archived merely because a version line changes.

## Single-primary-home rule

- `DOCUMENTATION_RULES` — documentation-governance canon;
- `PROJECT_PRINCIPLES` — project-development canon;
- `CHAT_RULES` — owner/assistant interpretation canon;
- `GITHUB_PUBLICATION` — complete GitHub-work canon;
- `PROJECT_STATE` — current facts for current second-component line;
- `START_HERE` — exact current `_N` handoff;
- `ROADMAP` — complete concise master plan;
- current version-line ledger — richer current chronology;
- devlog/patch/verification/decision — distinct deep execution/proof/rationale;
- `INDEX` — navigation/integrity map.

Duplication is not preservation. A standalone patch/devlog record is used only when it adds distinct information rather than repeating the same narrative already held by its primary current home.

## Reason

The repository must preserve complete engineering history for auditability and zero-memory recovery, while keeping the always-read context small. Tying documentation roles to explicit version components also prevents ambiguity about whether a new task, package iteration or full release should archive state or rotate the current line.

## Second-component rollover

When the owner explicitly authorizes a second-component change such as `v0.4.x -> v0.5.x`:

1. reconcile final old `PROJECT_STATE`;
2. finish old current-line ledger;
3. create/freeze `history/archive/v0.4.x.md` with compact map + final state snapshot;
4. preserve every original detailed record;
5. initialize `history/current/v0.5.x.md`;
6. initialize `PROJECT_STATE` and `START_HERE` for the new line/current revision;
7. update `ROADMAP`, `INDEX` and short lifetime path;
8. perform complete human-facing README review;
9. complete the full OPNsense Web/pkg release.

No separate owner reminder/confirmation is required after the second-component transition itself has already been authorized.

## Supersession

This decision, `DOCUMENTATION_RULES.md` and newer canonical principles supersede older documentation statements to the extent they conflict, including old rules that:

- used a rules-first cold-start order instead of the current context-first order;
- omitted `CHAT_RULES.md`, `GITHUB_PUBLICATION.md`, `ROADMAP.md`, or `INDEX.md` from complete Level-1 recovery;
- omitted `DOCUMENTATION_RULES.md` from Level 1;
- made `INDEX.md` the mandatory context entrypoint rather than navigation only;
- treated `PROJECT_STATE` as an unversioned generic snapshot instead of current second-line state;
- treated any `VERSION` change as an automatic full release;
- forced full releases to revision `_1` even when no stage/line transition occurred;
- required every approved rule to be duplicated into monolithic `DECISIONS.md`;
- required a standalone patch/devlog/evidence record when it would add no distinct information.

Underlying historical text remains intact as history and must not be read as current authority where newer rules explicitly supersede it.

## Initial migration boundary

- `v0.1.x`, `v0.2.x`, `v0.3.x` remain legacy compact archive maps;
- `v0.4.x` remains the active current line;
- new final-state-snapshot archive behavior begins when `v0.4.x` eventually closes;
- no rewrite of `v0.4.0` or earlier history is required;
- `INDEX.md` and the archive links at the end of `PROJECT_STATE.md` provide direct routes to archives.

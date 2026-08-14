# AGENTS.md

This is the mandatory repository bootstrap. It is a map to current authority, not a fifth rule book.

## Mandatory cold start

For a new session or after a long break, read completely through EOF in this order:

1. `AGENTS.md`;
2. `docs/START_HERE.md` — exact current `_N` handoff and immediate task;
3. `docs/PROJECT_STATE.md` — current facts for the active version line;
4. `docs/DOCUMENTATION_RULES.md` — documentation rules (`DOC-*`);
5. `docs/PROJECT_PRINCIPLES.md` — project-development rules (`DEV-*`);
6. `docs/CHAT_RULES.md` — owner/assistant chat rules (`CHAT-*`);
7. `docs/GITHUB_PUBLICATION.md` — all GitHub rules (`GH-*`);
8. `docs/ROADMAP.md` — complete concise master plan;
9. `docs/INDEX.md` — navigation/integrity map;
10. only specialist documents selected by the current handoff.

This order is context-first: learn the exact current task and facts before loading the complete rule canon, while still reading every canonical rule book before project mutation (`DOC-016`).

If a mandatory document is truncated or paginated, continue to EOF. If required authority cannot be read safely, do not guess (`GH-003`).

## Four canonical rule domains

- documentation structure, maintenance, reading, archiving, and reference integrity: `DOC-*`;
- project design, engineering, version, product, and verification principles: `DEV-*`;
- meaning of owner instructions and owner-facing communication: `CHAT-*`;
- repository, branch, PR, CI, merge, package, release, and GitHub hygiene: `GH-*`.

Each current general rule has one normative home. Each book contains an explicit inbound/outbound cross-reference registry; CI verifies that the registries and real rule references agree (`DOC-042`–`DOC-045`).

## Current-work documentation flow

Current development state follows one flow under `DOC-024`: `START_HERE.md -> PROJECT_STATE.md -> version-line archive`.

- active work, the immediate boundary, and the exact next action live in `START_HERE.md`;
- durable facts established by completed work flow into `PROJECT_STATE.md` for the active second-component line;
- when that line closes, its final state flows into the version-line archive;
- current ledgers, decisions, devlogs, and evidence preserve chronology, rationale, and proof but do not become parallel owners of current state.

The four rule books are reserved for durable canon and hard rules. Ordinary current work does not become a new canonical rule merely because it is important now.

## Reading efficiently without losing freshness

Level-1 reading is repository-state scoped (`DOC-049`). During one continuous piece of work, already-read mandatory files need not be reloaded when the exact repository state has not changed. If `main` advances, compare the new state and reread every affected mandatory/current document before further mutation.

Level 2 contains current-line/current-task detail. Level 3 contains historical rationale and proof. Load those only when `START_HERE.md`, `INDEX.md`, or the current problem requires them.

## Continue the project

After the mandatory set, follow `START_HERE.md`. It contains the exact current boundary, recently established result, next task, required specialist reading, and acceptance criteria. The owner's newest unambiguous instruction remains binding under `DEV-001` and `CHAT-026`.

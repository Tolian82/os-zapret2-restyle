# Documentation Rules

Status: **CANONICAL / MANDATORY LEVEL 1**
Updated: 2026-08-14

This file is the single normative home for rules about project documentation structure, maintenance, reading, archiving, and internal consistency.

The other three canonical rule books are:

- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development rules (`DEV-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant chat rules (`CHAT-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub rules (`GH-*`).

## A. Canonical rule architecture

DOC-001. **Exactly four canonical rule books exist.** Documentation rules live here; project-development rules live in `PROJECT_PRINCIPLES.md`; chat rules live in `CHAT_RULES.md`; GitHub rules live in `GITHUB_PUBLICATION.md`.

DOC-002. **One current rule has one normative home.** Other active documents reference its rule ID instead of restating the same rule as a second authority.

DOC-003. **Rule domains are semantic.** When a current rule is found in the wrong domain, move its normative meaning to the proper rule book and replace active duplicates with references where needed.

DOC-004. **Historical text is preserved as history.** Decisions, devlogs, patches, evidence, audits, releases, and Git history keep their original context and do not regain current authority merely because they remain available.

DOC-005. **Superseded rules stay superseded.** Check newer owner canon and explicit supersession before promoting an old statement into a current rule book.

DOC-006. **Rule IDs are stable references.** Use sequential domain-prefixed IDs (`DOC-*`, `DEV-*`, `CHAT-*`, `GH-*`); do not silently recycle an ID for a different meaning.

DOC-007. **Cross-document references use IDs.** Active documents should point to the canonical file and rule ID rather than copy the full normative wording.

DOC-008. **Rule-book changes require consistency reconciliation.** Adding, moving, merging, removing, or materially rewriting a rule requires same-scope review of dependent active documents, navigation, and automated checks.

## B. Documentation purpose and authority

DOC-009. **Documentation is part of the architecture.** A logical change is incomplete if committed documentation cannot recover current intent, state, constraints, and next action.

DOC-010. **Zero-memory recovery is a design target.** A fresh session must recover current direction from a bounded Level-1 set without reconstructing settled history from chat memory.

DOC-011. **Each active document has a bounded role.** State, handoff, roadmap, architecture, requirements, procedures, history, decisions, evidence, and navigation must not become interchangeable monoliths.

DOC-012. **One current fact has one primary current home.** Other active documents may link to it or summarize only what their own role requires.

DOC-013. **Current authority and history are different.** Current rule books/current architecture/current state govern present work; archived or superseded material is read for rationale, chronology, or proof.

DOC-014. **Specialist technical contracts stay specialist.** Product-specific stage orders, ports, paths, state machines, timeouts, algorithms, and protocol contracts remain in requirements/architecture instead of being copied into the four general rule books.

## C. Three-level engineering memory

DOC-015. **Engineering memory has three levels.** Level 1 is bounded mandatory recovery; Level 2 is current-line/current-task detail; Level 3 is historical/deep proof loaded on demand.

DOC-016. **Level 1 is bounded.** Read root `AGENTS.md`, the four canonical rule books, `START_HERE.md`, `PROJECT_STATE.md`, then only specialist documents required by the current handoff.

DOC-017. **Level 2 owns richer current-line detail.** `docs/history/current/vX.Y.x.md` carries active-line chronology, supplemented by selected current-task specialist documents.

DOC-018. **Level 3 preserves detailed history.** Completed line archives plus original devlogs, patches, evidence, decisions, audits, releases, and Git history remain available without default loading.

DOC-019. **`INDEX.md` is the integrity/navigation map.** It routes to the four rule books, Level-1 state/handoff/plan, current ledger, completed line archives, and deep record stores.

DOC-020. **Archiving never means deletion.** A compact archive may summarize a completed line, while original detailed records remain intact and reachable.

## D. `START_HERE.md`

DOC-021. **`START_HERE.md` is the exact revision handoff.** It states what was just established at the current `_N` boundary, its effect, exact next action, and minimum specialist reading.

DOC-022. **The top of `START_HERE.md` provides direct orientation links.** `PROJECT_STATE.md` is first, followed by the four rule books, the master plan, and `INDEX.md`.

DOC-023. **`START_HERE.md` is not a patch diary.** It carries the current `_N` boundary rather than a copy of every previous revision.

DOC-024. **Completed handoff facts flow forward.** Durable current facts move to `PROJECT_STATE.md`; detailed execution/proof remains in the current ledger or deep records.

DOC-025. **The handoff names the exact next task.** A fresh session must not rediscover completed investigations merely to identify the next approved change.

## E. `PROJECT_STATE.md` and archives

DOC-026. **`PROJECT_STATE.md` belongs to the active second-component line.** Its scope is `vX.Y.x` under `DEV-029`–`DEV-031`; third-component and `_N` changes do not rotate it.

DOC-027. **`PROJECT_STATE.md` contains current facts, not chronology.** Keep identity, settled facts, active constraints/debt, next boundary, and direct evidence/architecture pointers.

DOC-028. **Second-component rollover archives final state.** An owner-authorized transition under `DEV-036`–`DEV-037` preserves the final old-line state snapshot before the new line is initialized.

DOC-029. **Every current `PROJECT_STATE.md` ends with archive links.** It directly links every completed version-line archive in chronological order while `INDEX.md` independently preserves global navigation.

DOC-030. **The final-state-snapshot archive model starts with closure of `v0.4.x`.** Earlier history is not retroactively rewritten merely to imitate the newer archive shape.

## F. Master plan and current ledger

DOC-031. **`ROADMAP.md` is the complete concise master plan.** It contains the short lifetime path, current priority, and every known future development intention at least once.

DOC-032. **The roadmap keeps major completed path visible without becoming a devlog.**

DOC-033. **The roadmap stays concise.** Detailed measurements, implementation chronology, and proof belong in the current ledger/deep records.

DOC-034. **The current-line ledger owns current chronology.** It carries richer ordered work/evidence that is too large for mandatory Level 1.

DOC-035. **Standalone deep records must add distinct value.** Create them for distinct chronology, rationale, proof, or reproducibility, not merely to duplicate another primary home.

## G. Reconciliation and release presentation

DOC-036. **Every development stage begins and ends with documentation reconciliation.** Confirm current handoff/state/rules before implementation and update affected active documents after the logical change.

DOC-037. **Every GitHub delivery includes same-scope documentation consistency.** GitHub mechanics remain in `GH-*`; affected documentation is reconciled in the same logical PR.

DOC-038. **A full release includes a complete README review.** Before the full release defined by `DEV-039` and executed under `GH-039`–`GH-046`, review `README.md` against actual capabilities, installation path, support boundary, release identity, and contributor navigation.

DOC-039. **README is human-facing, current, and concise.** It should be attractive, readable, understandable, and sufficiently complete without becoming an internal engineering dump.

DOC-040. **Selected mandatory documents are read through EOF.** If the handoff/rules select a document as mandatory for the current task, read the entire selected document.

DOC-041. **Documentation-policy changes are recorded here first.** Assign the next `DOC-*` ID before updating dependent active documents.

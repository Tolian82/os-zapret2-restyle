# Documentation rules

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-08-14

This file is the single normative home for general rules about project documentation: structure, maintenance, reading, synchronization, archiving, rule references, and documentation integrity.

The other canonical rule books are:

- [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — project-development rules (`DEV-*`);
- [`CHAT_RULES.md`](CHAT_RULES.md) — owner/assistant chat rules (`CHAT-*`);
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — GitHub rules (`GH-*`).

## Canonical rule architecture

DOC-001. **Exactly four canonical general rule books exist.** Documentation rules live here; project-development rules live in `PROJECT_PRINCIPLES.md`; chat rules live in `CHAT_RULES.md`; GitHub rules live in `GITHUB_PUBLICATION.md`.

DOC-002. **One current general rule has one normative home.** Other active documents reference its rule ID instead of restating the same rule as a second authority.

DOC-003. **Rule domains are semantic.** When a current rule is found in the wrong domain, move its normative meaning to the proper rule book and replace active duplicates with references where needed.

DOC-004. **Historical text is preserved as history.** Decisions, devlogs, patches, evidence, audits, releases, and Git history keep their original context and do not regain current authority merely because they remain available.

DOC-005. **Superseded rules stay superseded.** Check newer owner canon and explicit supersession before promoting an old statement into a current rule book.

DOC-006. **Rule IDs are persistent identities, not ordinal positions.** Existing `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*` IDs are not renumbered merely because rules are sorted, inserted, merged, or rewritten. A new rule receives the next unused ID in its domain; a retired ID is not silently reused for a different meaning.

DOC-007. **Cross-document references use rule IDs.** Active documents point to the canonical file and rule ID rather than copy full normative wording.

DOC-008. **A rule-book change requires same-scope consistency reconciliation.** Adding, moving, merging, retiring, materially rewriting, or exceptionally migrating an ID requires review of dependent active documents, cross-reference registries, navigation, and automated checks.

## Documentation purpose and authority

DOC-009. **Documentation is part of the architecture.** A logical change is incomplete if committed documentation cannot recover current intent, state, constraints, and next action.

DOC-010. **Zero-memory recovery is a design target.** A fresh session must recover current direction from a bounded mandatory set without reconstructing settled history from chat memory.

DOC-011. **Each active document has a bounded role.** State, handoff, roadmap, architecture, requirements, procedures, history, decisions, evidence, and navigation must not become interchangeable monoliths.

DOC-012. **One current fact has one primary current home.** Other active documents may link to it or summarize only what their own bounded role requires.

DOC-013. **Current authority and history are different.** Current rule books, current architecture, current state, and current handoff govern present work; archived or superseded material is read for rationale, chronology, or proof.

DOC-014. **All useful current general normative information belongs in the four rule books; useful specialist information does not.** Product-specific stage orders, ports, paths, state machines, algorithms, measurements, protocol contracts, evidence, and other technical detail remain in requirements, architecture, current state/ledger, or proof records. Do not inflate Level 1 by copying the project into the rule books.

## Engineering memory and cold start

DOC-015. **Engineering memory has three levels.** Level 1 is bounded mandatory recovery; Level 2 is current-line/current-task detail; Level 3 is historical/deep proof loaded on demand.

DOC-016. **A zero-memory cold start is context-first but rule-complete.** Read completely, in this order: root `AGENTS.md`; `START_HERE.md`; `PROJECT_STATE.md`; the four canonical rule books; `ROADMAP.md`; `INDEX.md`; then only specialist documents selected by the current handoff. GitHub mutation additionally applies `GH-006`.

DOC-017. **Level 2 owns richer current-line detail.** `docs/history/current/vX.Y.x.md` carries active-line chronology, supplemented by selected current-task specialist documents.

DOC-018. **Level 3 preserves detailed history.** Completed line archives plus original devlogs, patches, evidence, decisions, audits, releases, and Git history remain available without default loading.

DOC-019. **`INDEX.md` is the integrity/navigation map.** It routes to the four rule books, Level-1 state/handoff/plan, current ledger, completed line archives, specialist documentation, compatibility pointers, and deep record stores.

DOC-020. **Archiving never means deletion.** A compact archive may summarize a completed line while original detailed records remain intact and reachable.

## `START_HERE.md`

DOC-021. **`START_HERE.md` is the exact revision handoff.** It states what was just established at the current `_N` boundary, its effect, exact next action, and minimum specialist reading.

DOC-022. **The top of `START_HERE.md` provides direct orientation links.** `PROJECT_STATE.md` is first, followed by all four rule books, the master plan, and `INDEX.md`.

DOC-023. **`START_HERE.md` is not a patch diary.** It carries the current `_N` boundary rather than a copy of every previous revision.

DOC-024. **Completed handoff facts flow forward.** Durable current facts move to `PROJECT_STATE.md`; detailed execution/proof remains in the current ledger or deep records.

DOC-025. **The handoff names the exact next task.** A fresh session must not rediscover completed investigations merely to identify the next approved change.

## `PROJECT_STATE.md` and archives

DOC-026. **`PROJECT_STATE.md` belongs to the active second-component line.** Its scope is defined by `DEV-029`–`DEV-031`; third-component and `_N` changes do not rotate it.

DOC-027. **`PROJECT_STATE.md` contains current facts, not chronology.** Keep identity, settled facts, active constraints/debt, next boundary, and direct evidence/architecture pointers.

DOC-028. **Second-component rollover archives final state.** An owner-authorized transition under `DEV-036`–`DEV-037` preserves the final old-line state snapshot before the new line is initialized.

DOC-029. **Every current `PROJECT_STATE.md` ends with archive links.** It directly links every completed version-line archive in chronological order while `INDEX.md` independently preserves global navigation.

DOC-030. **The final-state-snapshot archive model starts with closure of `v0.4.x`.** Earlier history is not retroactively rewritten merely to imitate the newer archive shape.

## Master plan and current ledger

DOC-031. **`ROADMAP.md` is the complete concise master plan.** It contains the short lifetime path, current priority, and every known future development intention at least once.

DOC-032. **The roadmap keeps the major completed path visible without becoming a devlog.**

DOC-033. **The roadmap stays concise.** Detailed measurements, implementation chronology, and proof belong in the current ledger/deep records.

DOC-034. **The current-line ledger owns current chronology.** It carries richer ordered work/evidence that is too large for mandatory Level 1.

DOC-035. **Standalone deep records must add distinct value.** Create them for distinct chronology, rationale, proof, or reproducibility, not merely to duplicate another primary home.

## Reconciliation and release presentation

DOC-036. **Every logical development scope begins and ends with documentation reconciliation.** Before implementation, establish the current handoff/state/rules; before completion, reconcile every affected active fact, contract, handoff, plan, and proof pointer.

DOC-037. **Every GitHub delivery includes a documentation-impact decision.** If committed behavior, facts, contracts, next work, or governance changed, update affected documentation in the same logical PR; GitHub execution follows `GH-053`.

DOC-038. **A full release includes a complete README review.** Before the release defined by `DEV-039` and executed under `GH-039`–`GH-046`, review `README.md` against actual capabilities, installation path, support boundary, release identity, and contributor navigation.

DOC-039. **README is human-facing, current, and concise.** It should be attractive, readable, understandable, and sufficiently complete without becoming an internal engineering dump.

DOC-040. **Selected mandatory documents are read through EOF.** If the handoff/rules select a document as mandatory for the current task, read the entire selected document.

DOC-041. **Documentation-policy changes are recorded here first.** Add or amend the appropriate persistent `DOC-*` rule before updating dependent active documents.

## Cross-reference integrity and maintainability

DOC-042. **Each canonical rule book contains an explicit cross-reference registry.** The registry lists every cross-book rule reference made by rules in that file and every cross-book rule reference made into that file.

DOC-043. **Cross-reference registries are bidirectional.** A source-book outbound reference and the target-book inbound reference must describe the same source/target relationship.

DOC-044. **Rule-ID migration is exceptional and atomic.** Ordinary edits never renumber existing IDs. If an ID must be replaced, the same logical change updates every rule body, registry, active-document reference, test, and navigation dependency before merge.

DOC-045. **CI protects rule-reference integrity.** It must reject duplicate canonical IDs, references to nonexistent IDs, stale registry entries, missing registry entries, or asymmetric inbound/outbound relationships.

DOC-046. **Current and newly written documentation uses clean standard Markdown.** Prefer one title, normal section headings, short paragraphs, bullets, tables, and code fences. Decorative separator walls such as long `=====` blocks are forbidden in current/active documents and new records. Historical Level-3 records need not be rewritten merely for style.

DOC-047. **Every GitHub change performs an explicit documentation-impact check.** The result may legitimately be “no documentation change required” when no documented fact, contract, handoff, plan, rule, or user-facing behavior changed; otherwise the documentation change belongs in the same scope under `GH-053`–`GH-054`.

DOC-048. **Compatibility pointers contain no independent current canon.** A legacy path retained to avoid breaking historical links may point to the current authority, but must not duplicate mutable rules, current state, or process detail.

DOC-049. **Level-1 reading is repository-state scoped.** Once the mandatory set has been fully read for an exact repository state, unchanged files need not be repeatedly reloaded during the same continuous work. If `main` advances, compare the new state and reread every affected mandatory/current document before further mutation under `GH-004` and `GH-026`.

## Cross-reference registry

This registry is part of the rule contract. It is maintained with rule changes and validated by CI under `DOC-042`–`DOC-045`.

### Outbound references

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `DOC-016` | `GH-006` |
| `DOC-026` | `DEV-029`, `DEV-030`, `DEV-031` |
| `DOC-028` | `DEV-036`, `DEV-037` |
| `DOC-037` | `GH-053` |
| `DOC-038` | `DEV-039`, `GH-039`–`GH-046` |
| `DOC-047` | `GH-053`, `GH-054` |
| `DOC-049` | `GH-004`, `GH-026` |
<!-- RULE-XREF-OUT-END -->

### Inbound references

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `DOC-003` | `CHAT-009` |
| `DOC-004` | `GH-009` |
| `DOC-005` | `GH-009` |
| `DOC-008` | `DEV-046`, `CHAT-009`, `CHAT-025`, `GH-055` |
| `DOC-011` | `GH-054` |
| `DOC-012` | `GH-054` |
| `DOC-016` | `GH-006` |
| `DOC-019` | `GH-057` |
| `DOC-021` | `CHAT-012` |
| `DOC-025` | `CHAT-012` |
| `DOC-028` | `DEV-037`, `GH-047` |
| `DOC-029` | `GH-047` |
| `DOC-030` | `GH-047` |
| `DOC-036` | `GH-053` |
| `DOC-037` | `GH-053` |
| `DOC-038` | `GH-042` |
| `DOC-039` | `GH-042` |
| `DOC-042` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-043` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-044` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-045` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-057`, `GH-058` |
| `DOC-047` | `GH-053`, `GH-054`, `GH-057` |
<!-- RULE-XREF-IN-END -->

## Retired rule IDs

None. When a rule is retired later, record the ID and replacement/reason here; never silently recycle it.

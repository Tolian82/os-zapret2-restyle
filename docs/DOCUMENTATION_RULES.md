# Documentation rules

**Status:** CANONICAL · MANDATORY LEVEL 1
**Updated:** 2026-08-15

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

DOC-006. **Rule IDs are permanent identities, not ordinal positions.** Existing `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*` IDs are not renumbered merely because rules are inserted, moved, grouped, merged, or rewritten. A new rule receives the next unused ID in its domain. Cascade renumbering of following rules is prohibited; any earlier noncanonical convention implying such renumbering is cancelled and must not be restored.

DOC-007. **Cross-document references use rule IDs.** Active documents point to the canonical file and rule ID rather than copy full normative wording.

DOC-008. **A rule-book change requires same-scope consistency reconciliation.** Adding, moving, replacing, cancelling, materially rewriting, or exceptionally migrating an ID requires review of dependent active documents, cross-reference registries, navigation, and automated checks.

## Documentation purpose and authority

DOC-009. **Documentation is part of the architecture.** A logical change is incomplete if committed documentation cannot recover current intent, state, constraints, and next action.

DOC-010. **Zero-memory recovery is a design target.** A fresh session must recover current direction from a bounded mandatory set without reconstructing settled history from chat memory.

DOC-011. **Each active document has a bounded role.** State, handoff, roadmap, architecture, requirements, procedures, history, decisions, evidence, and navigation must not become interchangeable monoliths.

DOC-012. **One current fact has one primary current home.** Other active documents may link to it or summarize only what their own bounded role requires.

DOC-013. **Current authority and history are different.** Current rule books, current architecture, current state, and current handoff govern present work; archived or superseded material is read for rationale, chronology, or proof.

DOC-014. **[ОТМЕНЕНО] All useful current general normative information belongs in the four rule books; useful specialist information does not.** This rule was cancelled by the owner on 2026-08-14 because the remaining documentation-role, single-home, cold-start, reconciliation, and navigation rules already provide the required integrity without this additional blanket formulation. The ID and original wording remain here permanently so existing references do not become ambiguous.

## Engineering memory and cold start

DOC-015. **Engineering memory has three levels.** Level 1 is bounded mandatory recovery; Level 2 is current-line/current-task detail; Level 3 is historical/deep proof loaded on demand.

DOC-016. **A zero-memory cold start is context-first but rule-complete.** Read completely, in this order: root `AGENTS.md`; `START_HERE.md`; `PROJECT_STATE.md`; the four canonical rule books; `ROADMAP.md`; `INDEX.md`; then only specialist documents selected by the current handoff. GitHub mutation additionally applies `GH-006`.

DOC-017. **Level 2 owns richer current-line detail.** `docs/history/current/vX.Y.x.md` carries active-line chronology, supplemented by selected current-task specialist documents.

DOC-018. **Level 3 preserves detailed history.** Completed line archives plus original devlogs, patches, evidence, decisions, audits, releases, and Git history remain available without default loading.

DOC-019. **`INDEX.md` is the integrity/navigation map.** It routes to the four rule books, Level-1 state/handoff/plan, current ledger, completed version-line archives, specialist documentation, and deep record stores.

DOC-020. **Archiving never means deletion.** A compact archive may summarize a completed line while original detailed records remain intact and reachable.

## `START_HERE.md`

DOC-021. **`START_HERE.md` is the exact revision handoff.** It states what was just established at the current `_N` boundary, its effect, exact next action, and minimum specialist reading.

DOC-022. **The top of `START_HERE.md` provides direct orientation links.** `PROJECT_STATE.md` is first, followed by all four rule books, the master plan, and `INDEX.md`.

DOC-023. **`START_HERE.md` is not a patch diary.** It carries the current `_N` boundary rather than a copy of every previous revision.

DOC-024. **Current-work documentation follows one state-flow: `START_HERE -> PROJECT_STATE -> archive`.** Active work and the immediate next boundary live in `START_HERE.md`. When a result becomes a durable current fact for the active second-component line, it flows into `PROJECT_STATE.md`. When that line closes, the final state flows into the version-line archive under `DOC-028`–`DOC-030`. The current ledger and deep records may preserve chronology, rationale, measurements, and proof, but they are not parallel owners of current state.

DOC-025. **The handoff names the exact next task.** A fresh session must not rediscover completed investigations merely to identify the next approved change.

## `PROJECT_STATE.md` and archives

DOC-026. **`PROJECT_STATE.md` belongs to the active second-component line.** Its scope is defined by `DEV-029`–`DEV-031`; third-component and `_N` changes do not rotate it.

DOC-027. **`PROJECT_STATE.md` contains current facts, not chronology.** Keep identity, settled facts, active constraints/debt, next boundary, and direct evidence/architecture pointers.

DOC-028. **Second-component rollover archives final state.** An owner-authorized transition under `DEV-036`–`DEV-037` preserves the final old-line state snapshot before the new line is initialized.

DOC-029. **Every current `PROJECT_STATE.md` ends with archive links.** It directly links every completed version-line archive in chronological order while `INDEX.md` independently preserves global navigation.

DOC-030. **The final-state-snapshot archive model starts with closure of `v0.4.x`.** Earlier history is not retroactively rewritten merely to imitate the newer archive shape.

## Master plan and current ledger

DOC-031. **`ROADMAP.md` is the complete concise master plan.** It contains the short lifetime path, current priority, and every owner-approved or otherwise accepted future development direction at least once. Ideas, hypotheses, rejected options, and unapproved possibilities do not become roadmap commitments merely because they were mentioned.

DOC-032. **The roadmap keeps the major completed path visible without becoming a devlog.**

DOC-033. **The roadmap stays concise.** Detailed measurements, implementation chronology, and proof belong in the current ledger/deep records.

DOC-034. **The current-line ledger owns current chronology.** It carries richer ordered work/evidence that is too large for mandatory Level 1.

DOC-035. **Standalone deep records must add distinct value.** Create them for distinct chronology, rationale, proof, or reproducibility, not merely to duplicate another primary home.

## Reconciliation and release presentation

DOC-036. **Every logical development scope begins and ends with documentation reconciliation.** Before implementation, establish the current handoff/state/rules; before completion, reconcile every affected active fact, contract, handoff, plan, and proof pointer. The reconciliation decision is mandatory, but editing documentation files is not: when nothing documented changed, the correct result is an evidence-based no-op under `DOC-047`.

DOC-037. **Every GitHub delivery includes a documentation-impact decision and one complete documentation reconciliation.** Facts, contracts, handoff, plan, and governance that exist before an engineering/source merge belong in that same logical source PR. Immutable testing-package facts that do not exist until after that merge and successful publication are the single bounded exception: the generic publisher must create the docs-only publication-record PR defined by `GH-060`–`GH-061`, and that PR is part of the same delivery rather than a second engineering scope. Before that tail is merged, reconcile every affected current document whose bounded role actually changed; do not create a separate ad-hoc cleanup PR for publication facts.

DOC-038. **A full release includes a complete README review.** Before the release defined by `DEV-039` and executed under `GH-039`–`GH-046`, review `README.md` against actual capabilities, installation path, support boundary, release identity, and contributor navigation.

DOC-039. **README is human-facing, current, and concise.** It should be attractive, readable, understandable, and sufficiently complete without becoming an internal engineering dump.

DOC-040. **Selected mandatory documents are read through EOF.** If the handoff/rules select a document as mandatory for the current task, read the entire selected document.

DOC-041. **Documentation-policy changes are recorded here first.** Add or amend the appropriate persistent `DOC-*` rule before updating dependent active documents.

## Cross-reference integrity and maintainability

DOC-042. **Each canonical rule book contains an explicit cross-reference registry.** The registry lists every cross-book rule reference made by active rules in that file and every active cross-book rule reference made into that file.

DOC-043. **Cross-reference registries are bidirectional.** A source-book outbound reference and the target-book inbound reference must describe the same active source/target relationship.

DOC-044. **Rule-ID migration is exceptional and atomic.** Ordinary edits never renumber existing IDs. If an ID must be migrated, the old rule remains physically present and is marked `ЗАМЕНЕНО НА <ID>`; the same logical change updates every active rule body, registry, active-document reference, test, and navigation dependency before merge.

DOC-045. **CI protects rule-reference integrity.** It must reject duplicate canonical IDs, references to nonexistent IDs, active-rule dependencies on cancelled/replaced IDs, invalid replacement targets or cycles, stale registry entries, missing registry entries, or asymmetric inbound/outbound relationships.

DOC-046. **Current and newly written documentation uses clean standard Markdown.** Prefer one title, normal section headings, short paragraphs, bullets, tables, and code fences. Decorative separator walls such as long `=====` blocks are forbidden in current/active documents and new records. Historical Level-3 records need not be rewritten merely for style.

DOC-047. **Every GitHub change performs an explicit documentation-impact check.** The result may legitimately be “no documentation change required” when no documented fact, contract, handoff, plan, rule, or user-facing behavior changed; otherwise the documentation change belongs in the same delivery under `GH-053`–`GH-054`, including the bounded post-publication tail required by `GH-060`–`GH-061` when immutable testing-package facts are created only after source merge.

DOC-048. **[ОТМЕНЕНО] Compatibility pointers contain no independent current canon.** This rule was cancelled by the owner on 2026-08-14 for the former duplicate quick-reference documents. Those files are removed after repository-wide reference migration instead of being retained solely as compatibility placeholders. The ID and original wording remain reserved.

DOC-049. **Level-1 reading is repository-state scoped.** Once the mandatory set has been fully read for an exact repository state, unchanged files need not be repeatedly reloaded during the same continuous work. If `main` advances, compare the new state and reread every affected mandatory/current document before further mutation under `GH-004` and `GH-026`.

DOC-050. **Cancelled or replaced canonical rules are never physically deleted.** Keep the original rule at its permanent ID and place an explicit marker at the beginning of the rule title: `[ОТМЕНЕНО]` when it has no successor, or `[ЗАМЕНЕНО НА <ID>]` when another canonical rule supersedes it. Preserve enough original wording, date, and reason to understand what ceased to apply.

DOC-051. **A cancelled or replaced rule has no current normative force.** Active rules and current documents must be reconciled away from a cancelled rule or toward the replacement rule in the same logical change. Historical Level-3 records may continue to cite the old permanent ID as history.

DOC-052. **Rule lifecycle metadata is validated, not decorative.** Replacement targets must exist, replacement chains must terminate in an active rule, cycles are forbidden, cancelled/replaced IDs remain reserved, and an active canonical rule may not normatively depend on a cancelled/replaced rule.

DOC-053. **Internal Markdown links are repository integrity.** Every tracked local Markdown link must resolve to an existing repository file/directory and, when a local Markdown fragment is supplied, to an existing heading/anchor. Deleting or renaming a documentation path requires repository-wide link migration in the same logical scope; CI rejects dangling local links before merge.

DOC-054. **Choose rule lifecycle actions by meaning, not convenience.** Create a new rule only for a new durable normative principle that is not already covered. Modify an existing active rule when its normative identity remains the same and the change only clarifies, narrows, strengthens, or otherwise refines that same principle. Cancel a rule when its requirement no longer applies and has no successor. Replace a rule when the old normative meaning ceases to apply and a materially different durable rule takes its place. One-off tasks, current implementation facts, test results, temporary plans, and ordinary handoff state are not new canonical rules; route them through the current-work flow in `DOC-024` and the appropriate state/history documents.

## Cross-reference registry

This registry is part of the rule contract. It is maintained with rule changes and validated by CI under `DOC-042`–`DOC-045`.

### Outbound references

<!-- RULE-XREF-OUT-BEGIN -->
| Source rule | Target rules |
|---|---|
| `DOC-016` | `GH-006` |
| `DOC-026` | `DEV-029`, `DEV-030`, `DEV-031` |
| `DOC-028` | `DEV-036`, `DEV-037` |
| `DOC-037` | `GH-053`, `GH-060`–`GH-061` |
| `DOC-038` | `DEV-039`, `GH-039`–`GH-046` |
| `DOC-047` | `GH-053`, `GH-054`, `GH-060`–`GH-061` |
| `DOC-049` | `GH-004`, `GH-026` |
<!-- RULE-XREF-OUT-END -->

### Inbound references

<!-- RULE-XREF-IN-BEGIN -->
| Target rule | Referenced by |
|---|---|
| `DOC-003` | `CHAT-009` |
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
| `DOC-037` | `GH-053`, `GH-060`, `GH-061` |
| `DOC-038` | `GH-042` |
| `DOC-039` | `GH-042` |
| `DOC-042` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-043` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-044` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-058` |
| `DOC-045` | `DEV-046`, `CHAT-025`, `GH-055`, `GH-057`, `GH-058` |
| `DOC-047` | `GH-053`, `GH-054`, `GH-057` |
| `DOC-049` | `GH-006` |
| `DOC-053` | `GH-057`, `GH-059` |
<!-- RULE-XREF-IN-END -->

## Rule lifecycle

- `DOC-014` — **ОТМЕНЕНО**, 2026-08-14; no replacement.
- `DOC-048` — **ОТМЕНЕНО**, 2026-08-14; no replacement.

Cancelled/replaced IDs remain physically in this file and are never recycled.

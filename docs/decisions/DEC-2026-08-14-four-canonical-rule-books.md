# Decision: Four canonical rule books

Date: 2026-08-14
Status: **ACTIVE / SUPERSEDING GENERAL-RULE AUTHORITY ONLY**

## Context

Project rules had accumulated across `PROJECT_PRINCIPLES.md`, `DOCUMENTATION_RULES.md`, `GITHUB_PUBLICATION.md`, `AGENTS.md`, working/development guides, current state/roadmap, active decisions, and CI assertions. Several rules were repeated in more than one active-looking place: owner-canon precedence, `зафиксируй`, Russian chat language, version semantics, GitHub plugin/preflight, release meaning, and documentation rollover.

That duplication created two risks:

1. a future session could read two differently worded versions of the same current rule and treat them as competing authority;
2. a later rule change could update one copy while another active copy remained stale.

The owner therefore required exactly four rule domains and a full current-rule review across project documentation.

## Decision

Exactly four canonical general rule books exist:

1. `docs/DOCUMENTATION_RULES.md` — documentation governance, IDs `DOC-*`;
2. `docs/PROJECT_PRINCIPLES.md` — project-development rules/principles/assertions, IDs `DEV-*`;
3. `docs/CHAT_RULES.md` — owner/assistant chat interpretation and communication rules, IDs `CHAT-*`;
4. `docs/GITHUB_PUBLICATION.md` — GitHub operation/publication rules, IDs `GH-*`.

A current general rule has one normative home. Active supporting documents reference the appropriate rule ID rather than creating another normative formulation.

Technical product contracts remain in requirements/architecture even when they contain words such as `must`: stage orders, ports, file layouts, timeouts, protocol behavior, runtime ownership, and similar subsystem requirements are not general governance rules.

Historical decisions/devlogs/patches/evidence/releases/audits remain historical records. Their text is not destructively rewritten to pretend the four-book scheme existed in the past. When an old rule was superseded, it stays superseded; when an old decision contains rationale for a still-current rule, the current normative wording is the appropriate `DOC-*`, `DEV-*`, `CHAT-*`, or `GH-*` rule.

## Rule review applied

The consolidation explicitly rejects reactivation of superseded process ideas, including:

- blanket full GitHub inventory before every mutation instead of scope/risk preflight;
- treating every `VERSION` change as an automatic full release;
- forcing a release-only reset of `_N`;
- treating all possible live test rows as mandatory release blockers;
- allowing stale tests or old active-looking documentation to override newer owner canon.

Current equivalent rules were rewritten for one clear meaning and placed in their proper books.

## Active-document consequences

- `AGENTS.md` becomes a bootstrap map to the four rule books and current handoff/state.
- `START_HERE.md` exposes `PROJECT_STATE` first and all four rule books at the top.
- `PROJECT_STATE.md` contains current facts, not version/documentation procedure.
- `ROADMAP.md` contains the development plan, not version/release policy.
- `INDEX.md` preserves independent navigation/integrity to all four books, current memory levels, archives, and deep history.
- CI documentation/governance tests validate the four-book boundary and rule identities rather than requiring duplicated phrases in supporting documents.

## Follow-up — permanent rule lifecycle and removal of duplicate quick references

A later owner-approved refinement on the same date keeps the four-book decision intact and changes only its cleanup mechanics:

- `GITHUB_PUBLICATION.md` keeps its filename and is explicitly the complete fourth book, **Правила работы с GitHub**;
- `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md`, which had first been reduced to compatibility pointers, are physically removed after repository-wide reference migration because they contain no unique current canon;
- canonical rule IDs are permanent and are not cascade-renumbered;
- cancelled/replaced rules remain physically in their canonical books with lifecycle markers instead of disappearing;
- local Markdown links/anchors are CI-validated so documentation paths can be removed without leaving dangling tracked links.

The detailed follow-up is recorded in `DEC-2026-08-14-rule-lifecycle-and-link-integrity.md` and the current `DOC-*` rules.

`CONTRIBUTING.md` remains a bounded noncanonical contributor entrypoint; it does not become a fifth rule book.

## Supersession boundary

This decision supersedes **general-rule authority**, not historical rationale, in earlier governance decisions including the efficient/evidence-first GitHub, owner-canon, operational-handoff, documentation-memory, version/release, and repository-hygiene decisions.

Those records remain valid history/rationale and may still describe the reason a current rule exists. Their old standalone normative wording does not compete with the four canonical books after this decision.

Product-specific architecture/requirements decisions are not superseded by this organizational change.

## Package boundary

This is documentation/governance/CI-contract work only. `VERSION=0.4.1` and `PLUGIN_REVISION=12` remain unchanged under `DEV-033`; packaged runtime/source behavior is unchanged. The exact next product source patch remains `v0.4.1_13` Model-C-only production finalization.

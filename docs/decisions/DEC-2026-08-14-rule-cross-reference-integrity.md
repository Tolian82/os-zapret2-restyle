# Decision: Stable rule references and active-document consolidation

**Date:** 2026-08-14  
**Status:** ACTIVE · EXTENDS FOUR-RULE-BOOK DECISION

## Context

After establishing four canonical rule books, a second audit found three maintainability risks:

1. `GITHUB_WORKFLOW.md` still duplicated the task-routing value of the GitHub rule book, while `DEVELOPMENT_GUIDE.md` and `WORKING_CONVENTIONS.md` also acted as extra quick-reference stores;
2. rule IDs were used as cross-document references, but the repository had no explicit bidirectional registry showing which canonical rule depended on which other canonical rule;
3. treating numbered rules as an always-renumbered sequence would make one insertion capable of invalidating many otherwise correct references.

The owner also required cold-start recovery after total context loss, unavoidable force of explicit owner instructions, continuous documentation consistency after GitHub work, preservation of useful information, and a cleaner Markdown style.

## Decision

- The project continues to have exactly four canonical general rule books.
- `GITHUB_PUBLICATION.md` is the sole GitHub rule book and now includes the task-oriented route formerly carried by `GITHUB_WORKFLOW.md`.
- `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` remain only as small compatibility pointers so historical links do not break; they contain no independent mutable canon and are removed from active Level-2 reading.
- Existing rule IDs are persistent identities, not ordinal positions. Sorting or inserting rules does not renumber old IDs.
- Each canonical book contains explicit outbound and inbound cross-reference registries.
- CI validates actual cross-book rule references against those registries and rejects nonexistent, duplicate, missing, stale, or asymmetric references.
- Cold start becomes context-first: current handoff/state precede the complete four-book canon, while all rule books remain mandatory before mutation.
- Mandatory reading may be reused while the exact repository state is unchanged; an advanced `main` requires affected mandatory/current material to be reread.
- Explicit owner instructions are immediately binding and must produce execution, persisted canon, or an explicit blocker.
- A read-only boundary is inferred only from an actual prohibition, not from the word `проверь` or `аудит` when the same instruction explicitly requests mutation.
- Every GitHub delivery makes a documentation-impact decision; affected documentation changes in the same scope, while a genuinely unaffected document is not touched mechanically.
- Current and newly written documentation uses standard Markdown rather than decorative separator walls.

## Useful-information boundary

“All useful information lives in the four files” is interpreted as **all useful current general normative information**. Product-specific technical contracts, measurements, evidence, current facts, and chronology remain useful but keep their specialist homes. Copying all of them into Level 1 would increase memory cost, duplicate sources of truth, and make documentation less reliable.

## Historical formatting boundary

Large Level-3 aggregate history files such as `DECISIONS.md`, `AUDIT.md`, and `DEVLOG.md` still contain legacy `=====` formatting. This decision does not rewrite historical bodies merely for style. New/current documents follow the clean style immediately; a future deliberate style-only migration may reformat deep history without changing its meaning if worthwhile.

## Package boundary

This is documentation/governance/CI work only. `VERSION=0.4.1` and `PLUGIN_REVISION=12` remain unchanged. The next packaged source task remains `v0.4.1_13` Model-C-only production finalization.

# Decision: Permanent rule lifecycle and Markdown link integrity

**Date:** 2026-08-14
**Status:** ACTIVE · EXTENDS FOUR-RULE-BOOK GOVERNANCE

## Context

After stable rule IDs and bidirectional cross-reference registries were introduced, the owner tightened two remaining integrity boundaries.

First, cancelling or replacing a rule must never make its historical ID disappear. Deleting a numbered rule or cascade-renumbering later rules would make old references ambiguous and create unnecessary cross-reference churn.

Second, the three former quick-reference files `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` had already been reduced to compatibility pointers with no unique current canon. Keeping empty duplicate paths only to preserve links was no longer useful once repository-wide references could be migrated and validated automatically.

The owner also approved internal Markdown link/anchor validation and reaffirmed the context-first, repository-state-scoped cold-start model.

## Decision

### Permanent rule IDs

Canonical `DOC-*`, `DEV-*`, `CHAT-*`, and `GH-*` IDs are permanent identities.

- inserting, moving, regrouping, or rewriting rules does not cascade-renumber existing IDs;
- a cancelled rule remains physically in its canonical book and begins with `[ОТМЕНЕНО]`;
- a replaced rule remains physically in its canonical book and begins with `[ЗАМЕНЕНО НА <ID>]`;
- the original meaning, cancellation/replacement date, and reason remain recoverable;
- a cancelled/replaced ID is never recycled for another meaning;
- active normative dependencies are migrated away from cancelled IDs or to the replacement ID in the same logical change;
- replacement chains must terminate in an active rule and may not form cycles.

`DOC-014` is the first canonical rule cancelled under this lifecycle. Its blanket formulation that all useful current general normative information belongs in the four books is no longer needed because the remaining role, single-home, cold-start, reconciliation, and navigation rules already preserve documentation integrity.

`DOC-048`, which described retained compatibility-pointer files, is also cancelled because those three duplicate paths are now removed after reference migration.

The older noncanonical idea that inserting a rule should renumber all following rules is explicitly cancelled by the permanent-ID contract.

### Read-only interpretation

The former interpretation that words such as `проверь` or `аудит` automatically imply read-only mode is cancelled. It never had a permanent canonical ID. Active `CHAT-011` is the authoritative meaning: mutation is blocked only by a real explicit read-only boundary such as `никаких правок`, `только анализ`, or `только аудит`; a same-message explicit action instruction keeps its literal force.

### GitHub rule book

`docs/GITHUB_PUBLICATION.md` keeps its filename and is the fourth canonical book, **Правила работы с GitHub**. Its scope is all GitHub work, not publication only.

### Removal of duplicate quick-reference files

The following files are removed from the active repository tree after their useful current meaning and links are migrated:

- `docs/GITHUB_WORKFLOW.md`;
- `docs/DEVELOPMENT_GUIDE.md`;
- `docs/WORKING_CONVENTIONS.md`.

Their historical existence and previous content remain recoverable from Git and decision/history records. They do not need empty compatibility placeholders.

### Markdown link integrity

Tracked local Markdown links become a CI integrity contract.

- local file and directory targets must exist;
- local Markdown heading fragments must resolve;
- documentation deletion/rename requires repository-wide link migration in the same logical scope;
- a dangling tracked Markdown link blocks merge;
- historical text may still mention removed filenames as historical facts, but it must not contain a live local Markdown link to a missing path.

### Cold-start efficiency

The mandatory zero-memory route is context-first:

`AGENTS -> START_HERE -> PROJECT_STATE -> four canonical rule books -> ROADMAP -> INDEX -> selected specialists`.

Once Level 1 is completely read for an exact repository state, unchanged mandatory material may be reused during the same continuous work. If `main` advances, affected mandatory/current documents are reread before further mutation.

## Validation consequences

CI validates:

- unique permanent rule IDs;
- cancellation/replacement markers and replacement chains;
- no active canonical rule dependency on a cancelled/replaced ID;
- exact active inbound/outbound cross-reference registries;
- tracked local Markdown path and heading-fragment resolution;
- absence of the three removed duplicate quick-reference files;
- current navigation and cold-start routing.

## Package boundary

This is documentation/governance/test-contract work only. `VERSION=0.4.1` and `PLUGIN_REVISION=12` remain unchanged. Packaged runtime/source behavior is unchanged. The exact next product source task remains `v0.4.1_13` Model-C-only production finalization.

# Decision: Owner canon precedence and zero-memory recovery checkpoints

Date: 2026-08-14
Status: **ACCEPTED / ACTIVE**

## Context

The project already treated repository documentation as Engineering Memory, but two remaining failure
modes were still possible.

First, a newer owner decision could be acknowledged in conversation while older active documentation
still contained the previous direction. A later cold-start session could then read the stale document
and incorrectly treat it as a veto over the newer owner decision. Model C is the concrete example:
the owner selected Model C as the production direction, so historical A/B/C or `C -> B -> A` text
must never be able to move the project back to Model B merely because it was written earlier.

Second, the existing documentation contract described what a patch changed and the next plan, but it
did not state strongly enough that **every published GitHub project state is a recovery checkpoint
that must survive complete loss of conversational/model memory**. The required recovery horizon is
not one chat or one week: the repository should allow fast continuation even years later.

A smaller factual drift also demonstrated the same class of problem. The local/container DNS path
had historically been slow and unreliable and once blocked a local network fallback. The owner later
fixed DNS and reported that fact, but the old failure could still be repeated as if it were current.

## Decision

### 1. Newest owner instruction is intended-direction authority

The owner's newest unambiguous explicit instruction, or an explicitly confirmed decision after a
narrow clarification, is the current project canon for intended direction.

When it conflicts with older active documentation:

- the newer owner instruction wins immediately;
- old documentation does not block, veto or silently reverse it;
- if the new instruction has a material ambiguity, ask only the narrow clarification required;
- once unambiguous/confirmed, synchronize the affected active documentation before later work can
  consume the stale rule;
- keep old records as historical/superseded evidence where useful instead of rewriting history.

Applied current example: **Model C is the selected production direction.** Existing source fallback
through B/A is transition debt scheduled for removal, not authority to reopen model selection.

### 2. `PROJECT_PRINCIPLES` is cumulative

`docs/PROJECT_PRINCIPLES.md` is not a one-time snapshot. Every new durable active development/project
principle approved later must be added there in the first synchronized documentation change.

A principle left only in chat, a one-off patch record or this decision rationale is not sufficiently
persisted for future cold-start work.

### 3. Every substantive GitHub delivery is a zero-memory recovery checkpoint

Before the first substantive changed branch state is published, and again before Ready-PR/merge,
repository documentation must let a future session with no useful chat/model memory determine:

1. what was completed most recently;
2. what the current/latest logical delivery changes and why;
3. the intended effect and acceptance boundary;
4. the exact immediate next step;
5. the complete ordered plan with completed/superseded/deferred states;
6. the active development rules through `PROJECT_PRINCIPLES`;
7. where detailed chronological/evidence records live.

The mandatory startup path remains short. `START_HERE.md` carries the concise current/recent summary
and links to the detailed `docs/devlog/`, `docs/patches/` and evidence record rather than forcing every
new session to reread the entire historical log.

### 4. Current factual correction: DNS is no longer a known blocker

The historical local/container DNS problem is closed. DNS previously worked slowly and with failures;
the owner fixed it. Current documentation must treat DNS as working.

A future DNS diagnosis requires fresh reproducible evidence. The historical failure may be used as
history, not as an assumed current root cause.

## Consequences

- current active documentation must be updated when owner canon changes instead of asking old docs
  for permission to follow the new instruction;
- stale active wording is a synchronization defect, not a competing vote;
- permanent principles cannot be lost simply because they originated in a later chat;
- `START_HERE` becomes the mandatory short recent-work checkpoint in addition to exact-next handoff;
- `PROJECT_STATE` holds current facts, including environment facts such as the DNS correction;
- `ROADMAP` marks completed/superseded/deferred plan state rather than retaining obsolete priorities
  as gates;
- detailed patch/devlog/evidence records preserve chronology without bloating mandatory startup;
- a docs-only governance correction does not change package metadata.

## Supersession boundary

This decision extends the operational-memory architecture recorded by
`DEC-2026-08-14-operational-handoff-and-scope-first-preflight.md`.

It supersedes only interpretations that allow older active documentation to override a newer
unambiguous owner instruction, that allow new permanent principles to remain outside the canonical
principles file, or that treat a GitHub delivery as complete when its repository state is not
sufficient for zero-memory resumption.

It does not weaken source-code authority for actual implemented behavior, evidence-first debugging,
CI requirements, runtime safety, package/release boundaries or historical-record preservation.

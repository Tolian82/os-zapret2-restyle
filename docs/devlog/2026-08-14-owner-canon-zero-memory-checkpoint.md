# Devlog — 2026-08-14 — Owner canon / zero-memory recovery checkpoint

Scope: documentation/governance only; `VERSION=0.4.1`, `PLUGIN_REVISION=12` unchanged.

## Trigger

Before further code work, the owner corrected the working documentation contract:

- an old note still treated the local/container DNS problem as current even though the owner had
  already fixed DNS; historically DNS had been slow and unreliable;
- the owner reiterated that a new explicit instruction is the new project canon and old documentation
  must be synchronized rather than used to block/reverse it;
- Model C was given as the concrete example: once the owner selected Model C, old A/B/C or Model-B
  text could not remain an effective future gate;
- the owner required all future durable principles to be added to the short always-read canonical
  principles file;
- the documentation goal was widened from “a cold session can find the next patch” to “after any
  interruption and complete memory loss, even years later, the repository alone lets work continue
  quickly at the exact boundary.”

## Baseline read before mutation

Verified through the connected GitHub plugin:

- `main`: `2a3a50176ee94c555cc45be4c587c9509a0a50cf`;
- `VERSION=0.4.1`;
- `PLUGIN_REVISION=12`;
- open same-scope PRs: none;
- `docs/GITHUB_PUBLICATION.md` read through EOF before mutation.

The existing `_12` operational-memory work was effective but did not explicitly encode owner-canon
precedence, cumulative future principles, the broader zero-memory recovery horizon or the corrected
DNS fact.

## Documentation change

The synchronized corrective:

- adds owner-canon precedence and zero-memory checkpoint rules to `PROJECT_PRINCIPLES` and `AGENTS`;
- makes `PROJECT_PRINCIPLES` explicitly cumulative for all future durable principles;
- adds a mandatory “most recent completed logical work” section to `START_HERE`;
- records DNS as fixed/currently working in `START_HERE` and `PROJECT_STATE`;
- records Model C as current owner canon and B/A production fallback only as transition debt;
- strengthens `ROADMAP` with completed governance milestones and explicit supersession semantics;
- makes `INDEX` point to the latest continuity decision/patch/devlog;
- strengthens `DEVELOPMENT_GUIDE` and `GITHUB_PUBLICATION` so every substantive GitHub delivery is a
  zero-memory recovery checkpoint;
- records rationale in `DEC-2026-08-14-owner-canon-and-zero-memory-recovery.md`;
- records the logical delivery contract in
  `docs/patches/v0.4.1_12-owner-canon-zero-memory-checkpoint.md`.

## Intended effect

A future session that remembers nothing must not rediscover these facts from chat or infer them from
old history. Mandatory startup documents must make it immediately clear that:

- newest owner canon wins over conflicting stale docs;
- new durable principles are persisted in `PROJECT_PRINCIPLES`;
- DNS is no longer a known blocker;
- Model C remains the selected production direction;
- `_13` remains the next packaged source task unless the owner supplies newer priority;
- overall completed/deferred/long-term work remains visible.

## Immediate continuation after this docs checkpoint

After verified merge of this docs-only change, no package is published. The next packaged source
change remains `v0.4.1_13`: make Model C the only normal production Stage-60 runtime and remove silent
production B/A replay, unless a newer owner instruction supersedes that priority.

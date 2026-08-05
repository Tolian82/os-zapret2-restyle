# 2026-08-05 — Reconcile Strategy Lab revision 35 with GitHub title governance

## Scope

Preserve the complete verified Strategy Lab hardening tree through revision 35 while
integrating the universal versioned-title governance merged into current `main`.

## Conflict

Accumulated PR #83 predates the rule that every PR-branch commit subject must begin with
the exact package-candidate prefix derived from the PR head. Its history contains work
and repair subjects created while the candidate advanced from revision 25 through 35.

Merging current `main` into that history would preserve file content but could never make
all historical subjects begin with `v0.3.2_35:`. Rewriting `main` is forbidden, and force-
rewriting the historical PR would discard useful review and CI evidence.

## Resolution

- use current `main` commit `bdea1e41427b6fa9ff8428f08618c1f45ed44a75` as the new
  parent;
- preserve the verified revision-35 `src` tree and product test tree from
  `4525b2dc333b1e3bd3b165c587dd68169c09f73d`;
- preserve current `main` GitHub workflows, title enforcement, `AGENTS.md`, and publication
  governance;
- merge Strategy Lab architecture, audit, patch, decision, devlog, index, and current-
  state records explicitly;
- mark the former serial-delivery decision as superseded while retaining it as historical
  evidence;
- retain the Strategy Lab hardening decision as active product authority and remove its
  obsolete process conflict;
- publish one replacement commit and PR titled
  `v0.3.2_35: Unify replay-verified protocol results`;
- keep PR #83 as historical evidence and close it only after the replacement PR exists.

## Verification contract

The replacement PR must prove:

- exactly one commit is ahead of the current `main` base;
- its commit subject and PR title both begin with `v0.3.2_35:`;
- current universal-title and post-merge integrity controls are present unchanged;
- all revision-35 product source, tests, architecture, audit, devlog, and patch records are
  present;
- full project validation and the FreeBSD package build succeed on the reconciled head;
- the final squash merge preserves the same versioned subject.

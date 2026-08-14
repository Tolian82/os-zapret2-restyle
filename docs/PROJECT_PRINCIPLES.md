# os-zapret2-restyle — Project principles

Status: **CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT**

This file contains permanent **project/development** principles. All documentation-specific rules are
canonically enumerated in [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md); detailed GitHub delivery
procedure lives in [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md). Rationale lives in decisions.

## Canonical principles

1. **Documentation is part of the project architecture.** Critical project knowledge must not depend
   on chat history or model memory. Apply the complete numbered documentation contract in
   `DOCUMENTATION_RULES.md`.

2. **The owner's newest unambiguous instruction or project fact is current canon.** It supersedes
   conflicting older active documentation, tests and plans immediately.

3. **Once accepted, owner canon stays locked until explicitly changed or directly disproved by fresh
   reproducible evidence.** Old documentation, an old roadmap item, a new chat or missing model memory
   is not counter-evidence.

4. **The owner-canon “Суслик” rule is permanent.** If active documentation contradicts the owner's
   newest unambiguous words, reconcile the documentation; do not reinterpret the owner's words to
   preserve stale text.

5. **`Зафиксируй` / `record this` requires full active-documentation reconciliation at the first GitHub
   documentation opportunity.** Record the canon and remove every active contradiction in the same
   logical change; history may retain old statements only as clearly historical/superseded material.

6. **A stale test never outranks current project canon.** Update stale assertions/contracts rather than
   bending current architecture or documentation back toward obsolete intent.

7. **Committed source code is authoritative for implemented behavior; documentation is authoritative
   for approved intent, current state, current task and plan.** Explicitly document transition debt
   until implementation catches up with approved direction.

8. **Every published GitHub project state is a zero-memory recovery checkpoint.** A future session must
   be able to resume from repository documentation without conversational memory.

9. **Every development stage begins with documentation and ends with documentation.** Record objective,
   plan and expected verification before work; record meaningful decisions during work; reconcile
   result, current facts, plan progress and exact continuation after work.

10. **Every GitHub delivery includes synchronized documentation.** State what changes and why, intended
    effect/acceptance, what was actually verified, the immediate next step and the complete concise
    future plan required by `DOCUMENTATION_RULES.md`.

11. **Owner-facing project communication is normal understandable Russian by default.** Internal
    English GitHub/CI terminology is used only when necessary and is translated or explained.

12. **Repository hygiene is continuous and normally silent.** Keep the tree, branches, documentation
    paths and tracked artifacts orderly; preserve unique work before deleting temporary branches.

13. **Correctness over speed; preserve working behavior before optimization.** Prefer minimal,
    reviewable and sufficient changes over speculative completeness.

14. **Audit before refactoring/removing inherited behavior when scope requires it.** Existing evidence
    is the starting point; loss of conversational memory is not itself a reason to repeat an audit.

15. **One logical scope per project change.** Same-scope repair commits may share one task branch/PR;
    `main` receives one verified squash commit. Affected documentation belongs to the same scope.

16. **Validate before activation/publication.** Never claim a check passed unless it ran; diagnose
    failures from exact evidence and do not modify source to mask external infrastructure failure.

17. **GitHub plugin first.** Use the connected GitHub plugin as the mandatory first repository
    interface. A narrow fallback is allowed only for an exact confirmed missing operation while the
    plugin is otherwise available.

18. **Preflight is scope/risk based.** Always verify current `main`, package metadata, current handoff/
    state/plan and same-scope PR state. Expand to broad tree/release/branch inventory when the task
    actually needs it; owner-canon reconciliation is a broad active-document sweep by definition.

19. **Published history is forward-only.** Never force-update `main`, move published tags or rewrite
    published release/package history.

20. **Package identity is deterministic and version roles are explicit.** `VERSION` is the project
    version source and `PLUGIN_REVISION` is the package revision suffix. In `v0.4.2_14`, `4` is the
    second numeric component/state line, `2` is the third numeric component/development stage and
    `_14` is the exact package patch/iteration.

21. **Ordinary same-stage packaged source changes increment only `PLUGIN_REVISION`.** Documentation/
    governance/CI-only changes change neither `VERSION` nor `PLUGIN_REVISION`.

22. **A genuine new development stage changes the third numeric component and resets the package
    revision to `_1`.** A third-component-only transition does not itself mean a full release.

23. **Changing the second numeric component is owner-controlled and always means a full release.** The
    second component is the `4` in `0.4.x`; the assistant must never initiate `v0.4.x -> v0.5.x` by
    inference. Explicit owner instruction/approval is required.

24. **A full release does not imply a second-component change and does not by itself reset `_N`.** A
    full release may use the current exact package candidate. Revision reset is caused by a new third-
    component or second-component stage transition, not merely by release publication.

25. **A full release is an installation-ready OPNsense delivery.** It includes the exact candidate
    package, semantic tag, GitHub Release assets/checksum, matching Pages/pkg repository and Web-GUI
    install/update availability. Every full release also includes a complete human-facing README review.

26. **Owner-facing testing packages live persistently on GitHub but are not full releases.** Actions
    artifacts/local files are build evidence only; a testing `.pkg` does not promote Pages/pkg repo.

27. **Runtime safety is fail-closed.** Preserve transactional Apply, bounded lifecycle behavior,
    cleanup/cancellation containment and exact semantic restoration across Strategy Lab/runtime changes.

28. **OPNsense commands target root `csh`.** POSIX-only syntax must explicitly enter `sh`/`/bin/sh` and
    return with `exit`.

29. **Documentation structure, version-state flow, master-plan completeness and archive behavior are
    governed only by the numbered rules in `DOCUMENTATION_RULES.md`.** Do not create competing active
    formulations in specialist documents.

30. **Current settled product facts remain settled until changed by owner or fresh direct evidence.**
    DNS is fixed/currently working; Model C is the selected normal production Stage-60 direction;
    A/B/C model selection is closed.

## Authority map

- `docs/DOCUMENTATION_RULES.md` — numbered canonical documentation rules;
- `docs/START_HERE.md` — exact current `_N` revision handoff;
- `docs/PROJECT_STATE.md` — current facts for the active second-component line;
- `docs/ROADMAP.md` — complete concise master development plan;
- `docs/history/current/` — richer current second-component-line chronology;
- `docs/history/archive/` — completed second-component archive maps/final-state snapshots from v0.4.x onward;
- `docs/WORKING_CONVENTIONS.md` — day-to-day engineering application;
- `docs/GITHUB_PUBLICATION.md` — authoritative GitHub/package/release procedure;
- `docs/ARCHITECTURE.md` / `docs/architecture/` — current technical architecture;
- `docs/devlog/` / `docs/patches/` / `docs/verification/` / `docs/releases/` / `docs/decisions/` — deep durable records;
- `docs/INDEX.md` — navigation/integrity map.

If a permanent project principle changes, update this file. If a documentation rule changes, update
`DOCUMENTATION_RULES.md` with the next sequential rule number and reconcile affected active documents
and tests in the same logical change.

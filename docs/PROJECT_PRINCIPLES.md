# os-zapret2-restyle — Project principles

Status: **CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT**

This file contains the permanent principles that must always be in context. It is cumulative: every
new durable project/development principle approved by the owner must be added here in the first
synchronized documentation change. Rationale lives in `docs/DECISIONS.md` / `docs/decisions/`;
detailed procedures live in specialist documents.

## Canonical principles

1. **Documentation is part of the project architecture.** It is the mandatory repository authority
   for approved decisions, documented project state and the current/long-term plan. Critical project
   knowledge must not depend on chat history or model memory.

2. **The owner's newest unambiguous instruction or project fact is current canon.** A newer explicit
   owner instruction, explicit project fact, or explicitly confirmed decision supersedes conflicting
   older documentation, tests and plans immediately. Old material cannot veto, weaken or silently
   reverse it. If the owner's statement is already unambiguous, do not ask for confirmation merely
   because old documentation says something else.

3. **Once accepted, owner canon stays locked until it is explicitly changed or directly disproved by
   fresh evidence.** Do not repeatedly ask whether a previously confirmed fact/decision is still true.
   Reopen it only when the owner changes it or new direct reproducible evidence contradicts the fact.
   Historical disagreement, an old test assertion, an old roadmap item, a new chat or missing model
   memory is not evidence. Current examples: DNS is fixed; Model C is the selected production
   direction.

4. **`Зафиксируй` / `record this` requires immediate full active-documentation reconciliation.** At
   the first GitHub documentation opportunity after such an instruction, record the canon and review
   all active/current documentation that could contradict it. Correct every active contradiction in
   the same logical documentation change. Historical records may retain the old state only when they
   are clearly historical/superseded and cannot be mistaken for current authority.

5. **A stale test never outranks current project canon.** If a test or CI contract encodes an obsolete
   decision, the test is stale. Update the stale test/contract and current documentation as required;
   never distort current documentation or architecture merely to satisfy an obsolete assertion.

6. **Committed source code is authoritative for actual implemented behavior.** Documentation and
   source answer different questions: source says what the code does; documentation says what has
   been approved, what state the project is in and what should happen next. When current source still
   implements transition debt (for example `_12` production fallback) while owner canon selects its
   replacement, document that difference explicitly and remove the debt according to the current
   plan. Source does not get a vote on already-settled product direction.

7. **The canonical principles layer is cumulative.** A durable principle must not exist only in chat,
   a one-off patch note or a decision rationale. Add every new active principle to this file in the
   first documentation synchronization that follows its approval, and update/supersede an older
   principle here when the owner changes it.

8. **Every published GitHub project state is a zero-memory recovery checkpoint.** After a complete
   loss of chat/model memory — even years later — repository documentation must be sufficient to
   resume quickly at the exact current boundary. The mandatory handoff must expose at least: the
   most recent completed logical work, what the current/latest delivery changed and the intended
   effect, the exact immediate next step, the ordered overall plan with completed/superseded/deferred
   states, and the active development rules through this canonical file. Detailed chronology may live
   in devlog/patch/evidence records, but the current handoff must point to the relevant record.

9. **Every development stage begins with documentation and ends with documentation.** Before work,
   record the objective, implementation plan and expected verification. During work, record approved
   decisions/discoveries that change later work. After work, record what changed, what was verified,
   what remains unresolved, current state, roadmap progress and the exact next stage.

10. **Every GitHub delivery includes synchronized documentation.** Before publication it must state:
    (a) what changes and why; (b) expected result and acceptance boundary; (c) the complete ordered
    next plan, including near-term and long-term/deferred actions. Reconcile that plan immediately
    before publication and update it first when implementation/testing or a newer owner instruction
    changed priorities.

11. **Owner-facing project communication is clear Russian by default.** Status updates and results to
    the owner must be written in normal understandable Russian. GitHub/CI/internal English labels may
    be shown only when materially useful and must be translated/explained in the same message. Do not
    make the owner decode phrases such as `latest head`, `Ready PR`, `exact-head`, `governance`,
    `hygiene`, or raw check names merely to understand whether work succeeded or failed.

12. **Repository hygiene is continuous and normally silent.** Keep the repository tree and branch
    set orderly at every completed operation. Before deleting a temporary branch, verify whether it
    contains useful unique work; preserve/merge useful work first, otherwise remove the branch after
    completion. Routine cleanup is part of the task and should not be pushed back to the owner or
    reported as a problem unless a real permission/tooling boundary prevents safe completion.

13. **Correctness over speed; preserve working behavior before optimization.** Prefer minimal,
    reviewable changes and reasonable sufficiency over speculative completeness.

14. **Audit before refactoring/removing inherited behavior when the task requires it.** Audits are
    first-class project work when requested by the owner, scheduled by the current plan, required by
    a refactor/removal boundary or triggered by new evidence. Existing audit/evidence is the starting
    point; absence of conversational memory is not itself a reason to repeat an audit.

15. **One logical scope per project change.** One task branch and one PR may contain same-scope repair
    commits; `main` receives one verified squash commit. Affected documentation belongs to the same
    logical change.

16. **Validate before activation/publication.** Never claim a test passed unless it ran. Diagnose
    failures from exact evidence; external infrastructure failure does not justify source changes.

17. **GitHub plugin first.** Use the connected GitHub plugin as the mandatory first repository
    interface. Fallback is narrow and only for an exact missing function/permission while the plugin
    is responding. Plugin unavailability stops GitHub work.

18. **Preflight is scope/risk based.** Always verify current `main`, package metadata, current plan and
    same-scope PR state. Expand to broad branch/workflow/tag/release/tree inventory only when the
    current operation or investigation needs it. A requested canon/documentation reconciliation is a
    broad active-documentation audit by definition when multiple authority files could conflict.

19. **Published history is forward-only.** Never force-update `main`, move a published tag or rewrite
    published release/package history.

20. **Package identity is deterministic.** `VERSION` is the semantic version source;
    `PLUGIN_REVISION` identifies packaged source revisions. Packaged source changes increment the
    revision once; docs/governance-only changes do not.

21. **Owner-facing testing packages live persistently on GitHub.** Actions artifacts/local files are
    build evidence, not final package delivery. A testing-package publication is not a stable/full
    semantic release.

22. **Runtime safety is fail-closed.** Transactional Apply, bounded lifecycle behavior, cleanup and
    semantic restoration must be preserved across Strategy Lab/runtime changes.

23. **OPNsense commands target root `csh`.** POSIX-only shell syntax must explicitly enter
    `sh`/`/bin/sh` and return with `exit`.

## Authority map

- `docs/START_HERE.md` — exact operational handoff, latest completed logical change and current task;
- `docs/PROJECT_STATE.md` — current factual project/repository/product/environment state;
- `docs/ROADMAP.md` — ordered near-term and long-term plan with completed/superseded/deferred status;
- `docs/WORKING_CONVENTIONS.md` — how these principles are applied day to day;
- `docs/GITHUB_PUBLICATION.md` — authoritative GitHub delivery procedure;
- `docs/ARCHITECTURE.md` / `docs/architecture/` — current technical architecture only;
- `docs/devlog/` / `docs/patches/` / `docs/verification/` — durable chronology and evidence;
- `docs/INDEX.md` — navigation only.

If a permanent principle is created, changed or superseded, update this file and its decision/procedure
in the same logical documentation change. Do not create competing active formulations of these
principles in current-state or specialist docs.

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

2. **The owner's newest unambiguous instruction is the current project canon for intended direction.**
   A newer explicit owner instruction or explicitly confirmed decision supersedes conflicting older
   documentation immediately. Old documentation cannot veto or silently reverse the new direction.
   If the instruction has a material ambiguity, ask only the narrow clarification needed; once the
   direction is unambiguous/confirmed, synchronize the affected active documentation before later
   work can consume the stale rule. Preserve superseded material as history where useful, but never
   present it as current authority.

3. **Committed source code is authoritative for actual implemented behavior.** Documentation and
   source answer different questions: source says what the code does; documentation says what has
   been approved, what state the project is in and what should happen next. A contradiction between
   them is a synchronization defect: verify the narrow mismatch and reconcile it before proceeding;
   never silently choose whichever side is more convenient.

4. **The canonical principles layer is cumulative.** A durable principle must not exist only in chat,
   a one-off patch note or a decision rationale. Add every new active principle to this file in the
   first documentation synchronization that follows its approval, and update/supersede an older
   principle here when the owner changes it.

5. **Every published GitHub project state is a zero-memory recovery checkpoint.** After a complete
   loss of chat/model memory — even years later — repository documentation must be sufficient to
   resume quickly at the exact current boundary. The mandatory handoff must expose at least: the
   most recent completed logical work, what the current/latest delivery changed and the intended
   effect, the exact immediate next step, the ordered overall plan with completed/superseded/deferred
   states, and the active development rules through this canonical file. Detailed chronology may live
   in devlog/patch/evidence records, but the current handoff must point to the relevant record.

6. **Every development stage begins with documentation and ends with documentation.** Before work,
   record the objective, implementation plan and expected verification. During work, record approved
   decisions/discoveries that change later work. After work, record what changed, what was verified,
   what remains unresolved, current state, roadmap progress and the exact next stage.

7. **Every GitHub delivery includes synchronized documentation.** Before publication it must state:
   (a) what changes and why; (b) expected result and acceptance boundary; (c) the complete ordered
   next plan, including near-term and long-term/deferred actions. Reconcile that plan immediately
   before publication and update it first when implementation/testing or a newer owner instruction
   changed priorities.

8. **Correctness over speed; preserve working behavior before optimization.** Prefer minimal,
   reviewable changes and reasonable sufficiency over speculative completeness.

9. **Audit before refactoring/removing inherited behavior when the task requires it.** Audits are
   first-class project work when requested by the owner, scheduled by the current plan, required by
   a refactor/removal boundary or triggered by new evidence. Existing audit/evidence is the starting
   point; absence of conversational memory is not itself a reason to repeat an audit.

10. **One logical scope per project change.** One task branch and one PR may contain same-scope repair
    commits; `main` receives one verified squash commit. Affected documentation belongs to the same
    logical change.

11. **Validate before activation/publication.** Never claim a test passed unless it ran. Diagnose
    failures from exact evidence; external infrastructure failure does not justify source changes.

12. **GitHub plugin first.** Use the connected GitHub plugin as the mandatory first repository
    interface. Fallback is narrow and only for an exact missing function/permission while the plugin
    is responding. Plugin unavailability stops GitHub work.

13. **Preflight is scope/risk based.** Always verify current `main`, package metadata, current plan and
    same-scope PR state. Expand to broad branch/workflow/tag/release/tree inventory only when the
    current operation or investigation needs it.

14. **Published history is forward-only.** Never force-update `main`, move a published tag or rewrite
    published release/package history.

15. **Package identity is deterministic.** `VERSION` is the semantic version source;
    `PLUGIN_REVISION` identifies packaged source revisions. Packaged source changes increment the
    revision once; docs/governance-only changes do not.

16. **Owner-facing testing packages live persistently on GitHub.** Actions artifacts/local files are
    build evidence, not final package delivery. A testing-package publication is not a stable/full
    semantic release.

17. **Runtime safety is fail-closed.** Transactional Apply, bounded lifecycle behavior, cleanup and
    semantic restoration must be preserved across Strategy Lab/runtime changes.

18. **OPNsense commands target root `csh`.** POSIX-only shell syntax must explicitly enter
    `sh`/`/bin/sh` and return with `exit`.

## Authority map

- `docs/START_HERE.md` — exact operational handoff, latest completed logical change and current task;
- `docs/PROJECT_STATE.md` — current factual project/repository/product/environment state;
- `docs/ROADMAP.md` — ordered near-term and long-term plan with completed/superseded/deferred status;
- `docs/WORKING_CONVENTIONS.md` — how these principles are applied day to day;
- `docs/GITHUB_PUBLICATION.md` — authoritative GitHub delivery procedure;
- `docs/devlog/` / `docs/patches/` / `docs/verification/` — durable chronology and evidence;
- `docs/INDEX.md` — navigation only.

If a permanent principle is created, changed or superseded, update this file and its decision/procedure
in the same logical documentation change. Do not create competing active formulations of these
principles in current-state or specialist docs.

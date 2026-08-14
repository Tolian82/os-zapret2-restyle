# os-zapret2-restyle — Project principles

Status: **CANONICAL / MANDATORY READING IN EVERY PROJECT CONTEXT**

This file answers one question: **Which permanent principles must always be in context?**

It is intentionally short. Historical rationale belongs in `docs/DECISIONS.md`; detailed working
procedures belong in `docs/WORKING_CONVENTIONS.md`, `docs/GITHUB_PUBLICATION.md` and specialist
documents.

## Canonical principles

1. **Documentation is part of the project architecture and is the mandatory repository source of
   current project state, decisions and plan. Critical project knowledge must not depend on chat
   history or model memory.**

2. **Every development stage begins with documentation and ends with documentation.** Before work,
   record the objective, implementation plan and expected verification. During work, record approved
   concepts/architecture discoveries that affect later work. After work, record what changed, what
   was verified, what remains unresolved, current state, roadmap progress and the next stage.

3. **Every GitHub delivery includes synchronized documentation.** Before publication it must state:
   (a) what changes and why; (b) what result is expected and how it will be accepted; (c) the complete
   next plan, including near-term and long-term actions. Immediately before publication, reconcile
   that plan with what implementation/testing actually learned and update it if priorities changed.

4. **Repository source is authoritative for committed project state.** Generated runtime is never
   committed. Unpublished owner-local changes are a separate explicit boundary and must not be
   reconstructed from memory.

5. **Correctness over speed; preserve working behavior before optimization.** Prefer minimal,
   reviewable changes and reasonable sufficiency over speculative completeness.

6. **Audit before refactoring or removing inherited behavior.** Audits are first-class project work
   when the owner or current plan requires them. Existing evidence is the starting point; do not
   assume prior work did not happen simply because a new chat started.

7. **One logical scope per project change.** One task branch and one PR may contain same-scope repair
   commits; `main` receives one verified squash commit. Documentation affected by the scope belongs
   in the same logical change.

8. **Validate before activation/publication.** Never claim a test passed unless it actually ran.
   Diagnose failures from exact evidence; external infrastructure failure does not justify source
   changes.

9. **GitHub plugin first.** Use the connected GitHub plugin as the mandatory first repository
   interface. Fallback is narrow and only for an exact missing function/permission while the plugin
   is responding. Plugin unavailability stops GitHub work.

10. **Preflight is scope/risk based.** Always verify current `main`, package metadata, current plan and
    same-scope PR state. Expand to full branch/workflow/tag/release/tree inventory only when the
    operation or investigation actually requires it.

11. **Published history is forward-only.** Never force-update `main`, move a published tag or rewrite
    published release/package history.

12. **Package identity is deterministic.** `VERSION` is the single semantic version source;
    `PLUGIN_REVISION` identifies packaged source revisions. Packaged source changes increment the
    revision once; docs/governance-only changes do not.

13. **Owner-facing testing packages live persistently on GitHub.** Actions artifacts/local files are
    build evidence, not final package delivery. A testing-package publication is not a stable/full
    semantic release.

14. **Runtime safety is fail-closed.** Transactional Apply, bounded lifecycle behavior, cleanup and
    semantic restoration must be preserved across Strategy Lab/runtime changes.

15. **OPNsense commands target root `csh`.** POSIX-only shell syntax must be explicitly placed inside
    `sh`/`/bin/sh` and returned with `exit`.

## Authority and maintenance

- Read this file in every new or resumed project context, immediately after `AGENTS.md`.
- `docs/DECISIONS.md` records why these principles were approved.
- `docs/WORKING_CONVENTIONS.md` records detailed settled procedures and domain-specific rules.
- `docs/START_HERE.md` records current operational handoff.
- `docs/PROJECT_STATE.md` records current state.
- `docs/ROADMAP.md` records ordered future work.
- If a permanent principle changes, update this file and the corresponding decision/procedure in the
  same logical change.
- Do not duplicate alternative formulations of these principles in current-state or specialist
  documents; reference this file instead.

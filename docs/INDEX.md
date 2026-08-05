# os-zapret2-restyle — Engineering Memory Index

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where should I look first?

Purpose:
Define the mandatory context-recovery order and identify the specialist authority for
each class of project information.

Updated when:
A document is added, removed, renamed, reordered, or given a different responsibility.

Read after:
Repository-root `AGENTS.md`.

Do not store here:
Detailed project state, decisions, implementation history, architecture, or procedures.

==================================================
MANDATORY READING ORDER
==================================================

Before diagnosis, commands, repository mutation, or publication, read in this order:

1. `docs/INDEX.md`
2. `docs/PROJECT_STATE.md`
3. `docs/AUDIT.md`
4. `docs/DECISIONS.md`
5. `docs/WORKING_CONVENTIONS.md`
6. `docs/DEVELOPMENT_GUIDE.md`
7. `docs/ARCHITECTURE.md`
8. `docs/DEVLOG.md`
9. `docs/ROADMAP.md`
10. `docs/REQUIREMENTS.md`
11. `docs/GITHUB_WORKFLOW.md`
12. `docs/GITHUB_PUBLICATION.md`

`docs/GITHUB_PUBLICATION.md` is the final specialist authority immediately before any
GitHub mutation. Its current atomic-commit, one-remote-branch, automatic-cleanup,
patch/release, PR, check, and merge rules supersede older generic Draft/Ready or
repair-commit wording that remains in historical or general documents.

==================================================
DOCUMENT MAP
==================================================

`PROJECT_STATE.md`
Where is the project now?

`AUDIT.md` and `docs/audit/`
What has been checked, what is broken, and what requires evidence?

`DECISIONS.md` and `docs/decisions/`
Why was a project rule or architecture choice approved?

`WORKING_CONVENTIONS.md`
Which permanent engineering rules are settled?

`DEVELOPMENT_GUIDE.md`
How is normal development performed?

`ARCHITECTURE.md` and `docs/architecture/`
How is the plugin built and how do components interact?

`docs/architecture/STRATEGY_LAB_ACTIVATION.md`
How does the asynchronous Diagnostics path replace synchronous Blockcheck?

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
What is the current authoritative Strategy Lab state machine, timing, cancellation, restoration, target, result, and circular-validation contract?

`docs/USER_GUIDE_STRATEGY_LAB.md`
How does an operator use Strategy Lab and temporary circular validation?

`DEVLOG.md` and `docs/devlog/`
What work and verification were completed?

`ROADMAP.md`
What is ordered next?

`REQUIREMENTS.md`
What must the product do?

`GITHUB_WORKFLOW.md`
How are repository maintenance, package patches, and project releases controlled?

`GITHUB_PUBLICATION.md`
How is one clean logical change delivered with exactly one remote task branch and
automatic cleanup?

`CHANGELOG.md`, `docs/releases/`, and `docs/patches/`
What changed in a published release or an ordinary package patch?

==================================================
PRECEDENCE
==================================================

1. The project owner's explicit current instruction defines scope and release version.
2. Repository-root `AGENTS.md` defines blocking entry rules.
3. This index defines reading order and specialist ownership.
4. The relevant specialist document controls its subject.
5. Historical records remain evidence but do not override later active decisions.
6. Historical DIAG, audit, devlog, release, and patch records require an explicit status banner when their wording can be mistaken for current behavior.

Never infer current state only from chat history, a prior summary, or an older release
record. Re-read current `main` and the applicable specialist document.

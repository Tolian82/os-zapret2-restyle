# os-zapret2-restyle

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where should I look?

Purpose:
Provide the entry point, reading order, and responsibility map for the complete
engineering memory system.

Updated when:
A document is added, removed, renamed, reordered, or assigned a different
responsibility.

Read after:
Nothing. Read this document first.

Do not store here:
Detailed project state, decisions, rules, procedures, architecture, history,
roadmap items, or product requirements.

==================================================
START HERE
==================================================

This repository uses an engineering memory system.

All engineering documentation is stored in the `docs/` directory. Document names
in this index omit the `docs/` prefix for readability unless a repository-relative
path is required.

Do not begin development from chat history or memory alone.

Read the documents in this exact order:

1. INDEX.md
2. PROJECT_STATE.md
3. AUDIT.md
4. DECISIONS.md
5. WORKING_CONVENTIONS.md
6. DEVELOPMENT_GUIDE.md
7. ARCHITECTURE.md
8. DEVLOG.md
9. ROADMAP.md
10. REQUIREMENTS.md

==================================================
DOCUMENT MAP
==================================================

INDEX.md

Question answered:
Where should I look?

Contains:
Reading order and document responsibilities.

Does not contain:
Project details.

--------------------------------------------------

PROJECT_STATE.md

Question answered:
Where is the project now?

Contains:
Current version, branch, phase, priority, last completed work, blockers, and
immediate next actions.

Does not contain:
Decision history, permanent rules, detailed workflow, or full architecture.

--------------------------------------------------


AUDIT.md

Question answered:
What has been checked, what is broken, and what still requires verification?

Contains:
Audit scope, verified interface chains, Findings with actionable remediation plans,
Architecture Debt with decision lifecycles, broken chains, live-test requirements,
remediation status, and remaining audit work.

Does not contain:
Decision rationale, permanent rules, detailed development procedures, or general
history.

--------------------------------------------------

DECISIONS.md

Question answered:
Why was this approved?

Contains:
Approved concepts, reasons, consequences, status, and affected documents.

Does not contain:
Current task tracking or detailed procedures.

--------------------------------------------------

WORKING_CONVENTIONS.md

Question answered:
Which rules are already settled?

Contains:
Stable identities, engineering principles, runtime safety rules, audit rules,
patch rules, testing rules, Git conventions, and documentation rules.

Does not contain:
Historical narrative or current task status.

--------------------------------------------------

DEVELOPMENT_GUIDE.md

Question answered:
How do we work?

Contains:
Repository layout, installed paths, build flow, patching process, validation,
live testing, staging, commit, push, and audit workflow.

Does not contain:
Reasons for decisions or current project status.

--------------------------------------------------

ARCHITECTURE.md

Question answered:
How is the system built?

Contains:
System components, interfaces, data flow, runtime model, service lifecycle, and
technical boundaries.

Does not contain:
Development history, roadmap, or workflow instructions.

--------------------------------------------------

DEVLOG.md

Question answered:
What was done?

Contains:
Dated development work, fixes, tests, failures, and confirmed results.

Does not contain:
Permanent rules or future requirements.

--------------------------------------------------

ROADMAP.md

Question answered:
What should be done next?

Contains:
Ordered implementation stages and completion status.

Does not contain:
Detailed history or architectural explanation.

--------------------------------------------------

REQUIREMENTS.md

Question answered:
What must the product do?

Contains:
Approved functional and non-functional product requirements.

Does not contain:
Implementation details or development history.

--------------------------------------------------

README.md

Question answered:
What is this project for a user or visitor?

Contains:
Public project overview, capabilities, installation status, and links.

Does not contain:
Complete internal engineering memory.

--------------------------------------------------

CHANGELOG.md

Question answered:
What changed between releases?

Contains:
Release-oriented changes.

Does not contain:
Full development history or internal decision rationale.

==================================================
SINGLE-RESPONSIBILITY RULE
==================================================

Each document answers one primary question.

When information appears in the wrong document:

1. Identify the question it answers.
2. Move it to the corresponding document.
3. Avoid unnecessary duplication.
4. Keep only a short cross-reference when useful.

==================================================
DOCUMENT ROLE REQUIREMENT
==================================================

Every internal engineering memory document begins with a DOCUMENT ROLE block.

The block must state:

Question answered
Purpose
Updated when
Read after
Do not store here

==================================================
SYNCHRONIZATION RULE
==================================================

Documentation is part of the project architecture.

A code change or approved concept is complete only after all affected documents
are updated in the same logical commit.

Every approved concept must be recorded in DECISIONS.md and in the applicable
specialist document.

Each audit block is complete only after all affected Engineering Memory documents
are updated, reviewed, and committed. AUDIT.md must contain detailed verification
and remediation plans for every non-OK finding before code changes begin.

==================================================
CURRENT DOCUMENT STATUS
==================================================

Present:

INDEX.md
PROJECT_STATE.md
AUDIT.md
DECISIONS.md
WORKING_CONVENTIONS.md
DEVELOPMENT_GUIDE.md
ARCHITECTURE.md
DEVLOG.md
ROADMAP.md
REQUIREMENTS.md
README.md
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
NOTICE

All required Engineering Memory documents are present.

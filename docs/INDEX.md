# os-zapret2-restyle — Engineering Memory Index

==================================================
DOCUMENT ROLE
==================================================

Question answered:
Where should I look first, and which document controls a subject?

Purpose:
Define a risk-based context-recovery order and specialist authority without forcing a
complete reread of the repository for every small task.

==================================================
DEFAULT READING ORDER
==================================================

For every new or resumed project task:

1. repository-root `AGENTS.md`;
2. `docs/INDEX.md`;
3. `docs/PROJECT_STATE.md`;
4. the specialist documents that directly govern the requested scope.

Additional reading by task type:

- code or runtime change: applicable sections of `WORKING_CONVENTIONS.md`,
  `DEVELOPMENT_GUIDE.md`, architecture, requirements, audit, and tests;
- audit: the relevant audit register, architecture, requirements, and decisions;
- GitHub mutation: `docs/GITHUB_PUBLICATION.md` and the active GitHub decisions;
- release: release workflow, release gate, current state, changelog, and release records;
- repository-wide audit or genuine lost-context recovery: complete Engineering Memory.

Do not treat a complete reread of every large historical file as a blocking prerequisite
for a small diagnosis, focused edit, or routine GitHub status action.

==================================================
DOCUMENT MAP
==================================================

`PROJECT_STATE.md`
Current version, verified baseline, active work, blockers, and next action.

`AUDIT.md` and `docs/audit/`
Confirmed findings, evidence, impact, remediation, and verification state.

`docs/audit/AUDIT-2026-08-05-STRATEGY-LAB-HARDENING.md`
Audit-to-patch traceability for Strategy Lab hardening revisions 25 onward.

`DECISIONS.md` and `docs/decisions/`
Approved engineering decisions and their supersession history.

`docs/decisions/DEC-2026-08-05-strategy-lab-hardening-series.md`
Active Strategy Lab hardening product contract. Its former serial-publication wording is
superseded by the active GitHub delivery decisions.

`WORKING_CONVENTIONS.md`
Stable engineering and operational conventions.

`DEVELOPMENT_GUIDE.md`
Repeatable implementation and validation workflow.

`ARCHITECTURE.md` and `docs/architecture/`
Product and runtime architecture.

`docs/architecture/STRATEGY_LAB_CORRECTIVE_CONTRACT.md`
Current Strategy Lab behavioral authority.

`docs/architecture/STRATEGY_LAB_ACTIVATION.md`
Active Diagnostics path and the delivery-authority override for older Strategy Lab plans.

`docs/architecture/STRATEGY_LAB_PROFILE_OUTPUT.md`
Complete Traffic Strategy profile construction and exact replay-verification contract.

`docs/architecture/STRATEGY_LAB_UNIFIED_SHORTLIST.md`
Deterministic multi-protocol result and TLS 1.3 circular-boundary contract.

`docs/architecture/STRATEGY_LAB_UDP_INPUT.md`
Validated extended-mode UDP port/payload request, private job-local storage, and cleanup
contract.

`docs/architecture/STRATEGY_LAB_CIRCULAR_ISOLATION.md`
Immutable parent-result snapshots and independent circular session state, runtime, and
restoration evidence.

`docs/architecture/STRATEGY_LAB_CIRCULAR_OWNERSHIP.md`
Dedicated circular launcher serialization, PID-plus-start-token ownership, stale-session
cleanup, semantic restoration, and retry blocking.

`DEVLOG.md` and `docs/devlog/`
Completed work and verification evidence.

`ROADMAP.md`
Ordered product work and gates.

`REQUIREMENTS.md`
Approved product requirements.

`GITHUB_WORKFLOW.md`
Compact stable summary of normal GitHub work.

`GITHUB_PUBLICATION.md`
Final authority for branches, PRs, checks, repairs, title and commit-subject identity,
merge, cleanup, patch/release boundaries, transport selection, and concurrency.

`CHANGELOG.md`, `docs/releases/`, and `docs/patches/`
Published changes and historical patch/release records.

==================================================
PRECEDENCE
==================================================

1. The project owner's explicit current instruction defines scope and exact release
   authority.
2. Repository-root `AGENTS.md` defines blocking safety and entry rules.
3. This index defines specialist ownership and reading scope.
4. The relevant active specialist document controls its subject.
5. A later approved decision explicitly marked active supersedes earlier conflicting
   decisions and historical plans.
6. Historical audit, devlog, patch, release, or architecture-delivery records remain
   evidence but do not override current behavior or process.

For GitHub delivery, the authority order is:

1. current owner instruction;
2. `AGENTS.md`;
3. `docs/GITHUB_PUBLICATION.md`;
4. `docs/decisions/DEC-2026-08-05-universal-versioned-github-titles.md` for PR and commit
   subject identity;
5. `docs/decisions/DEC-2026-08-05-efficient-github-delivery.md` for branch, PR, CI, repair,
   merge, and cleanup mechanics;
6. other general or historical documents.

This GitHub authority explicitly supersedes conflicting wording in older sections of
`WORKING_CONVENTIONS.md`, `DEVELOPMENT_GUIDE.md`, `STRATEGY_LAB.md`, patch records, and
prior atomic/serial publication decisions. Such text must not be used to require:

- exactly one work commit inside a PR branch;
- exactly one workflow run;
- closing a valid PR after an ordinary same-scope CI failure;
- waiting idly for CI before independent analysis or preparation;
- a low-level blobs/tree API sequence when another safe transport is available;
- Draft → Ready as a mandatory normal path;
- branch-cleanup success as proof that code delivery itself succeeded.

No active or historical text may be used to permit an unversioned project-delivery title.
Every PR title, PR-branch commit subject, and final squash subject must begin with the
exact current package-candidate prefix.

Never infer current state only from chat history or a historical record. Re-read current
`main`, current PR state, and the applicable specialist authority.

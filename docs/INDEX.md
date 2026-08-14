# os-zapret2-restyle — Engineering memory index

**Status:** NAVIGATION / INTEGRITY MAP · NOT A CURRENT-STATE NARRATIVE
**Updated:** 2026-08-14

This file answers only: **where should I look?** Its role is defined by `DOC-019`–`DOC-020`.

## Level 1 — mandatory cold start

Read completely in this order (`DOC-016`):

1. [`../AGENTS.md`](../AGENTS.md)
2. [`START_HERE.md`](START_HERE.md)
3. [`PROJECT_STATE.md`](PROJECT_STATE.md)
4. [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md) — `DOC-*`
5. [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md) — `DEV-*`
6. [`CHAT_RULES.md`](CHAT_RULES.md) — `CHAT-*`
7. [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md) — `GH-*`
8. [`ROADMAP.md`](ROADMAP.md)
9. this `INDEX.md`
10. only current-task specialist documents selected by `START_HERE.md`

## Level 2 — current line and specialist detail

- **[`v0.4.x working ledger`](history/current/v0.4.x.md)** — richer current-line chronology and proof links.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) / [`architecture/`](architecture/) — current technical architecture and subsystem contracts.
- [`REQUIREMENTS.md`](REQUIREMENTS.md) — product requirements.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor entry points and local check examples.
- [`USER_GUIDE_STRATEGY_LAB.md`](USER_GUIDE_STRATEGY_LAB.md) — user-facing Strategy Lab guide.
- [`SECURITY.md`](SECURITY.md) — security reporting/reference.

The former duplicate quick-reference files `GITHUB_WORKFLOW.md`, `DEVELOPMENT_GUIDE.md`, and `WORKING_CONVENTIONS.md` were removed after their useful current meaning was migrated to the canonical homes above. They are not navigation targets or current authority.

## Level 3 — completed version-line archives

- **[`v0.1.x archive`](history/archive/v0.1.x.md)**
- **[`v0.2.x archive`](history/archive/v0.2.x.md)**
- **[`v0.3.x archive`](history/archive/v0.3.x.md)**

`v0.4.x` remains current. Archive mechanics are owned by `DOC-026`–`DOC-030`; version authority is owned by `DEV-029`–`DEV-038`.

## Level 3 — deep history, decisions, audits, and proof

- [`DECISIONS.md`](DECISIONS.md) / [`decisions/`](decisions/)
- [`AUDIT.md`](AUDIT.md) / [`audit/`](audit/)
- [`DEVLOG.md`](DEVLOG.md) / [`devlog/`](devlog/)
- [`patches/`](patches/)
- [`verification/`](verification/)
- [`verification/evidence/`](verification/evidence/)
- [`releases/`](releases/)
- [`CHANGELOG.md`](CHANGELOG.md)

These stores preserve original chronology, rationale, and evidence. Historical statements remain historical and do not become a fifth source of current general rules (`DOC-004`–`DOC-005`). Legacy formatting in these deep records may also remain historical under `DOC-046`.

## User and repository front door

- [`README.md`](../README.md)
- [`LICENSE`](../LICENSE)
- [`NOTICE`](../NOTICE)

## Integrity contract

A documentation change must not strand a current authority, active specialist, completed version-line archive, or deep record store outside this map. Rule-reference integrity is independently protected by the four in-file registries and CI (`DOC-042`–`DOC-045`). Local Markdown file/directory links and Markdown heading fragments are independently protected by `DOC-053` and CI. `PROJECT_STATE.md` independently retains direct completed-archive links (`DOC-029`).

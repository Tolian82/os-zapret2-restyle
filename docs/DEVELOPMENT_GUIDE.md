# os-zapret2-restyle — Development guide

Status: **NONCANONICAL PROCESS MAP**
Updated: 2026-08-14

This file is a practical map. Normative rules live only in the four canonical rule books:

- `DOCUMENTATION_RULES.md` (`DOC-*`)
- `PROJECT_PRINCIPLES.md` (`DEV-*`)
- `CHAT_RULES.md` (`CHAT-*`)
- `GITHUB_PUBLICATION.md` (`GH-*`)

Current revision: [`START_HERE.md`](START_HERE.md). Current facts: [`PROJECT_STATE.md`](PROJECT_STATE.md). Master plan: [`ROADMAP.md`](ROADMAP.md).

## Practical development sequence

1. **Recover context.** Follow the Level-1 route in `AGENTS.md` / `DOC-015`–`DOC-018`; then read only current-task specialists from `START_HERE.md`.
2. **Establish exact repository baseline.** Apply `GH-004`–`GH-009`.
3. **Define one logical engineering scope.** Apply `DEV-007`–`DEV-019` and `GH-010`–`GH-015`.
4. **Apply package/version identity.** Use `DEV-027`–`DEV-040`; do not redefine version semantics here.
5. **Implement the smallest sufficient change.** Preserve required behavior and runtime safety under `DEV-020`–`DEV-026`.
6. **Validate from exact evidence.** Apply `DEV-011`–`DEV-016` and `GH-016`–`GH-023`.
7. **Reconcile documentation.** Apply `DOC-036`–`DOC-041`; update only bounded documents whose facts/contracts actually changed.
8. **Deliver through GitHub.** Apply `GH-024`–`GH-033` for PR/merge/hygiene and `GH-034` onward when package/release publication is in scope.
9. **Use owner-assisted live testing only when the current risk gate requires it.** Apply `DEV-041`–`DEV-045` and `CHAT-021`.

## Technical reading routes

- Runtime/plugin architecture: `ARCHITECTURE.md`, `architecture/ZAPRET2_SERVICE.md`.
- Strategy Lab: `architecture/STRATEGY_LAB.md` plus the current specialist file named by `START_HERE.md`.
- Product requirements: `REQUIREMENTS.md`.
- Current line chronology and accepted measurements: `history/current/v0.4.x.md`.
- Historical rationale/proof: use `INDEX.md` to reach decisions, audits, devlogs, patches, verification, and releases.

## Current owner-console boundary

Owner-facing command presentation follows `CHAT-019`–`CHAT-020`: root `csh` by default, explicit `sh`/`/bin/sh` only when POSIX syntax is required.

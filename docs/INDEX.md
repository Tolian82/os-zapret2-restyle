# os-zapret2-restyle — Engineering Memory Index

Status: **NAVIGATION ONLY — NOT A CURRENT-STATE NARRATIVE**

This file answers only: **where should I look?**
Do not load every linked document during startup.

## Level 1 — always read

1. [`../AGENTS.md`](../AGENTS.md)
2. [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
3. [`START_HERE.md`](START_HERE.md)
4. [`PROJECT_STATE.md`](PROJECT_STATE.md)
5. only the current-task specialist documents named by `START_HERE.md`

## Level 2 — current version line / task-selected detail

Current line (same second numeric component, the `4` in `0.4.x`):

- **[`v0.4.x working ledger`](history/current/v0.4.x.md)** — richer current-line chronology,
  decisions/evidence links and handoff detail; read only when the current task needs more than Level 1.

Current technical authorities:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/`](architecture/)
- [`ROADMAP.md`](ROADMAP.md)
- [`DEVELOPMENT_GUIDE.md`](DEVELOPMENT_GUIDE.md)
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- [`WORKING_CONVENTIONS.md`](WORKING_CONVENTIONS.md)

## Level 3 — completed version-line archives

These are compact maps, not replacements for original records:

- **[`v0.1.x archive`](history/archive/v0.1.x.md)**
- **[`v0.2.x archive`](history/archive/v0.2.x.md)**
- **[`v0.3.x archive`](history/archive/v0.3.x.md)**

`v0.4.x` is current and therefore is **not** archived yet. Only after the owner explicitly authorizes
a change of the second numeric component from `4` to `5` (`v0.4.x -> v0.5.x`), the same full-release
change finalizes `history/archive/v0.4.x.md`, creates `history/current/v0.5.x.md`, updates this index and
performs the required README/full-release procedure. A full release can occur without changing the
second numeric component.

## Level 3 — deep chronology / evidence

Open only when exact old chronology, rationale, audit finding or proof is needed:

- [`DECISIONS.md`](DECISIONS.md) / [`decisions/`](decisions/)
- [`AUDIT.md`](AUDIT.md) / [`audit/`](audit/)
- [`DEVLOG.md`](DEVLOG.md) / [`devlog/`](devlog/)
- [`patches/`](patches/)
- [`verification/`](verification/)
- [`verification/evidence/`](verification/evidence/)
- [`releases/`](releases/)

Archive maps link back into these stores. **Archiving never deletes, rewrites or folds away original
records.** Git history and published release history remain intact.

## Reading rule

Default cold start:

`principles -> compact handoff/state -> short lifetime path -> exact current task -> only needed architecture`

Escalate to the current-line ledger only when richer `v0.4.x` context is needed. Escalate to archives
or deep records only for a concrete historical dependency, investigation or proof request.

This read-set discipline is the project's memory-economy mechanism: preserve complete engineering
history while avoiding repeated loading of history that cannot affect the current task.

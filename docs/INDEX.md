# os-zapret2-restyle — Engineering Memory Index

Status: **NAVIGATION / INTEGRITY MAP — NOT A CURRENT-STATE NARRATIVE**

This file answers only: **where should I look?** Do not load every linked document during startup.

## Level 1 — always read

1. [`../AGENTS.md`](../AGENTS.md)
2. [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md)
3. [`DOCUMENTATION_RULES.md`](DOCUMENTATION_RULES.md)
4. [`START_HERE.md`](START_HERE.md)
5. [`PROJECT_STATE.md`](PROJECT_STATE.md)
6. only the current-task specialist documents named by `START_HERE.md`

Always-available plan/navigation links:

- [`ROADMAP.md`](ROADMAP.md) — concise master development plan
- this `INDEX.md` — integrity/navigation map

## Level 2 — current second-component line / task-selected detail

Current line (same second numeric component, the `4` in `0.4.x`):

- **[`v0.4.x working ledger`](history/current/v0.4.x.md)** — richer current-line chronology,
  decisions/proof links and handoff detail; read only when the task needs more than Level 1.

Current technical/procedural authorities:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`architecture/`](architecture/)
- [`DEVELOPMENT_GUIDE.md`](DEVELOPMENT_GUIDE.md)
- [`GITHUB_PUBLICATION.md`](GITHUB_PUBLICATION.md)
- [`GITHUB_WORKFLOW.md`](GITHUB_WORKFLOW.md)
- [`WORKING_CONVENTIONS.md`](WORKING_CONVENTIONS.md)

## Level 3 — completed second-component archives

These files are compact archive maps. Starting with the eventual `v0.4.x` archive, each new archive
also preserves the final `PROJECT_STATE` snapshot for that completed line. Older lines are not
retroactively rewritten into the new snapshot format.

- **[`v0.1.x archive`](history/archive/v0.1.x.md)** — legacy compact map
- **[`v0.2.x archive`](history/archive/v0.2.x.md)** — legacy compact map
- **[`v0.3.x archive`](history/archive/v0.3.x.md)** — legacy compact map

`v0.4.x` is current and is not archived yet. Only an explicitly owner-authorized change of the second
numeric component (`v0.4.x -> v0.5.x`) closes it. That same full-release change preserves the final
`PROJECT_STATE` in `history/archive/v0.4.x.md`, initializes `history/current/v0.5.x.md`, rewrites the
current `PROJECT_STATE` for `v0.5.x`, updates this index and performs the required README/release work.

## Level 3 — deep action history, decisions and proof

Open only when exact chronology, rationale, audit finding or proof is needed:

- [`DECISIONS.md`](DECISIONS.md) / [`decisions/`](decisions/)
- [`AUDIT.md`](AUDIT.md) / [`audit/`](audit/)
- [`DEVLOG.md`](DEVLOG.md) / [`devlog/`](devlog/)
- [`patches/`](patches/)
- [`verification/`](verification/)
- [`verification/evidence/`](verification/evidence/)
- [`releases/`](releases/)

Archive maps link back into these stores. **Archiving never deletes, rewrites or folds away original
records.** Git history and published release history remain intact.

## Integrity rule

A documentation change is incomplete when a current authority, archive route or deep-record store
becomes unreachable from this map. `PROJECT_STATE` separately carries direct links to every completed
second-component archive so current state and global navigation independently expose the archive chain.

## Reading rule

Default cold start:

`AGENTS -> PROJECT_PRINCIPLES -> DOCUMENTATION_RULES -> START_HERE -> PROJECT_STATE -> current-task specialists`

Use `ROADMAP` for the concise whole-project plan. Escalate to the current `v0.4.x` ledger only when
richer current-line context is needed. Escalate to archives or deep records only for a concrete
historical dependency, investigation, rationale or proof request.

This read-set discipline preserves complete engineering memory while avoiding repeated loading of
history that cannot affect the current task.

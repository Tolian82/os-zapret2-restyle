# 2026-08-07 — Strategy Lab Python migration handoff

==================================================
DOCUMENT ROLE
==================================================

Question answered:
What was completed at the transition from shell-era Strategy Lab debugging to the approved Python migration?

Purpose:
Record the final `v0.3.3_17` live result, the migration decision, documentation synchronization, and the exact next work unit.

==================================================
COMPLETED
==================================================

- Owner installed and tested testing prerelease `v0.3.3_17` against `rutracker.org` in Standard mode.
- Job `job.w0nXxQ` again passed stages 00–40, failed stage 50 with `Temporary candidate runtime failed internally.`, skipped stages 60–85, passed stage 90 restoration, and ended stage 99 as ERROR.
- The same run reconfirmed immediate visible `Статус: ОШИБКА`, `Strategy Lab returned no output.`, and 0% progress while the job was active, followed by a direct jump to 100% at terminal result.
- No `_17` candidate-runtime log bundle was collected, so the new Stage-50 root cause is deliberately left unclaimed.
- The owner approved a change in implementation direction: migrate appropriate Strategy Lab orchestration from large sourced POSIX shell to Python instead of continuing an open-ended shell-only defect chase.
- PHP remains the OPNsense MVC/API boundary; shell remains only for small explicit FreeBSD/OPNsense lifecycle/system adapters where appropriate.
- The existing bug backlog is preserved and must be re-qualified after migration rather than assumed fixed by rewrite.
- Stable release and pkg-repository promotion remain blocked on live verification.

==================================================
DOCUMENTS ADDED
==================================================

- `docs/decisions/DEC-2026-08-07-strategy-lab-python-orchestration.md`
- `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`
- `docs/verification/evidence/2026-08-07-v0.3.3_17-scenario-01-python-handoff.md`

==================================================
NEXT WORK UNIT
==================================================

Begin a fresh development topic from current `main` and perform only Migration Patch 1 from `docs/architecture/STRATEGY_LAB_PYTHON_MIGRATION.md`:

- verify the supported OPNsense Python interpreter path/version and dependency model;
- add the minimal packaged Python foundation and compatibility launcher;
- add deterministic CI/package coverage;
- do not change Strategy Lab product behavior in that first patch;
- do not resume speculative Stage-50 shell patching unless required for service safety.

The first packaged migration patch must follow the normal branch/Ready-PR/CI/squash flow and FreeBSD 15 package build. Testing-prerelease publication follows the owner's existing installable-patch authority without another routine confirmation.

# os-zapret2-restyle agent preflight

These instructions apply to the complete repository.

Before any substantive project diagnosis, recommendation, command, file change, GitHub action, build, or publication:

1. Read `docs/INDEX.md` completely.
2. Read every document in its mandatory order completely.
3. Before any GitHub mutation, additionally read `docs/GITHUB_PUBLICATION.md` completely.
4. Read the relevant source files and record the exact current GitHub `main` commit.

This is a blocking preflight. Chat context, memory, summaries, and partial searches do not replace it.

The permanent development and publication sequence is:

`one logical change -> one ready branch -> one atomic commit -> one pull request -> one complete check set -> one squash merge -> one build -> one focused verification`

GitHub rules:

- Prepare the complete code, tests, documentation, and file modes before publishing the branch.
- Create the ready branch directly at one atomic commit whose sole parent is the recorded current `main` commit.
- Never stream intermediate files or commits into a pull-request branch.
- Never modify the pull-request branch while checks are queued or running.
- When a delivery cycle fails, close it, prepare the correction outside the pull request, and replace it with a new clean branch, commit, and pull request.
- Temporary workflows, encoded patches, patch fragments, self-modifying Actions, delivery-only files, repeated check retriggers, repair commits, and force-push repair are prohibited as delivery mechanisms.
- The pull-request title must begin with the exact package candidate derived from `VERSION` and `PLUGIN_REVISION`. Example: `v0.2.8_4: Add GUI Zapret2 service and release management`.
- A branch that changes `PLUGIN_REVISION` must use the new revision in its pull-request title.
- Final integration is a squash merge only after the complete check set passes.
- Update every affected Engineering Memory document in the same logical commit.
- Never claim a check, build, publication, or live test that was not actually completed.

For OPNsense console commands, target the default root `csh`; enter `sh` explicitly before POSIX-only syntax and run `exit` afterward.

Current owner instructions override documentation. Synchronize affected documentation in the same logical change.

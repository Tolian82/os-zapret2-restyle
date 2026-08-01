# os-zapret2-restyle agent preflight

These instructions apply to the complete repository.

Before any substantive project diagnosis, recommendation, command, file change,
GitHub action, build, or publication:

1. Read `docs/INDEX.md` completely.
2. Read every document in its mandatory order completely. Do not replace this with
   chat context, memory, a summary, or a partial search.
3. Pay particular attention to the approved methodology and principles in
   `docs/DECISIONS.md`, `docs/WORKING_CONVENTIONS.md`, and
   `docs/DEVELOPMENT_GUIDE.md` before choosing how to work.
4. Read the relevant source files and establish the exact current GitHub `main`
   commit before changing repository state.

This is a blocking preflight. Before it finishes, a progress message may say only
that documentation recovery is in progress; it must not contain technical advice
or commands.

After the preflight:

- follow `one logical change -> one atomic commit -> one build -> one focused
  verification`;
- update every affected Engineering Memory document in the same logical commit;
- write OPNsense console commands for root `csh`; enter `sh` explicitly and later
  run `exit` when POSIX-only syntax is unavoidable;
- use the standing publication and release authority exactly as defined in
  `docs/GITHUB_WORKFLOW.md`; do not repeat settled questions;
- never claim a check, build, publication, or live test that was not actually
  completed.

If an active owner instruction conflicts with the documentation, follow the active
instruction and synchronize the affected documentation in the same logical change.

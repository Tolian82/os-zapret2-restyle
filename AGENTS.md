# AGENTS.md

This repository has a mandatory documentation preflight.

Before any project diagnosis, command, file change, GitHub mutation, or release action:

1. Read `docs/INDEX.md`.
2. Complete its mandatory Engineering Memory reading order.
3. Read `docs/GITHUB_PUBLICATION.md` immediately before any GitHub mutation.
4. Treat the current project-owner instruction as the highest scope boundary.
5. Do not substitute chat history, memory, or summaries for repository documents.

==================================================
BLOCKING GITHUB RULES
==================================================

The default publication sequence is:

one logical change
        ↓
all blobs and one tree
        ↓
one atomic commit with no remote branch yet
        ↓
exactly one remote task branch created at that final commit
        ↓
one ready pull request
        ↓
one complete check set
        ↓
one squash merge
        ↓
automatic branch cleanup and verification

- Exactly one remote task branch may be created for one logical delivery cycle.
- Branch creation is the last preparation step. Do not create a remote branch before
  all final blobs, the tree, the atomic commit, validation, title, and cleanup path are
  ready.
- Do not create preparatory or replacement remote branches with suffixes such as
  `-clean`, `-final`, `-atomic`, `-fixed`, `-retry`, or `-publish`.
- Before branch creation, verify the exact branch name is absent and that merged-branch
  cleanup is available through repository automation or the selected authenticated
  transport.
- Multi-file GitHub/API delivery must use all blobs, one tree, and one commit.
  Sequential contents-API commits are prohibited.
- Open the pull request only when the final branch is ready. Do not use Draft → Ready
  as the normal path.
- Compute the exact pull-request title before opening it:
  `v<VERSION>_<PLUGIN_REVISION>: <logical change>` when the revision is non-zero.
- Leave the pull-request branch unchanged while checks run.
- After merge, verify both `main` and absence of the task branch.
- If a cycle fails after branch publication, close the PR, delete that branch, verify
  its absence, and only then begin one replacement cycle.

==================================================
PATCH AND RELEASE BOUNDARY
==================================================

A package patch and a project release are different operations.

- A request for patch `vX.Y.Z_N` keeps `VERSION=X.Y.Z`, sets
  `PLUGIN_REVISION=N`, uses the ordinary PR/squash cycle, and creates no tag,
  GitHub Release, release assets, or pkg-repository publication.
- A project release changes `VERSION` and requires explicit owner authorization for
  that exact version.
- Ambiguous phrases such as “continue”, “do it”, or “let’s do this” do not authorize a
  release by themselves.
- Never choose a new project version independently.
- Published tags, releases, assets, and versions are immutable and forward-only.

==================================================
OPNSENSE COMMAND RULE
==================================================

OPNsense console commands target the default root `csh` shell. POSIX-only syntax must
be enclosed by an explicit standalone `sh` command and a matching standalone `exit`.

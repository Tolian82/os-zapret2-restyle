# AGENTS.md

This repository has a mandatory documentation preflight.

Before any project diagnosis, command, file change, GitHub mutation, or release action:

1. Read `docs/INDEX.md`.
2. Complete its mandatory Engineering Memory reading order.
3. Read `docs/GITHUB_PUBLICATION.md` immediately before any GitHub mutation.
4. Treat the current project-owner instruction as the highest scope boundary.
5. Do not substitute chat history, memory, or summaries for the repository documents.

==================================================
BLOCKING GITHUB RULES
==================================================

The default publication sequence is:

one logical change
        ↓
one atomic commit
        ↓
one ready pull request
        ↓
one complete check set
        ↓
one squash merge
        ↓
verify `main`

- Do not use Draft → Ready as the normal path. Open the pull request only when the
  complete final branch is ready for its single check set.
- Multi-file GitHub/API delivery must create all blobs, one tree, and one commit.
  Sequential contents-API commits are prohibited.
- Read every workflow triggered by the planned event before creating the pull request.
- Compute the exact pull-request title before opening it:
  `v<VERSION>_<PLUGIN_REVISION>: <logical change>` when the revision is non-zero.
- A release pull-request title and its squash subject are different protocol fields.
  The release squash subject is exactly `release: prepare v<VERSION>`.
- Leave the pull-request branch unchanged while checks run.
- If a delivery cycle fails, wait for the complete result, diagnose once, close the
  failed pull request, and replace it with a new clean branch and pull request.
  Do not add repair commits, repeatedly retrigger checks, or force-push.

==================================================
BLOCKING RELEASE RULES
==================================================

- Ambiguous phrases such as “continue”, “do it”, or “let’s do this” do not authorize a
  release by themselves.
- Release authority requires an explicit project-owner request naming the version or
  unambiguously referring to an already approved version.
- Never choose a new project version independently.
- Published tags, releases, and package versions are immutable. Do not move tags,
  replace published assets, roll back `VERSION`, or reuse an earlier version.
  A later release always advances the version line.
- Do not pass a mandatory live-verification gate unless the evidence is recorded or the
  project owner explicitly states that the verification was completed successfully.
- Before giving package installation commands, verify the release workflow, tag,
  package asset, checksum, Pages deployment, and exact pkg-repository version.

==================================================
OPNSENSE COMMAND RULE
==================================================

OPNsense console commands target the default root `csh` shell. POSIX-only syntax must
be enclosed by an explicit standalone `sh` command and a matching standalone `exit`.

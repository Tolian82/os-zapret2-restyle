# Decision — Repository artifact and authority hygiene

Date: 2026-08-05
Status: accepted

## Decision

The authoritative repository must not track editor backups, merge rejects, ad-hoc patch
or transport fragments, encoded payload carriers, or local backup files. CI enforces a
closed forbidden-suffix list through `scripts/test-repository-hygiene.sh`, and
`.gitignore` prevents routine reintroduction.

Historical engineering records remain valid evidence. When an old record contains
statements that could be mistaken for current product behavior, it must carry an
explicit historical/superseded banner and point to the current specialist authority.

Remote branch steady state is `main` plus the separately preserved `recovery/base`.
Temporary development and release branches are deleted after their work is superseded
or squash merged. No history rewrite or force push is permitted.

## Reason

Tracked backups and transport fragments create competing document authority and can be
accidentally packaged, reviewed, or reused. Large collections of superseded branches
also obscure the current source baseline. A permanent mechanical gate is more reliable
than periodic manual cleanup.

## Consequences

- `docs/PROJECT_STATE.md.orig` is removed;
- obsolete remote branches are removed while `recovery/base` is retained;
- CI rejects forbidden tracked artifacts;
- current Strategy Lab authority is explicit;
- package metadata remains `VERSION=0.3.2`, `PLUGIN_REVISION=24` because this is a repository-governance change outside package contents.
